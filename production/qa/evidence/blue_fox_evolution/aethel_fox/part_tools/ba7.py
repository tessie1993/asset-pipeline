"""ba7.py OLD NEW OUTDIR: per head view one sheet: reference crop | OLD lit | NEW lit | OLD clay | NEW clay."""
import sys, cv2, numpy as np
D = "/home/user/asset-pipeline/.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/c7/"
R = "/home/user/asset-pipeline/production/qa/evidence/blue_fox_evolution/aethel_fox/part_tools/"
old, new, out = sys.argv[1:4]
H = 420
def fit(im):
    return cv2.resize(im, (int(im.shape[1] * H / im.shape[0]), H), interpolation=cv2.INTER_AREA)
def lab(im, t):
    cv2.putText(im, t, (8, 22), 0, 0.6, (255, 255, 255), 3); cv2.putText(im, t, (8, 22), 0, 0.6, (0, 0, 160), 1)
    return im
for v, ref in (("front", "r_front_head.png"), ("34", "r_front_head.png"), ("side", "r_side_head.png"), ("profile", "r_side_head.png")):
    ims = [lab(fit(cv2.imread(R + ref)), "reference")]
    for tag, kind in ((old, "shot"), (new, "shot"), (old, "clayshot"), (new, "clayshot")):
        ims.append(lab(fit(cv2.imread(D + f"{tag}_{kind}_head_{v}.png")), f"{'build 6' if tag == old else 'cycle 7'} {'lit' if kind == 'shot' else 'clay'}"))
    cv2.imwrite(f"{out}/ba7_head_{v}.png", np.concatenate(ims, 1))
