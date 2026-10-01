"""Bake the finished asset's materials into glTF textures, so every shader reaches Godot.

A generator may give its parts any Cycles material: Poly Haven, ambientCG or cgbookcase texture
sets, procedural textures (Noise, Voronoi, Wave, Gradient, colour ramps), layered mixes driven by
masks (ambient occlusion, pointiness, attributes, noise), bump and normal maps, Mix Shader
blends. glTF carries none of that node logic, so the final build bakes it:

- one non-overlapping UV atlas (``Atlas``) for the whole joined asset;
- per channel, each material's shaders are swapped for emission of that channel (a Principled
  BSDF's Base Color, Roughness, Metallic, Alpha, Emission), keeping every mix, mask and texture
  in between, and Cycles bakes it into the atlas: what a Mix Shader blends, the bake blends too;
- the tangent-space normal (normal maps, bump nodes, the mesh's own shading) and ambient
  occlusion are baked as they render;
- the textures become one glTF material: base colour (+ alpha), ORM (occlusion, roughness,
  metallic), normal and, when anything glows, emission.

Materials marked ``mat["keep"] = True`` (glass, say, whose transmission glTF carries itself) keep
their faces and are not baked.
"""
from __future__ import annotations

import time
from pathlib import Path

import bmesh
import bpy
import numpy as np

ATLAS_UV = "Atlas"
AO_SAMPLES = 32
ANGLE_LIMIT_DEG = 66.0
GAP_SHARE = 1 / 128  # gap between islands, of the atlas side (8 px at 1024, 16 px at 2048)

# Per shader node type: which input feeds each baked channel (None = the constant in CONSTANTS).
CHANNEL_INPUTS = {
    "BSDF_PRINCIPLED": {"base_color": "Base Color", "roughness": "Roughness", "metallic": "Metallic",
                        "alpha": "Alpha", "emission": ("Emission Color", "Emission Strength")},
    "BSDF_DIFFUSE": {"base_color": "Color", "roughness": None, "metallic": None, "alpha": None, "emission": None},
    "BSDF_GLOSSY": {"base_color": "Color", "roughness": "Roughness", "metallic": None, "alpha": None,
                    "emission": None},
    "BSDF_METALLIC": {"base_color": "Base Color", "roughness": "Roughness", "metallic": None, "alpha": None,
                      "emission": None},
    "BSDF_TRANSLUCENT": {"base_color": "Color", "roughness": None, "metallic": None, "alpha": None,
                         "emission": None},
    "SUBSURFACE_SCATTERING": {"base_color": "Color", "roughness": None, "metallic": None, "alpha": None,
                              "emission": None},
    "BSDF_SHEEN": {"base_color": "Color", "roughness": None, "metallic": None, "alpha": None, "emission": None},
    "EMISSION": {"base_color": None, "roughness": None, "metallic": None, "alpha": None,
                 "emission": ("Color", "Strength")},
    "BSDF_TRANSPARENT": {"base_color": None, "roughness": None, "metallic": None, "alpha": None,
                         "emission": None},
}
# The value a shader without that input contributes.
CONSTANTS = {
    "base_color": {"BSDF_TRANSPARENT": 0.0, "EMISSION": 0.0},
    "roughness": {"BSDF_DIFFUSE": 1.0, "BSDF_TRANSLUCENT": 1.0, "SUBSURFACE_SCATTERING": 1.0,
                  "BSDF_SHEEN": 1.0, "EMISSION": 1.0, "BSDF_TRANSPARENT": 0.0},
    "metallic": {"BSDF_METALLIC": 1.0},
    "alpha": {"BSDF_TRANSPARENT": 0.0},
    "emission": {},
}
DEFAULT_CONSTANT = {"base_color": 0.0, "roughness": 0.5, "metallic": 0.0, "alpha": 1.0, "emission": 0.0}


class BakeError(RuntimeError):
    pass


