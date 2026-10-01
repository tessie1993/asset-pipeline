"""Close-up of one view: the Canva sheet's view beside the same rendered view, enlarged.

At the size of a whole sheet a texture is a few pixels; this shows the pattern, its scale,
direction and relief big enough to read and compare. ``--box`` crops both to the same part of
the view (fractions of the view, from its top-left corner).

    blender -b --factory-startup --python tools/blender/assetgen/zoom.py -- <pack> <id> \
        --view <azimuth> [--box X0 Y0 X1 Y1] [--scale 2]

Writes ``production/qa/evidence/<pack>/<id>/<id>_zoom_<azimuth>.png``: the Canva sheet's view
on the left and, once the object has been built, the rendered view on the right.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assetgen import kit  # noqa: E402
from common import cli  # noqa: E402

GAP_PX = 8


def _crop(cell: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    """``box`` (x0, y0, x1, y1 as fractions from the top-left) of a bottom-up pixel array."""
    height, width = cell.shape[:2]
    x0, y0, x1, y1 = box
    return cell[round((1 - y1) * height):round((1 - y0) * height), round(x0 * width):round(x1 * width)]


def zoom(pack_name: str, asset_id: str, azimuth: int, box: tuple[float, float, float, float],
         scale: int) -> Path:
    if azimuth not in kit.VIEW_AZIMUTHS:
        raise ValueError(f"--view must be one of {kit.VIEW_AZIMUTHS}, not {azimuth}")
    if not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
        raise ValueError(f"--box must be X0 Y0 X1 Y1 with 0 <= X0 < X1 <= 1 and 0 <= Y0 < Y1 <= 1, not {box}")
    pack = kit.Pack(pack_name)
    sheet_path = pack.sheet(asset_id)
    render_path = pack.evidence_dir / asset_id / f"{asset_id}_view_{azimuth:03d}.png"
    if sheet_path is None:
        raise FileNotFoundError(f"{pack_name} has no Canva sheet for {asset_id}")

    sheet = kit._on_backdrop(kit._pixels(sheet_path))
    index = kit.VIEW_AZIMUTHS.index(azimuth)
    row, column = divmod(index, 4)
    cell_h, cell_w = sheet.shape[0] // 2, sheet.shape[1] // 4
    top = (1 - row) * cell_h  # image rows run bottom-up
    reference = sheet[top:top + cell_h, column * cell_w:(column + 1) * cell_w]
    images = [reference]
    if render_path.exists():
        images.append(kit._pixels(render_path)[:cell_h, :cell_w])

    parts = [np.repeat(np.repeat(_crop(image, box), scale, axis=0), scale, axis=1) for image in images]
    height = max(part.shape[0] for part in parts)
    parts = [np.pad(part, ((height - part.shape[0], 0), (0, 0), (0, 0)), constant_values=1.0) for part in parts]
    gap = np.ones((height, GAP_PX, 4), dtype=np.float32)
    out = pack.evidence_dir / asset_id / f"{asset_id}_zoom_{azimuth:03d}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    kit._save_png(np.concatenate([parts[0], gap, parts[1]], axis=1) if len(parts) == 2 else parts[0], out)
    shown = "Canva left, render right" if len(parts) == 2 else "Canva only: not built yet"
    print(f"ZOOM {asset_id} {azimuth}: {out.relative_to(kit.REPO_ROOT)} ({shown})")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Close-up of one view: Canva sheet beside the render")
    parser.add_argument("pack")
    parser.add_argument("id")
    parser.add_argument("--view", type=int, required=True, help="azimuth of the view")
    parser.add_argument("--box", type=float, nargs=4, default=(0.0, 0.0, 1.0, 1.0),
                        metavar=("X0", "Y0", "X1", "Y1"), help="part of the view, fractions from its top-left")
    parser.add_argument("--scale", type=int, default=2, help="enlargement (whole pixels)")
    args = cli.script_args(parser)
    zoom(args.pack, args.id, args.view, tuple(args.box), args.scale)
