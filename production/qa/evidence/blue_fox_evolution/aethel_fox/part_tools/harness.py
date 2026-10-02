"""Part test harness for aethel_fox (run in Blender, never the full kit build).

  blender -b --factory-startup --python harness.py -- --base
      full build() of the generator, saved (scaled to 0.50 m) as parts/base.blend
  blender -b --factory-startup --python harness.py -- --part face|ears|tail|body --out NAME
          [--views 1 2 3] [--shots shots.json] [--set face.EYE_A=0.016 ...] [--samples 16] [--res 768]
      opens base.blend, rebuilds only that part from its module (constants overridden by --set),
      rescales the fox to 0.50 m, joins as the kit does and renders the kit views (kit camera) and
      ortho close-up shots into parts/out/NAME_*.png (+ NAME_meta.json for cmp.py)
"""
import argparse
import importlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

REPO = Path("/home/user/asset-pipeline")
PACKDIR = REPO / "tools/blender/assetgen/packs/blue_fox_evolution"
WORK = REPO / ".scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts"
BASE = WORK / "base.blend"
sys.path.insert(0, str(REPO / "tools/blender/assetgen"))
sys.path.insert(0, str(PACKDIR))
import kit  # noqa: E402

PREFIX = {
    "face": ("eye_", "eyelid_", "Nose"),
    "ears": ("Ear_", "ear_tuft_"),
    "tail": ("tail_",),
}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--base", action="store_true")
ap.add_argument("--part")
ap.add_argument("--out", default="test")
ap.add_argument("--views", type=int, nargs="*", default=[1, 2, 3])
ap.add_argument("--shots", default=None)
ap.add_argument("--set", nargs="*", default=[])
ap.add_argument("--samples", type=int, default=16)
ap.add_argument("--res", type=int, default=768)
ap.add_argument("--shot_res", type=int, default=600)
ap.add_argument("--threads", type=int, default=1)
ap.add_argument("--clay", action="store_true", help="also render clay for the views")
ap.add_argument("--outdir", default=None, help="folder for the renders (default parts/out)")
args = ap.parse_args(argv)
T0 = time.time()


def log(msg):
    print(f"HARNESS [{time.time() - T0:6.1f}s] {msg}", flush=True)


def apply_sets():
    for s in args.set:
        key, val = s.split("=", 1)
        modname, const = key.split(".")
        mod = importlib.import_module(f"aethel_fox_parts.{modname}")
        v = eval(val, {"np": np, "math": math})
        setattr(mod, const, v)
        log(f"set {modname}.{const} = {v!r}")


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def tail_top(objs):
    return max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in objs)


if args.base:
    from common import scene  # noqa: E402
    scene.reset_scene()
    kit._active_pack = kit.Pack("blue_fox_evolution")
    gen = importlib.import_module("aethel_fox")
    from aethel_fox_parts import body as B
    apply_sets()
    parts = gen.build()
    f = 0.50 / 0.50  # build() scaled already; recover f from the brow nodes
    # remember the pre-scale brow frame and the scale, label the brow mapping nodes
    loc = B.BROW_NODES[0].inputs["Location"].default_value.copy()
    sc = B.BROW_NODES[0].inputs["Scale"].default_value.copy()
    rot = B.BROW_NODES[0].inputs["Rotation"].default_value.copy()
    for mp in B.BROW_NODES:
        mp.label = "brow_map"
    sc0 = Vector((0.0080, 0.0046, 0.006))
    # the fox's 0.50 m scale: a body vertex's Y over its pre-scale Y (the pys attribute)
    _b = bpy.data.objects["Body"]
    _pys = _b.data.attributes["pys"].data
    _i = max(range(len(_b.data.vertices)), key=lambda i: abs(_b.data.vertices[i].co.y))
    f = _b.data.vertices[_i].co.y / (_pys[_i].value * B.MARK_SPAN + B.SIDE_Y0)
    bpy.context.scene["fox_f"] = f
    bpy.context.scene["brow_loc0"] = list(loc)   # pre-scale (the shader reads pre-scale attributes)
    bpy.context.scene["brow_rot"] = list(rot)
    bpy.context.scene["brow_sc0"] = list(sc0)
    for o in meshes():
        o.data.use_fake_user = True
    for m in bpy.data.materials:
        m.use_fake_user = True
    bpy.ops.wm.save_as_mainfile(filepath=str(BASE))
    log(f"BASE saved {BASE} f={f:.4f} objects={len(meshes())}")
    for o in meshes():
        print("OBJ", o.name, len(o.data.polygons))
    sys.exit(0)

# ---------------------------------------------------------------- part run
if args.part == "full":
    from common import scene as _sc  # noqa: E402
    _sc.reset_scene()
    kit._active_pack = kit.Pack("blue_fox_evolution")
    apply_sets()
    gen = importlib.import_module("aethel_fox")
    new = gen.build()
    bpy.context.scene["fox_f"] = 1.0
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / f"full_{args.out}.blend"))
    BASE = WORK / f"full_{args.out}.blend"
    args.part = "none"
bpy.ops.wm.open_mainfile(filepath=str(BASE))
kit._active_pack = kit.Pack("blue_fox_evolution")
from aethel_fox_parts import common as C  # noqa: E402
from aethel_fox_parts import body as B  # noqa: E402
apply_sets()
sc = bpy.context.scene
f_old = sc["fox_f"]
for o in meshes():
    o.data.transform(Matrix.Scale(1.0 / f_old, 4))
    o.data.update()
log(f"opened base, unscaled by {f_old:.4f}")
part = args.part
new = []
if part in PREFIX:
    for o in list(meshes()):
        if o.name.startswith(PREFIX[part]):
            bpy.data.objects.remove(o, do_unlink=True)
