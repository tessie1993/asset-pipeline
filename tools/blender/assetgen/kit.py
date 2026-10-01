"""Kit for the image-to-assets pipeline: one generator per object, built from its reference.

The pipeline is described in ``.claude/skills/image-to-assets/SKILL.md``; a pack is the user's image
and the objects chosen from it, recorded in ``design/asset-packs/<pack>/pack.json``. Each object has
reference images (Google Flow's drawings of it, or the user's own images) and the views its builder
recorded in them: per view the image, the box around the object, its azimuth and its elevation.

What a generator builds is the model itself, mid to high poly: real forms (sculpted signed-distance
"clay", subdivision, bevels, booleans, lathes, geometry nodes, displacement) and every detail the
reference shows, each surface a real material: texture sets from Poly Haven, ambientCG,
cgbookcase and Blendkit (:func:`material`), procedural and layered shaders built from nodes, mixed
by masks (:func:`mark`, :func:`attribute`). There are no flat colours and the reference image is
never projected onto the model. The final build bakes every shader into glTF textures
(``bake.py``), so what renders here is what Godot shows.

The vendored skills are importable from a generator: ``kit.skill("scenario-blender-sculpting",
"bx_sculpt")`` returns that skill's script module (sculpting clay, hard surface, texturing, UVs,
retopology, geometry nodes, hair).

A generator lives at ``tools/blender/assetgen/packs/<pack>/<id>.py``; its folder names the pack
and its file name the object. It puts ``tools/blender`` on ``sys.path``, imports
``from assetgen import kit``, defines ``build()`` returning its mesh objects and ends with
``kit.run(build)`` (``kit.run(build, origin="back")`` for wall-mounted objects).

Command line::

    blender -b --factory-startup --python tools/blender/assetgen/packs/<pack>/<id>.py -- \
        [--views N ...] [--final] [--bake] [--no-render] [--no-clay] [--samples S] [--resolution PX]
        [--texture PX] [--threads T]

A cycle build renders every recorded view (or only ``--views``), lit and in clay; ``--final`` bakes
the textures, renders the baked model larger with more samples, plus the turnaround; ``--bake``
bakes in a cycle build too. Outputs:

- ``assets/models/<pack>/<id>.glb``: one mesh named ``<id>``, metres, +Y up, front facing Godot +Z;
  after a bake, one material with base colour, ORM and normal textures (+ emission).
- ``production/qa/evidence/<pack>/<id>/``: ``<id>_view_<n>.png`` (lit) and ``<id>_clay_<n>.png``
  (shape only) per recorded view, ``<id>_turn_<k>.png`` (final), ``<id>_build.json`` (with the
  structure checks and the bake), and the CV compare the kit runs after every build
  (``tools/assetgen/cv.py compare``): ``<id>_compare.png``, ``<id>_cv_survey_<n>.png``,
  ``<id>_cv.json``, ``<id>_turnaround.png``.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import importlib
import inspect
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Iterable, Iterator

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assetgen"))
from common import cli, export, scene  # noqa: E402
from common.colour import srgb_hex_to_linear  # noqa: E402
from common.paths import MODELS_DIR, REPO_ROOT  # noqa: E402
import downloads as fetch  # noqa: E402  (tools/assetgen/downloads.py: cached, size-checked downloads)
from assetgen import bake, checks  # noqa: E402

PACKS_DATA = REPO_ROOT / "design" / "asset-packs"
EVIDENCE_ROOT = REPO_ROOT / "production" / "qa" / "evidence"
GENERATORS_ROOT = Path(__file__).resolve().parent / "packs"
CV_TOOL = REPO_ROOT / "tools" / "assetgen" / "cv.py"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
BAKE_ROOT = REPO_ROOT / ".scratch" / "assetgen" / "bake"  # baked textures (the .glb carries them)

TEXTURE_RESOLUTION = "2k"
MAP_API_KEYS = {"color": "Diffuse", "normal": "nor_gl", "arm": "arm"}
OPTIONAL_MAP_API_KEYS = {"height": "Displacement"}
MATERIAL_SOURCES = ("polyhaven", "ambientcg", "cgbookcase", "blendkit")
MAPPINGS = ("uv", "triplanar")
TRIPLANAR_BLEND = 0.25
AMBIENTCG_ADDON = "ambientcg_material_importer"
AMBIENTCG_RESOLUTION = "2K"
AMBIENTCG_FORMAT = "JPG"
CGBOOKCASE_MAP = "https://cgbookcase.b-cdn.net/textures/thumbnails/{name}_1K/{name}_1K_{map}.png"
CGBOOKCASE_MAPS = {"color": "BaseColor", "normal": "Normal", "roughness": "Roughness"}
CGBOOKCASE_OPTIONAL_MAPS = {"metallic": "Metallic", "height": "Height"}
HDRI = "studio_small_09"
HDRI_RESOLUTION = "1k"
INSTANT_MESHES = "instant-meshes"  # tools/blender/install_blender.sh installs it

# Renders. Every view gets the aspect of its box in the reference, so render and reference line up;
# each is rendered lit and in clay (shape only, no colour). Final builds are larger and cleaner and
# show the baked textures.
CYCLE_SAMPLES, CYCLE_RESOLUTION = 16, 768
FINAL_SAMPLES, FINAL_RESOLUTION = 32, 1280  # denoised; 64 doubled a final build for no visible gain
TEXTURE_SIZE = 2048  # the baked atlas; kit.run(build, texture=4096) for a hero object
CLAY_COLOUR = "#bdbdbd"
TURNAROUND_VIEWS = 8  # evenly spaced from the front, final build only: a review aid, never judged
FRAME_MARGIN = 1.1
FRAME_SAMPLES = 64
DEFAULT_LENS_MM = 85.0  # unless the builder recorded another lens or an orthographic camera (pack.py views)
# Measured under the studio set-up below (white lights aimed at the asset, 2026-10-01): at this exposure a lit
# surface's median brightness matches its material colour on average (spheres in 8 colours from L 0.34 to 0.79: mean
# difference -0.005, at most 0.046; dark colours render a little lighter, light ones a little darker), so a builder
# that gives a part the reference's colour sees that colour in the render and Godot gets the true colour.
RENDER_EXPOSURE = -1.3
BACKDROP = "#d3d3d3"
UV_LAYER = "UVMap"
HDRI_STRENGTH = 0.6

# Studio area lights: (name, position from the asset's centre, energy W, size m), laid out for an
# object of STUDIO_REFERENCE_RADIUS, scaled to the asset's bounding radius and aimed at its centre.
# All white: a tinted light would shift every colour the CV compare measures.
STUDIO_LIGHTS = (
    ("Key", (2.0, -2.0, 3.0), 350.0, 3.0),
    ("Fill", (-2.5, -1.0, 2.0), 250.0, 4.0),
    ("Rim", (0.0, 2.0, 2.5), 250.0, 2.0),
    ("Bounce", (0.0, 0.0, -1.5), 100.0, 5.0),
)
STUDIO_REFERENCE_RADIUS = 1.0


# --------------------------------------------------------------------------------- #
# Packs: the source image, its objects and its material table (design/asset-packs/<pack>/)
# --------------------------------------------------------------------------------- #

class Pack:
    """One pack's manifest (``pack.json``) and the folders its outputs go to."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.data_dir = PACKS_DATA / name
        manifest_path = self.data_dir / "pack.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"{manifest_path} not found; create the pack with tools/assetgen/pack.py init")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.models_dir = MODELS_DIR / name
        self.evidence_dir = EVIDENCE_ROOT / name

    def entry(self, asset_id: str) -> dict:
        return next((o for o in self.manifest["objects"] if o["id"] == asset_id), {})

    def camera(self, asset_id: str) -> dict:
        """The camera the builder chose to match the reference: ``{"lens": mm}`` or ``{"ortho": True}``."""
        return self.entry(asset_id).get("camera") or {"lens": DEFAULT_LENS_MM}

    def views(self, asset_id: str) -> list[dict]:
        """The views the object's builder recorded (``pack.py views``): image, box, azimuth, elevation."""
        views = self.entry(asset_id).get("views") or []
        if not views:
            raise ValueError(f"{asset_id} has no recorded views: record them with tools/assetgen/pack.py views")
        return views


