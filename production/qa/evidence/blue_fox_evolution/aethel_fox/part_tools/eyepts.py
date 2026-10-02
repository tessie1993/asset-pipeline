"""Eye outline extreme points (wing tip, inner corner, top, bottom, w, h in a 600 px frame) of the
reference crops (name ref) and of harness runs (NAME_pair_*.png in parts/out). Run inside parts/out."""
import cv2, numpy as np, sys
def pts(img, side):
    h = img.shape[0]
    reg = img[int(0.33*h):int(0.75*h)]
    if side == "front":
        reg = reg[:, :int(0.5*img.shape[1])]
    hsv = cv2.cvtColor(reg, cv2.COLOR_BGR2HSV)
    m = (hsv[..., 2] < 95).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    k = 1 + np.argmax(st[1:, 4])
    ys, xs = np.nonzero(lab == k)
    ys = ys + int(0.33*h)
    s = 600 / img.shape[1]
    o = lambda i: (int(xs[i]*s), int(ys[i]*s))
    return dict(left=o(np.argmin(xs)), right=o(np.argmax(xs)), top=o(np.argmin(ys)), bottom=o(np.argmax(ys)), w=int((xs.max()-xs.min())*s), h=int((ys.max()-ys.min())*s))
for name in sys.argv[1:]:
    for shot in ("eyes_front", "eye_side"):
        im = cv2.imread(f"{name}_pair_{shot}.png")
        if name == "ref":   # the reference crops beside this script (0.12 m / 0.075 m boxes)
            from pathlib import Path as _P
            crop = {"eyes_front": "t_front_eyes.png", "eye_side": "t_side_eye.png"}[shot]
            im = cv2.resize(cv2.imread(str(_P(__file__).resolve().parent / crop)), (600, 600))
        else:
            im = im[:, 600:]
        print(name, shot, pts(im, "front" if shot == "eyes_front" else "side"))
