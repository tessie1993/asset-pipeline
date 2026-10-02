"""Side-by-side of a reference crop and a build render, the render scaled and moved so that two anchor points
(measured by eye on each image, e.g. the two iris centres, or eye centre and nose tip) coincide.
  python3 align.py REF "x1,y1,x2,y2" BUILD "x1,y1,x2,y2" OUT [--grid 20] [--labels a,b]
Panels: reference | build (aligned) | 50 % blend; a shared grid in reference pixels (every 20 px, red every 100)."""
import sys
import numpy as np
import cv2

ref = cv2.imread(sys.argv[1])
ra = np.array([float(v) for v in sys.argv[2].split(",")]).reshape(2, 2)
bld = cv2.imread(sys.argv[3])
ba = np.array([float(v) for v in sys.argv[4].split(",")]).reshape(2, 2)
out = sys.argv[5]
grid = 20
if "--grid" in sys.argv:
    grid = int(sys.argv[sys.argv.index("--grid") + 1])
# similarity transform from build anchors to reference anchors (scale + translation, no rotation:
# the anchors' rotation is a real difference to look at, not to remove)
s = np.linalg.norm(ra[1] - ra[0]) / np.linalg.norm(ba[1] - ba[0])
t = ra.mean(0) - s * ba.mean(0)
M = np.array([[s, 0, t[0]], [0, s, t[1]]])
h, w = ref.shape[:2]
warp = cv2.warpAffine(bld, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
# the renders have a black background: show it white
dark = warp.sum(2) < 30
warp[dark] = 255
blend = cv2.addWeighted(ref, 0.5, warp, 0.5, 0)


def gridded(im):
    im = cv2.resize(im, None, fx=1.25, fy=1.25, interpolation=cv2.INTER_CUBIC)
    H, W = im.shape[:2]
    for x in range(0, w, grid):
        X = int(x * 1.25)
        cv2.line(im, (X, 0), (X, H), (0, 0, 220) if x % 100 == 0 else (190, 190, 190), 1)
        if x % 100 == 0:
            cv2.putText(im, str(x), (X + 2, 12), 0, 0.4, (0, 0, 220), 1)
    for y in range(0, h, grid):
        Y = int(y * 1.25)
        cv2.line(im, (0, Y), (W, Y), (0, 0, 220) if y % 100 == 0 else (190, 190, 190), 1)
        if y % 100 == 0:
            cv2.putText(im, str(y), (2, Y - 2), 0, 0.4, (0, 0, 220), 1)
    for p in ra:
        cv2.circle(im, (int(p[0] * 1.25), int(p[1] * 1.25)), 4, (0, 160, 0), 2)
    return im


sheet = np.concatenate([gridded(ref), gridded(warp), gridded(blend)], 1)
cv2.imwrite(out, sheet)
print(f"scale {s:.3f} shift {t.round(1).tolist()} -> {out}")