_active_pack: Pack | None = None


def active_pack() -> Pack:
    """The pack of the generator being run (set by :func:`run`)."""
    if _active_pack is None:
        raise RuntimeError("no active pack: run the generator through kit.run(build)")
    return _active_pack


# --------------------------------------------------------------------------------- #
# Poly Haven downloads (API, cached outside the repository)
# --------------------------------------------------------------------------------- #

def _cache_dir(asset_id: str) -> Path:
    return fetch.asset_cache_dir(fetch.DEFAULT_CACHE, "polyhaven", asset_id)


@contextlib.contextmanager
def _download_lock(source: str, asset_id: str) -> Iterator[None]:
    """Hold an exclusive lock for one downloadable asset, so builds running in parallel never
    download or unpack the same files at the same time."""
    path = fetch.DEFAULT_CACHE / "locks" / f"{source}_{asset_id}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def texture_maps(asset_id: str) -> dict[str, Path]:
    """Return the colour, normal, ARM and (when it has one) height maps of Poly Haven texture
    ``asset_id``, downloading once.

    File names vary between assets (``_diff_`` or ``_col_``), so the names the API served are
    recorded in ``maps_<resolution>.json`` beside the files.
    """
    folder = _cache_dir(asset_id)
    index = folder / f"maps_{TEXTURE_RESOLUTION}.json"
    with _download_lock("polyhaven", asset_id):
        if index.exists():
            maps = {key: folder / name for key, name in json.loads(index.read_text()).items()}
            if all(path.exists() for path in maps.values()):
                return maps
        files = fetch.get_json(f"{fetch.POLYHAVEN_API}/files/{asset_id}")
        names = {}
        for key, api_key in {**MAP_API_KEYS, **OPTIONAL_MAP_API_KEYS}.items():
            if api_key not in files:
                if key in OPTIONAL_MAP_API_KEYS:
                    continue
                raise fetch.FetchError(f"{asset_id}: Poly Haven has no {api_key} map")
            formats = files[api_key].get(TEXTURE_RESOLUTION) or files[api_key][min(files[api_key])]
            entry = formats.get("jpg") or formats.get("png")
            if entry is None:
                continue
            target = folder / Path(entry["url"]).name
            if not target.exists():
                fetch.download(entry["url"], target, entry["size"])
            names[key] = target.name
        index.write_text(json.dumps(names, indent=2) + "\n")
    return {key: folder / name for key, name in names.items()}


