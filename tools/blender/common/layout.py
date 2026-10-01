"""Access to ``level_layout.json`` and Godot → Blender coordinate conversion.

Godot uses +Y up and -Z north; Blender uses +Z up. A Godot point ``(x, y, z)`` is the Blender point
``(x, -z, y)``. A Godot yaw (about +Y) equals the same angle about Blender +Z.
"""
import math
from functools import lru_cache

from mathutils import Euler, Vector

from .paths import DATA_DIR, load_json

LAYOUT_FILE = DATA_DIR / "level_layout.json"


@lru_cache(maxsize=1)
def layout() -> dict:
    """Return the parsed level layout."""
    return load_json(LAYOUT_FILE)


def to_blender(godot_xyz) -> Vector:
    """Convert a Godot position ``[x, y, z]`` to a Blender ``Vector``."""
    x, y, z = godot_xyz
    return Vector((x, -z, y))


def yaw_to_euler(yaw_deg: float) -> Euler:
    """Blender rotation for a Godot yaw in degrees (front +Z_godot == -Y_blender at yaw 0)."""
    return Euler((0.0, 0.0, math.radians(yaw_deg)), "XYZ")


def placement(placement_id: str) -> dict:
    """Return the placement entry with ``id == placement_id``."""
    for entry in layout()["placements"]:
        if entry["id"] == placement_id:
            return entry
    raise KeyError(placement_id)