def _log(message: str) -> None:
    print(f"BAKE {message}", flush=True)


# --------------------------------------------------------------------------------- #
# UV atlas
# --------------------------------------------------------------------------------- #

def _triangulate(obj: bpy.types.Object) -> None:
    """Triangles before the atlas and the bakes, so the tangents Godot computes match the baked normals."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) > 3],
                          quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


XATLAS_MAX_TRIANGLES = 150_000  # above this xatlas takes minutes; Smart UV Project is used instead
XATLAS_FILLS = (0.62, 0.53, 0.45)  # share of the atlas the charts are scaled to; lower when they overflow


def _xatlas_atlas(obj: bpy.types.Object, layer, resolution: int) -> bool:
    """Chart and pack the (triangulated) mesh with xatlas into one square atlas: fewer, larger
    charts than Smart UV Project (fewer seams) at one texel density. False when xatlas is not
    installed or the mesh is too large for it."""
    try:
        import xatlas  # .scratch/blender-pydeps (tools/blender/install_blender_pydeps.sh)
    except ImportError:
        return False
    mesh = obj.data
    if len(mesh.polygons) > XATLAS_MAX_TRIANGLES:
        return False
    vertices = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", vertices)
    faces = np.empty(len(mesh.polygons) * 3, np.int32)
    mesh.polygons.foreach_get("vertices", faces)
    vertices, faces = vertices.reshape(-1, 3), faces.reshape(-1, 3)
    corners = vertices[faces]
    area = float(0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum())
    for fill in XATLAS_FILLS:
        atlas = xatlas.Atlas()
        atlas.add_mesh(vertices, faces.astype(np.uint32))
        options = xatlas.PackOptions()
        options.resolution = resolution
        options.padding = max(2, round(resolution * GAP_SHARE / 2))
        options.bilinear = True
        options.rotate_charts = True
        options.blockAlign = True
        options.texels_per_unit = float(np.sqrt(fill * resolution * resolution / max(area, 1e-9)))
        atlas.generate(xatlas.ChartOptions(), options)
        if atlas.atlas_count == 1:
            break
    else:
        return False
    _, indices, uvs = atlas[0]
    loop_uvs = uvs[indices.reshape(-1)]  # polygon order is kept: loop i of polygon p is corner i of face p
    layer.data.foreach_set("uv", np.ascontiguousarray(loop_uvs, dtype=np.float32).ravel())
    return True


def atlas_unwrap(obj: bpy.types.Object, resolution: int) -> str:
    """Add the ``Atlas`` UV layer: one square atlas at one texel density, from xatlas when it is
    installed, else Smart UV Project and Blender's packer. Returns the method used.

    The existing layer (the materials' texture coordinates) stays the render layer, so every
    texture keeps its mapping while the bake writes into the atlas.
    """
    mesh = obj.data
    render_layer = next((layer for layer in mesh.uv_layers if layer.active_render), None)
    if ATLAS_UV in mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[ATLAS_UV])
    atlas = mesh.uv_layers.new(name=ATLAS_UV)
    if render_layer is not None:
        render_layer.active_render = True
    mesh.uv_layers.active = atlas
    if _xatlas_atlas(obj, atlas, resolution):
        return "xatlas"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=np.radians(ANGLE_LIMIT_DEG), island_margin=GAP_SHARE / 2,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    # Bounding-box packing: instant on the hundreds of islands Smart UV Project makes (the exact-shape
    # packer takes minutes there).
    bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, margin_method="FRACTION",
                            margin=GAP_SHARE / 2, shape_method="AABB")
    bpy.ops.object.mode_set(mode="OBJECT")
    return "smart_project"


# --------------------------------------------------------------------------------- #
# Channel bakes
# --------------------------------------------------------------------------------- #

def _output_node(tree: bpy.types.NodeTree):
    outputs = [node for node in tree.nodes if node.type == "OUTPUT_MATERIAL"]
    for target in ("CYCLES", "ALL"):
        active = [node for node in outputs if node.is_active_output and node.target in (target, "ALL")]
        if active:
            return active[0]
    return outputs[0] if outputs else None


def _feed(tree, target_socket, source_socket, constant):
    """Link ``source_socket``'s upstream (or copy its default value) into ``target_socket``."""
    if source_socket is not None and source_socket.is_linked:
        tree.links.new(source_socket.links[0].from_socket, target_socket)
        return
    value = constant if source_socket is None else source_socket.default_value
    if hasattr(value, "__len__"):
        values = list(value)[:3]
        target_socket.default_value = (*values, 1.0) if len(values) == 3 else (values[0],) * 3 + (1.0,)
    else:
        target_socket.default_value = (float(value),) * 3 + (1.0,)


SHADER_TYPES = set(CHANNEL_INPUTS) | {"HOLDOUT", "VOLUME_ABSORPTION", "VOLUME_SCATTER", "PRINCIPLED_VOLUME",
                                     "BSDF_HAIR", "BSDF_HAIR_PRINCIPLED", "BSDF_TOON", "BSDF_RAY_PORTAL"}


def _has_shaders(tree: bpy.types.NodeTree) -> bool:
    return any(node.type in SHADER_TYPES or node.type.startswith("BSDF_")
               or (node.type == "GROUP" and node.node_tree is not None and _has_shaders(node.node_tree))
               for node in tree.nodes)


def _emit_channel(tree: bpy.types.NodeTree, channel: str, copies: list) -> None:
    """Swap every shader in ``tree`` (and in copies of the node groups that hold shaders) for an
    Emission of its ``channel`` value; mixes, masks and textures in between stay as they are."""
    for node in list(tree.nodes):
        if node.type == "GROUP" and node.node_tree is not None and _has_shaders(node.node_tree):
            group = node.node_tree.copy()
            copies.append(group)
            node.node_tree = group
            _emit_channel(group, channel, copies)
            continue
        if not (node.type in SHADER_TYPES or node.type.startswith("BSDF_")):
            continue
        spec = CHANNEL_INPUTS.get(node.type)
        emission = tree.nodes.new("ShaderNodeEmission")
        emission.location = node.location
        emission.inputs["Strength"].default_value = 1.0
        source = spec.get(channel) if spec else None
        constant = CONSTANTS[channel].get(node.type, DEFAULT_CONSTANT[channel])
        if channel == "emission":
            if source:
                colour_name, strength_name = source
                _feed(tree, emission.inputs["Color"], node.inputs[colour_name], 0.0)
                strength = node.inputs[strength_name]
                if strength.is_linked:
                    tree.links.new(strength.links[0].from_socket, emission.inputs["Strength"])
                else:
                    emission.inputs["Strength"].default_value = strength.default_value
            else:
                emission.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        else:
            _feed(tree, emission.inputs["Color"], node.inputs[source] if source else None, constant)
        for output in node.outputs:
            for link in list(output.links):
                tree.links.new(emission.outputs["Emission"], link.to_socket)
        tree.nodes.remove(node)


def _emission_tree(material: bpy.types.Material, channel: str, copies: list) -> bpy.types.Material:
    """A copy of ``material`` in which every shader emits its ``channel`` value instead; the copies
    of node groups it needed are added to ``copies`` (removed after the bake)."""
    copy = material.copy()
    tree = copy.node_tree
    _emit_channel(tree, channel, copies)
    output = _output_node(tree)
    if output is not None:
        for name in ("Displacement", "Volume"):
            for link in list(output.inputs[name].links):
                tree.links.remove(link)
    return copy


def _mixes_shaders(material: bpy.types.Material) -> bool:
    """Whether ``material`` blends whole shaders (Mix/Add Shader), which bakes to an average."""
    def walk(tree):
        return any(node.type in ("MIX_SHADER", "ADD_SHADER")
                   or (node.type == "GROUP" and node.node_tree is not None and walk(node.node_tree))
                   for node in tree.nodes)
    return walk(material.node_tree)


def _target_node(material: bpy.types.Material, image: bpy.types.Image):
    nodes = material.node_tree.nodes
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    node.label = node.name = "BakeTarget"
    nodes.active = node
    node.select = True
    return node


def _new_image(name: str, resolution: int, colour: bool, alpha: bool = False) -> bpy.types.Image:
    existing = bpy.data.images.get(name)
    if existing is not None:
        bpy.data.images.remove(existing)
    image = bpy.data.images.new(name, resolution, resolution, alpha=alpha, float_buffer=not colour)
    image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    image.generated_color = (0.0, 0.0, 0.0, 1.0)
    return image


def _bake(obj: bpy.types.Object, kind: str, materials: list, image: bpy.types.Image, **options) -> None:
    """Bake ``kind`` into ``image`` (Cycles needs a target image node in every material of the object)."""
    unique = list({material.name: material for material in materials if material is not None}.values())
    for material in unique:
        _target_node(material, image)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        result = bpy.ops.object.bake(type=kind, margin=max(2, round(image.size[0] * GAP_SHARE)), margin_type="EXTEND",
                                     use_clear=True, **options)
    finally:
        for material in unique:
            node = material.node_tree.nodes.get("BakeTarget")
            if node is not None:
                material.node_tree.nodes.remove(node)
    if result != {"FINISHED"}:
        raise BakeError(f"{kind} bake did not finish: {result}")


def _pixels(image: bpy.types.Image) -> np.ndarray:
    data = np.empty(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(data)
    return data.reshape(image.size[1], image.size[0], 4)


def _channel(obj, slots, baked_slots, channel: str, resolution: int, colour: bool) -> np.ndarray:
    """Bake ``channel`` through emission copies of the baked materials; returns RGBA pixels."""
    image = _new_image(f"bake_{channel}", resolution, colour)
    copies, groups = {}, []
    for index in baked_slots:
        material = slots[index]
        if material.name not in copies:
            copies[material.name] = _emission_tree(material, channel, groups)
    try:
        for index in baked_slots:
            obj.material_slots[index].material = copies[slots[index].name]
        kept = [slots[index] for index in range(len(slots)) if index not in baked_slots]
        _bake(obj, "EMIT", list(copies.values()) + kept, image)
        return _pixels(image)
    finally:
        for index, material in enumerate(slots):
            obj.material_slots[index].material = material
        for copy in copies.values():
            bpy.data.materials.remove(copy)
        for group in groups:
            bpy.data.node_groups.remove(group)
        bpy.data.images.remove(image)


def _coverage(obj, slots, resolution: int) -> np.ndarray:
    """Texels inside the atlas islands (a white emission bake without margin)."""
    image = _new_image("bake_coverage", resolution, colour=False)
    marker = bpy.data.materials.new("bake_coverage")
    tree = marker.node_tree
    for node in list(tree.nodes):
        if node.type != "OUTPUT_MATERIAL":
            tree.nodes.remove(node)
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    tree.links.new(emission.outputs["Emission"], _output_node(tree).inputs["Surface"])
    try:
        for index in range(len(slots)):
            obj.material_slots[index].material = marker
        _target_node(marker, image)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type="EMIT", margin=0, use_clear=True)
        return _pixels(image)[..., 0] > 0.5
    finally:
        for index, material in enumerate(slots):
            obj.material_slots[index].material = material
        bpy.data.materials.remove(marker)
        bpy.data.images.remove(image)


def _save(name: str, pixels: np.ndarray, folder: Path, colour: bool) -> bpy.types.Image:
    """Write ``pixels`` (H x W x 4, linear for colour) as ``folder/name.png`` and load it back."""
    height, width = pixels.shape[:2]
    image = bpy.data.images.new(name, width, height, alpha=True, float_buffer=False)
    image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    image.pixels.foreach_set(np.ascontiguousarray(pixels, dtype=np.float32).ravel())
    path = folder / f"{name}.png"
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    image.reload()
    return image


def _ao_distance(obj: bpy.types.Object) -> None:
    """Ambient occlusion reaches a fifth of the asset's size (Cycles reads it from the world)."""
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Bake")
    scene.world.light_settings.distance = max(0.01, 0.2 * max(obj.dimensions))


def _gltf_output_group() -> bpy.types.NodeTree:
    """The node group the glTF exporter reads the occlusion texture from."""
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:
        from io_scene_gltf2.blender.com.material_helpers import create_settings_group
        group = create_settings_group("glTF Material Output")
    return group


def _export_material(name: str, maps: dict[str, bpy.types.Image], emission_strength: float = 1.0) -> bpy.types.Material:
    """One Principled material fed by the baked maps on the atlas UVs (what glTF exports)."""
    material = bpy.data.materials.new(name)
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = ATLAS_UV

    def texture(image):
        node = nodes.new("ShaderNodeTexImage")
        node.image = image
        links.new(uv.outputs["UV"], node.inputs["Vector"])
        return node

    base = texture(maps["base_color"])
    links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    if "alpha" in maps:
        links.new(base.outputs["Alpha"], bsdf.inputs["Alpha"])
        material.surface_render_method = "BLENDED"
    orm = texture(maps["orm"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(orm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    gltf = nodes.new("ShaderNodeGroup")
    gltf.node_tree = _gltf_output_group()
    links.new(split.outputs["Red"], gltf.inputs["Occlusion"])
    normal = texture(maps["normal"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.uv_map = ATLAS_UV
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    if "emission" in maps:
        emission = texture(maps["emission"])
        links.new(emission.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    material.use_backface_culling = True  # otherwise glTF marks it double-sided and Godot stops culling
    material["baked"] = True
    return material


def _one_material(obj: bpy.types.Object, slots: list, baked_slots: set, export: bpy.types.Material) -> None:
    """Every baked face gets the one export material (one surface, one draw call in Godot); kept
    materials stay, after it."""
    kept = [index for index in range(len(slots)) if index not in baked_slots]
    remap = {index: 0 for index in baked_slots}
    remap.update({index: position + 1 for position, index in enumerate(kept)})
    mesh = obj.data
    indices = np.empty(len(mesh.polygons), np.int32)
    mesh.polygons.foreach_get("material_index", indices)
    indices = np.vectorize(lambda value: remap.get(int(value), 0), otypes=[np.int32])(indices) if len(indices) else indices
    mesh.materials.clear()
    mesh.materials.append(export)
    for index in kept:
        mesh.materials.append(slots[index])
    mesh.polygons.foreach_set("material_index", indices)
    mesh.update()


def bake_asset(obj: bpy.types.Object, folder: Path, resolution: int, ao: bool = True,
               ao_samples: int = AO_SAMPLES, threads: int = 2) -> dict:
    """Bake every material of ``obj`` (the joined asset) into textures in ``folder`` and give the
    baked faces one glTF material; returns a report for the build record."""
    started = time.time()
    folder.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = threads
    slots = [slot.material for slot in obj.material_slots]
    if not slots:
        raise BakeError(f"{obj.name} has no materials to bake: give every part a material")
    baked_slots = {index for index, material in enumerate(slots) if material and not material.get("keep")}
    if not baked_slots:
        return {"baked": False, "reason": "every material is marked keep"}
    averaged = sorted({slots[index].name for index in baked_slots if _mixes_shaders(slots[index])})
    if averaged:
        _log(f"note: {', '.join(averaged)} blend whole shaders (Mix/Add Shader); the bake averages their "
             "inputs. Mix the inputs into one Principled BSDF instead for an exact bake.")
    _triangulate(obj)
    step = time.time()
    method = atlas_unwrap(obj, resolution)
    _log(f"atlas ({method}) in {time.time() - step:.1f} s")
    step = time.time()
    scene.cycles.samples = 1
    covered = _coverage(obj, slots, resolution)
    channels = {}
    for channel, colour in (("base_color", True), ("roughness", False), ("metallic", False),
                            ("alpha", False), ("emission", True)):
        channels[channel] = _channel(obj, slots, baked_slots, channel, resolution, colour)
    _log(f"channels in {time.time() - step:.1f} s")
    step = time.time()
    normal_image = _new_image("bake_normal", resolution, colour=False)
    _bake(obj, "NORMAL", slots, normal_image, normal_space="TANGENT")
    normal = _pixels(normal_image)
    bpy.data.images.remove(normal_image)
    _log(f"normal in {time.time() - step:.1f} s")
    step = time.time()
    occlusion = np.ones(normal.shape[:2], np.float32)
    if ao:
        scene.cycles.samples = ao_samples
        ao_image = _new_image("bake_ao", resolution, colour=False)
        _ao_distance(obj)
        _bake(obj, "AO", slots, ao_image)
        occlusion = _pixels(ao_image)[..., 0]
        bpy.data.images.remove(ao_image)
        scene.cycles.samples = 1
        _log(f"ambient occlusion ({ao_samples} samples) in {time.time() - step:.1f} s")
    name = obj.name
    base = channels["base_color"].copy()
    alpha = channels["alpha"][..., 0]
    has_alpha = bool((alpha[covered] < 0.98).mean() > 0.001)
    base[..., 3] = np.clip(alpha, 0.0, 1.0) if has_alpha else 1.0
    maps = {"base_color": _save(f"{name}_basecolor", base, folder, colour=True)}
    orm = np.ones_like(base)
    orm[..., 0] = np.clip(occlusion, 0.0, 1.0)
    orm[..., 1] = np.clip(channels["roughness"][..., 0], 0.0, 1.0)
    orm[..., 2] = np.clip(channels["metallic"][..., 0], 0.0, 1.0)
    maps["orm"] = _save(f"{name}_orm", orm, folder, colour=False)
    normal[..., 3] = 1.0
    maps["normal"] = _save(f"{name}_normal", normal, folder, colour=False)
    emission = channels["emission"]
    peak = float(emission[..., :3].max())
    glows = peak > 0.004
    emission_strength = 1.0
    if glows:
        # Brighter than 1 is kept as the strength (glTF KHR_materials_emissive_strength), not clipped.
        emission_strength = max(1.0, peak)
        emission = emission / emission_strength
        emission[..., 3] = 1.0
        maps["emission"] = _save(f"{name}_emission", np.clip(emission, 0.0, 1.0), folder, colour=True)
    if has_alpha:
        maps["alpha"] = maps["base_color"]
    export = _export_material(f"M_{name}", maps, emission_strength)
    _one_material(obj, slots, baked_slots, export)
    # The export keeps one UV layer per mesh: the atlas, named as the kit names every layer.
    mesh = obj.data
    for layer in [layer.name for layer in mesh.uv_layers if layer.name != ATLAS_UV]:
        mesh.uv_layers.remove(mesh.uv_layers[layer])
    mesh.uv_layers[ATLAS_UV].active = True
    mesh.uv_layers[ATLAS_UV].active_render = True
    report = {"baked": True, "resolution": resolution, "atlas": method, "maps": sorted(maps), "alpha": has_alpha,
              "emission": glows, "averaged_shader_mixes": averaged, "coverage": round(float(covered.mean()), 3), "kept_materials": sorted(slots[index].name for index in range(len(slots))
                                                         if index not in baked_slots and slots[index]),
              "seconds": round(time.time() - started, 1),
              "files": [str(folder / f"{name}_{suffix}.png") for suffix in
                        ("basecolor", "orm", "normal") + (("emission",) if glows else ())]}
    _log(f"{name}: {', '.join(report['maps'])} at {resolution} px in {report['seconds']} s")
    return report
