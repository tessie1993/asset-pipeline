"""The body: SDF clay (torso, neck, head, legs, paws with toes, fur locks), the painted marking
images, the fur shaders with the brow markings, the cream field and the body attributes."""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

import kit  # noqa: E402
from aethel_fox_parts.common import EYE_X, MOUTH_SIDE, NT, S, bez2, lin, new_image, poly_paint, set_attr, set_bsdf, smoothstep, spiral, verts_np  # noqa: E402

# ============================================================================ BODY CLAY
def leg_defs():
    """Leg joint chains (points, radii): front legs straight under the chest, hind legs in stride."""
    legs = {}
    for s in (1, -1):
        fy = -0.113 if s > 0 else -0.127       # side view (kit camera): two separate legs, the far one a step ahead
        legs[f"fl{s}"] = ([(s * 0.036, fy - 0.006, 0.200), (s * 0.031, fy + 0.001, 0.135), (s * 0.028, fy - 0.001, 0.075),
                           (s * 0.027, fy, 0.035), (s * 0.027, fy + 0.001, 0.016)],
                          [0.026, 0.017, 0.0135, 0.0125, 0.0132])
    # hind: near (+X) paw at Y 0.095, far (-X) paw at Y 0.05 (side-view stride)
    for s, py in ((1, 0.092), (-1, 0.035)):      # side view (kit camera rows): wide stride, far paw under the loin
        legs[f"hl{s}"] = ([(s * 0.040, 0.052, 0.20), (s * 0.041, py - 0.045, 0.135), (s * 0.036, py + 0.018, 0.078),
                           (s * 0.033, py + 0.004, 0.035), (s * 0.033, py, 0.016)],
                          [0.029, 0.02, 0.013, 0.012, 0.013])
    return legs


HEAD = {   # (centre, radii) ellipsoids and (a, b, ra, rb) cones of the head clay, before the 0.50 m scale
    "neck": ([(0, -0.106, 0.205), (0, -0.131, 0.262), (0, -0.137, 0.301)], [0.044, 0.037, 0.033]),   # was top (0,-0.147,0.313) r 0.037: filled under the jaw
    "cranium": ((0, -0.152, 0.340), (0.055, 0.051, 0.050)),   # crown 0.390, rounder (was (0,-0.154,0.334) r (0.062,0.052,0.042))
    "brow": ((0, -0.176, 0.334), (0.040, 0.030, 0.024)),       # as built before cycle 4 (taller bulged over the eye bed)
    "cheek": ((0.038, -0.170, 0.311), (0.032, 0.030, 0.021)),  # was (0.04,-0.172,0.305) r (0.035,0.034,0.029): jowls
    # (centre, radii) along the snout: a narrow bridge on top (it runs between the eyes' inner corners, which
    # sit on the snout's upper edge) over a broad, deep lower part that tapers to the nose: in section a
    # trapezoid, wide below, so the wedge is broad at the cheeks without bulging under the eyes
    "snout": [((0, -0.200, 0.3160), (0.0105, 0.016, 0.0125)), ((0, -0.218, 0.3080), (0.0100, 0.012, 0.0100)),
              ((0, -0.230, 0.3020), (0.0100, 0.010, 0.0085)),
              ((0, -0.188, 0.3020), (0.0320, 0.020, 0.0140)), ((0, -0.206, 0.3000), (0.0240, 0.016, 0.0120)),
              ((0, -0.221, 0.2990), (0.0160, 0.012, 0.0100))],
    "jaw": [((0, -0.186, 0.2895), (0.027, 0.020, 0.0120)), ((0, -0.205, 0.2875), (0.019, 0.015, 0.0095)),
            ((0, -0.219, 0.2850), (0.0115, 0.0095, 0.0070))],   # the last one is the chin
}


