"""The face: eyes (domed lens on the finished body: EyeBed), eyelid lines, nose."""
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
from aethel_fox_parts.common import EYE_X, NOSE_C, MOUTH_SIDE, MOUTH_PHILTRUM, catmull, dark_material, NT, S, lin, set_bsdf, sweep  # noqa: E402

def eye_material():
    """The eye's surface from its own UVs (x outward, y up, metres in the opening): the eyeball's
    warm grey-white sclera, shaded under the upper eyelid and a little warmer at the tear duct; a
    large grey iris (IRIS_R, centred IRIS_C toward the nose) dark slate on top where the lid shades
    it, lighter below with a pale crescent (light through the cornea), fine radial fibres and a dark
    limbal ring; a big dark pupil; the cornea's reflection: one white catch light on the pupil's upper
    inner side and a faint small one low on the outer side. Glossy (cornea)."""
    mat, tree, bsdf = kit.principled("M_eye")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    x = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[0], 0.5), 2 * EYE_A)
    y = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[1], 0.5), 2 * EYE_BT)
    ix = nt.math("DIVIDE", nt.math("SUBTRACT", x, IRIS_C[0]), IRIS_R[0])
    iy = nt.math("DIVIDE", nt.math("SUBTRACT", y, IRIS_C[1]), IRIS_R[1])
    r = nt.math("SQRT", nt.math("ADD", nt.math("POWER", ix, 2.0), nt.math("POWER", iy, 2.0)))   # 1 at the iris edge
    ang = nt.node("ShaderNodeMath", operation="ARCTAN2")
    nt.link(iy, ang.inputs[0]); nt.link(ix, ang.inputs[1])
    fib = nt.noise(nt.combine(nt.math("MULTIPLY", ang.outputs[0], 4.0), nt.math("MULTIPLY", r, 0.8)), 5.0, 2, 0.5)
    vert = nt.math("ADD", nt.math("MULTIPLY", iy, 0.5), 0.5)                     # 0 iris bottom .. 1 top
    yf = nt.math("ADD", nt.math("MULTIPLY", nt.math("DIVIDE", y, EYE_BT), 0.5), 0.5)  # 0 bottom .. 1 top of the opening
    sclera = nt.ramp(yf, SCLERA)
    duct = nt.maprange(x, -EYE_A * 0.95, -EYE_A * 0.6)                           # tear duct: inner corner warmer
    sclera = nt.mix(nt.math("MULTIPLY", duct, DUCT_WARM), sclera, lin("#c9b7b2"))
    iris = nt.ramp(vert, [(0.0, "#b3b7c6"), (0.14, "#9aa1b7"), (0.38, "#6c7389"), (0.62, "#4b5068"), (0.85, "#32344a"), (1.0, "#26273a")])
    iris = nt.mix(nt.math("MULTIPLY", nt.maprange(fib, 0.42, 0.7), 0.3), iris, lin("#a9b2c9"))
    cres = nt.math("MULTIPLY", nt.math("MULTIPLY", nt.maprange(r, 0.5, 0.62), nt.maprange(r, 0.92, 0.8)),
                   nt.maprange(iy, -0.25, -0.65))
    iris = nt.mix(nt.math("MULTIPLY", cres, 0.55), iris, lin("#c2c6d3"))       # pale crescent low in the iris
    col = nt.mix(nt.maprange(r, 0.97, 1.03), iris, sclera)                       # iris -> sclera
    col = nt.mix(nt.math("MULTIPLY", nt.maprange(r, 0.84, 0.96), nt.maprange(r, 1.04, 0.98)), col, lin("#23253a"))  # limbal ring
    col = nt.mix(nt.maprange(r, 0.50, 0.44), col, lin("#1b1a28"))               # pupil
    lid = nt.maprange(yf, 0.84, 1.0)                                             # upper eyelid shadow on the eyeball
    col = nt.mix(nt.math("MULTIPLY", lid, 0.45), col, lin("#25263a"))
    hx = nt.math("SUBTRACT", x, IRIS_C[0] - 0.0021)
    hy = nt.math("SUBTRACT", y, IRIS_C[1] + 0.0040)
    hl = nt.math("SQRT", nt.math("ADD", nt.math("POWER", hx, 2.0), nt.math("POWER", hy, 2.0)))
    hlm = nt.maprange(hl, 0.0023, 0.0018)
    hx2 = nt.math("SUBTRACT", x, IRIS_C[0] + 0.0034)
    hy2 = nt.math("SUBTRACT", y, IRIS_C[1] - 0.0052)
    hl2 = nt.math("SQRT", nt.math("ADD", nt.math("POWER", hx2, 2.0), nt.math("POWER", hy2, 2.0)))
    hlm2 = nt.math("MULTIPLY", nt.maprange(hl2, 0.0010, 0.0006), 0.15)
    col = nt.mix(hlm, col, lin("#fbfdff"))
    col = nt.mix(hlm2, col, lin("#dfe7f3"))
    set_bsdf(nt, bsdf, base=col, rough=nt.math("ADD", nt.math("MULTIPLY", fib, 0.05), 0.24),
             emis_col=nt.mix(nt.math("MAXIMUM", hlm, hlm2), lin("#000000"), lin("#ffffff")), emis_str=0.8)
    return mat


