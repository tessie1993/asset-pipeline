"""Contract section 6.2 markers: empties, trigger volumes and collision proxies."""
import bpy
from mathutils import Vector

from .scene import link


def add_marker(name: str, location, parent: bpy.types.Object | None = None,
               display: str = "PLAIN_AXES", size: float = 0.3) -> bpy.types.Object:
    """Create an empty called ``name`` at ``location`` (Blender coords, relative to ``parent``)."""
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = display
    empty.empty_display_size = size
    empty.location = Vector(location)
    link(empty)
    if parent is not None:
        empty.parent = parent
    return empty


def add_volume(name: str, center, half_extents, parent: bpy.types.Object | None = None) -> bpy.types.Object:
    """Box trigger marker: a CUBE empty of size 1 whose scale equals the box half-extents."""
    empty = add_marker(name, center, parent, display="CUBE", size=1.0)
    empty.scale = Vector(half_extents)
    return empty


def add_collision_proxy(name: str, verts, faces, convex: bool = False,
                        parent: bpy.types.Object | None = None) -> bpy.types.Object:
    """Invisible collision mesh; Godot's importer turns the name suffix into a StaticBody3D."""
    suffix = "-convcolonly" if convex else "-colonly"
    full_name = name if name.endswith(suffix) else name + suffix
    mesh = bpy.data.meshes.new(full_name)
    mesh.from_pydata([Vector(v) for v in verts], [], faces)
    mesh.update()
    obj = link(bpy.data.objects.new(full_name, mesh))
    obj.display_type = "WIRE"
    obj.hide_render = True  # preview renders only; glTF export ignores render visibility by default
    if parent is not None:
        obj.parent = parent
    return obj