CHEEK_FUR = [   # (root, tip, root radius, tip radius) of the +X cheek ruff's two soft points
    ((0.042, -0.150, 0.303), (0.079, -0.129, 0.291), 0.0135, 0.0045),   # lower, longer point (mouth height)
    ((0.044, -0.143, 0.311), (0.071, -0.121, 0.307), 0.0115, 0.0040),   # upper point, shorter, behind it
]
CHEEK_BLEND = 0.010
LEG_JOINT_BLEND = 0.004   # smooth blend between a leg's segments (was 0: a crease at every joint)


def body_clay():
    """Signed-distance clay of torso, neck, head, legs, paws and fur locks (sculpting skill)."""
    clay = S.Clay((-0.13, -0.29, -0.01), (0.13, 0.17, 0.40), voxel=0.0021)
    E, C, T = S.sd_ellipsoid, S.sd_cone, S.sd_tube
    # --- torso (side view: chest front Y -0.19, back line Z 0.245, chest bottom Z 0.13, rump Y 0.115)
    clay.add(E((0, -0.112, 0.192), (0.054, 0.058, 0.058)))                     # chest (front Y -0.17)
    clay.add(E((0, -0.060, 0.200), (0.053, 0.072, 0.046)), blend=0.03)        # ribcage (belly up: bottom 0.154)
    clay.add(E((0, 0.0, 0.205), (0.044, 0.06, 0.04)), blend=0.03)             # waist / loin (tuck-up)
    clay.add(E((0, 0.047, 0.198), (0.050, 0.058, 0.048)), blend=0.028)       # pelvis / rump (top 0.246, back end Y 0.105)
    clay.add(E((0.034, -0.096, 0.198), (0.024, 0.04, 0.048), rot=(12, 0, 0)), blend=0.02, mirror=True)  # shoulders
    clay.add(E((0, -0.142, 0.165), (0.042, 0.030, 0.055)), blend=0.03)       # chest ruff mound (front -0.172)
    # brisket: the breastbone's front runs down between the front legs, so the cream bib reaches its V point
    # low between them (front drawing) on a smooth surface (cycle 6: replaces the chest spike cones)
    clay.add(E((0, -0.140, 0.133), (0.024, 0.021, 0.030)), blend=0.022)
    # --- neck and head (nose Y -0.24 Z 0.30, eye Z 0.318, crown Z 0.36, back of skull Y -0.10)
    clay.add(T(*HEAD["neck"]), blend=0.022)   # neck: joins the skull behind the jaw, so the throat stays under the jaw's rear
    hd = HEAD
    clay.add(E(*hd["cranium"]), blend=0.02)      # cranium: rounder and higher (front: the forehead rises well above the brows)
    clay.add(E(*hd["brow"]), blend=0.015)        # brow / frontal plane
    clay.add(E(*hd["cheek"]), blend=0.016, mirror=True)   # cheeks: under the eyes, not hanging jowls
    # snout: a fox's wedge, broad and deep where it meets the cheeks under the eyes, wider than tall, tapering
    # evenly to the small nose, its bridge a straight slope from below the eyes (user, cycle 4: "snout too
    # narrow, make a more fox shaped snout"); then the lower jaw under it and the soft rounded chin
    for c_, r_ in hd["snout"]:
        clay.add(E(c_, r_), blend=0.012)
    for c_, r_ in hd["jaw"]:
        clay.add(E(c_, r_), blend=0.010)
    clay.add(E((0, -0.118, 0.304), (0.038, 0.036, 0.038)), blend=0.022)      # nape
    for s in (1, -1):                                                            # eye seats: a shallow bed for the eye lens
        clay.sub(E((s * EYE_X, -0.199, 0.327), (0.0160, 0.0018, 0.0085), rot=(0, s * -12, s * 30)), blend=0.004)
    # stop / bridge between the eyes: the forehead runs down into the muzzle in front of the eyes, so
    # from the side the far eye hides behind it (side drawing: only its lashes show at the profile)
    clay.add(E((0, -0.199, 0.326), (0.012, 0.011, 0.017)), blend=0.010)
    # mouth corner crease
    for s in (1, -1):    # a shallow groove along the smile (the dark mouth line lies in it: face.build_mouth)
        mp = [(s * x, y, z) for x, y, z in MOUTH_SIDE]
        for a_, b_ in zip(mp[:-1], mp[1:]):
            clay.sub(C(a_, b_, 0.0009, 0.0009), blend=0.0008)
    rng = random.Random(7)
    # cheek fur: in both drawings the cheeks flare out behind the jaw into one soft, full ruff with two
    # rounded points (front: to x +-0.08 at the mouth's height; side: behind the jaw, pointing back and
    # down). Built as two broad soft wedges with rounded tips and wide blends, so the outline is one
    # smooth scalloped curve (cycle 6, user: "Smoothen model ... too literal copy": the four thin
    # needle cones read as torn, blocky spikes)
    for s in (1, -1):
        for a, b, r1, r2 in CHEEK_FUR:
            clay.add(C((s * a[0], a[1], a[2]), (s * b[0], b[1], b[2]), r1, r2), blend=CHEEK_BLEND)
    # (no nape locks, elbow tufts, belly fringe, chest-side ruff locks or chest spikes: the drawings paint
    # that fur as strokes on smooth forms; as geometry they were spikes on the chest and belly. The chest
    # is the smooth ruff mound above; its cream bib ends in a painted V (cream_field). Cycle 6, user:
    # "Remove spikes in belly")
    # --- legs, thighs, paws with toes and creases
    for key, (pts, rad) in leg_defs().items():
        clay.add(T(pts, rad, LEG_JOINT_BLEND), blend=0.008)
        sx = 1 if key.endswith("1") and not key.endswith("-1") else -1
        if key.startswith("h"):
            clay.add(E((sx * 0.038, pts[0][1] - 0.004, 0.172), (0.026, 0.05, 0.058), rot=(-25, 0, 0)), blend=0.025)
        px, py = pts[-1][0], pts[-1][1]
        clay.add(E((px, py - 0.006, 0.0125), (0.0165, 0.023, 0.0135)), blend=0.006)
        for k, dx in enumerate((-0.0105, -0.0036, 0.0036, 0.0105)):
            r = 0.0072 + (0.0011 if k in (1, 2) else 0) + rng.uniform(-0.0004, 0.0004)
            clay.add(S.sd_sphere((px + dx, py - 0.0245 + (0.0035 if k in (0, 3) else 0), 0.0082), r), blend=0.003)
        for dx in (-0.0072, 0.0, 0.0072):
            clay.sub(C((px + dx, py - 0.037, 0.011), (px + dx * 0.8, py - 0.017, 0.016), 0.0013, 0.0009), blend=0.001)
    clay.intersect(S.sd_halfspace((0, 0, 0.0), (0, 0, -1)))
    obj = clay.to_object("Body", symmetric=False)
    return obj, clay