def _remote_size(url: str) -> int | None:
    """The size in bytes of the file at ``url``, or None when the server does not have it."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": fetch.USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=fetch.REQUEST_TIMEOUT_S) as response:
            return int(response.headers["Content-Length"])
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _flip_green(source: Path, target: Path) -> None:
    """Write ``source`` with its green channel inverted (a DirectX normal map as OpenGL)."""
    image = bpy.data.images.load(str(source))
    image.colorspace_settings.name = "Non-Color"
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels[1::image.channels] = 1.0 - pixels[1::image.channels]
    flipped = bpy.data.images.new(target.stem, *image.size, alpha=image.channels == 4)
    flipped.colorspace_settings.name = "Non-Color"
    flipped.pixels.foreach_set(pixels)
    flipped.filepath_raw = str(target)
    flipped.file_format = "PNG"
    flipped.save()
    bpy.data.images.remove(flipped)
    bpy.data.images.remove(image)


def cgbookcase_maps(name: str) -> dict[str, Path]:
    """Return the colour, OpenGL normal, roughness and (when it has them) metallic and height maps
    of cgbookcase texture ``name``, downloading once."""
    folder = fetch.asset_cache_dir(fetch.DEFAULT_CACHE, "cgbookcase", name)
    maps = {}
    with _download_lock("cgbookcase", name):
        for key, map_name in {**CGBOOKCASE_MAPS, **CGBOOKCASE_OPTIONAL_MAPS}.items():
            url = CGBOOKCASE_MAP.format(name=name, map=map_name)
            target = folder / Path(url).name
            if not target.exists():
                size = _remote_size(url)
                if size is None:
                    if key in CGBOOKCASE_OPTIONAL_MAPS:
                        continue
                    raise fetch.FetchError(f"{name}: cgbookcase has no {map_name} map ({url})")
                fetch.download(url, target, size)
            maps[key] = target
        normal_gl = folder / f"{name}_1K_Normal_gl.png"
        if not normal_gl.exists():
            _flip_green(maps["normal"], normal_gl)
        maps["normal"] = normal_gl
    return maps


def hdri_path(asset_id: str = HDRI) -> Path:
    """Return the cached Poly Haven HDRI ``asset_id``, downloading it once."""
    folder = _cache_dir(asset_id)
    with _download_lock("polyhaven", asset_id):
        existing = sorted(folder.glob(f"*_{HDRI_RESOLUTION}.hdr"))
        if existing:
            return existing[0]
        entry = fetch.get_json(f"{fetch.POLYHAVEN_API}/files/{asset_id}")["hdri"][HDRI_RESOLUTION]["hdr"]
        target = folder / Path(entry["url"]).name
        fetch.download(entry["url"], target, entry["size"])
    return target


# --------------------------------------------------------------------------------- #
# Materials: texture sets from four libraries, procedural and layered shaders, masks
# --------------------------------------------------------------------------------- #

def _image_node(nodes, path: Path, non_color: bool):
    node = nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        node.image.colorspace_settings.name = "Non-Color"
    return node


def _texture_ref(ref: str) -> tuple[str, str]:
    """``(source, asset id)`` of a texture reference ``"<source>:<asset id>"``."""
    source, _, asset_id = ref.partition(":")
    if source not in MATERIAL_SOURCES or not asset_id:
        raise ValueError(f"material {ref!r} must be '<source>:<asset id>' with source one of "
                         f"{MATERIAL_SOURCES}; find one with tools/assetgen/pack.py material-search")
    return source, asset_id


def _material_name(asset_id: str, tint: str | None, tile: float, roughness: float | None,
                   normal_strength: float, mapping: str) -> str:
    """A name unique to every setting, so a material is only reused when it is the same one."""
    parts = [asset_id[:24], tint and tint.lstrip("#").lower(), f"t{tile:g}",
             normal_strength != 1.0 and f"n{normal_strength:g}", roughness is not None and f"r{roughness:g}",
             mapping != "uv" and mapping]
    return "M_" + "_".join(str(part) for part in parts if part)


def principled(name: str) -> tuple[bpy.types.Material, bpy.types.NodeTree, bpy.types.Node]:
    """A new material with one Principled BSDF, for a shader built from nodes:
    ``mat, tree, bsdf = kit.principled("M_fur")``. Feed every input that varies on the reference
    (colour, roughness, relief) from textures, procedural nodes or masks; the final build bakes it."""
    material = bpy.data.materials.new(name)
    tree = material.node_tree
    bsdf = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    return material, tree, bsdf


def uv_node(tree: bpy.types.NodeTree) -> bpy.types.Node:
    """A UV Map node on the kit's texture layer (the part's own UVs, or the world-space box UVs):
    use it for every image lookup, so textures keep their mapping when the final build bakes."""
    node = tree.nodes.new("ShaderNodeUVMap")
    node.uv_map = UV_LAYER
    return node


def material(ref: str, *, tile: float, tint: str | None = None, roughness: float | None = None,
             normal_strength: float = 1.0, mapping: str = "uv", relief: float = 0.01,
             name: str | None = None) -> bpy.types.Material:
    """PBR material from the texture set ``ref``: ``"polyhaven:<id>"``, ``"ambientcg:<id>"``,
    ``"cgbookcase:<name>"`` or ``"blendkit:<asset base id>"`` (free CC0 only), found with
    ``tools/assetgen/pack.py material-search``.

    ``tile`` is repeats per metre (1 / the texture's real-world size keeps it at its true scale).
    ``mapping="uv"`` maps it on the part's UVs (the kit gives every part world-space box UVs in
    metres unless ``obj["keep_uv"]``), with its tangent-space normal map; ``mapping="triplanar"``
    projects it from the three axes in object space with soft blends, seamless on organic forms,
    and makes the relief from the set's height map (``relief`` metres deep; Poly Haven and
    cgbookcase sets). ``tint`` (``#rrggbb``) multiplies the colour map, so pick a texture at least
    as light as the colour wanted; ``roughness`` replaces the roughness map with a constant.
    Identical arguments return the same material; ``name`` overrides the name.
    """
    source, asset_id = _texture_ref(ref)
    if mapping not in MAPPINGS:
        raise ValueError(f"mapping must be one of {MAPPINGS}, not {mapping!r}")
    if mapping == "triplanar" and source not in ("polyhaven", "cgbookcase"):
        raise ValueError(f"triplanar mapping needs a polyhaven or cgbookcase texture, not {source}")
    mat_name = name or _material_name(asset_id, tint, tile, roughness, normal_strength, mapping)
    existing = bpy.data.materials.get(mat_name)
    if existing is not None:
        return existing
    if source == "polyhaven":
        maps = texture_maps(asset_id)
        mat = _texture_set_material(mat_name, maps, mapping, tile, normal_strength, relief, arm=True)
    elif source == "cgbookcase":
        maps = cgbookcase_maps(asset_id)
        mat = _texture_set_material(mat_name, maps, mapping, tile, normal_strength, relief, arm=False)
    elif source == "ambientcg":
        mat = _ambientcg_material(mat_name, asset_id)
    else:
        mat = _blendkit_material(mat_name, asset_id)

    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    if source in ("ambientcg", "blendkit"):
        for mapping_node in (node for node in nodes if node.type == "MAPPING"):
            mapping_node.inputs["Scale"].default_value = (tile, tile, tile)
        for normal_map in (node for node in nodes if node.type == "NORMAL_MAP"):
            normal_map.inputs["Strength"].default_value = normal_strength
    if roughness is not None:
        for link in list(bsdf.inputs["Roughness"].links):
            links.remove(link)
        bsdf.inputs["Roughness"].default_value = roughness
    if tint and bsdf.inputs["Base Color"].is_linked:
        color_link = bsdf.inputs["Base Color"].links[0]
        multiply = nodes.new("ShaderNodeMix")
        multiply.data_type = "RGBA"
        multiply.blend_type = "MULTIPLY"
        multiply.inputs["Factor"].default_value = 1.0
        multiply.inputs["B"].default_value = srgb_hex_to_linear(tint)
        links.new(color_link.from_socket, multiply.inputs["A"])
        links.new(multiply.outputs["Result"], bsdf.inputs["Base Color"])
    mat["source"] = f"{source}:{asset_id}"
    return mat


def material_variants(ref: str, tint: str, count: int, spread: float = 0.08, seed: int = 0,
                      **options) -> list[bpy.types.Material]:
    """``count`` versions of ``material(ref, tint=tint)``, each tint scaled in lightness by up to
    ``±spread`` (deterministic for a given ``seed``). Give each separate part its own variant so
    copies differ as on the reference; ``options`` (``tile`` is required) go to :func:`material`.
    """
    rng = random.Random(seed)
    base = [int(tint.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    variants = []
    for _ in range(count):
        scale = 1.0 + rng.uniform(-spread, spread)
        channels = [max(0, min(255, round(c * scale))) for c in base]
        variants.append(material(ref, tint="#%02x%02x%02x" % tuple(channels), **options))
    return variants


def _texture_set_material(mat_name: str, maps: dict[str, Path], mapping: str, tile: float,
                          normal_strength: float, relief: float, arm: bool) -> bpy.types.Material:
    """Principled BSDF fed by a downloaded texture set: colour, roughness and metallic (an ARM map
    for Poly Haven, separate maps for cgbookcase) and the relief (normal map on UVs, height map
    through a Bump node in triplanar mapping)."""
    mat = bpy.data.materials.new(mat_name)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    mapping_node = nodes.new("ShaderNodeMapping")
    mapping_node.inputs["Scale"].default_value = (tile, tile, tile)
    if mapping == "triplanar":
        coords = nodes.new("ShaderNodeTexCoord")
        links.new(coords.outputs["Object"], mapping_node.inputs["Vector"])
    else:
        links.new(uv_node(mat.node_tree).outputs["UV"], mapping_node.inputs["Vector"])

    def image(key: str, non_color: bool):
        node = _image_node(nodes, maps[key], non_color)
        if mapping == "triplanar":
            node.projection = "BOX"
            node.projection_blend = TRIPLANAR_BLEND
        links.new(mapping_node.outputs["Vector"], node.inputs["Vector"])
        return node

    links.new(image("color", False).outputs["Color"], bsdf.inputs["Base Color"])
    if arm:
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(image("arm", True).outputs["Color"], split.inputs["Color"])
        links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
        links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    else:
        links.new(image("roughness", True).outputs["Color"], bsdf.inputs["Roughness"])
        if "metallic" in maps:
            links.new(image("metallic", True).outputs["Color"], bsdf.inputs["Metallic"])
    if mapping == "triplanar":
        if "height" in maps:
            bump = nodes.new("ShaderNodeBump")
            bump.inputs["Distance"].default_value = relief
            bump.inputs["Strength"].default_value = min(1.0, normal_strength)
            links.new(image("height", True).outputs["Color"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        else:
            print(f"KIT note: {mat_name}: the texture set has no height map, so triplanar mapping gives it no relief")
    else:
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.uv_map = UV_LAYER
        normal_map.inputs["Strength"].default_value = normal_strength
        links.new(image("normal", True).outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _ambientcg_material(mat_name: str, asset_id: str) -> bpy.types.Material:
    """Material made by the AmbientCG Material Importer add-on's own operator, renamed ``mat_name``.

    The add-on wires a height map into the material output's Displacement as true displacement;
    it is set to bump, which the bake turns into the normal map.
    """
    enable_addon(AMBIENTCG_ADDON, with_preferences=True)  # it reads its cache folder from there
    settings = bpy.context.scene
    settings.ambientcg_material_name = asset_id
    settings.ambientcg_resolution = AMBIENTCG_RESOLUTION
    settings.ambientcg_format = AMBIENTCG_FORMAT
    settings.ambientcg_projection = "FLAT"
    before = set(bpy.data.materials)
    with _download_lock("ambientcg", asset_id):
        if bpy.ops.material.fetch_and_create() != {"FINISHED"}:
            raise RuntimeError(f"ambientCG add-on could not create {asset_id}")
    mat = next(m for m in bpy.data.materials if m not in before)
    mat.name = mat_name
    mat.displacement_method = "BUMP"
    return mat


def _blendkit_material(mat_name: str, asset_base_id: str) -> bpy.types.Material:
    """A free CC0 Blendkit material, appended from its .blend (a full Blender node material,
    often procedural; its images are packed in the file) and renamed ``mat_name``."""
    with _download_lock("blendkit", asset_base_id):
        asset = fetch.blendkit_asset(asset_base_id)
        path = fetch.blendkit_download(asset)
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        names = list(source.materials)
        wanted = asset["name"] if asset["name"] in names else None
        target.materials = [wanted] if wanted else names
    loaded = [m for m in target.materials if m is not None]
    if not loaded:
        raise RuntimeError(f"Blendkit {asset_base_id} ({asset['name']}) holds no material")
    mat = max(loaded, key=lambda m: len(m.node_tree.nodes))
    for other in loaded:
        if other is not mat and other.users == 0:
            bpy.data.materials.remove(other)
    mat.name = mat_name
    mat.displacement_method = "BUMP"
    if not any(node.type == "BSDF_PRINCIPLED" for node in mat.node_tree.nodes):
        raise RuntimeError(f"Blendkit {asset_base_id} ({asset['name']}) has no Principled BSDF at its top level; "
                           "pick another material")
    return mat


def mark(obj: bpy.types.Object, field: Callable[[Vector], float], mat: bpy.types.Material) -> int:
    """Give ``mat`` to the part of ``obj``'s surface where ``field`` (a function of a world-space
    point) is below zero, with the edge cut into the mesh exactly where the field crosses zero,
    so a marking (a face mask, a belly patch, a stripe, a ring) has as smooth an edge as its field,
    at any mesh density. A ragged edge comes from a field with noise in it
    (``mathutils.noise.noise(point * scale)``). Returns the number of faces marked.

    Call it on the finished shape, before adding modifiers that change the surface. For a soft
    blend instead of an edge, write the field as an attribute (:func:`attribute`) and mix the two
    materials' inputs by it in one shader.
    """
    if mat.name not in obj.data.materials:
        obj.data.materials.append(mat)
    index = list(obj.data.materials).index(bpy.data.materials[mat.name])
    to_world = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    value = {vert: field(to_world @ vert.co) for vert in bm.verts}
    cuts = set()
    for edge in list(bm.edges):
        start, end = edge.verts
        a, b = value[start], value[end]
        if (a < 0) == (b < 0):
            continue
        _, cut = bmesh.utils.edge_split(edge, start, a / (a - b))
        value[cut] = 0.0
        cuts.add(cut)
    for face in list(bm.faces):
        ring = [vert for vert in face.verts if vert in cuts]
        for first, second in zip(ring[0::2], ring[1::2]):
            if not bm.edges.get((first, second)):
                bmesh.ops.connect_verts(bm, verts=[first, second])
    marked = 0
    for face in bm.faces:
        if field(to_world @ face.calc_center_median()) < 0:
            face.material_index = index
            marked += 1
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return marked


def attribute(obj: bpy.types.Object, name: str, field: Callable[[Vector], float]) -> None:
    """Store ``field`` (a function of a world-space point, any float) per vertex as the float
    attribute ``name``; a shader reads it with an Attribute node (``attribute_name = name``) as a
    soft mask: where one material blends into another, colour zones, wear, dirt, fur direction.
    It survives joining and is baked with the shader."""
    to_world = obj.matrix_world
    values = [float(field(to_world @ vertex.co)) for vertex in obj.data.vertices]
    layer = obj.data.attributes.get(name) or obj.data.attributes.new(name, "FLOAT", "POINT")
    layer.data.foreach_set("value", values)
    obj.data.update()
# --------------------------------------------------------------------------------- #
# Geometry helpers (all sizes in metres, Blender +Z up, front of the asset toward -Y)
# --------------------------------------------------------------------------------- #

def mesh_object(name: str, bm: bmesh.types.BMesh, mat: bpy.types.Material | None = None,
                location=(0.0, 0.0, 0.0), rotation_deg=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    """Turn ``bm`` into a linked mesh object (``bm`` is freed)."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = scene.link(bpy.data.objects.new(name, mesh))
    if mat is not None:
        mesh.materials.append(mat)
    obj.location = Vector(location)
    obj.rotation_euler = [math.radians(a) for a in rotation_deg]
    return obj