# ============================================================================ EYES, NOSE
# The eye of an anime-style fox, measured on the front and side drawings (cycle 2): the opening is
# 0.029 long and 0.021 tall (front: 60 x 53 px seen obliquely, side: 59 x 41 px), its long axis
# rising 20 deg from the low, pointed inner corner (tear duct) to the higher outer corner, which the
# upper eyelid line carries on into a wing. A big grey iris (0.016 x 0.020, upper lid over its top)
# sits toward the nose, the warm grey eye white shows behind it, a white catch light on the pupil's
# upper inner side. Upper eyelid line thick, lower eyelid line thin, both run the whole opening.
# (cycle 4, from 12 variants measured against the crops (work parts/eyepts.py): the opening longer and lower,
# wrapping round the head so the side view sees a long almond, the inner corner dropped to the eye's lowest point,
# the outer corner raised; front 164 x 116 px vs 166 x 117 in the 0.12 m crop)
EYE_A, EYE_BT, EYE_BB = 0.0165, 0.0076, 0.0066   # opening half-length, upper and lower half-height
EYE_TILT = 16.0                                   # deg, outer corner up
IRIS_C = (-0.0042, 0.0000)                        # iris centre in the eye (x outward, y up)
IRIS_R = (0.0086, 0.0098)                         # iris half-width, half-height
EYE_TURN = 0.25                                   # how far the eye normal turns outward from the face normal
EYE_DOME = 0.0012                                 # lens dome height at the centre
EYE_TOPK = 0.72         # how far the upper eyelid's top is carried high toward the outer corner
EYE_PEAK = 0.0          # shifts the upper arch's peak toward the outer corner (0 = as built in cycle 3)
EYE_INNER_FLAT = 0.15   # lowers the upper eyelid over the inner half (the line rises from the tear duct)
EYE_OUTER_LIFT = 0.003  # raises the outer corner (both eyelids) above the tilted axis
EYE_INNER_DROP = 0.005  # drops the inner corner (tear duct) below the tilted axis: the lowest point of the eye
LID_UP_R = 0.00135      # upper eyelid line: added half-thickness over the top
LID_LO_R = (0.0002, 0.00008, 0.0004)   # lower eyelid line: base, middle swell, tear-duct thickening
LID_LO_COL = "#4b5068"  # lower eyelid line colour (the drawing's is a thinner grey-navy)
LID_LO_HI = "#5d627a"
WING = ((1.14, 0.13), (1.30, 0.25), (1.46, 0.35), (1.60, 0.43))   # wing points (x / EYE_A, y / EYE_BT)
SCLERA = [(0.0, "#c9c6c4"), (0.3, "#d6d3d1"), (0.62, "#cccac9"), (0.82, "#a9a8b0"), (1.0, "#77768a")]   # cool light grey (side crop #cac6c7)
DUCT_WARM = 0.2


