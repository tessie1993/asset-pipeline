"""Colour conversion for Blender colour sockets."""


def srgb_hex_to_linear(hex_color: str) -> tuple[float, float, float, float]:
    """Convert ``#rrggbb`` (sRGB) to a linear RGBA tuple for Blender colour sockets."""
    value = hex_color.lstrip("#")
    channels = [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return (*linear, 1.0)