# ============================================================================ MARK IMAGES
MARK_RES = 2048
MARK_SPAN = 0.72   # metres covered by the projection images
SIDE_Y0 = -0.36    # side image: u -> Y from SIDE_Y0, v -> Z from 0
FRONT_X0 = -0.36   # front image: u -> X from FRONT_X0


def side_strokes(rng):
    """Glowing markings on the flank (side-view Y, Z metres): haunch spiral, flames, back strokes,
    shoulder and leg streaks, cheek strokes; jittered per side."""
    j = lambda: rng.uniform(-0.003, 0.003)
    st = []
    # haunch spiral with its tail sweeping up toward the back
    sp = spiral((0.047 + j(), 0.172 + j()), 0.016, 1.3, math.pi * 0.9, -1, 1.05, 0.0, 60, 0.9)
    st.append((bez2((0.005, 0.232), (0.035, 0.228 + j()), (0.062, 0.205), sp[0]) + sp,
               np.concatenate([np.linspace(0.0015, 0.0042, 20), np.linspace(0.0042, 0.0018, 60)])))
    # flame strokes over the haunch, curling down the thigh
    st.append((bez2((-0.02, 0.236), (0.03, 0.245 + j()), (0.075, 0.215), (0.08, 0.16 + j())), [0.0015, 0.004, 0.0035, 0.0012]))
    st.append((bez2((0.06, 0.20), (0.078, 0.18), (0.083, 0.15), (0.072, 0.125 + j())), [0.0012, 0.0035, 0.003, 0.001]))
    st.append((bez2((0.02, 0.15), (0.03, 0.135), (0.048, 0.128), (0.056, 0.135)), [0.001, 0.003, 0.0025, 0.001]))
    st.append((bez2((0.075, 0.14), (0.085, 0.125), (0.086, 0.11), (0.08, 0.098)), [0.001, 0.0028, 0.0022, 0.0008]))
    # dots
    st.append(([(0.088, 0.195), (0.0885, 0.1945)], [0.004, 0.004]))
    st.append(([(0.064, 0.118 + j()), (0.0645, 0.1175)], [0.0032, 0.0032]))
    st.append(([(0.03, 0.12), (0.0305, 0.1195)], [0.0026, 0.0026]))
    # two long strokes along the back (shoulder to tail root)
    for k, (y0, y1, z) in enumerate([(-0.085, 0.06, 0.243), (-0.05, 0.035, 0.232)]):
        pts = [(y0 + (y1 - y0) * f, z + 0.004 * math.sin(f * 6 + k) + 0.006 * f) for f in np.linspace(0, 1, 30)]
        st.append((pts, list(np.sin(np.linspace(0.15, 3.0, 30)) * 0.0035 + 0.0008)))
    # shoulder and front leg streaks
    st.append((bez2((-0.105, 0.215), (-0.098, 0.195), (-0.095, 0.175), (-0.098, 0.155)), [0.001, 0.003, 0.0025, 0.001]))
    st.append((bez2((-0.09, 0.12), (-0.093, 0.10), (-0.094, 0.08), (-0.097, 0.06)), [0.001, 0.0025, 0.002, 0.0008]))
    # hind leg streak
    st.append((bez2((0.10, 0.09), (0.106, 0.075), (0.108, 0.06), (0.11, 0.045)), [0.001, 0.0025, 0.002, 0.0008]))
    # face: two pale strokes behind the eye, one on the crown
    # (side drawing: three short pale strokes behind the outer eye corner, rising toward the back)
    st.append(([(-0.160, 0.3355), (-0.1555, 0.3385), (-0.151, 0.3420)], [0.0004, 0.0012, 0.0003]))
    st.append(([(-0.157, 0.3290), (-0.1515, 0.3320), (-0.146, 0.3355)], [0.0004, 0.0013, 0.0003]))
    st.append(([(-0.155, 0.3110), (-0.1495, 0.3140), (-0.144, 0.3175)], [0.0004, 0.0011, 0.0003]))
    return st