def box(name: str, size, location, mat=None, rotation_deg=(0.0, 0.0, 0.0),
        bevel: float = 0.0, segments: int = 2) -> bpy.types.Object:
    """Box of ``size`` (x, y, z) centred on ``location``, optionally with bevelled edges."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    obj = mesh_object(name, bm, mat, location, rotation_deg)
    if bevel > 0.0:
        add_bevel(obj, bevel, segments)
    return obj


def cylinder(name: str, radius: float, depth: float, location, mat=None, rotation_deg=(0.0, 0.0, 0.0),
             segments: int = 24, radius_top: float | None = None, bevel: float = 0.0) -> bpy.types.Object:
    """Cylinder (or cone when ``radius_top`` differs) along local Z, centred on ``location``."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius,
                          radius2=radius if radius_top is None else radius_top, depth=depth)
    obj = mesh_object(name, bm, mat, location, rotation_deg)
    if bevel > 0.0:
        add_bevel(obj, bevel, 2)
    return obj


def sphere(name: str, radius: float, location, mat=None, scale=(1.0, 1.0, 1.0),
           segments: int = 24, rings: int = 12) -> bpy.types.Object:
    """UV sphere of ``radius`` centred on ``location``, stretched by ``scale``."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    return mesh_object(name, bm, mat, location)


def lathe(name: str, profile: Iterable[tuple[float, float]], location=(0.0, 0.0, 0.0), mat=None,
          segments: int = 32, cap_bottom: bool = True, cap_top: bool = False) -> bpy.types.Object:
    """Surface of revolution about Z from ``profile`` points ``(radius, z)``, bottom to top.

    For any round part: trace the outer silhouette up; for an open, hollow part continue with the
    inner wall back down (a little smaller radius) so the wall has thickness.
    """
    points = list(profile)
    bm = bmesh.new()
    rings = []
    for radius, z in points:
        ring = [bm.verts.new((radius * math.cos(2 * math.pi * i / segments),
                              radius * math.sin(2 * math.pi * i / segments), z)) for i in range(segments)]
        rings.append(ring)
    for lower, upper in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
    if cap_bottom and points[0][0] > 0.0:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and points[-1][0] > 0.0:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm, mat, location)


def add_bevel(obj: bpy.types.Object, width: float, segments: int = 2) -> bpy.types.Modifier:
    """Rounded edges (angle-limited bevel): edges the sheet shows soft catch a highlight."""
    modifier = obj.modifiers.new("Bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.harden_normals = False
    return modifier


NOISE_BASES = ("BLENDER_ORIGINAL", "ORIGINAL_PERLIN", "IMPROVED_PERLIN", "VORONOI_F1", "VORONOI_F2")


def roughen(obj: bpy.types.Object, strength: float, noise_size: float = 0.25,
            subdivisions: int = 2, seed: int = 0) -> None:
    """Irregular, lumpy surface: subdivide, then displace along normals with noise.

    The noise is sampled in world space, so copies at different places already differ; ``seed``
    picks another noise basis for extra variety.
    """
    subsurf = obj.modifiers.new("Subdivision", "SUBSURF")
    subsurf.levels = subdivisions
    subsurf.render_levels = subdivisions
    texture = bpy.data.textures.new(f"{obj.name}_noise", "CLOUDS")
    texture.noise_scale = noise_size
    texture.noise_depth = 2
    texture.noise_basis = NOISE_BASES[seed % len(NOISE_BASES)]
    displace = obj.modifiers.new("Displace", "DISPLACE")
    displace.texture = texture
    displace.strength = strength
    displace.mid_level = 0.5
    displace.texture_coords = "GLOBAL"


def smooth(obj: bpy.types.Object, angle_deg: float = 35.0) -> None:
    """Smooth shading with sharp edges kept above ``angle_deg``."""
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle_deg))


def enable_addon(module: str, with_preferences: bool = False) -> None:
    """Enable an installed extension (``--factory-startup`` ignores the saved preferences).

    ``with_preferences`` also registers the add-on in this session's preferences, for add-ons
    that read their own settings there; ``--factory-startup`` never saves them to disk.
    """
    import addon_utils

    addon_utils.enable(f"bl_ext.user_default.{module}", default_set=with_preferences)


def skill(skill_name: str, module: str):
    """Import a vendored skill's script module, e.g. ``S = kit.skill("scenario-blender-sculpting",
    "bx_sculpt")`` for its signed-distance ``Clay``; read the skill's SKILL.md for how to use it."""
    folder = SKILLS_DIR / skill_name / "scripts"
    if not (folder / f"{module}.py").exists():
        raise FileNotFoundError(f"{folder / module}.py not found: see python3 tools/assetgen/pack.py skills-list")
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    return importlib.import_module(module)


