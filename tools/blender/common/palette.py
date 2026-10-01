"""Palette materials shared by every generated asset.

Slot names and colours come from ``assets/data/sky_village/rendering_palette.json``; Godot swaps
each slot for a toon material by name, so use :func:`material` rather than creating materials.
"""
from functools import lru_cache

import bpy

from .paths import DATA_DIR, load_json

PALETTE_FILE = DATA_DIR / "rendering_palette.json"


@lru_cache(maxsize=1)
def slots() -> dict:
    """Return the palette slot table keyed by slot name (``M_*``)."""
    return load_json(PALETTE_FILE)["slots"]


def srgb_hex_to_linear(hex_color: str) -> tuple[float, float, float, float]:
    """Convert ``#rrggbb`` (sRGB) to a linear RGBA tuple for Blender colour sockets."""
    value = hex_color.lstrip("#")
    channels = [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return (*linear, 1.0)


def material(slot: str) -> bpy.types.Material:
    """Return the palette material ``slot``, creating it on first use.

    Raises ``KeyError`` for a slot that is not in the palette file.
    """
    spec = slots()[slot]
    existing = bpy.data.materials.get(slot)
    if existing is not None:
        return existing
    mat = bpy.data.materials.new(slot)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb_hex_to_linear(spec["base"])
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    if "emission" in spec:
        bsdf.inputs["Emission Color"].default_value = srgb_hex_to_linear(spec["emission"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    mat.diffuse_color = srgb_hex_to_linear(spec["base"])
    return mat