def front_strokes():
    """Front-projected markings (X, Z): forehead flame, pale strokes beyond the outer eye corners."""
    st = []
    st.append((bez2((0.0, 0.3440), (0.0015, 0.3490), (-0.001, 0.3540), (0.0, 0.3590)), [0.0008, 0.0038, 0.0026, 0.0004]))
    for s in (1, -1):
        st.append((bez2((s * 0.005, 0.3440), (s * 0.010, 0.3490), (s * 0.011, 0.3530), (s * 0.008, 0.3570)), [0.0005, 0.0016, 0.0012, 0.0004]))
        # three short pale fur strokes beyond the outer corner of each eye (front drawing x 130-150 px)
        for (x0, z0), (x1, z1), w in (((0.047, 0.3335), (0.0525, 0.3275), 0.0011), ((0.0485, 0.3265), (0.0545, 0.3205), 0.0012),
                                      ((0.0495, 0.3200), (0.0540, 0.3165), 0.0009)):
            st.append(([(s * x0, z0), (s * (x0 + x1) / 2 + s * 0.0006, (z0 + z1) / 2), (s * x1, z1)], [0.0003, w, 0.0002]))
    return st


def mark_images():
    """marks: R = +X flank glow, G = -X flank glow, B = front glow. decal: R = front cream spots,
    G = side cream spots, B = front dark lines (mouth)."""
    n = MARK_RES
    c = (np.arange(n) + 0.5) / n * MARK_SPAN
    Ys, Zs = np.meshgrid(c + SIDE_Y0, c)
    Xf, Zf = np.meshgrid(c + FRONT_X0, c)
    marks = np.zeros((n, n, 3), np.float32)
    decal = np.zeros((n, n, 3), np.float32)
    px = MARK_SPAN / n
    for ch in (0, 1):
        rng = random.Random(100 + ch)
        for pts, w in side_strokes(rng):
            # the haunch moved forward 0.035 with the hind legs: strokes behind the loin follow it
            pts = [(y - 0.035 * min(max((y + 0.02) / 0.06, 0.0), 1.0), z) for y, z in pts]
            poly_paint(marks[..., ch], Ys, Zs, pts, np.asarray(w), 1.5 * px, halo=0.16, halo_w=0.0016)
    for pts, w in front_strokes():
        poly_paint(marks[..., 2], Xf, Zf, pts, w, 1.5 * px, halo=0.18, halo_w=0.0015)
    # (the cream brow markings are drawn in 3D in the fur shader: see brow_marking)
    # (cycle 4: the mouth is a 3D line on the muzzle, face.build_mouth, no longer a front-projected decal)
    return new_image("AF_marks", n, n, marks), new_image("AF_decal", n, n, decal)