def clean(obj: bpy.types.Object, merge_distance: float = 2e-4) -> bpy.types.Object:
    """Merge vertices closer than ``merge_distance``, drop loose geometry and make the normals
    point out: what voxel, signed-distance and boolean output needs before remeshing or shading."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_distance)
    loose = [vert for vert in bm.verts if not vert.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def quad_remesh(obj: bpy.types.Object, faces: int, symmetry: bool = False) -> bpy.types.Object:
    """Rebuild ``obj`` as clean quads, about ``faces`` faces, following its surface: for sculpted,
    voxel or signed-distance output before subdivision, displacement or a bevelled finish.
    Instant Meshes when installed, else Blender's QuadriFlow. UVs and attributes are not kept:
    remesh first, then mark, write attributes and give materials."""
    clean(obj)
    binary = shutil.which(INSTANT_MESHES)
    if binary:
        with tempfile.TemporaryDirectory() as folder:
            source, result = Path(folder) / "in.obj", Path(folder) / "out.obj"
            _write_obj(obj, source)
            # Instant Meshes makes about 4 quads per requested vertex at -f; -D allows a few triangles.
            command = [binary, str(source), "-o", str(result), "-f", str(max(100, faces // 4)), "-d", "-S", "2", "-t", "2"]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=900)
            if completed.returncode == 0 and result.exists():
                _read_obj(obj, result)
                return obj
            print(f"KIT note: Instant Meshes failed ({completed.stderr.strip()[-200:]}); using QuadriFlow")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.object.quadriflow_remesh(mode="FACES", target_faces=faces, use_mesh_symmetry=symmetry,
                                              smooth_normals=True, use_preserve_sharp=False, use_preserve_boundary=False)
    if result != {"FINISHED"}:
        raise RuntimeError(f"QuadriFlow could not remesh {obj.name}: make it one closed surface (kit.clean, voxel remesh)")
    return obj


def _write_obj(obj: bpy.types.Object, path: Path) -> None:
    mesh = obj.data
    with path.open("w") as handle:
        for vertex in mesh.vertices:
            handle.write("v %.6f %.6f %.6f\n" % tuple(vertex.co))
        for polygon in mesh.polygons:
            handle.write("f " + " ".join(str(index + 1) for index in polygon.vertices) + "\n")


def _read_obj(obj: bpy.types.Object, path: Path) -> None:
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            vertices.append(tuple(float(value) for value in line.split()[1:4]))
        elif line.startswith("f "):
            faces.append([int(token.split("/")[0]) - 1 for token in line.split()[1:]])
    mesh = bpy.data.meshes.new(obj.data.name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for material in obj.data.materials:
        mesh.materials.append(material)
    old = obj.data
    obj.data = mesh
    bpy.data.meshes.remove(old)


# --------------------------------------------------------------------------------- #
# Finishing: bake modifiers, world-space UVs, join, place the origin
# --------------------------------------------------------------------------------- #

def _realize_tree() -> bpy.types.GeometryNodeTree:
    tree = bpy.data.node_groups.get("KIT_realize_instances")
    if tree is None:
        tree = bpy.data.node_groups.new("KIT_realize_instances", "GeometryNodeTree")
        tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        group_in, group_out = tree.nodes.new("NodeGroupInput"), tree.nodes.new("NodeGroupOutput")
        realize = tree.nodes.new("GeometryNodeRealizeInstances")
        tree.links.new(group_in.outputs[0], realize.inputs[0])
        tree.links.new(realize.outputs[0], group_out.inputs[0])
    return tree


def _apply(obj: bpy.types.Object) -> None:
    """Apply modifiers and the world transform into the mesh data. Geometry nodes' instances are
    realized first: an object's mesh does not hold them, so scattered or arrayed copies would be lost."""
    if any(modifier.type == "NODES" for modifier in obj.modifiers):
        obj.modifiers.new("KIT_realize_instances", "NODES").node_group = _realize_tree()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    baked = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
    world = obj.matrix_world.copy()
    obj.modifiers.clear()
    obj.parent = None
    obj.data = baked
    baked.transform(world)
    obj.matrix_world = Matrix.Identity(4)


