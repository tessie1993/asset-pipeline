"""Head-only quick test (cycle 7): the body clay cut to the head and neck, with the real fur materials,
eyes, eyelids, nose, mouth and ears, rendered (Cycles, low samples) from the front, three-quarter, side
and profile, lit and clay, pre-scale coordinates. Never the full build.
  blender -b --factory-startup --python headtest.py -- --out NAME [--set body.CONST=value ...] [--res 520]
"""
import argparse, importlib, math, sys, time, random
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

REPO = Path("/home/user/asset-pipeline")
PACKDIR = REPO / "tools/blender/assetgen/packs/blue_fox_evolution"
WORK = REPO / ".scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts"
sys.path.insert(0, str(REPO / "tools/blender/assetgen"))
sys.path.insert(0, str(PACKDIR))
import kit  # noqa

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="ht")
ap.add_argument("--set", nargs="*", default=[])
ap.add_argument("--res", type=int, default=520)
ap.add_argument("--samples", type=int, default=12)
ap.add_argument("--threads", type=int, default=1)
ap.add_argument("--outdir", default=str(WORK / "c7"))
ap.add_argument("--shots", nargs="*", default=["front", "34", "side", "profile"])
ap.add_argument("--exec", default="")
args = ap.parse_args(argv)
T0 = time.time()


def log(m):
    print(f"HT [{time.time() - T0:6.1f}s] {m}", flush=True)


from common import scene  # noqa
scene.reset_scene()
kit._active_pack = kit.Pack("blue_fox_evolution")
from aethel_fox_parts import common as C, body as B, face as F, ears as E  # noqa
for s in args.set:
    key, val = s.split("=", 1)
    modname, const = key.split(".")
    mod = importlib.import_module(f"aethel_fox_parts.{modname}")
    setattr(mod, const, eval(val, {"np": np, "math": math}))
    log(f"set {key} = {val}")

if args.exec:
    exec(args.exec, {"B": B, "C": C, "F": F, "E": E, "np": np})
    log(f"exec {args.exec}")
# cut the clay box to the head and neck (fast)
_Clay = C.S.Clay


class HeadClay(_Clay):
    def __init__(self, lo, hi, voxel, far=None):
        if hi[2] > 0.39 and lo[2] < 0.0:
            lo, hi, voxel = (-0.13, -0.29, 0.215), (0.13, -0.06, 0.40), 0.0016
        super().__init__(lo, hi, voxel, far)


C.S.Clay = HeadClay
B.S.Clay = HeadClay
marks, decal = B.mark_images()
m_fur = B.fur_material("M_fur", marks, decal, cream=False)
m_cream = B.fur_material("M_fur_cream", marks, decal, cream=True)
body, clay = B.body_clay()
log("clay")
body.data.shade_smooth()
body.data.materials.append(m_fur)
kit.mark(body, B.cream_field, m_cream)
B.body_attributes(body)
bvh = C.bvh_of(body)
parts = [body]
m_eye = F.eye_material()
m_lid = C.dark_material("M_eyelid", "#1b1d30", 0.6, "#2c2e44")
m_out, m_in = E.ear_materials(E.ear_image())
m_tuft = E.ear_tuft_material()
rng = random.Random(12)
for side, uoff in ((1, 0.0), (-1, 0.5)):
    parts.append(E.build_ear(side, m_out, m_in, uoff))
    parts += E.build_ear_tufts(side, m_tuft, rng)
    bed = F.EyeBed(bvh, clay, side)
    parts.append(F.build_eye(bed, m_eye))
    parts += F.build_eyelids(bed, m_lid)
parts.append(F.build_nose(C.dark_material("M_nose", "#2c2428", 0.3, "#544650")))
parts += F.build_mouth(bvh, C.dark_material("M_mouth", "#3a2f35", 0.5, "#4b3d44"))
loc, rot, sc = B.brow_frame(clay, bvh)
for mp in B.BROW_NODES:
    mp.inputs["Location"].default_value = loc
    mp.inputs["Rotation"].default_value = rot
    mp.inputs["Scale"].default_value = sc
log("parts built")
# the measurements the review needs: head width at heights, cheek extents
co = np.array([v.co[:] for v in body.data.vertices])
for zq in (0.36, 0.345, 0.335, 0.327, 0.318, 0.31, 0.30, 0.29, 0.28):
    sel = co[(np.abs(co[:, 2] - zq) < 0.0012) & (co[:, 1] < -0.10)]
    if len(sel):
        print(f"MEAS z {zq:.3f}: half-width {sel[:, 0].max():.4f}  front y {sel[:, 1].min():.4f}")
print(f"MEAS crown z {co[(np.abs(co[:, 0]) < 0.004) & (co[:, 1] < -0.10), 2].max():.4f}")

center = Vector((0, -0.19, 0.33))
kit._studio(0.35, center)
kit._configure_render(args.samples, args.threads)
SHOTS = {"front": (0, -8, (0.0, -0.205, 0.325), 0.20), "34": (30, 4, (0.015, -0.19, 0.323), 0.20),
         "side": (62, 6, (0.03, -0.18, 0.318), 0.20), "profile": (90, 0, (0.0, -0.18, 0.322), 0.20)}
OUT = Path(args.outdir)
OUT.mkdir(parents=True, exist_ok=True)
layer = bpy.context.view_layer
for name in args.shots:
    az, el, tg, w = SHOTS[name]
    d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    data = bpy.data.cameras.new("Shot")
    data.type = "ORTHO"
    data.ortho_scale = w
    cam = kit.scene.link(bpy.data.objects.new("Shot", data))
    cam.location = Vector(tg) + d * 1.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    data.clip_start, data.clip_end = 0.01, 5.0
    bpy.context.scene.camera = cam
    kit._render(OUT / f"{args.out}_{name}.png", (args.res, args.res))
    layer.material_override = kit._clay()
    kit._render(OUT / f"{args.out}_{name}_clay.png", (args.res, args.res))
    layer.material_override = None
    bpy.data.objects.remove(cam, do_unlink=True)
    log(f"shot {name}")
log("DONE")