# ============================================================================ MATERIALS
BROW_NODES = []   # Mapping nodes of the brow markings, set to the final scale in build()


def brow_frame(clay, body_bvh):
    """The cream brow marking above each eye (front drawing: centre X +-0.0214, 0.023 above the eye
    centre; 0.016 long, 0.009 wide, its inner end higher): centre on the head, axes (long, short,
    normal) in the head's tangent plane, for the +X side (the shader mirrors X)."""
    hit, _, _, _ = body_bvh.ray_cast(Vector((0.0214, -0.30, 0.350)), Vector((0.0, 1.0, 0.0)), 0.3)
    _, n = clay.project(np.array([tuple(hit)]))
    c, n = np.array(hit), n[0]
    d = np.array([-0.5, 0.0, 1.0])
    d1 = d - (d @ n) * n
    d1 /= np.linalg.norm(d1)
    d2 = np.cross(n, d1)
    R = Matrix((tuple(d1), tuple(d2), tuple(n))).transposed()
    return Vector(c), R.to_euler("XYZ"), Vector((0.0080, 0.0046, 0.006))


def brow_marking(nt):
    """Soft-edged cream oval on each brow, drawn in object space (X mirrored), one mark per side."""
    # the body's own position before the 0.50 m scale, from the projection attributes: object
    # coordinates move when the kit sets the origin (cycle 4: they had pushed the marks off the head)
    x = nt.math("ADD", nt.math("MULTIPLY", nt.attr("pxf"), MARK_SPAN), FRONT_X0)
    y = nt.math("ADD", nt.math("MULTIPLY", nt.attr("pys"), MARK_SPAN), SIDE_Y0)
    z = nt.math("MULTIPLY", nt.attr("pzs"), MARK_SPAN)
    mirrored = nt.combine(nt.math("ABSOLUTE", x), y, z)
    mp = nt.node("ShaderNodeMapping", vector_type="TEXTURE")
    nt.link(mirrored, mp.inputs["Vector"])
    BROW_NODES.append(mp)
    ln = nt.node("ShaderNodeVectorMath", operation="LENGTH")
    nt.link(mp.outputs[0], ln.inputs[0])
    return nt.maprange(ln.outputs["Value"], 1.0, 0.82)


