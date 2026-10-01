#!/usr/bin/env python3
"""Cut a Canva 360-degree sheet into its eight views and its caption.

A sheet is what the Canva prompt in ``design/levels/forest/HANDOFF.md`` produces: eight views in two rows of four
across the top of the image and a caption bar with the description underneath. The split is by fixed proportions
(``VIEWS_HEIGHT_FRACTION`` of the height holds the views), so check the result by eye once per sheet.

Usage::

    python3 tools/assets/forest_canva_views.py <asset>          # one asset, from assets/data/forest/forest_canva_objects.json
    python3 tools/assets/forest_canva_views.py --all            # every object that has a turnaround image

Writes ``design/levels/forest/canva/views/<asset>/view_0.png`` .. ``view_7.png`` (0, 45, ... 315 degrees, left to
right then top to bottom) and ``caption.png``. Requires Pillow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "assets" / "data" / "forest" / "forest_canva_objects.json"
OUT_DIR = REPO_ROOT / "design" / "levels" / "forest" / "canva" / "views"
COLUMNS, ROWS = 4, 2
VIEWS_HEIGHT_FRACTION = 0.78  # measured on the first sheet: the caption bar starts at 78 % of the height
CELL_INSET_PX = 6  # trims the white gutter between cells


def cut(sheet_path: Path, out_dir: Path) -> None:
    """Write the eight view crops and the caption crop of ``sheet_path`` into ``out_dir``."""
    image = Image.open(sheet_path).convert("RGB")
    width, height = image.size
    views_height = round(height * VIEWS_HEIGHT_FRACTION)
    cell_w, cell_h = width // COLUMNS, views_height // ROWS
    out_dir.mkdir(parents=True, exist_ok=True)
    for index in range(COLUMNS * ROWS):
        col, row = index % COLUMNS, index // COLUMNS
        box = (col * cell_w + CELL_INSET_PX, row * cell_h + CELL_INSET_PX, (col + 1) * cell_w - CELL_INSET_PX, (row + 1) * cell_h - CELL_INSET_PX)
        image.crop(box).save(out_dir / f"view_{index}.png")
    image.crop((0, views_height, width, height)).save(out_dir / "caption.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("asset", nargs="?")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    objects = json.loads(MANIFEST.read_text(encoding="utf-8"))["objects"]
    chosen = [o for o in objects if o.get("turnaround") and (args.all or o["asset"] == args.asset)]
    if not chosen:
        raise SystemExit("no object with a turnaround image matches; pass an asset name or --all")
    for obj in chosen:
        target = OUT_DIR / obj["asset"]
        cut(REPO_ROOT / obj["turnaround"]["image"], target)
        print(f"{obj['asset']}: 8 views and caption -> {target.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
