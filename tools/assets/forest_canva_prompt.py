#!/usr/bin/env python3
"""Print the Canva prompt that asks for one object's 360-degree sheet with a written description.

The prompt is filled from the data files, never typed by hand, so Canva's own name and description reach it
verbatim. The template is the one that produced the treehouse cabin sheet (``design/levels/forest/HANDOFF.md``, section 4).

Usage::

    python3 tools/assets/forest_canva_prompt.py <asset>                 # eight views of the object, camera slightly above
    python3 tools/assets/forest_canva_prompt.py <asset> --layout block  # eight views of a terrain diorama block, camera raised

``--layout block`` is for flat or sloped ground surfaces, where a low camera shows little. It swaps the layout sentence for the
one in ``forest_style.json`` (``terrain_turnaround_layout``) and has not been tried yet: check the first result by eye.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "assets" / "data" / "forest"
MANIFEST = DATA_DIR / "forest_canva_objects.json"
PROFILES_DIR = DATA_DIR / "profiles"

OBJECT_LAYOUT = (
    "show it as a 360-degree turnaround sheet: eight evenly spaced views (0, 45, 90, 135, 180, 225, 270 and 315 degrees) in two "
    "rows of four cells across the top 80 percent of the image. Every cell shows the identical object at identical scale, "
    "proportions, colours and lighting, camera slightly above, on a plain flat light-grey background, no floor."
)
BLOCK_LAYOUT = (
    "show it as a 360-degree turnaround sheet of ONE terrain diorama block (a square slab of ground with the terrain on top, "
    "no other scenery): eight evenly spaced views (0, 45, 90, 135, 180, 225, 270 and 315 degrees around the block) in two "
    "rows of four cells across the top 80 percent of the image. Every cell shows the identical block at identical scale and "
    "lighting, camera raised about 35 degrees looking down at the block's centre, on a plain flat light-grey background."
)
TEMPLATE = (
    'The FIRST attached image is a stylised forest scene (the reference). The SECOND attached image is an object identification '
    'sheet made from it. Find object number {number}, "{name}", described as: "{description}" {where}\n\n'
    "Regenerate ONLY that one object, on its own, as a 3D-rendered game asset in the same painterly storybook style, colours and "
    "materials as the reference, and {layout}\n\n"
    "Across the bottom 20 percent add a caption bar with large, crisp, easy-to-read text: first line \"{number} {category} - {name}\", "
    "then a clear description in 2 to 3 sentences of exactly what you drew: its shape, parts, materials and colours. "
    "No other text anywhere."
)


def load_json(path: Path) -> dict:
    """The JSON document at ``path``."""
    return json.loads(path.read_text(encoding="utf-8"))


def location_hint(obj: dict) -> str:
    """Where the object is in the mockup: the profile's ``where_in_image``, else the manifest's ``mockup_note``."""
    profile_path = PROFILES_DIR / f"forest_{obj['asset']}.json"
    if profile_path.exists():
        return f"It is {load_json(profile_path)['where_in_image']}."
    return obj["mockup_note"]


def build_prompt(obj: dict, layout: str) -> str:
    """The prompt for ``obj`` with the ``object`` or ``block`` layout sentence."""
    return TEMPLATE.format(
        number=obj["canva_id"], name=obj["name"], description=obj["canva_description"], where=location_hint(obj),
        layout={"object": OBJECT_LAYOUT, "block": BLOCK_LAYOUT}[layout], category=obj["category"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("asset")
    parser.add_argument("--layout", choices=("object", "block"), default="object")
    args = parser.parse_args()
    matches = [o for o in load_json(MANIFEST)["objects"] if o["asset"] == args.asset]
    if not matches:
        raise SystemExit(f"no object with asset '{args.asset}' in {MANIFEST.name}")
    print(build_prompt(matches[0], args.layout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
