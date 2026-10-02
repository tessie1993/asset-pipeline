"""sheet.py SHOT OUT name1 name2 ...: per row one variant (lit | clay) for that shot, the reference crop at the top."""
import sys, cv2, numpy as np
D = "/home/user/asset-pipeline/.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/c7/"
R = "/home/user/asset-pipeline/production/qa/evidence/blue_fox_evolution/aethel_fox/part_tools/"
shot, out, names = sys.argv[1], sys.argv[2], sys.argv[3:]
H = 360
def fit(im):
    return cv2.resize(im, (int(im.shape[1] * H / im.shape[0]), H), interpolation=cv2.INTER_AREA)
rows = []
ref = {"front": "r_front_head.png", "side": "r_side_head.png", "34": "r_front_head.png", "profile": "r_side_head.png"}[shot]
for n in names:
    a, b = cv2.imread(D + f"{n}_{shot}.png"), cv2.imread(D + f"{n}_{shot}_clay.png")
    row = np.concatenate([fit(cv2.imread(R + ref)), fit(a), fit(b)], 1)
    cv2.putText(row, n, (8, 20), 0, 0.6, (0, 0, 200), 2)
    rows.append(row)
W = max(r.shape[1] for r in rows)
rows = [np.pad(r, ((0, 0), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
cv2.imwrite(out, np.concatenate(rows, 0))