def fur_material(name, marks, decal, cream):
    """Stylised painted fur: blue body (navy lower legs, light head) or cream (tan belly / patch);
    fur strokes in colour, roughness and bump; glow markings and decals from the projection images."""
    mat, tree, bsdf = kit.principled(name)
    nt = NT(tree)
    obj_co = nt.coords("Object")
    zh = nt.attr("zh")
    face = nt.attr("face")
    legm = nt.attr("legs")
    body_str = nt.noise(nt.scale_vec(obj_co, 160, 22, 160), 1.0, 4, 0.6)
    leg_str = nt.noise(nt.scale_vec(obj_co, 160, 160, 22), 1.0, 4, 0.6)
    strokes = nt.mixf(legm, body_str, leg_str)
    blotch = nt.noise(obj_co, 16.0, 3, 0.5)
    if not cream:
        base = nt.ramp(zh, [(0.0, "#3c4f76"), (0.03, "#41567d"), (0.07, "#4d6690"), (0.105, "#64819f"),
                            (0.14, "#7698b4"), (0.18, "#83a8bf"), (0.24, "#8db4cb"), (0.29, "#98c2d8"), (0.33, "#a3cfe3")])
        base = nt.mix(nt.math("MULTIPLY", face, 0.8), base, lin("#a6d3e6"))
    else:
        base = nt.ramp(zh, [(0.10, "#ada096"), (0.14, "#b6aaa1"), (0.19, "#c6bcb3"), (0.26, "#d3c7b9"), (0.30, "#dcd2c5")])
        tan = nt.attr("tan")
        base = nt.mix(tan, base, lin("#8f8079"))
        patch = nt.attr("patch")
        base = nt.mix(nt.math("MULTIPLY", patch, 0.85), base, lin("#85756e"))
    var = nt.ramp(blotch, [(0.3, (0.92, 0.93, 0.96, 1)), (0.5, (1, 1, 1, 1)), (0.7, (1.06, 1.05, 1.03, 1))])
    base = nt.mix(1.0, base, var, "MULTIPLY")
    strk = nt.ramp(strokes, [(0.35, (0.90, 0.92, 0.94, 1)), (0.5, (1, 1, 1, 1)), (0.68, (1.09, 1.08, 1.06, 1))])
    base = nt.mix(0.8, base, strk, "MULTIPLY")
    side_uv = nt.combine(nt.attr("pys"), nt.attr("pzs"))
    front_uv = nt.combine(nt.attr("pxf"), nt.attr("pzs"))
    ncomp = nt.sep(nt.coords("Normal"))   # object space: the kit turns the model on a turntable
    wside = nt.maprange(nt.math("ABSOLUTE", ncomp[0]), 0.15, 0.45)
    wfront = nt.maprange(nt.math("MULTIPLY", ncomp[1], -1.0), 0.2, 0.55)
    plus = nt.maprange(ncomp[0], -0.05, 0.05)
    mk_side = nt.rgb_sep(nt.image(marks, side_uv).outputs["Color"])
    mk_front = nt.rgb_sep(nt.image(marks, front_uv).outputs["Color"])
    side_glow = nt.mixf(plus, mk_side[1], mk_side[0])
    glow = nt.math("MAXIMUM", nt.math("MULTIPLY", side_glow, wside), nt.math("MULTIPLY", mk_front[2], wfront))
    dc_side = nt.rgb_sep(nt.image(decal, side_uv).outputs["Color"])
    dc_front = nt.rgb_sep(nt.image(decal, front_uv).outputs["Color"])
    creamspot = brow_marking(nt)
    darkline = nt.math("MULTIPLY", dc_front[2], wfront)
    if not cream:
        base = nt.mix(creamspot, base, lin("#e0d6c8"))
    base = nt.mix(darkline, base, lin("#2b2a3c"))
    base = nt.mix(nt.math("MULTIPLY", glow, 0.85), base, lin("#bdf0fb"))
    emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3fb8dc"), (1.0, "#a8f0ff")])
    rough = nt.math("ADD", nt.math("MULTIPLY", strokes, 0.12), 0.74)
    rough = nt.mixf(glow, rough, 0.45)
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.012
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.45, 0.0, 0.5), base, lin("#2c3a5e" if not cream else "#7e7470"))
    bump = nt.bump(strokes, 0.3, 0.0008)
    set_bsdf(nt, bsdf, base=base, rough=rough, emis_col=emis, emis_str=0.8, normal=bump)
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mat


