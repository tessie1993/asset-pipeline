"""Scene utilities: reset, transforms, joining and triangle counts."""
import bmesh
import bpy


def reset_scene() -> None:
    """Start from an empty scene (factory settings without the default cube, light and camera)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(obj: bpy.types.Object, collection: bpy.types.Collection | None = None) -> bpy.types.Object:
    """Link ``obj`` into ``collection`` (the scene collection by default) and return it."""
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def apply_transforms(objects: list[bpy.types.Object]) -> None:
    """Bake location/rotation/scale of mesh ``objects`` into their data (origins move to world 0)."""
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        return
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def join(objects: list[bpy.types.Object], name: str) -> bpy.types.Object:
    """Join mesh ``objects`` into one object called ``name`` and return it."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined.data.name = name
    return joined


def triangle_count(obj: bpy.types.Object) -> int:
    """Triangles in the evaluated mesh of ``obj`` (modifiers applied), 0 for non-meshes."""
    if obj.type != "MESH":
        return 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    count = sum(len(face.verts) - 2 for face in bm.faces)
    bm.free()
    evaluated.to_mesh_clear()
    return count