def eye_frame(clay, side):
    """Eye centre on the head surface (front view: X +-0.031, Z 0.327 before the 0.50 m scale), the
    surface normal turned a little outward, and the eye's long axis tilted EYE_TILT (outer corner up)."""
    p, n = clay.project(np.array([[side * EYE_X, -0.197, 0.327]]))
    p, n = p[0], n[0]
    n = n + np.array([side * EYE_TURN, -0.1, 0.0])
    n /= np.linalg.norm(n)
    up = np.array([0.0, 0.0, 1.0])
    e_up = up - (up @ n) * n
    e_up /= np.linalg.norm(e_up)
    e_long = np.cross(e_up, n)
    if e_long[0] * side < 0:
        e_long = -e_long
    sl = math.radians(EYE_TILT)
    e_l = e_long * math.cos(sl) + e_up * math.sin(sl)
    e_u = -e_long * math.sin(sl) + e_up * math.cos(sl)
    return p, n, e_l, e_u


def eye_opening(theta):
    """Outline of the eye opening in the eye frame (x outward along e_l, y up along e_u): a full
    upper eyelid arc, a flatter lower eyelid, the inner corner (tear duct) pointed and dropped, the
    outer corner pointed and a little raised."""
    c, s_ = np.cos(theta), np.sin(theta)
    b = np.where(s_ > 0, EYE_BT, EYE_BB)
    x = EYE_A * c
    k = np.where(c < 0, 0.75, 0.35) * np.abs(c) ** 2          # corner sharpness: tear duct pointed
    y = b * s_ * np.abs(s_) ** k * (1 - 0.18 * c * c)
    # upper eyelid: steep rise from the tear duct, the top carried long and high toward the outer
    # corner (drawing: a long, nearly straight top line running on into the wing), not a round dome
    top = s_ > 0
    y = np.where(top, y * (1 - EYE_INNER_FLAT * np.clip(-c, 0, 1)) + EYE_TOPK * EYE_BT * s_ * np.clip(c + EYE_PEAK, 0, 1) * (1 - c * c), y) - EYE_INNER_DROP * np.clip(-c, 0, 1) ** 2 + EYE_OUTER_LIFT * np.clip(c, 0, 1) ** 2
    return x, y


class EyeBed:
    """Where the eye and its eyelid lines lie: heights along the eye normal above the eye plane,
    measured on the finished body mesh (ray cast, so nothing of the body pokes through the eye)
    and smoothed into one quadratic surface under the eye."""

    def __init__(self, body_bvh, clay, side):
        self.side = side
        self.p, self.n, self.el, self.eu = eye_frame(clay, side)
        self.bvh = body_bvh
        th = np.linspace(0, 2 * math.pi, 48, endpoint=False)
        bx, by = eye_opening(th)
        xs, ys = [], []
        for k in np.linspace(0.0, 1.0, 9):
            xs.append(bx * k)
            ys.append(by * k)
        X, Y = np.concatenate(xs), np.concatenate(ys)
        H = self.body_h(X, Y)
        self.coef = np.linalg.lstsq(self._basis(X, Y), H, rcond=None)[0]

    @staticmethod
    def _basis(X, Y):
        X, Y = np.asarray(X, float), np.asarray(Y, float)
        return np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y], -1)

    def body_h(self, X, Y):
        out = []
        for x, y in zip(np.atleast_1d(X), np.atleast_1d(Y)):
            o = self.p + self.el * x + self.eu * y + self.n * 0.03
            hit, _, _, _ = self.bvh.ray_cast(Vector(o), Vector(-self.n), 0.08)
            out.append((np.array(hit) - self.p) @ self.n if hit is not None else 0.0)
        return np.array(out)

    def lens_h(self, X, Y):
        """The eye's bed: the smooth fitted face, or the face itself where it rises above the fit
        (so it never cuts into the eye), plus 0.4 mm."""
        face = self.body_h(X, Y)
        return face + np.clip(self._basis(X, Y) @ self.coef - face, 0.0, 0.0006) + 0.0004

    def point(self, X, Y, h):
        X, Y, h = (np.asarray(a, float) for a in (X, Y, h))
        return self.p[None, :] + self.el[None, :] * X[:, None] + self.eu[None, :] * Y[:, None] + self.n[None, :] * h[:, None]


