"""Budget and naming report for the current scene (contract sections 6.1 and 6.2)."""
import json
import re

import bpy

from .palette import slots
from .scene import triangle_count

MARKER_PATTERN = re.compile(r"^(door_\d+|roof_group|interior_volume|light_\d+|window_\d+|npc_spot_\w+|"
                            r"interact_\w+|place_\w+|water_\d+)$")


def report(triangle_budget: int) -> dict:
    """Return (and print as JSON) triangle totals, unknown material slots and markers found."""
    known = set(slots())
    visible = [o for o in bpy.context.scene.objects
               if o.type == "MESH" and not o.name.endswith(("-colonly", "-convcolonly"))]
    triangles = sum(triangle_count(o) for o in visible)
    used = {slot.material.name for o in visible for slot in o.material_slots if slot.material}
    result = {
        "triangles": triangles,
        "triangle_budget": triangle_budget,
        "within_budget": triangles <= triangle_budget,
        "unknown_material_slots": sorted(used - known),
        "meshes_without_material": sorted(o.name for o in visible if not o.material_slots),
        "markers": sorted(o.name for o in bpy.context.scene.objects if MARKER_PATTERN.match(o.name)),
        "collision_proxies": sorted(o.name for o in bpy.context.scene.objects
                                    if o.name.endswith(("-colonly", "-convcolonly"))),
    }
    print("VALIDATION " + json.dumps(result))
    return result
