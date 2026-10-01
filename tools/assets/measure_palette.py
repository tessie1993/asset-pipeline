#!/usr/bin/env python3
"""Measure a reference painting's palette from named crop boxes.

For every crop in a JSON spec the script clusters the pixels with k-means (fixed seed, so runs are
repeatable), orders the clusters by luminance and reports them as shadow / mid / lit bands. It also
writes a labelled contact sheet so the crop boxes can be checked by eye before the numbers are used.

The spec is a JSON object::

    {"image": "design/levels/reference/forest/forest_biome_mockup.jpg",
     "crops": {"bark": [x0, y0, x1, y1], ...}}

Boxes are in source-image pixels, ``x1``/``y1`` exclusive. Requires Pillow and numpy.

Usage::

    python3 tools/assets/measure_palette.py <spec.json> --sheet <sheet.png> --out <palette.json>
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
CLUSTERS = 3
KMEANS_ITERATIONS = 24
KMEANS_SEED = 7
MAX_SAMPLES = 20000
SHEET_CELL = (300, 240)
SHEET_COLUMNS = 4
LUMA_WEIGHTS = np.array([0.2126, 0.7152, 0.0722])
BAND_NAMES = ("shadow", "mid", "lit")


def to_hex(rgb: np.ndarray) -> str:
    """Format an RGB triple in 0..255 as ``#rrggbb``."""
    r, g, b = (int(round(float(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def kmeans(pixels: np.ndarray, clusters: int) -> tuple[np.ndarray, np.ndarray]:
    """Cluster ``pixels`` (N x 3) and return ``(centres, share)`` with ``share`` summing to 1."""
    rng = np.random.default_rng(KMEANS_SEED)
    if len(pixels) > MAX_SAMPLES:
        pixels = pixels[rng.choice(len(pixels), MAX_SAMPLES, replace=False)]
    centres = pixels[rng.choice(len(pixels), clusters, replace=False)].astype(np.float64)
    labels = np.zeros(len(pixels), dtype=np.int64)
    for _ in range(KMEANS_ITERATIONS):
        distance = ((pixels[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        labels = distance.argmin(axis=1)
        for index in range(clusters):
            members = pixels[labels == index]
            if len(members):
                centres[index] = members.mean(axis=0)
    share = np.bincount(labels, minlength=clusters) / len(labels)
    return centres, share


def measure(image: Image.Image, box: list[int]) -> dict:
    """Return the shadow / mid / lit bands and the mean colour of ``box``."""
    pixels = np.asarray(image.crop(tuple(box)).convert("RGB"), dtype=np.float64).reshape(-1, 3)
    centres, share = kmeans(pixels, CLUSTERS)
    order = np.argsort(centres @ LUMA_WEIGHTS)
    bands = {
        name: {"hex": to_hex(centres[index]), "share": round(float(share[index]), 3)}
        for name, index in zip(BAND_NAMES, order)
    }
    return {"mean": to_hex(pixels.mean(axis=0)), "bands": bands}


def build_sheet(image: Image.Image, crops: dict[str, list[int]], measured: dict[str, dict]) -> Image.Image:
    """Return a contact sheet: each crop with its label and its three band swatches underneath."""
    swatch_height = 28
    cell_w, cell_h = SHEET_CELL
    rows = math.ceil(len(crops) / SHEET_COLUMNS)
    sheet = Image.new("RGB", (cell_w * SHEET_COLUMNS, (cell_h + swatch_height) * rows), "#202020")
    draw = ImageDraw.Draw(sheet)
    for slot, (name, box) in enumerate(crops.items()):
        col, row = slot % SHEET_COLUMNS, slot // SHEET_COLUMNS
        x, y = col * cell_w, row * (cell_h + swatch_height)
        crop = image.crop(tuple(box)).convert("RGB")
        scale = min((cell_w - 6) / crop.width, (cell_h - 6) / crop.height)
        crop = crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))), Image.Resampling.LANCZOS)
        sheet.paste(crop, (x + 3, y + 3))
        draw.rectangle((x + 3, y + 3, x + 3 + 8 * len(name) + 6, y + 17), fill="#000000")
        draw.text((x + 6, y + 5), name, fill="#ffffff")
        for band, colour in enumerate(measured[name]["bands"].values()):
            left = x + 3 + band * (cell_w - 6) // CLUSTERS
            right = x + 3 + (band + 1) * (cell_w - 6) // CLUSTERS - 2
            draw.rectangle((left, y + cell_h, right, y + cell_h + swatch_height - 4), fill=colour["hex"])
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="JSON spec with the image path and the named crop boxes")
    parser.add_argument("--sheet", type=Path, help="write the labelled contact sheet here (PNG)")
    parser.add_argument("--out", type=Path, help="write the measured palette here (JSON)")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    image = Image.open(REPO_ROOT / spec["image"])
    crops: dict[str, list[int]] = spec["crops"]
    for name, box in crops.items():
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
            print(f"crop '{name}' {box} is outside the {image.width}x{image.height} image", file=sys.stderr)
            return 1

    measured = {name: measure(image, box) for name, box in crops.items()}
    if args.sheet:
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        build_sheet(image, crops, measured).save(args.sheet)
    result = {
        "image": spec["image"],
        "image_size": [image.width, image.height],
        "method": f"k-means, {CLUSTERS} clusters per crop, seed {KMEANS_SEED}, ordered by Rec.709 luminance",
        "crops": {name: {"box": crops[name], **data} for name, data in measured.items()},
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