body = bpy.data.objects["Body"]
if part == "face":
    F = importlib.import_module("aethel_fox_parts.face")
    _, clay = B.body_clay()
    bpy.data.objects.remove(bpy.data.objects["Body.001"] if "Body.001" in bpy.data.objects else
                            [o for o in meshes() if o.name.startswith("Body") and o is not body][0], do_unlink=True)
    log("clay ready")
    body_bvh = C.bvh_of(body)
    m_eye = F.eye_material()
    m_nose = bpy.data.materials["M_nose"]
    m_lid = C.dark_material("M_eyelid_t", "#1b1d30", 0.6, "#2c2e44")
    for side in (1, -1):
        bed = F.EyeBed(body_bvh, clay, side)
        new.append(F.build_eye(bed, m_eye))
        new += F.build_eyelids(bed, m_lid)
    new.append(F.build_nose(m_nose))
    loc, rot, s0 = B.brow_frame(clay, body_bvh)
    sc["brow_loc0"] = list(loc)
    sc["brow_rot"] = list(rot)
elif part == "ears":
    E = importlib.import_module("aethel_fox_parts.ears")
    import random
    m_out, m_in = E.ear_materials(E.ear_image())
    m_tuft = E.ear_tuft_material()
    rng = random.Random(12)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        new.append(E.build_ear(side, m_out, m_in, uoff))
        new += E.build_ear_tufts(side, m_tuft, rng)
elif part == "tail":
    Tm = importlib.import_module("aethel_fox_parts.tail")
    new += Tm.build_tail(None)
elif part == "none":
    pass
else:
    raise SystemExit(f"unknown part {part}")
log(f"rebuilt {part}: {len(new)} objects, {sum(len(o.data.polygons) for o in new)} faces")

objs = meshes()
f = 0.50 / tail_top(objs)
for o in objs:
    o.data.transform(Matrix.Scale(f, 4))
    o.data.update()
for m in bpy.data.materials:
    if m.node_tree:
        for n in m.node_tree.nodes:
            if n.label == "brow_map":
                n.inputs["Location"].default_value = Vector(sc["brow_loc0"])
                n.inputs["Rotation"].default_value = Vector(sc["brow_rot"])
                n.inputs["Scale"].default_value = Vector(sc["brow_sc0"])
log(f"scale x{f:.4f}")
tris = 0
for o in objs:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
part_tris = 0
for o in new:
    o.data.calc_loop_triangles()
    part_tris += len(o.data.loop_triangles)
pts = np.concatenate([np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices]) for o in objs])
lo, hi = pts.min(0), pts.max(0)
offset = Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
dims = hi - lo
obj = kit._finalize("aethel_fox", objs, "bottom")
log(f"joined; tris {tris} (part {part_tris}); dims {dims.round(4).tolist()}")

OUT = Path(args.outdir).resolve() if args.outdir else WORK / "out"
OUT.mkdir(exist_ok=True)
views = kit.active_pack().views("aethel_fox")
setting = kit.active_pack().camera("aethel_fox")
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
center = sum(corners, Vector()) / 8.0
radius = max((c - center).length for c in corners)
P = [obj.matrix_world @ v.co for v in obj.data.vertices]
half_width = max(math.hypot(p.x - center.x, p.y - center.y) for p in P)
half_height = max(abs(p.z - center.z) for p in P)
pivot = kit.scene.link(bpy.data.objects.new("Turntable", None))
pivot.location = center
obj.parent = pivot
obj.matrix_parent_inverse = Matrix.Translation(-center)
kit._studio(radius, center)
kit._configure_render(args.samples, args.threads)
meta = {"part": part, "tris": tris, "part_tris": part_tris, "scale": f, "dims": dims.tolist(), "views": {}, "shots": {}}
layer = bpy.context.view_layer
for number in args.views:
    view = views[number - 1]
    cell = kit._cell(view["box"], args.res)
    cam = kit._camera(center, half_width, half_height, float(view["elevation"]), cell, setting)
    pivot.rotation_euler = (0.0, 0.0, math.radians(-float(view["azimuth"])))
    p = kit._render(OUT / f"{args.out}_view_{number}.png", cell)
    meta["views"][number] = str(p)
    if args.clay:
        layer.material_override = kit._clay()
        kit._render(OUT / f"{args.out}_clay_{number}.png", cell)
        layer.material_override = None
    bpy.data.objects.remove(cam, do_unlink=True)
    log(f"view {number} rendered")
pivot.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
if args.shots:
    shots = json.loads(Path(args.shots).read_text())
    for name, (az, el, tx, ty, tz, width) in shots.items():
        target = Vector((tx, ty, tz)) + offset
        az_r, el_r = math.radians(az), math.radians(el)
        d = Vector((math.sin(az_r) * math.cos(el_r), -math.cos(az_r) * math.cos(el_r), math.sin(el_r)))
        data = bpy.data.cameras.new("Shot")
        data.type = "ORTHO"
        data.ortho_scale = width
        cam = kit.scene.link(bpy.data.objects.new("Shot", data))
        cam.location = target + d * 2.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        data.clip_start, data.clip_end = 0.01, 10.0
        sc.camera = cam
        p = kit._render(OUT / f"{args.out}_shot_{name}.png", (args.shot_res, args.shot_res))
        meta["shots"][name] = str(p)
        if args.clay:
            layer.material_override = kit._clay()
            kit._render(OUT / f"{args.out}_clayshot_{name}.png", (args.shot_res, args.shot_res))
            layer.material_override = None
        bpy.data.objects.remove(cam, do_unlink=True)
        log(f"shot {name} rendered")
(OUT / f"{args.out}_meta.json").write_text(json.dumps(meta, indent=1))
log("DONE")