def build_eye(bed, mat):
    """The eye: a closed, gently domed lens over the opening (1.3 mm at the centre), lying on the
    smoothed bed so the face never cuts into it; its rim turns down 1 mm into the head. UVs map the
    opening in metres (x, y) for the iris shader."""
    M, K = 48, 10
    th = np.linspace(0, 2 * math.pi, M, endpoint=False)
    bx, by = eye_opening(th)
    ks = np.linspace(1.0 / K, 1.0, K)
    X = np.r_[0.0, (ks[:, None] * bx[None, :]).ravel()]
    Y = np.r_[0.0, (ks[:, None] * by[None, :]).ravel()]
    kk = np.r_[0.0, np.repeat(ks, M)]
    h = bed.lens_h(X, Y) + EYE_DOME * (1 - kk ** 2)
    front = bed.point(X, Y, h)
    rimp = bed.point(bx, by, bed.lens_h(bx, by) - 0.0012)
    back_c = bed.point([0.0], [0.0], bed.lens_h([0.0], [0.0]) - 0.002)[0]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    fv = [bm.verts.new(Vector(v)) for v in front]
    bc = bm.verts.new(Vector(back_c))
    rim = [bm.verts.new(Vector(v)) for v in rimp]

    def uv(i):
        return (0.5 + X[i] / (2 * EYE_A), 0.5 + Y[i] / (2 * EYE_BT))
    for j in range(M):
        j2 = (j + 1) % M
        f = bm.faces.new((fv[0], fv[1 + j], fv[1 + j2]))
        for lp, idx in zip(f.loops, (0, 1 + j, 1 + j2)):
            lp[uvl].uv = uv(idx)
        for k in range(K - 1):
            a, b = 1 + k * M + j, 1 + k * M + j2
            c, d = 1 + (k + 1) * M + j2, 1 + (k + 1) * M + j
            f = bm.faces.new((fv[a], fv[d], fv[c], fv[b]))
            for lp, idx in zip(f.loops, (a, d, c, b)):
                lp[uvl].uv = uv(idx)
        o1, o2 = 1 + (K - 1) * M + j, 1 + (K - 1) * M + j2
        f = bm.faces.new((fv[o1], rim[j], rim[j2], fv[o2]))
        for lp, idx in zip(f.loops, (o1, o1, o2, o2)):
            lp[uvl].uv = uv(idx)
        f = bm.faces.new((rim[j2], rim[j], bc))
        for lp in f.loops:
            lp[uvl].uv = (0.5, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    obj = kit.mesh_object(f"eye_{'left' if bed.side > 0 else 'right'}", bm, mat)
    obj["keep_uv"] = True
    return obj


def build_eyelids(bed, mat):
    """The eyelid lines drawn round the eye: the upper eyelid a thick dark line from the tear duct
    over the top to the outer corner, carried on past it into a tapered wing that rises outward
    (front and side drawings); the lower eyelid a thin line along the whole lower edge, thicker at
    the tear duct where both meet. Each lies on whichever is higher, the eye or the face, so it
    covers the eye's edge and never floats."""
    name = "left" if bed.side > 0 else "right"
    out = []
    # upper eyelid: from just past the tear duct (theta pi + 0.12) over the top to the outer corner
    th = np.linspace(math.pi + 0.12, 0.0, 34)
    bx, by = eye_opening(th)
    pts = [(x * 1.015, y * 1.03 + 0.0003) for x, y in zip(bx, by)]
    pts += [(EYE_A * wx, EYE_BT * wy) for wx, wy in WING]
    tt = np.linspace(0, 1, len(pts))
    rv = 0.00045 + LID_UP_R * np.sin(np.clip(tt * 1.12, 0, 1) * math.pi * 0.92) ** 0.55
    rv[-5:] = [0.0016, 0.0013, 0.0009, 0.00045, 0.0]
    # lower eyelid: from the outer corner along the bottom to the tear duct
    th2 = np.linspace(-0.05, -math.pi - 0.12, 26)
    bx2, by2 = eye_opening(th2)
    pts2 = [(x * 1.01, y * 1.02 - 0.0002) for x, y in zip(bx2, by2)]
    t2 = np.linspace(0, 1, len(pts2))
    rv2 = LID_LO_R[0] + LID_LO_R[1] * np.sin(t2 * math.pi) + LID_LO_R[2] * t2 ** 4
    m_lo = bpy.data.materials.get("M_eyelid_lower") or dark_material("M_eyelid_lower", LID_LO_COL, 0.6, LID_LO_HI)
    rv2[0] = 0.0
    for part, pp, rr, mm in (("upper", pts, rv, mat), ("lower", pts2, rv2, m_lo)):
        X = np.array([q[0] for q in pp])
        Y = np.array([q[1] for q in pp])
        k = np.array([float(np.hypot(x / EYE_A, y / (EYE_BT if y > 0 else EYE_BB))) for x, y in zip(X, Y)])
        hb = bed.body_h(X, Y)
        hl = np.where(k < 1.35, bed.lens_h(X, Y), -1.0)
        ru = np.asarray(rr) * 0.5
        h = np.maximum(hb, hl) + ru * 0.6 + 0.00015
        P = bed.point(X, Y, h)
        o, _ = sweep(f"eyelid_{part}_{name}", P, ru, np.asarray(rr), 8, mm, hint=np.tile(bed.n, (len(P), 1)))
        out.append(o)
    return out


def build_nose(mat):
    """The nose: a small leathery pad, a rounded inverted triangle from the front (wide rounded top, softly
    pointed bottom running into the philtrum), a rounded tip from the side; no nostril lobes in this style."""
    cx, cy, cz = NOSE_C
    clay = S.Clay((-0.016, cy - 0.014, cz - 0.012), (0.016, cy + 0.016, cz + 0.013), voxel=0.0007)
    clay.add(S.sd_ellipsoid((0, cy, cz + 0.0012), (0.0088, 0.0060, 0.0042)))                 # wide top of the pad
    clay.add(S.sd_ellipsoid((0, cy - 0.0004, cz - 0.0022), (0.0042, 0.0052, 0.0034)), blend=0.003)   # rounded point below
    clay.add(S.sd_ellipsoid((0, cy + 0.003, cz + 0.0030), (0.0070, 0.0055, 0.0030)), blend=0.002)    # bridge end over it
    for s in (1, -1):      # the nostril slits: only a hint, low on each side
        clay.sub(S.sd_ellipsoid((s * 0.0042, cy - 0.0050, cz - 0.0008), (0.0012, 0.0010, 0.0006), rot=(0, 0, s * 30)), blend=0.0006)
    obj = clay.to_object("Nose", symmetric=False)
    obj.data.materials.append(mat)
    return obj


MOUTH_W = 0.0010   # mouth line width under the nose (drawing ~1.3 mm at 0.50 m)


def build_mouth(body_bvh, mat):
    """The mouth: a thin dark line in the groove of the muzzle, from under the nose down the philtrum, then
    each side curving back and up into a lifted corner (the drawings' smile), lying on the finished body
    surface (nearest point + 0.25 mm along its normal), thickest under the nose, tapering at the corners."""
    out = []
    for s in (1, -1):
        pts = list(MOUTH_PHILTRUM) + [(s * x, y, z) for x, y, z in MOUTH_SIDE]
        P = np.array(catmull(np.array(pts), 6))
        Q, N = [], []
        for p_ in P:
            hit, n, _, _ = body_bvh.find_nearest(Vector(p_), 0.02)
            if hit is None:
                hit, n = Vector(p_), Vector((0.0, -1.0, 0.0))
            Q.append(np.array(hit) + np.array(n) * 0.00025)
            N.append(np.array(n))
        Q = np.array(Q)
        tt = np.linspace(0, 1, len(Q))
        w = MOUTH_W * (1.0 - 0.7 * tt ** 2) + 0.0001
        w[-1] = 0.0
        o, _ = sweep(f"mouth_{'left' if s > 0 else 'right'}", Q, w * 0.45, w, 6, mat, hint=np.array(N))
        out.append(o)
    return out
