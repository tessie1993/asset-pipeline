"""Compare a harness run with the reference: overlap per kit view (fox-only for the side view), a sheet
per view (reference | render | overlay) and close-up pairs.
  python3 cmp.py NAME [--box V X0 Y0 X1 Y1 ...]   (boxes as fractions of the normalised object, like cv.py closeup)"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/user/asset-pipeline/tools/assetgen")
import cv  # noqa
import cv2  # noqa
ROOT = Path("/home/user/asset-pipeline")
OUT = ROOT / ".scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/out"
CROPS = Path(__file__).resolve().parent if (Path(__file__).resolve().parent / "t_front_eyes.png").exists() else ROOT / ".scratch/assetgen/work/blue_fox_evolution/aethel_fox/crops"
name = sys.argv[1]
if "--outdir" in sys.argv:
    _i = sys.argv.index("--outdir"); OUT = Path(sys.argv[_i + 1]).resolve(); del sys.argv[_i:_i + 2]
boxes = []
a = sys.argv[2:]
while a:
    if a[0] == "--box":
        boxes.append((int(a[1]), [float(v) for v in a[2:6]])); a = a[6:]
    else:
        a = a[1:]
meta = json.loads((OUT / f"{name}_meta.json").read_text())
_, entry = cv._entry(ROOT, "blue_fox_evolution", "aethel_fox")
views = entry["views"]
res = {}
for num, path in meta["views"].items():
    num = int(num)
    region = cv.reference_view(ROOT, "blue_fox_evolution", views[num - 1]).copy()
    if num == 2:   # remove the small back-view fox from the side box
        h, w = region.shape[:2]
        region[int(0.45 * h):, int(0.72 * w):, :3] = 255
        if region.shape[2] == 4:
            region[int(0.45 * h):, int(0.72 * w):, 3] = 255
    render = cv.read_image(Path(path))
    r = cv.compare_view(region, render)
    rc, nc, rs, ns = r["_images"]
    ov = cv.overlay_image(rc, nc, rs, ns)
    sheet = np.concatenate([cv.on_grey(rc), cv.on_grey(nc), ov[..., :3] if ov.shape[2] == 4 else ov], 1)
    cv.write_image(OUT / f"{name}_cmp_{num}.png", cv.fit_width(sheet, 1500))
    res[num] = (r["overlap"], r["aspect_change"], r["missing"][:3], r["extra"][:3])
    print(f"view {num}: overlap {r['overlap']:.3f} w/h {r['aspect_change']:+.3f} missing {r['missing'][:3]} extra {r['extra'][:3]}")
    for bv, (x0, y0, x1, y1) in boxes:
        if bv != num:
            continue
        crops = []
        ovc = ov[..., :3] if ov.shape[2] == 4 else ov
        for colour in (rc, nc, ovc):
            H, W = colour.shape[:2]
            cr = colour[round(y0 * H):round(y1 * H), round(x0 * W):round(x1 * W)]
            cr = cv.on_grey(cr) if cr.shape[2] == 4 else cr
            crops.append(cv2.resize(cr, (round(cr.shape[1] * 600 / cr.shape[0]), 600), interpolation=cv2.INTER_CUBIC))
        cv.write_image(OUT / f"{name}_close_{num}_{x0:g}_{y0:g}.png", cv.fit_width(np.concatenate(crops, 1), 1500))
for shot, path in meta.get("shots", {}).items():
    img = cv.on_grey(cv.read_image(Path(path)))
    ref = {"eyes_front": "t_front_eyes.png", "eye_side": "t_side_eye.png", "head_front": "t_front_head.png", "head_side": "t_side_head2.png"}.get(shot)
    if ref:
        r = cv2.imread(str(CROPS / ref))
        img = cv2.resize(img, (600, 600))
        r = cv2.resize(r, (600, 600))
        cv.write_image(OUT / f"{name}_pair_{shot}.png", np.concatenate([r, img], 1))
print("tris", meta["tris"], "part", meta["part_tris"], "scale", round(meta["scale"], 4), "dims", np.round(meta["dims"], 4).tolist())