def _box_uvs(obj: bpy.types.Object) -> None:
    """Planar UVs per face along its dominant axis, in metres, so every texture has one scale."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        for loop in face.loops:
            x, y, z = loop.vert.co
            loop[uv_layer].uv = {0: (y, z), 1: (x, z), 2: (x, y)}[axis]
    bm.to_mesh(obj.data)
    bm.free()


def _single_uv_layer(obj: bpy.types.Object) -> None:
    """Keep one UV layer per part, named :data:`UV_LAYER`. Joining merges UV layers by name, so
    parts whose layers were named differently would lose their UVs and export as one flat colour."""
    layers = obj.data.uv_layers
    if not layers:
        raise ValueError(f"{obj.name}: keep_uv is set but the mesh has no UV layer")
    keep = next((layer for layer in layers if layer.active_render), layers[0]).name
    for name in [layer.name for layer in layers if layer.name != keep]:
        layers.remove(layers[name])
    layers[keep].name = UV_LAYER


SMOOTH_ANGLE_DEG = 40.0  # shading default: smooth across gentle bends, sharp at real edges


def _finalize(asset_id: str, objects: list[bpy.types.Object], origin: str) -> bpy.types.Object:
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        raise ValueError(f"{asset_id}: build() returned no mesh objects")
    for obj in meshes:
        if not obj.get("flat_shading") and not obj.get("keep_shading"):
            # Round parts read round and hard edges stay hard, at no cost in triangles. A part that must look
            # faceted sets obj["flat_shading"] = True; one whose shading the generator set itself, "keep_shading".
            smooth(obj, SMOOTH_ANGLE_DEG)
        elif obj.get("flat_shading"):
            obj.data.shade_flat()
        _apply(obj)
        if not obj.get("keep_uv"):
            _box_uvs(obj)
        _single_uv_layer(obj)
    for obj in [o for o in bpy.context.scene.objects if o not in meshes]:
        bpy.data.objects.remove(obj, do_unlink=True)
    joined = scene.join(meshes, asset_id) if len(meshes) > 1 else meshes[0]
    joined.name = joined.data.name = asset_id
    corners = [Vector(v.co) for v in joined.data.vertices]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    if origin == "bottom":
        offset = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    elif origin == "back":
        offset = Vector((-(lo.x + hi.x) / 2, -hi.y, -lo.z))
    else:
        raise ValueError(f"origin must be 'bottom' or 'back', not {origin!r}")
    joined.data.transform(Matrix.Translation(offset))
    joined.data.update()
    return joined


def _report(asset_id: str, obj: bpy.types.Object, glb: Path) -> dict:
    dims = obj.dimensions
    result = {
        "triangles": scene.triangle_count(obj),
        "dimensions_m": [round(dims.x, 3), round(dims.y, 3), round(dims.z, 3)],
        "materials": [slot.material.name for slot in obj.material_slots if slot.material],
        "texture_sources": sorted({slot.material["source"] for slot in obj.material_slots
                                   if slot.material and "source" in slot.material}),
        "glb": str(glb.relative_to(REPO_ROOT)),
        "glb_bytes": glb.stat().st_size,
    }
    print(f"BUILT {asset_id} " + json.dumps(result))
    return result


# --------------------------------------------------------------------------------- #
# Renders: turntable views, sheet and side-by-side comparison
# --------------------------------------------------------------------------------- #

def _studio(radius: float, center: Vector) -> None:
    """HDRI lighting (seen by light rays only) over a flat grey backdrop, plus the four white studio
    lights around ``center``, each aimed at it."""
    world = bpy.data.worlds.new("Studio")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    environment = nodes.new("ShaderNodeTexEnvironment")
    environment.image = bpy.data.images.load(str(hdri_path()), check_existing=True)
    hdri_bg = nodes.new("ShaderNodeBackground")
    hdri_bg.inputs["Strength"].default_value = HDRI_STRENGTH
    links.new(environment.outputs["Color"], hdri_bg.inputs["Color"])
    grey_bg = nodes.new("ShaderNodeBackground")
    grey_bg.inputs["Color"].default_value = srgb_hex_to_linear(BACKDROP)
    light_path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(light_path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(hdri_bg.outputs["Background"], mix.inputs[1])
    links.new(grey_bg.outputs["Background"], mix.inputs[2])
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    scale = max(radius / STUDIO_REFERENCE_RADIUS, 0.25)
    for name, offset, energy, size in STUDIO_LIGHTS:
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy * scale * scale
        light.size = size * scale
        obj = scene.link(bpy.data.objects.new(name, light))
        obj.location = center + Vector(offset) * scale
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()  # area lights shine along -Z


def _cell(box: list[int], long_side: int) -> tuple[int, int]:
    """Render size with the aspect of a reference box, ``long_side`` pixels on its longer side."""
    width, height = box[2] - box[0], box[3] - box[1]
    scale = long_side / max(width, height)
    return max(16, round(width * scale)), max(16, round(height * scale))


def _camera(center: Vector, half_width: float, half_height: float, elevation_deg: float,
            cell: tuple[int, int], setting: dict) -> bpy.types.Object:
    """Camera ``elevation_deg`` above the horizon that keeps the object in frame from every azimuth.

    The object turns about the vertical axis through ``center``, so every view fits inside the
    cylinder of radius ``half_width`` and half height ``half_height`` around that axis. A
    perspective camera (``{"lens": mm}``) stands at the smallest distance at which that whole
    cylinder projects inside the frame (with :data:`FRAME_MARGIN`); an orthographic one
    (``{"ortho": True}``) gets the smallest scale that holds it. Either way, views at the same
    elevation and aspect share one scale.
    """
    data = bpy.data.cameras.new("Camera")
    camera = scene.link(bpy.data.objects.new("Camera", data))
    elevation = math.radians(elevation_deg)
    back = Vector((0.0, -math.cos(elevation), math.sin(elevation)))  # from the centre to the camera
    up = Vector((0.0, math.sin(elevation), math.cos(elevation)))
    if setting.get("ortho"):
        data.type = "ORTHO"
        reach_x = 2 * half_width
        reach_y = 2 * (half_height * math.cos(elevation) + half_width * abs(math.sin(elevation)))
        if cell[0] >= cell[1]:
            data.ortho_scale = FRAME_MARGIN * max(reach_x, reach_y * cell[0] / cell[1])
        else:
            data.ortho_scale = FRAME_MARGIN * max(reach_x * cell[1] / cell[0], reach_y)
        distance = 4.0 * max(half_width, half_height) + 1.0
    else:
        data.lens = float(setting.get("lens", DEFAULT_LENS_MM))
        wide = data.sensor_width / 2 / data.lens  # tan of the half field of view along the longer side
        tan_x = wide if cell[0] >= cell[1] else wide * cell[0] / cell[1]
        tan_y = wide if cell[1] > cell[0] else wide * cell[1] / cell[0]
        distance = 0.0
        for i in range(FRAME_SAMPLES):
            angle = 2 * math.pi * i / FRAME_SAMPLES
            for z in (-half_height, half_height):
                point = Vector((half_width * math.cos(angle), half_width * math.sin(angle), z))
                spread = max(abs(point.x) / tan_x, abs(point.dot(up)) / tan_y)
                distance = max(distance, point.dot(back) + FRAME_MARGIN * spread)
    camera.location = center + back * distance
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.clip_start = distance / 100.0
    data.clip_end = distance * 10.0
    bpy.context.scene.camera = camera
    return camera


def _clay() -> bpy.types.Material:
    """Plain grey material: the clay renders show the shape alone (forms, details, relief)."""
    mat = bpy.data.materials.get("KIT_clay")
    if mat is None:
        mat = bpy.data.materials.new("KIT_clay")
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = srgb_hex_to_linear(CLAY_COLOUR)
        bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def _configure_render(samples: int, threads: int) -> None:
    render_scene = bpy.context.scene
    render_scene.render.engine = "CYCLES"
    cycles = render_scene.cycles
    cycles.device = "CPU"
    cycles.samples = samples
    cycles.use_adaptive_sampling = True
    cycles.use_denoising = True
    cycles.max_bounces = 6
    cycles.diffuse_bounces = 2
    cycles.glossy_bounces = 2
    cycles.transmission_bounces = 4
    cycles.transparent_max_bounces = 8
    render_scene.render.threads_mode = "FIXED"
    render_scene.render.threads = threads
    render_scene.render.resolution_percentage = 100
    render_scene.render.film_transparent = True  # the object's outline is the render's alpha
    render_scene.render.image_settings.file_format = "PNG"
    render_scene.render.image_settings.color_mode = "RGBA"
    render_scene.view_settings.view_transform = "Standard"
    render_scene.view_settings.exposure = RENDER_EXPOSURE


def _render(path: Path, cell: tuple[int, int]) -> Path:
    render_scene = bpy.context.scene
    render_scene.render.resolution_x, render_scene.render.resolution_y = cell
    render_scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def render_views(asset_id: str, obj: bpy.types.Object, samples: int, threads: int, resolution: int,
                 only: list[int] | None = None, final: bool = False, clay: bool = True) -> dict:
    """Render the recorded views (or only the view numbers in ``only``), lit and in clay, and, for a
    final build, the turnaround; returns what was rendered, relative to the repository."""
    views = active_pack().views(asset_id)
    numbers = list(range(1, len(views) + 1)) if not only else sorted(set(only))
    unknown = [number for number in numbers if not 1 <= number <= len(views)]
    if unknown:
        raise ValueError(f"--views {unknown}: {asset_id} has views 1 to {len(views)}")
    out_dir = active_pack().evidence_dir / asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    center = sum(corners, Vector()) / 8.0
    radius = max((c - center).length for c in corners)
    # The real vertices, not the box corners: a round object reaches only as far as its rim.
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    half_width = max(math.hypot(p.x - center.x, p.y - center.y) for p in points)
    half_height = max(abs(p.z - center.z) for p in points)
    pivot = scene.link(bpy.data.objects.new("Turntable", None))
    pivot.location = center
    obj.parent = pivot
    obj.matrix_parent_inverse = Matrix.Translation(-center)  # the asset stays where it is
    _studio(radius, center)
    _configure_render(samples, threads)
    setting = active_pack().camera(asset_id)
    rendered = {"views": [], "turnaround": [], "camera": setting}
    for stale in out_dir.glob(f"{asset_id}_clay_*.png"):
        stale.unlink()
    layer = bpy.context.view_layer
    for number in numbers:
        view = views[number - 1]
        cell = _cell(view["box"], resolution)
        camera = _camera(center, half_width, half_height, float(view["elevation"]), cell, setting)
        pivot.rotation_euler = (0.0, 0.0, math.radians(-float(view["azimuth"])))
        path = _render(out_dir / f"{asset_id}_view_{number}.png", cell)
        record = {"view": number, "azimuth": view["azimuth"], "elevation": view["elevation"],
                  "file": str(path.relative_to(REPO_ROOT))}
        if clay:
            layer.material_override = _clay()
            clay_path = _render(out_dir / f"{asset_id}_clay_{number}.png", cell)
            layer.material_override = None
            record["clay"] = str(clay_path.relative_to(REPO_ROOT))
        bpy.data.objects.remove(camera, do_unlink=True)
        rendered["views"].append(record)
    for stale in out_dir.glob(f"{asset_id}_turn_*.png"):
        stale.unlink()
    if final:
        elevation = float(views[0]["elevation"])
        cell = _cell([0, 0, 1, 1], round(resolution * 2 / 3))
        camera = _camera(center, half_width, half_height, elevation, cell, setting)
        for index in range(TURNAROUND_VIEWS):
            azimuth = 360.0 * index / TURNAROUND_VIEWS
            pivot.rotation_euler = (0.0, 0.0, math.radians(-azimuth))
            path = _render(out_dir / f"{asset_id}_turn_{index + 1}.png", cell)
            rendered["turnaround"].append({"azimuth": azimuth, "elevation": elevation,
                                           "file": str(path.relative_to(REPO_ROOT))})
    print(f"RENDERED {asset_id}: {len(rendered['views'])} view(s)" + (" lit and in clay" if clay else "")
          + (f" and a {TURNAROUND_VIEWS}-view turnaround" if final else "") + f" in {out_dir.relative_to(REPO_ROOT)}")
    return rendered


def _write_build(asset_id: str, report: dict, rendered: dict, final: bool, samples: int, resolution: int,
                 extra: dict) -> dict:
    """Record the build (numbered from 1 per object) for the CV compare, the build gate and pack.py done."""
    path = active_pack().evidence_dir / asset_id / f"{asset_id}_build.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    record = {"build": previous.get("build", 0) + 1, "final": final,
              "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "samples": samples, "resolution": resolution, "report": report, **extra, **rendered}
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def _compare(pack_name: str, asset_id: str) -> None:
    """Run the CV compare of this build (system Python with the CV libraries, not Blender's)."""
    try:
        result = subprocess.run(["python3", str(CV_TOOL), "compare", pack_name, asset_id],
                                capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"CV ERROR: {error}; run python3 tools/assetgen/cv.py compare {pack_name} {asset_id}")
        return
    print(result.stdout.rstrip())
    if result.returncode != 0:
        print(f"CV ERROR: {result.stderr.strip()}")


# --------------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------------- #

def _generator_identity(generator: Path) -> tuple[str, str]:
    """``(pack, asset id)`` of a generator at ``packs/<pack>/<id>.py``."""
    if generator.parent.parent != GENERATORS_ROOT:
        raise ValueError(f"{generator} is not a generator: expected {GENERATORS_ROOT}/<pack>/<id>.py")
    return generator.parent.name, generator.stem


def run(build: Callable[[], list[bpy.types.Object]], origin: str = "bottom", texture: int = TEXTURE_SIZE) -> dict:
    """Build, check, finish, (bake,) export and render the calling generator's asset, then compare
    it with the reference (CV); returns the build report.

    The generator's folder names the pack and its file name the asset. ``origin`` is
    ``"bottom"`` (centre of the base, for free-standing objects) or ``"back"`` (centre of the
    back face's bottom edge, for wall-mounted objects). ``texture`` is the side of the baked
    atlas in pixels (2048; 4096 for an object seen up close).
    """
    global _active_pack
    pack_name, asset_id = _generator_identity(Path(inspect.stack()[1].filename).resolve())
    parser = argparse.ArgumentParser(description=f"Build {pack_name}/{asset_id}")
    parser.add_argument("--views", type=int, nargs="+", help="render only these recorded views (a quick check)")
    parser.add_argument("--final", action="store_true", help="final build: bake, larger and cleaner renders, turnaround")
    parser.add_argument("--bake", action="store_true", help="bake the textures in a cycle build too")
    parser.add_argument("--no-render", action="store_true", help="export the .glb only")
    parser.add_argument("--no-clay", action="store_true", help="skip the clay renders")
    parser.add_argument("--samples", type=int, help=f"Cycles samples per view ({CYCLE_SAMPLES}, final {FINAL_SAMPLES})")
    parser.add_argument("--resolution", type=int, help=f"longer side of a view in px ({CYCLE_RESOLUTION}, final {FINAL_RESOLUTION})")
    parser.add_argument("--texture", type=int, help=f"baked atlas side in px (the generator's, default {TEXTURE_SIZE})")
    parser.add_argument("--threads", type=int, default=2, help="render threads (builds run in parallel)")
    args = cli.script_args(parser)
    if args.final and args.views:
        parser.error("--final renders every view; leave out --views")
    samples = args.samples or (FINAL_SAMPLES if args.final else CYCLE_SAMPLES)
    resolution = args.resolution or (FINAL_RESOLUTION if args.final else CYCLE_RESOLUTION)
    texture_size = args.texture or texture
    scene.reset_scene()
    _active_pack = Pack(pack_name)
    parts = build()
    parts_report = checks.parts_report(parts)
    obj = _finalize(asset_id, parts, origin)
    mesh_report = checks.mesh_report(obj)
    for line in checks.lines(parts_report, mesh_report):
        print(line)
    baked = None
    if args.final or args.bake:
        baked = bake.bake_asset(obj, BAKE_ROOT / pack_name / asset_id, texture_size, threads=args.threads)
    glb = export.export_glb(_active_pack.models_dir / f"{asset_id}.glb", selection=[obj])
    report = _report(asset_id, obj, glb)
    if not args.no_render:
        rendered = render_views(asset_id, obj, samples, args.threads, resolution, args.views, args.final,
                                clay=not args.no_clay)
        extra = {"checks": {"parts": parts_report, "mesh": mesh_report}, "bake": baked, "texture": texture_size}
        record = _write_build(asset_id, report, rendered, args.final, samples, resolution, extra)
        print(f"BUILD {record['build']} of {asset_id}" + (" (final)" if args.final else "")
              + (" baked" if baked and baked.get("baked") else ""))
        _compare(pack_name, asset_id)
    return report