# ============================================================================ BODY ATTRIBUTES AND CREAM
CREAM_NOISE = (0.0, 0.0)   # edge waviness of the cream marking: broad, fine (cycle 6: none; the drawing's colour
                           # boundaries are clean painted curves)
THROAT_WC = [0.0, 0.010, 0.032, 0.044, 0.046, 0.042, 0.034, 0.032]   # (cycle 4: throat narrower up to the jaw, blue neck sides)
HEAD_CREAM_Z = 0.292   # below this the head's cream is limited to the jaw front (neckcut in cream_field)
CREAM_ROUND = 0.006    # corner rounding of the cream regions (smooth max / min), metres


def smooth_profile(xk, yk, sigma=0.35):
    """A smooth curve through the knots (xk, yk): the polyline resampled densely and Gaussian
    smoothed (sigma in units of the mean knot spacing), so a boundary built from a few knots has no
    kinks at them (cycle 6: linear interpolation put a corner at every knot)."""
    xk, yk = np.asarray(xk, float), np.asarray(yk, float)
    xs = np.linspace(xk[0], xk[-1], 400)
    ys = np.interp(xs, xk, yk)
    sg = sigma * (xk[-1] - xk[0]) / (len(xk) - 1) / (xs[1] - xs[0])
    k = int(3 * sg) + 1
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sg) ** 2)
    w /= w.sum()
    pad = np.concatenate([np.full(k, ys[0]), ys, np.full(k, ys[-1])])
    ys = np.convolve(pad, w, mode="valid")
    return lambda x: float(np.interp(x, xs, ys))


def smax(*v, k=None):
    """Smooth maximum (polynomial): rounded corners where two boundaries meet."""
    k = CREAM_ROUND if k is None else k
    out = v[0]
    for b in v[1:]:
        h = max(k - abs(out - b), 0.0) / k
        out = max(out, b) + h * h * k * 0.25
    return out


def smin(*v, k=None):
    return -smax(*[-a for a in v], k=k)


HEAD_ZB = smooth_profile([-0.25, -0.225, -0.205, -0.185, -0.165, -0.145, -0.125, -0.105, -0.09],
                         [0.295, 0.299, 0.307, 0.313, 0.313, 0.307, 0.298, 0.286, 0.273])
CHEST_YB = smooth_profile([0.10, 0.13, 0.16, 0.20, 0.24, 0.28, 0.30], [-0.157, -0.147, -0.136, -0.124, -0.115, -0.105, -0.10])
CHEST_WC = smooth_profile([0.104, 0.115, 0.14, 0.18, 0.22, 0.26, 0.29, 0.30], THROAT_WC, sigma=0.25)
# the belly's cream top in the side view: one smooth line from behind the elbow, rising a little with
# the tuck-up toward the stifle (side drawing), instead of a flat cut at Z 0.152
BELLY_ZT = smooth_profile([-0.12, -0.08, -0.04, 0.0, 0.03, 0.05], [0.150, 0.151, 0.153, 0.157, 0.160, 0.158])


