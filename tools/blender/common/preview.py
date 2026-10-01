"""Auto-framed preview renders for checking generated assets against the references."""
import math
from pathlib import Path

import bpy
from mathutils import Vector

from .palette import srgb_hex_to_linear
from .scene import link


def _scene_bounds(objects) -> tuple[Vector, float]:
    corners = [o.matrix_world @ Vector(c) for o in objects if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return (lo + hi) / 2.0, (hi - lo).length / 2.0


def render_preview(out_png: Path, azimuth_deg: float = 20.0, elevation_deg: float = 25.0,
                   resolution: tuple[int, int] = (960, 540), engine: str = "BLENDER_EEVEE",
                   sky_hex: str = "#b5d8da") -> Path:
    """Render all visible meshes from a camera orbiting their bounds; returns the PNG path.

    ``azimuth_deg`` 0 looks from the south (Godot +Z, the front of an asset) toward the north.
    EEVEE needs a display (``xvfb-run``); pass ``engine="CYCLES"`` when none is available.
    """
    scene = bpy.context.scene
    meshes = [o for o in scene.objects if o.type == "MESH" and not o.name.endswith(("-colonly", "-convcolonly"))]
    center, radius = _scene_bounds(meshes)
    cam_data = bpy.data.cameras.new("PreviewCamera")
    cam_data.lens = 50
    camera = link(bpy.data.objects.new("PreviewCamera", cam_data))
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    distance = radius / math.sin(math.radians(19.0)) + 0.5
    camera.location = center + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * distance
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    sun = link(bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN")))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = srgb_hex_to_linear(sky_hex)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    scene.render.engine = engine
    if engine == "CYCLES":
        scene.cycles.samples = 32
        scene.cycles.device = "CPU"
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    for obj in (camera, sun):
        bpy.data.objects.remove(obj, do_unlink=True)
    return Path(out_png)