def cream_field(p):
    """Cream regions of the body, every boundary a smooth curve with rounded corners (cycle 6)."""
    x, y, z = p.x, p.y, p.z
    nz = CREAM_NOISE[0] * noise.noise(Vector((x * 90, y * 90, z * 90))) + CREAM_NOISE[1] * noise.noise(Vector((x * 260, y * 260, z * 260)))
    # head: below a line from the nose under the eye back to the cheek tufts
    zb = HEAD_ZB(y)
    zb += 0.006 * float(smoothstep(abs(x), 0.036, 0.056))      # outer cheeks: cream up to the eye's outer corner
    # the head's cream stops at the jaw: under the cheeks only the front of the jaw is cream, the sides of
    # the neck stay blue (front and side drawings); the throat strip comes from the chest part below
    below = min(1.0, max(0.0, (HEAD_CREAM_Z - z) / 0.004))
    neckcut = y - (-0.09 - below * (0.06 + 2.0 * max(0.0, HEAD_CREAM_Z - z)))
    head = max(z - zb, y + 0.09, 0.248 - z, neckcut)
    wb = 0.004 + 0.012 * min(1.0, max(0.0, (y + 0.24) / 0.05))
    bridge = max(abs(x) - wb, 0.2965 - z, y + 0.20)
    head = max(head, -bridge)
    # throat and chest front: cream in front of the boundary, within the bib, ending below in the painted
    # V between the front legs (front drawing), every side a smooth curve
    chest = smax(y - CHEST_YB(z), abs(x) - CHEST_WC(z), 0.104 - z, z - 0.30)
    # belly underside and inner thighs
    belly = smax(z - BELLY_ZT(y), 0.11 - z, y - 0.045, -0.115 - y, abs(x) - 0.032, k=0.008)
    # patch under the tail
    patch = smax(abs(x) - 0.019, 0.118 - z, z - 0.195, 0.068 - y, k=0.004)
    return min(head, smin(chest, belly, k=0.010), patch) + nz


def body_attributes(obj):
    co = verts_np(obj)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    set_attr(obj, "zh", z)
    face = smoothstep(-y, 0.14, 0.17) * smoothstep(z, 0.288, 0.318)
    set_attr(obj, "face", face)
    legs = smoothstep(0.14 - z, 0.0, 0.02)
    set_attr(obj, "legs", legs)
    set_attr(obj, "tan", smoothstep(0.17 - z, 0.0, 0.025) * smoothstep(y, -0.13, -0.09) * smoothstep(0.06 - y, 0.0, 0.02))
    set_attr(obj, "patch", smoothstep(y, 0.066, 0.09) * smoothstep(z, 0.12, 0.14) * smoothstep(0.022 - np.abs(x), 0.0, 0.008))
    set_attr(obj, "pys", (y - SIDE_Y0) / MARK_SPAN)
    set_attr(obj, "pzs", z / MARK_SPAN)
    set_attr(obj, "pxf", (x - FRONT_X0) / MARK_SPAN)




# ============================================================================ SURFACE RELAX
RELAX = (10, 0.50, -0.53)   # Taubin passes, lambda, mu (cycle 6: smooths the remesh's quad-scale lumps and the
                            # clay's small creases without shrinking the forms)


def relax_weight(co):
    """How much each vertex may be relaxed: 0 on the approved face (eye beds, stop, snout, nose, mouth,
    jaw: built and judged at mm precision) and on the toes and their creases, 1 elsewhere, soft between."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    face = smoothstep(-y, 0.165, 0.185) * smoothstep(z, 0.268, 0.282)       # muzzle, eyes, stop, jaw front
    toes = 1.0 - smoothstep(z, 0.022, 0.034)
    return np.clip(1.0 - np.maximum(face, toes), 0.0, 1.0)


def relax_surface(obj, passes=None, lam=None, mu=None):
    """Taubin (lambda | mu) smoothing of the body mesh, weighted by relax_weight: a low-pass filter on the
    surface that removes bumps a few faces wide (remesh noise, small blend creases) and keeps the volume
    and the large forms (a plain Laplacian smooth would shrink the thin legs)."""
    passes, lam0, mu0 = RELAX if passes is None else (passes, lam, mu)
    me = obj.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ed)
    ed = ed.reshape(-1, 2)
    deg = np.bincount(ed.ravel(), minlength=n).astype(float)
    w = relax_weight(co)[:, None]
    for _ in range(passes):
        for f in (lam0, mu0):
            acc = np.zeros_like(co)
            np.add.at(acc, ed[:, 0], co[ed[:, 1]])
            np.add.at(acc, ed[:, 1], co[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            co = co + f * w * (avg - co)
    me.vertices.foreach_set("co", co.ravel())
    me.update()
