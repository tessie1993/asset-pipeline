"""Lumina Warden (Phase 3 evolution of the blue fox): a slender stylised fox standing on all four
legs, huge star-speckled ears, cream chest ruff under a silver filigree collar with a glowing
rhombus crystal, iridescent shoulder feathers and five banded tails coiling into spiral lobes,
one carrying a glowing constellation.

Coordinates: metres, +Z up, the fox faces -Y, its left side is +X (the side seen in the main side
view, az 90). Y = (side-view metres from the nose tip) - 0.62. Every size comes from the side view
(1353 px per metre, height 1.00 m to the ear tip), widths from the front (1500 px/m) and back
(1382 px/m) views; see the notes' Analysis.
"""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import kit  # noqa: E402

S = kit.skill("scenario-blender-sculpting", "bx_sculpt")

RNG = random.Random(4417)
V = Vector

# ----------------------------------------------------------------------------- colours
def hexrgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]  # sRGB -> linear


def lin(h):
    return (*hexrgb(h), 1.0)


# ----------------------------------------------------------------------------- node helpers
class NT:
    """Tiny node-tree builder."""

    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links
        self.x = -1800

    def node(self, kind, **props):
        nd = self.n.new(kind)
        for k, v in props.items():
            setattr(nd, k, v)
        nd.location = (self.x, 0)
        self.x += 40
        return nd

    def link(self, a, b):
        self.l.new(a, b)

    def attr(self, name):
        return self.node("ShaderNodeAttribute", attribute_name=name).outputs["Fac"]

    def val(self, v):
        nd = self.node("ShaderNodeValue")
        nd.outputs[0].default_value = v
        return nd.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        nd = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                nd.inputs[i].default_value = x
            else:
                self.link(x, nd.inputs[i])
        return nd.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_result=True)
        for idx, x in ((0, fac), (6, a), (7, b)):
            if isinstance(x, (int, float)):
                nd.inputs[idx].default_value = x
            elif isinstance(x, tuple):
                nd.inputs[idx].default_value = x
            else:
                self.link(x, nd.inputs[idx])
        return nd.outputs[2]

    def mixf(self, fac, a, b):
        nd = self.node("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        for idx, x in ((0, fac), (2, a), (3, b)):
            if isinstance(x, (int, float)):
                nd.inputs[idx].default_value = x
            else:
                self.link(x, nd.inputs[idx])
        return nd.outputs[0]

    def ramp(self, fac, stops, interp="LINEAR"):
        nd = self.node("ShaderNodeValToRGB")
        cr = nd.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = lin(stops[0][1]) if isinstance(stops[0][1], str) else stops[0][1]
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = lin(col) if isinstance(col, str) else col
        self.link(fac, nd.inputs[0])
        return nd.outputs[0]

    def maprange(self, x, a, b, c=0.0, d=1.0, smooth=True):
        if a > b:
            a, b, c, d = b, a, d, c
        nd = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP" if smooth else "LINEAR", clamp=True)
        self.link(x, nd.inputs[0])
        nd.inputs[1].default_value, nd.inputs[2].default_value = a, b
        nd.inputs[3].default_value, nd.inputs[4].default_value = c, d
        return nd.outputs[0]

    def noise(self, vec, scale, detail=3.0, rough=0.55, out="Fac"):
        nd = self.node("ShaderNodeTexNoise")
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        if vec is not None:
            self.link(vec, nd.inputs["Vector"])
        return nd.outputs[out]

    def coords(self, kind="Object"):
        return self.node("ShaderNodeTexCoord").outputs[kind]

    def scale_vec(self, vec, sx, sy, sz):
        nd = self.node("ShaderNodeVectorMath", operation="MULTIPLY")
        self.link(vec, nd.inputs[0])
        nd.inputs[1].default_value = (sx, sy, sz)
        return nd.outputs[0]

    def combine(self, x, y, z=0.0):
        nd = self.node("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def sep(self, vec):
        nd = self.node("ShaderNodeSeparateXYZ")
        self.link(vec, nd.inputs[0])
        return nd.outputs

    def image(self, img, vec, interp="Linear"):
        nd = self.node("ShaderNodeTexImage", image=img, interpolation=interp, extension="EXTEND")
        self.link(vec, nd.inputs["Vector"])
        return nd

    def rgb_sep(self, col):
        nd = self.node("ShaderNodeSeparateColor")
        self.link(col, nd.inputs[0])
        return nd.outputs

    def bump(self, height, strength, distance, normal=None):
        nd = self.node("ShaderNodeBump")
        nd.inputs["Strength"].default_value = strength
        nd.inputs["Distance"].default_value = distance
        self.link(height, nd.inputs["Height"])
        if normal is not None:
            self.link(normal, nd.inputs["Normal"])
        return nd.outputs["Normal"]


def set_bsdf(nt, bsdf, base=None, rough=None, metal=None, emis_col=None, emis_str=None, normal=None):
    for key, val in (("Base Color", base), ("Roughness", rough), ("Metallic", metal),
                     ("Emission Color", emis_col), ("Emission Strength", emis_str), ("Normal", normal)):
        if val is None:
            continue
        if isinstance(val, (int, float, tuple)):
            bsdf.inputs[key].default_value = val
        else:
            nt.link(val, bsdf.inputs[key])


# ----------------------------------------------------------------------------- images
def new_image(name, w, h, data):
    """Float image from an (h, w, 4) or (h, w, 3) array, Non-Color."""
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"   # before the pixels: changing it regenerates a generated image
    if data.shape[2] == 3:
        data = np.concatenate([data, np.ones((h, w, 1), np.float32)], 2)
    img.pixels.foreach_set(np.ascontiguousarray(data, np.float32).ravel())
    img.pack()
    return img


def seg_dist(P, a, b):
    """Distance from points P (..., 2 or 3) to segment ab."""
    ab = b - a
    t = np.clip(((P - a) * ab).sum(-1) / max(float(ab @ ab), 1e-12), 0, 1)
    return np.linalg.norm(P - (a + t[..., None] * ab), axis=-1)


def poly_paint(chan, X, Y, pts, widths, soft, halo=0.0, halo_w=0.0, value=1.0):
    """Paint a stroke along polyline pts (metres) with per-point widths into channel chan whose
    pixel centres sit at metric coordinates X, Y (same shape). Max-composited."""
    pts = np.asarray(pts, float)
    if len(pts) < 2:
        return
    widths = np.atleast_1d(np.asarray(widths, float))
    if len(widths) != len(pts):
        widths = np.interp(np.linspace(0, 1, len(pts)), np.linspace(0, 1, len(widths)), widths)
    pad = float(widths.max()) + soft + halo_w * 3 + 1e-4
    lo, hi = pts.min(0) - pad, pts.max(0) + pad
    sel = (X >= lo[0]) & (X <= hi[0]) & (Y >= lo[1]) & (Y <= hi[1])
    if not sel.any():
        return
    P = np.stack([X[sel], Y[sel]], -1)
    best = np.full(len(P), 1e9)
    wbest = np.zeros(len(P))
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        t = np.clip(((P - a) * ab).sum(-1) / max(float(ab @ ab), 1e-12), 0, 1)
        d = np.linalg.norm(P - (a + t[:, None] * ab), axis=-1)
        w = widths[i] + (widths[i + 1] - widths[i]) * t
        better = d - w / 2 < best - wbest / 2
        best = np.where(better, d, best)
        wbest = np.where(better, w, wbest)
    edge = best - wbest / 2
    core = np.clip(0.5 - edge / max(soft, 1e-6), 0, 1)
    val = core * value
    if halo > 0:
        val = np.maximum(val, halo * value * np.exp(-np.maximum(edge, 0) / max(halo_w, 1e-6)) * (edge > -1))
    chan[sel] = np.maximum(chan[sel], val)


def spiral(c, r0, turns, start_ang, direction=1, squash=1.0, rot=0.0, n=60, power=1.0):
    """Points of a spiral (outer end first) around c in 2D."""
    out = []
    ca, sa = math.cos(rot), math.sin(rot)
    for i in range(n):
        f = i / (n - 1)
        r = r0 * (1 - f) ** power
        a = start_ang + direction * f * turns * 2 * math.pi
        x, y = r * math.cos(a), r * math.sin(a) * squash
        out.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
    return out


def bez2(p0, p1, p2, p3, n=20):
    return [tuple(v) for v in S.bezier(p0, p1, p2, p3, n)]


# ----------------------------------------------------------------------------- swept tubes
def frames(P, hint=None):
    """Tangents and rotation-minimising normals along P (N,3); hint = vector or (N,3) to aim normals."""
    P = np.asarray(P, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    N = np.zeros_like(P)
    if hint is not None and np.ndim(hint) == 2:
        H = np.asarray(hint, float)
        for i in range(len(P)):
            n = H[i] - (H[i] @ T[i]) * T[i]
            N[i] = n / (np.linalg.norm(n) + 1e-12)
    else:
        h = np.asarray(hint if hint is not None else (0.0, 0.0, 1.0), float)
        n = h - (h @ T[0]) * T[0]
        if np.linalg.norm(n) < 1e-6:
            n = np.cross(T[0], (1.0, 0.0, 0.0))
        N[0] = n / np.linalg.norm(n)
        for i in range(1, len(P)):
            n = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
            N[i] = n / (np.linalg.norm(n) + 1e-12)
    B = np.cross(T, N)
    return T, N, B


def sweep(name, P, ru, rv, M, mat, hint=None, uv_rect=(0, 0, 1, 1), closed=False, tip=True, start_cap=True,
          attrs=None):
    """Tube through P with elliptic section: radius ru along the normal, rv along the binormal.
    Returns (obj, grid) where grid = (rings (N,M,3), ring normals (N,M,3)). UVs: u along the path,
    v around, inside uv_rect = (u0, v0, u1, v1)."""
    P = np.asarray(P, float)
    n = len(P)
    ru = np.broadcast_to(np.asarray(ru, float), (n,)).copy()
    rv = np.broadcast_to(np.asarray(rv, float), (n,)).copy()
    if closed:
        P2 = np.concatenate([P[-1:], P, P[:1]])
        T, N, B = frames(P2, hint)
        T, N, B = T[1:-1], N[1:-1], B[1:-1]
    else:
        T, N, B = frames(P, hint)
    ang = np.arange(M) / M * 2 * math.pi
    ca, sa = np.cos(ang), np.sin(ang)
    rings = P[:, None, :] + N[:, None, :] * (ru[:, None] * ca)[..., None] + B[:, None, :] * (rv[:, None] * sa)[..., None]
    nrm = N[:, None, :] * (ca / np.maximum(ru[:, None], 1e-6))[..., None] + B[:, None, :] * (sa / np.maximum(rv[:, None], 1e-6))[..., None]
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-12
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    flayers = {}
    if attrs:
        for key in attrs:
            flayers[key] = bm.verts.layers.float.new(key)
    last_tip = (not closed) and tip and ru[-1] < 1e-4 and rv[-1] < 1e-4
    nring = n - 1 if last_tip else n
    vs = []
    for i in range(nring):
        row = []
        for j in range(M):
            v = bm.verts.new(rings[i, j])
            for key, arr in (attrs or {}).items():
                v[flayers[key]] = float(arr[i])
            row.append(v)
        vs.append(row)
    u0, v0, u1, v1 = uv_rect
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    s /= s[-1] if s[-1] > 0 else 1
    U = u0 + (u1 - u0) * s

    def setuv(face, coords):
        for loop, c in zip(face.loops, coords):
            loop[uvl].uv = c

    rows = range(nring if closed else nring - 1)
    for i in rows:
        i2 = (i + 1) % nring
        for j in range(M):
            j2 = (j + 1) % M
            f = bm.faces.new((vs[i][j], vs[i][j2], vs[i2][j2], vs[i2][j]))
            ua, ub = U[i], (U[i2] if i2 > i else u1)
            setuv(f, [(ua, v0 + (v1 - v0) * j / M), (ua, v0 + (v1 - v0) * (j + 1) / M),
                      (ub, v0 + (v1 - v0) * (j + 1) / M), (ub, v0 + (v1 - v0) * j / M)])
    if not closed:
        if last_tip:
            tv = bm.verts.new(P[-1])
            for key, arr in (attrs or {}).items():
                tv[flayers[key]] = float(arr[-1])
            i = nring - 1
            for j in range(M):
                j2 = (j + 1) % M
                f = bm.faces.new((vs[i][j], vs[i][j2], tv))
                setuv(f, [(U[i], v0 + (v1 - v0) * j / M), (U[i], v0 + (v1 - v0) * (j + 1) / M), (u1, v0 + (v1 - v0) * (j + 0.5) / M)])
        else:
            f = bm.faces.new(list(reversed(vs[-1])))
            for loop in f.loops:
                loop[uvl].uv = (u1, (v0 + v1) / 2)
        if start_cap:
            cv = bm.verts.new(P[0] - T[0] * 0.0)
            for key, arr in (attrs or {}).items():
                cv[flayers[key]] = float(arr[0])
            for j in range(M):
                j2 = (j + 1) % M
                f = bm.faces.new((vs[0][j2], vs[0][j], cv))
                for loop in f.loops:
                    loop[uvl].uv = (u0, (v0 + v1) / 2)
    bm.normal_update()
    obj = kit.mesh_object(name, bm, mat)
    return obj, (rings, nrm, s)


def bvh_of(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def set_attr(obj, name, values):
    me = obj.data
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    a = me.attributes.new(name, "FLOAT", "POINT")
    a.data.foreach_set("value", np.asarray(values, np.float32))


def verts_np(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def vnormals_np(obj):
    obj.data.update()
    no = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("normal", no)
    return no.reshape(-1, 3)


def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ============================================================================ BODY CLAY
EYE = {}   # side -> eye frame and lid rims (set by cut_eye_opening)
EYE_RA, EYE_RB = 0.040, 0.0118   # almond half-width / half-height (reference: width 0.050-0.058, h:w 0.45-0.5)
EYEBALL = (0.046, 0.020, 0.022)  # eyeball radii along the opening's long axis, the normal and up


LEGS = {
    # (points, radii): hip/shoulder, stifle/elbow, hock/carpus, pastern, paw top. Review 1: the hind legs
    # have the stifle forward at z 0.30, the hock pushed back at z 0.13-0.18 and the cannon sloping
    # forward to the paw; the front legs bend a little at the elbow and the carpus.
    "fl+": ([(0.075, -0.350, 0.46), (0.077, -0.318, 0.33), (0.073, -0.360, 0.118), (0.072, -0.378, 0.062), (0.072, -0.383, 0.045)],
            [0.05, 0.037, 0.025, 0.026, 0.027]),
    "fl-": ([(-0.075, -0.316, 0.46), (-0.077, -0.262, 0.33), (-0.073, -0.272, 0.118), (-0.072, -0.287, 0.062), (-0.072, -0.292, 0.045)],
            [0.05, 0.037, 0.025, 0.026, 0.027]),
    "hl+": ([(0.078, 0.065, 0.44), (0.085, 0.012, 0.30), (0.081, 0.190, 0.165), (0.079, 0.150, 0.07), (0.078, 0.140, 0.045)],
            [0.072, 0.05, 0.026, 0.027, 0.028]),
    "hl-": ([(-0.078, 0.035, 0.44), (-0.085, -0.090, 0.30), (-0.081, 0.002, 0.165), (-0.079, -0.040, 0.07), (-0.078, -0.050, 0.045)],
            [0.072, 0.05, 0.026, 0.027, 0.028]),
}


def body_clay():
    """Signed-distance clay of torso, neck, head, legs and fur locks (sculpting skill). The paws are
    separate finer clay (build_paw) so the toe lobes and creases keep their shape."""
    clay = S.Clay((-0.25, -0.70, -0.01), (0.25, 0.27, 0.90), voxel=0.0042)
    E, C, T = S.sd_ellipsoid, S.sd_cone, S.sd_tube
    # --- torso: chest, ribcage, waist (tuck-up), pelvis (side view back line z 0.60-0.62)
    clay.add(E((0, -0.37, 0.47), (0.110, 0.13, 0.15)))                       # chest, front at Y -0.50
    clay.add(E((0, -0.20, 0.485), (0.112, 0.17, 0.125)), blend=0.06)         # ribcage, bottom z 0.36
    clay.add(E((0, -0.03, 0.505), (0.098, 0.13, 0.10)), blend=0.06)          # waist, belly z 0.405
    clay.add(E((0, 0.075, 0.49), (0.104, 0.10, 0.115)), blend=0.05)          # pelvis, rump Y 0.175
    clay.add(E((0.068, -0.325, 0.47), (0.048, 0.075, 0.12), rot=(12, 0, 0)), blend=0.04, mirror=True)  # shoulder blades
    clay.add(E((0, -0.443, 0.45), (0.092, 0.097, 0.15)), blend=0.045)        # chest ruff mound (front Y -0.54)
    # --- neck and head (side view: nose tip z 0.68, eye z 0.72, crown z 0.84; Review 1: back of the
    # skull at Y -0.335 so nose to back of skull is 0.30 of the height)
    clay.add(T([(0, -0.38, 0.50), (0, -0.415, 0.60), (0, -0.415, 0.69)], [0.094, 0.085, 0.07]), blend=0.04)
    clay.add(E((0, -0.425, 0.755), (0.123, 0.088, 0.086)), blend=0.035)      # cranium, crown z 0.84
    clay.add(E((0, -0.472, 0.756), (0.085, 0.056, 0.045)), blend=0.03)       # brow / frontal plane
    clay.add(E((0.082, -0.448, 0.672), (0.068, 0.064, 0.054)), blend=0.03, mirror=True)  # cheeks
    clay.add(C((0, -0.472, 0.70), (0, -0.617, 0.677), 0.05, 0.015), blend=0.03)          # muzzle
    clay.add(C((0, -0.452, 0.662), (0, -0.590, 0.660), 0.038, 0.012), blend=0.022)      # lower jaw
    clay.add(E((0, -0.365, 0.69), (0.084, 0.06, 0.08)), blend=0.04)          # nape mass
    # eyes (Cycle 11): the lids are skin folds round an almond opening; the eyeball sits behind it
    for s in (1, -1):
        cut_eye_opening(clay, s)
    # --- fur locks (cones): cheek tufts, cheek/nape ruff, chest ruff spikes, elbow tufts, belly fringe
    rng = random.Random(7)
    for s in (1, -1):
        cheek = [((0.095, -0.43, 0.660), (0.185, -0.40, 0.628), 0.03),
                 ((0.095, -0.42, 0.645), (0.175, -0.39, 0.592), 0.028),
                 ((0.090, -0.43, 0.630), (0.150, -0.41, 0.565), 0.024),
                 ((0.075, -0.44, 0.625), (0.115, -0.44, 0.552), 0.02),
                 ((0.090, -0.40, 0.680), (0.170, -0.37, 0.672), 0.026)]
        for a, b, r in cheek:
            j = 1.25 + (rng.random() - 0.5) * 0.18 * s   # Cycle 11: cheek fur 15 % longer, flaring to x +-0.16
            bb = (a[0] + (b[0] - a[0]) * j, b[1], b[2] + (rng.random() - 0.5) * 0.01)
            clay.add(C((s * a[0], a[1], a[2]), (s * bb[0], bb[1], bb[2]), r, 0.002), blend=0.012)
        # cheek / nape ruff seen from behind (back view 0.38 of the width): blue locks from the back of the
        # jaw and the nape sweeping out and down into the shoulders, each its own length and droop
        nape = [((0.07, -0.37, 0.70), (0.150, -0.33, 0.672), 0.026),
                ((0.075, -0.36, 0.66), (0.155, -0.32, 0.615), 0.026),
                ((0.07, -0.34, 0.62), (0.145, -0.30, 0.565), 0.024),
                ((0.06, -0.31, 0.585), (0.13, -0.27, 0.53), 0.022),
                ((0.05, -0.34, 0.72), (0.12, -0.30, 0.715), 0.02)]
        for a, b, r in nape:
            clay.add(C((s * a[0], a[1], a[2]), (s * (b[0] + rng.uniform(-0.01, 0.01)), b[1] + rng.uniform(-0.01, 0.01),
                                                 b[2] + rng.uniform(-0.01, 0.006)), r, 0.002), blend=0.016)
        # elbow tufts (back of the front legs, side view z 0.30-0.34), larger so the silhouette shows them
        ey = -0.322 if s > 0 else -0.266
        clay.add(C((s * 0.076, ey + 0.01, 0.35), (s * 0.08, ey + 0.075, 0.285 + rng.uniform(-0.008, 0.008)), 0.028, 0.002), blend=0.012)
        clay.add(C((s * 0.076, ey + 0.02, 0.33), (s * 0.079, ey + 0.06, 0.262), 0.018, 0.002), blend=0.01)
        # belly fringe: 7 locks per side hanging down and back from the chest bottom and belly
        for k in range(7):
            y = -0.30 + k * 0.05 + rng.uniform(-0.008, 0.008)
            zt = 0.33 + 0.012 * k / 6 + rng.uniform(-0.012, 0.01)
            ln = rng.uniform(0.03, 0.06)
            clay.add(C((s * 0.048, y, 0.405), (s * (0.05 + rng.uniform(0, 0.01)), y + ln * 0.6, min(zt, 0.40 - ln * 0.8)),
                       0.022 + rng.uniform(-0.003, 0.003), 0.002), blend=0.012)
        # side ruff locks along the chest front edge
        for k, (z, l) in enumerate([(0.52, 0.05), (0.46, 0.06), (0.40, 0.055)]):
            clay.add(C((s * 0.085, -0.44, z), (s * (0.12 + rng.uniform(0, 0.015)), -0.47, z - l), 0.02, 0.002), blend=0.012)
    # chest ruff spikes, V point at z 0.25 between the front legs (front view)
    for x, z0, z1, r in [(0.0, 0.34, 0.245, 0.032), (0.035, 0.345, 0.27, 0.026), (-0.038, 0.345, 0.275, 0.025),
                         (0.07, 0.36, 0.30, 0.022), (-0.068, 0.36, 0.295, 0.022)]:
        clay.add(C((x, -0.47, z0), (x * 1.1, -0.47, z1), r, 0.002), blend=0.014)
    # --- legs (side view: front paws Y -0.39 (+X) / -0.30 (-X); hind paws Y 0.14 (+X) / -0.05 (-X))
    for key, (pts, rad) in LEGS.items():
        clay.add(T(pts, rad), blend=0.015)
        if key.startswith("h"):
            sx = 1 if key.endswith("+") else -1
            clay.add(E((sx * 0.072, pts[0][1] - 0.01, 0.40), (0.052, 0.105, 0.125), rot=(-25, 0, 0)), blend=0.05)  # thigh
            # heel (point of the hock) a little proud at the back of the joint
            hx, hy, hz = pts[2]
            clay.add(E((hx, hy + 0.014, hz + 0.005), (0.022, 0.02, 0.026)), blend=0.012)
            # stifle (knee) bulge at the front
            kx, ky, kz = pts[1]
            clay.add(E((kx, ky - 0.012, kz), (0.04, 0.035, 0.045)), blend=0.02)
    # flat underside (the legs end inside the separate paws)
    clay.intersect(S.sd_halfspace((0, 0, 0.03), (0, 0, -1)))
    # chin: a slight soft chin under the smile
    clay.add(S.sd_ellipsoid((0.0, -0.560, 0.640), (0.020, 0.020, 0.009)), blend=0.014)
    # mouth: a smile crease cut along a W under the nose that runs back along the jaw (Review 1)
    for s in (1, -1):
        clay.stroke(mouth_line(s), [0.0032, 0.0034, 0.0034, 0.0032, 0.003, 0.0028, 0.0024, 0.0018],
                    [0.0028, 0.003, 0.003, 0.003, 0.0028, 0.0024, 0.0018, 0.001], op="sub", blend=0.0015, n=40)
    obj = clay.to_object("Body", symmetric=False)
    return obj, clay


def eye_rim(side, n_pts=24):
    """Lid margins of the almond eye opening in the eye frame: (upper arc, lower arc) as (a, b) points from
    the inner corner to the outer corner. The upper arc is fuller than the lower; both meet in points."""
    ra = EYE_RA
    hu, hl = EYE_RB * 1.08, EYE_RB * 0.80
    a = np.linspace(-ra, ra, n_pts)
    # circular arcs through (+-ra, 0) and (0, h); the outer corner a little sharper than the inner
    Ru, Rl = (ra * ra + hu * hu) / (2 * hu), (ra * ra + hl * hl) / (2 * hl)
    up = np.sqrt(np.maximum(Ru * Ru - a * a, 0)) - (Ru - hu)
    lo = -(np.sqrt(np.maximum(Rl * Rl - a * a, 0)) - (Rl - hl))
    skew = 1.0 - 0.12 * (a / ra)          # the opening is a little taller toward the inner corner
    return np.stack([a, up * skew], 1), np.stack([a, lo * skew], 1)


def eye_frame_at(clay, side):
    """Eye centre on the skin, outward normal and the opening's long / up axes (16 deg tilt: inner corner
    low). The eye faces 38 deg outward and level, so the front view sees 0.8 of its width, the side 0.6."""
    p, _ = clay.project(np.array([[side * 0.064, -0.502, 0.718]]))
    p = p[0]
    n = np.array([side * 0.70, -0.71, 0.04])
    n /= np.linalg.norm(n)
    up = np.array([0.0, 0.0, 1.0])
    e_up = up - (up @ n) * n
    e_up /= np.linalg.norm(e_up)
    e_long = np.cross(e_up, n)
    if e_long[0] * side < 0:
        e_long = -e_long
    sl = math.radians(21)
    e_l = e_long * math.cos(sl) + e_up * math.sin(sl)
    e_u = -e_long * math.sin(sl) + e_up * math.cos(sl)
    return p, n, e_l, e_u


def cut_eye_opening(clay, side):
    """Cut the almond eye opening through the skin (a lens-shaped well 12 mm deep along the eye's normal),
    then roll the lid margins: a fuller upper lid fold and a thin lower one, on the skin around the rim."""
    p, n, el, eu = eye_frame_at(clay, side)
    rim_u, rim_l = eye_rim(side)
    # skin positions along the rims (before the cut), stored for the eyeball and the lid lines
    U = np.array([p + el * a + eu * b for a, b in rim_u])
    L = np.array([p + el * a + eu * b for a, b in rim_l])
    Us, _ = clay.project(U + n * 0.01)
    Ls, _ = clay.project(L + n * 0.01)
    EYE[side] = dict(p=p, n=n, el=el, eu=eu, upper=Us, lower=Ls)
    ra = EYE_RA
    hu, hl = EYE_RB * 1.08, EYE_RB * 0.80
    Ru, Rl = (ra * ra + hu * hu) / (2 * hu), (ra * ra + hl * hl) / (2 * hl)
    depth = 0.012

    def fn(x, y, z):
        dx, dy, dz = x - p[0], y - p[1], z - p[2]
        a = el[0] * dx + el[1] * dy + el[2] * dz
        b = eu[0] * dx + eu[1] * dy + eu[2] * dz
        w = n[0] * dx + n[1] * dy + n[2] * dz
        skew = 1.0 - 0.12 * np.clip(a / ra, -1, 1)
        bb = b / skew
        d_up = np.sqrt(a * a + (bb - (hu - Ru)) ** 2) - Ru
        d_lo = np.sqrt(a * a + (bb + (hl - Rl)) ** 2) - Rl
        return np.maximum(np.maximum(d_up, d_lo), -(w + depth))
    m = ra + 0.02
    clay.sub(S.Prim(fn, p - m, p + m), blend=0.0015)
    # lid folds: a rolled upper lid (2.6 mm) and a thin lower lid (1.4 mm) along the rims, a little inside
    # the opening so they lap over the eyeball
    for pts, r in ((Us, 0.0026), (Ls, 0.0014)):
        Q = pts - n * 0.0022
        rr = r * np.sin(np.linspace(0.12, math.pi - 0.12, len(Q))) ** 0.5
        clay.add(S.sd_tube(list(Q), list(rr)), blend=0.0025)


def mouth_line(s):
    """One half of the closed smile (reference front: a short line down from the nose, then a soft W whose
    corners turn up under the pupils; side: the line runs back along the muzzle and curls up at the
    corner under the eye)."""
    return [(0.0, -0.618, 0.664), (s * 0.006, -0.615, 0.6545), (s * 0.016, -0.608, 0.6505), (s * 0.028, -0.596, 0.6505),
            (s * 0.039, -0.578, 0.6545), (s * 0.046, -0.556, 0.6595), (s * 0.051, -0.530, 0.6665), (s * 0.054, -0.512, 0.6745)]


def crease_mouth(obj, clay):
    """Press the smile line into the remeshed body (the remesh is coarser than the 3 mm crease): vertices
    within 7 mm of the line move inward up to 3 mm, deepest under the nose and fading at the corner."""
    co = verts_np(obj)
    no = vnormals_np(obj)
    move = np.zeros(len(co))
    for s in (1, -1):
        P, _ = clay.project(np.array(mouth_line(s)))
        depth = np.linspace(0.0032, 0.0012, len(P) - 1)
        for i in range(len(P) - 1):
            d = seg_dist(co, P[i], P[i + 1])
            move = np.maximum(move, depth[i] * np.clip(1 - d / 0.007, 0, 1) ** 2)
    co = co - no * move[:, None]
    obj.data.vertices.foreach_set("co", co.astype(np.float32).ravel())
    obj.data.update()


def build_paw(key, mat):
    """One paw: a rounded pad with four toe lobes split by three creases (front view), finer clay than
    the body so the toes and creases keep their shape (Review 1: paws read as smooth blobs)."""
    pts, _ = LEGS[key]
    px, py = pts[-1][0], pts[-1][1]
    rng = random.Random({"fl+": 1, "fl-": 2, "hl+": 3, "hl-": 4}[key])
    clay = S.Clay((px - 0.05, py - 0.10, -0.002), (px + 0.05, py + 0.05, 0.085), voxel=0.0016)
    E, C = S.sd_ellipsoid, S.sd_cone
    clay.add(C((px, py + 0.002, 0.075), (px, py - 0.004, 0.035), 0.027, 0.03))                # pastern into the paw
    clay.add(E((px, py - 0.010, 0.027), (0.039, 0.048, 0.027)), blend=0.012)                  # pad
    clay.add(E((px, py + 0.022, 0.024), (0.026, 0.022, 0.022)), blend=0.01)                   # heel pad
    for k, dx in enumerate((-0.0235, -0.008, 0.008, 0.0235)):
        r = 0.0148 + (0.0024 if k in (1, 2) else 0) + rng.uniform(-0.0012, 0.0012)
        cy = py - 0.046 + (0.008 if k in (0, 3) else 0) + rng.uniform(-0.002, 0.002)
        clay.add(E((px + dx * 1.05, cy, 0.0165), (r * 0.95, r * 1.15, r * 1.0)), blend=0.004)
    for dx in (-0.0158, 0.0, 0.0158):
        # crease between two toes: ~4 mm wide, ~6 mm deep at the front, fading up the paw
        clay.sub(C((px + dx * 1.05, py - 0.072, 0.016), (px + dx * 0.85, py - 0.030, 0.034), 0.0021, 0.0016), blend=0.0015)
    clay.intersect(S.sd_halfspace((0, 0, 0.0), (0, 0, -1)))
    obj = clay.to_object(f"Paw_{key}", symmetric=False)
    kit.quad_remesh(obj, 1300)
    close_holes(obj)
    obj.data.shade_smooth()
    obj.data.materials.append(mat)
    return obj


# ============================================================================ MARK IMAGES
MARK_RES = 2048
MARK_SPAN = 1.02  # metres covered by the projection images


def side_strokes(sign, rng):
    """Glowing strokes on the flank, in side-view metres (Y, Z); a little different per side."""
    j = lambda: rng.uniform(-0.006, 0.006)
    st = []
    # haunch spiral with an outer swoosh and a flame over it
    st.append((spiral((0.048 + j(), 0.47 + j()), 0.034, 1.35, math.pi * 0.95, -1, 1.1, 0.0, 70, 0.9),
               np.linspace(0.009, 0.004, 70)))
    st.append((bez2((-0.035, 0.565), (0.06, 0.58 + j()), (0.11, 0.47), (0.085, 0.36 + j())), [0.004, 0.009, 0.008, 0.003] ))
    st.append((bez2((0.0, 0.53), (0.05, 0.545), (0.085, 0.52), (0.09, 0.49)), [0.003, 0.006, 0.004, 0.002]))
    st.append((bez2((0.075, 0.42), (0.09, 0.40), (0.10, 0.37), (0.098, 0.33)), [0.003, 0.006, 0.005, 0.002]))
    # thigh dots and a short stroke
    st.append(([(0.105, 0.335), (0.107, 0.333)], [0.011, 0.011]))
    st.append(([(0.118, 0.312), (0.119, 0.311)], [0.007, 0.007]))
    st.append((bez2((0.07, 0.30), (0.09, 0.28), (0.10, 0.25), (0.10, 0.22)), [0.003, 0.005, 0.004, 0.002]))
    # three wavy strokes along the back (withers to loin)
    for k, (y0, y1, z) in enumerate([(-0.27, -0.06, 0.588), (-0.22, -0.09, 0.565), (-0.12, 0.02, 0.598)]):
        pts = [(y0 + (y1 - y0) * f, z + 0.008 * math.sin(f * 7 + k) + j() * 0.3) for f in np.linspace(0, 1, 30)]
        st.append((pts, list(np.sin(np.linspace(0.15, 3.0, 30)) * 0.006 + 0.0015)))
    # front leg streaks and shoulder streaks
    st.append((bez2((-0.30, 0.42), (-0.29, 0.38), (-0.285, 0.33), (-0.29, 0.28)), [0.002, 0.006, 0.005, 0.002]))
    st.append((bez2((-0.255, 0.40), (-0.25, 0.37), (-0.25, 0.34), (-0.255, 0.31)), [0.002, 0.005, 0.004, 0.0015]))
    st.append((bez2((-0.335, 0.24), (-0.33, 0.21), (-0.335, 0.18), (-0.34, 0.15)), [0.002, 0.004, 0.003, 0.0015]))
    # hind leg streak
    st.append((bez2((0.10, 0.20), (0.115, 0.17), (0.12, 0.14), (0.125, 0.11)), [0.002, 0.004, 0.003, 0.0015]))
    # face: stroke under and behind the eye, brow stroke, forehead stroke
    st.append((bez2((-0.505, 0.708), (-0.48, 0.70), (-0.455, 0.705), (-0.425, 0.722)), [0.002, 0.007, 0.006, 0.002]))
    st.append((bez2((-0.49, 0.742), (-0.475, 0.75), (-0.46, 0.752), (-0.45, 0.748)), [0.0015, 0.004, 0.003, 0.001]))
    # neck streaks above the collar
    st.append((bez2((-0.40, 0.62), (-0.38, 0.60), (-0.37, 0.58), (-0.37, 0.56)), [0.002, 0.004, 0.003, 0.0015]))
    return st


def front_strokes():
    """Glowing strokes seen from the front (X, Z): forehead flame, under-eye strokes, chest feathers."""
    st = []
    # forehead flame: teardrop in the middle and two curling side strokes
    st.append((bez2((0.0, 0.755), (0.003, 0.772), (-0.002, 0.788), (0.0, 0.80)), [0.002, 0.010, 0.006, 0.0008]))
    for s in (1, -1):
        st.append((bez2((s * 0.014, 0.758), (s * 0.026, 0.768), (s * 0.03, 0.782), (s * 0.022, 0.794)), [0.001, 0.0035, 0.0028, 0.0008]))
        # under-eye stroke sweeping to the cheek
        st.append((bez2((s * 0.046, 0.699), (s * 0.057, 0.695), (s * 0.069, 0.696), (s * 0.080, 0.702)), [0.0012, 0.0042, 0.0032, 0.001]))
        # chest glow feathers below and beside the gem
        st.append((bez2((s * 0.012, 0.345), (s * 0.03, 0.33), (s * 0.05, 0.315), (s * 0.068, 0.31)), [0.004, 0.012, 0.009, 0.002]))
        st.append((bez2((s * 0.015, 0.325), (s * 0.03, 0.30), (s * 0.04, 0.285), (s * 0.05, 0.275)), [0.003, 0.010, 0.007, 0.002]))
        st.append((bez2((s * 0.04, 0.395), (s * 0.06, 0.385), (s * 0.08, 0.37), (s * 0.095, 0.36)), [0.003, 0.009, 0.007, 0.002]))
        st.append((bez2((s * 0.045, 0.37), (s * 0.06, 0.35), (s * 0.07, 0.335), (s * 0.08, 0.325)), [0.002, 0.007, 0.005, 0.0015]))
        # leg streak (front)
        st.append((bez2((s * 0.08, 0.30), (s * 0.078, 0.27), (s * 0.076, 0.24), (s * 0.075, 0.21)), [0.002, 0.004, 0.003, 0.0012]))
    return st


def mark_images():
    """marks: R = +X flank glow, G = -X flank glow, B = front glow. decal: R = front cream spots,
    G = side cream spots, B = front dark lines (mouth)."""
    n = MARK_RES
    c = (np.arange(n) + 0.5) / n * MARK_SPAN
    Ys, Zs = np.meshgrid(c - 0.72, c)         # side image: u -> Y, v -> Z
    Xf, Zf = np.meshgrid(c - 0.51, c)         # front image: u -> X, v -> Z
    marks = np.zeros((n, n, 3), np.float32)
    decal = np.zeros((n, n, 3), np.float32)
    px = MARK_SPAN / n
    for ch, sign in ((0, 1), (1, -1)):
        rng = random.Random(100 + ch)
        for pts, w in side_strokes(sign, rng):
            poly_paint(marks[..., ch], Ys, Zs, pts, np.asarray(w) * 0.8, 1.5 * px, halo=0.15, halo_w=0.0025)
    for pts, w in front_strokes():
        poly_paint(marks[..., 2], Xf, Zf, pts, w, 1.5 * px, halo=0.18, halo_w=0.003)
    # cream brow spots (front and side), oval
    for s in (1, -1):
        d = np.sqrt(((Xf - s * 0.040) / 0.015) ** 2 + ((Zf - 0.764) / 0.0085) ** 2)
        decal[..., 0] = np.maximum(decal[..., 0], np.clip((1 - d) * 8, 0, 1))
    d = np.sqrt(((Ys + 0.522) / 0.015) ** 2 + ((Zs - 0.764) / 0.0085) ** 2)
    decal[..., 1] = np.maximum(decal[..., 1], np.clip((1 - d) * 8, 0, 1))
    # (the mouth is modelled: a crease and a dark line, build_mouth)
    return new_image("LW_marks", n, n, marks), new_image("LW_decal", n, n, decal)


# ============================================================================ MATERIALS
def fur_material(name, marks, decal, cream):
    """Stylised painted fur: blue body (gradient to navy legs, light face) or cream; fur strokes in
    colour and bump; glowing cyan markings and decals from the projection images."""
    mat, tree, bsdf = kit.principled(name)
    nt = NT(tree)
    obj_co = nt.coords("Object")
    zh = nt.attr("zh")
    face = nt.attr("face")
    legm = nt.attr("legs")
    # fur strokes: stretched noise along the body (Y) and down the legs (Z)
    body_str = nt.noise(nt.scale_vec(obj_co, 70, 9, 70), 1.0, 4, 0.6)
    leg_str = nt.noise(nt.scale_vec(obj_co, 70, 70, 9), 1.0, 4, 0.6)
    strokes = nt.mixf(legm, body_str, leg_str)
    blotch = nt.noise(obj_co, 7.0, 3, 0.5)
    if not cream:
        base = nt.ramp(zh, [(0.0, "#3d5079"), (0.08, "#455a82"), (0.22, "#4f688b"), (0.33, "#6684a6"),
                            (0.43, "#82a5c0"), (0.56, "#8bb2cc"), (0.68, "#97c3d8"), (0.85, "#93bfd6")])
        base = nt.mix(nt.math("MULTIPLY", face, 0.85), base, lin("#9dcde2"))
    else:
        base = nt.ramp(zh, [(0.2, "#bccbd3"), (0.32, "#ccd2d2"), (0.45, "#d8d3cc"), (0.62, "#ddd5cc"), (0.75, "#e0d8cf")])
    # tonal variation: blotches and strokes
    var = nt.ramp(blotch, [(0.3, (0.90, 0.92, 0.95, 1)), (0.5, (1, 1, 1, 1)), (0.7, (1.07, 1.06, 1.04, 1))])
    base = nt.mix(1.0, base, var, "MULTIPLY")
    strk = nt.ramp(strokes, [(0.35, (0.88, 0.90, 0.93, 1)), (0.5, (1, 1, 1, 1)), (0.68, (1.10, 1.09, 1.07, 1))])
    base = nt.mix(0.8, base, strk, "MULTIPLY")
    # projections: side (pys, pzs) and front (pxf, pzs)
    side_uv = nt.combine(nt.attr("pys"), nt.attr("pzs"))
    front_uv = nt.combine(nt.attr("pxf"), nt.attr("pzs"))
    ncomp = nt.sep(nt.coords("Normal"))   # object space: the kit turns the model on a turntable
    wside = nt.maprange(nt.math("ABSOLUTE", ncomp[0]), 0.15, 0.45)
    wfront = nt.maprange(nt.math("MULTIPLY", ncomp[1], -1.0), 0.2, 0.55)
    plus = nt.maprange(ncomp[0], -0.05, 0.05)
    mk_side = nt.rgb_sep(nt.image(marks, side_uv).outputs["Color"])
    mk_front = nt.rgb_sep(nt.image(marks, front_uv).outputs["Color"])
    side_glow = nt.mixf(plus, mk_side[1], mk_side[0])
    # the side face stroke must not reach across the nose bridge (Review 1: one stroke under each eye)
    side_glow = nt.math("MULTIPLY", side_glow, nt.attr("nobridge"))
    glow = nt.math("MAXIMUM", nt.math("MULTIPLY", side_glow, wside), nt.math("MULTIPLY", mk_front[2], wfront))
    dc_side = nt.rgb_sep(nt.image(decal, side_uv).outputs["Color"])
    dc_front = nt.rgb_sep(nt.image(decal, front_uv).outputs["Color"])
    creamspot = nt.math("MAXIMUM", nt.math("MULTIPLY", dc_front[0], wfront), nt.math("MULTIPLY", dc_side[1], wside))
    darkline = nt.math("MULTIPLY", dc_front[2], wfront)
    if not cream:
        base = nt.mix(creamspot, base, lin("#e2dbd2"))
    base = nt.mix(darkline, base, lin("#2a3050"))
    # glow: light cyan core
    base = nt.mix(nt.math("MULTIPLY", glow, 0.9), base, lin("#c4f6ff"))
    emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3fbfe0"), (1.0, "#a8f4ff")])
    rough = nt.math("ADD", nt.math("MULTIPLY", strokes, 0.12), 0.74)
    rough = nt.mixf(glow, rough, 0.45)
    # crevices (toe creases, leg joints, under the fur locks) a little darker
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.025
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.45, 0.0, 0.55), base, lin("#2c3a5e" if not cream else "#8f8c90"))
    # the smile line is a crease: the dark line also cuts into the bump
    bump = nt.bump(nt.math("SUBTRACT", strokes, nt.math("MULTIPLY", darkline, 1.5)), 0.3, 0.0015)
    set_bsdf(nt, bsdf, base=base, rough=rough, emis_col=emis, emis_str=0.8, normal=bump)
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mat


def ear_materials(img):
    """Ear back (blue fur, cyan swirls) and inner bowl (indigo, painted stars and spiral)."""
    out = []
    for inner in (False, True):
        mat, tree, bsdf = kit.principled("M_ear_inner" if inner else "M_ear_outer")
        nt = NT(tree)
        uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
        ch = nt.rgb_sep(nt.image(img, uv).outputs["Color"])
        uvs = nt.sep(uv)
        t = uvs[1]
        strk = nt.noise(nt.scale_vec(uv, 160, 18, 1), 1.0, 4, 0.6)
        blot = nt.noise(nt.coords("Object"), 9.0, 3, 0.5)
        if inner:
            base = nt.ramp(t, [(0.0, "#3f4277"), (0.25, "#4f5791"), (0.6, "#5a64a0"), (0.95, "#5f6ba8")])
            base = nt.mix(nt.maprange(blot, 0.35, 0.7), base, lin("#4c4a8a"))
            base = nt.mix(nt.math("MULTIPLY", ch[2], 1.0), base, lin("#eef8ff"))
            glow = nt.math("MAXIMUM", ch[0], nt.math("MULTIPLY", ch[2], 0.8))
            rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.15), 0.6)
        else:
            base = nt.ramp(t, [(0.0, "#7092ba"), (0.5, "#7898c0"), (0.9, "#6383ad"), (1.0, "#5c7aa5")])
            sv = nt.ramp(strk, [(0.3, (0.9, 0.92, 0.95, 1)), (0.7, (1.08, 1.07, 1.05, 1))])
            base = nt.mix(1.0, base, sv, "MULTIPLY")
            glow = nt.math("MULTIPLY", ch[1], 0.75)
            rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.12), 0.74)
        base = nt.mix(nt.math("MULTIPLY", glow, 0.85), base, lin("#bdf3ff"))
        emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3aa8e0"), (1.0, "#b0f2ff")])
        set_bsdf(nt, bsdf, base=base, rough=rough, emis_col=emis, emis_str=2.6 if inner else 1.0, normal=nt.bump(strk, 0.25, 0.001))
        out.append(mat)
    return out


def cream_tuft_material():
    mat, tree, bsdf = kit.principled("M_cream_tuft")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    strk = nt.noise(nt.scale_vec(uv, 6, 60, 1), 1.0, 4, 0.6)
    base = nt.ramp(uvs[0], [(0.0, "#9fa2b4"), (0.3, "#cfc8c3"), (0.7, "#ddd6cf"), (1.0, "#e6e0d8")])
    sv = nt.ramp(strk, [(0.3, (0.86, 0.88, 0.93, 1)), (0.7, (1.06, 1.05, 1.03, 1))])
    base = nt.mix(1.0, base, sv, "MULTIPLY")
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", strk, 0.1), 0.78), normal=nt.bump(strk, 0.3, 0.001))
    return mat


def shoulder_fur_material():
    """Iridescent shoulder fur: blue at the root -> mint/cyan -> lilac toward the tip, mint streaks along the
    strands, lavender edges, fine glowing specks (from the lock attributes lu along, lv around)."""
    mat, tree, bsdf = kit.principled("M_shoulder_fur")
    nt = NT(tree)
    lu, lv, ljit = nt.attr("lu"), nt.attr("lv"), nt.attr("ljit")
    streak = nt.noise(nt.combine(nt.math("MULTIPLY", lu, 3.0), nt.math("MULTIPLY", lv, 22.0), nt.math("MULTIPLY", ljit, 5.0)), 1.0, 3, 0.5)
    base = nt.ramp(lu, [(0.0, "#7fa6c6"), (0.18, "#93cbe0"), (0.36, "#9eeedd"), (0.52, "#a6c6f2"), (0.68, "#b3a0ec"), (1.0, "#c6b0f6")])
    mint = nt.maprange(streak, 0.5, 0.65)
    base = nt.mix(nt.math("MULTIPLY", mint, 0.6), base, lin("#9ff2d6"))
    edge = nt.maprange(nt.math("ABSOLUTE", nt.math("SUBTRACT", nt.math("FRACT", nt.math("MULTIPLY", lv, 2.0)), 0.5)), 0.18, 0.0)
    base = nt.mix(nt.math("MULTIPLY", edge, 0.5), base, lin("#b9a9ec"))
    vor = nt.node("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 140.0
    nt.link(nt.coords("Object"), vor.inputs["Vector"])
    speck = nt.maprange(vor.outputs["Distance"], 0.06, 0.02)
    base = nt.mix(nt.math("MULTIPLY", speck, 0.8), base, lin("#f2fbff"))
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.02
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.5, 0.0, 0.4), base, lin("#4a5a8a"))
    glow = nt.math("MAXIMUM", nt.math("MULTIPLY", mint, 0.35), speck)
    emis = nt.ramp(glow, [(0.0, "#000000"), (1.0, "#7fe8e0")])
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", streak, 0.2), 0.42),
             emis_col=emis, emis_str=0.8, normal=nt.bump(streak, 0.3, 0.001))
    return mat


def silver_material():
    mat, tree, bsdf = kit.principled("M_silver")
    nt = NT(tree)
    co = nt.coords("Object")
    nz = nt.noise(co, 60.0, 4, 0.6)
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.02
    base = nt.ramp(nz, [(0.3, "#aeb3c0"), (0.5, "#c9cdd8"), (0.7, "#dde0e8")])
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.9, 0.4), base, lin("#4d5266"))
    rough = nt.ramp(nz, [(0.3, (0.18, 0.18, 0.18, 1)), (0.7, (0.38, 0.38, 0.38, 1))])
    set_bsdf(nt, bsdf, base=base, rough=nt.rgb_sep(rough)[0], metal=1.0, normal=nt.bump(nz, 0.15, 0.0005))
    return mat


def gem_material():
    mat, tree, bsdf = kit.principled("M_gem")
    nt = NT(tree)
    co = nt.coords("Object")
    vor = nt.node("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 90.0
    nt.link(co, vor.inputs["Vector"])
    facet = nt.sep(nt.coords("Normal"))
    f = nt.math("ADD", nt.math("MULTIPLY", facet[0], 0.5), nt.math("MULTIPLY", facet[2], 0.5))
    base = nt.ramp(nt.math("ADD", nt.math("MULTIPLY", f, 0.6), 0.5), [(0.0, "#1a3fa8"), (0.45, "#2f6ce0"), (0.7, "#4d8ef0"), (1.0, "#8ccaff")])
    spark = nt.maprange(vor.outputs["Distance"], 0.08, 0.02)
    base = nt.mix(nt.math("MULTIPLY", spark, 0.7), base, lin("#d8f0ff"))
    emis = nt.mix(nt.math("MULTIPLY", spark, 0.6), lin("#2f7cff"), lin("#c6e8ff"))
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", spark, 0.1), 0.05), emis_col=emis, emis_str=3.5)
    return mat


def eye_material(side):
    """Anime eye from the eye's own UVs (u along the eye toward the outer corner, v up): a big light-blue
    iris (light below, dark blue under the upper lid) with a navy rim and a small dark pupil, a pale sclera
    sliver at the corners, a white catch light at the upper inner side and a small second one lower
    outside. Each eye its own highlight jitter (0.5 mm)."""
    mat, tree, bsdf = kit.principled(f"M_eye_{'L' if side > 0 else 'R'}")
    nt = NT(tree)
    jx, jy = (0.0005, -0.0003) if side > 0 else (-0.0003, 0.0005)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    x = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[0], 0.5), 2 * EYEBALL[0])
    y = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[1], 0.5), 2 * EYEBALL[2])
    # iris a little toward the nose and low, big enough that the heavy upper lid cuts its top (hooded) and
    # its bottom touches the lower lid (no dark crescent under it)
    dx = nt.math("ADD", x, 0.001)
    dy = nt.math("ADD", y, 0.0008)
    r = nt.math("DIVIDE", nt.math("SQRT", nt.math("ADD", nt.math("POWER", dx, 2.0), nt.math("POWER", dy, 2.0))), 0.0138)
    vert = nt.math("ADD", nt.math("DIVIDE", y, 2 * EYE_RB), 0.5)
    iris = nt.ramp(vert, [(0.0, "#d4ecf2"), (0.35, "#a9cde0"), (0.62, "#7fa6cf"), (1.0, "#3a5a9a")])
    # fine radial fibres in the iris (painted look)
    fib = nt.noise(nt.combine(nt.math("ARCTAN2", dy, dx), r, 0.0), 6.0, 2, 0.5)
    iris = nt.mix(nt.math("MULTIPLY", nt.maprange(fib, 0.45, 0.7), 0.25), iris, lin("#d6f2ff"))
    col = nt.mix(nt.maprange(r, 0.24, 0.20), iris, lin("#141c45"))            # pupil
    col = nt.mix(nt.maprange(r, 0.88, 0.98), col, lin("#1e2d62"))             # dark iris rim
    sclera = nt.mix(nt.maprange(nt.math("ABSOLUTE", x), EYE_RA - 0.012, EYE_RA - 0.003), lin("#3a4a82"), lin("#222a58"))
    col = nt.mix(nt.maprange(r, 1.0, 1.06), col, sclera)                       # pale sclera at the corners
    hl1 = nt.math("SQRT", nt.math("ADD", nt.math("POWER", nt.math("ADD", x, 0.004 - jx), 2.0),
                                  nt.math("POWER", nt.math("SUBTRACT", y, 0.004 + jy), 2.0)))
    hl2 = nt.math("SQRT", nt.math("ADD", nt.math("POWER", nt.math("SUBTRACT", x, 0.004 + jx), 2.0),
                                  nt.math("POWER", nt.math("ADD", y, 0.003 - jy), 2.0)))
    hlm = nt.math("MAXIMUM", nt.maprange(hl1, 0.0024, 0.0018), nt.maprange(hl2, 0.0012, 0.0008))
    col = nt.mix(hlm, col, lin("#f7fdff"))
    sparkle = nt.noise(uv, 30.0, 2, 0.5)
    set_bsdf(nt, bsdf, base=col, rough=nt.math("ADD", nt.math("MULTIPLY", sparkle, 0.1), 0.12),
             emis_col=nt.mix(hlm, lin("#000000"), lin("#ffffff")), emis_str=0.6)
    return mat


def dark_material(name, hexcol, rough):
    mat, tree, bsdf = kit.principled(name)
    nt = NT(tree)
    nz = nt.noise(nt.coords("Object"), 120.0, 3, 0.5)
    base = nt.ramp(nz, [(0.3, hexcol), (0.7, "#3a3a52")])
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", nz, 0.15), rough), normal=nt.bump(nz, 0.2, 0.0004))
    return mat


def star_material():
    mat, tree, bsdf = kit.principled("M_constellation_star")
    nt = NT(tree)
    nz = nt.noise(nt.coords("Object"), 200.0, 2, 0.5)
    col = nt.ramp(nz, [(0.3, "#d8f6ff"), (0.7, "#ffffff")])
    set_bsdf(nt, bsdf, base=col, rough=0.3, emis_col=nt.ramp(nz, [(0.3, "#9fe8ff"), (0.7, "#e8fbff")]), emis_str=6.0)
    return mat


# ============================================================================ EARS
def ear_shape(side):
    """Leaf-shaped ear frame for side +1 (+X) or -1: base B, axis a, bowl normal f, width w."""
    j = 0.006 * side
    # Review 1: bases 0.035 forward and lower (the bowl starts right behind the eye, the outer edge runs
    # down to the cheek), tips turned further out (front tip spread) and the near tip further back
    B = np.array([side * 0.104, -0.437 + 0.010 * side, 0.706])
    Tp = np.array([side * (0.215 + j), -0.378 + 0.056 * side, 0.996 - abs(j) * 0.5])   # side view: far ear forward
    L = float(np.linalg.norm(Tp - B))
    a = (Tp - B) / L
    f0 = np.array([side * 0.80, -1.0, 0.12])
    f = f0 - (f0 @ a) * a
    f /= np.linalg.norm(f)
    w = np.cross(a, f)
    if w[0] * side < 0:
        w = -w
    return B, a, f, w, L


EAR_K = 1.17   # width scale (Cycle 5: ears seen wider in the side view)


def ear_hw(u_sign, t):
    """Half-width of the ear leaf at fraction t along it; outer edge (u >= 0) convex and pulled in at the
    base so it runs down into the cheek, inner edge nearly straight. Works on numpy arrays."""
    t = np.asarray(t, float)
    outer = EAR_K * 0.10 * (1 - t) ** 0.8 * (1 + 1.0 * t) * (0.55 + 0.45 * np.clip(t / 0.25, 0, 1) ** 0.7)
    inner = EAR_K * 0.056 * (1 - t) ** 0.9 * (1 + 0.55 * t)
    out = np.where(np.asarray(u_sign) >= 0, outer, inner)
    return float(out) if out.ndim == 0 else out


def build_ear(side, m_out, m_in, uoff):
    B, a, f, w, L = ear_shape(side)
    Nt, Nu = 26, 11
    us = -np.cos(np.linspace(0, math.pi, Nu))           # -1..1, dense at the rim
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for it in range(Nt):
        t = it / (Nt - 1) * 0.985
        c = B + a * L * t - f * 0.022 * math.sin(math.pi * t) * 0.7
        D = 0.026 * (1 - t) ** 0.7
        th = 0.009 + 0.007 * (1 - t)
        front, back = [], []
        for u in us:
            hw = ear_hw(u, t)
            x = u * hw
            bowl = D * (1 - u * u)
            p = c + w * x - f * bowl
            q = c + w * x - f * (bowl * 0.9 + th + 0.006 * (1 - u * u) * (1 - t))
            front.append(bm.verts.new(p))
            back.append(bm.verts.new(q))
        rings.append((front, back, t))
    tipv = bm.verts.new(B + a * L * 1.0 - f * 0.004)
    basev = bm.verts.new(B - a * 0.01 - f * 0.012)

    def uvc(u, t):
        return (uoff + 0.25 * (u + 1), t)

    for it in range(Nt - 1):
        f0, b0, t0 = rings[it]
        f1, b1, t1 = rings[it + 1]
        loop0 = f0 + list(reversed(b0))
        loop1 = f1 + list(reversed(b1))
        uu = list(us) + list(reversed(us))
        n = len(loop0)
        for k in range(n):
            k2 = (k + 1) % n
            face = bm.faces.new((loop0[k], loop0[k2], loop1[k2], loop1[k]))
            for loop, (uv_u, tt) in zip(face.loops, [(uu[k], t0), (uu[k2], t0), (uu[k2], t1), (uu[k], t1)]):
                loop[uvl].uv = uvc(uv_u, tt)
            inner = k < Nu - 1 and abs(uu[k]) <= 0.82 and abs(uu[k2]) <= 0.82
            face.material_index = 1 if inner else 0
    # tip and base caps
    fL, bL, tL = rings[-1]
    loopL = fL + list(reversed(bL))
    uu = list(us) + list(reversed(us))
    for k in range(len(loopL)):
        k2 = (k + 1) % len(loopL)
        face = bm.faces.new((loopL[k], loopL[k2], tipv))
        for loop, c in zip(face.loops, [uvc(uu[k], tL), uvc(uu[k2], tL), uvc(0, 1.0)]):
            loop[uvl].uv = c
    f0, b0, _ = rings[0]
    loop0 = f0 + list(reversed(b0))
    for k in range(len(loop0)):
        k2 = (k + 1) % len(loop0)
        face = bm.faces.new((loop0[k2], loop0[k], basev))
        for loop in face.loops:
            loop[uvl].uv = uvc(0, 0)
    bm.normal_update()
    obj = kit.mesh_object(f"Ear_{'L' if side > 0 else 'R'}", bm, m_out)
    obj.data.materials.append(m_in)
    obj["keep_uv"] = True
    mod = obj.modifiers.new("Subd", "SUBSURF")
    mod.levels = mod.render_levels = 1
    return obj


def ear_image():
    """Ear texture: R = inner cyan spiral, G = cyan swirls on the back, B = star specks."""
    W, H = 1024, 1024
    img = np.zeros((H, W, 3), np.float32)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        B, a, f, w, L = ear_shape(side)
        i0, i1 = int(uoff * W), int((uoff + 0.5) * W)
        uu = ((np.arange(i0, i1) + 0.5) / W - uoff) / 0.25 - 1            # -1..1
        tt = (np.arange(H) + 0.5) / H
        Ug, Tg = np.meshgrid(uu, tt)
        hw = ear_hw(Ug, Tg)
        X = Ug * hw                    # metres across (outer +)
        Y = Tg * L                     # metres along
        sub = img[:, i0:i1]
        rng = random.Random(30 + side)
        # inner spiral: one curl in the upper middle, its tail running down to the base (front view)
        # Cycle 11: one big soft curl in the upper-outer bowl (t 0.62-0.70, r 0.04), its tail running down
        # toward the base, with a wide soft glow round it
        sc = (0.022 + 0.003 * side, 0.66 * L + 0.006 * side)
        sp = spiral(sc, 0.040 + 0.003 * side, 1.2, -0.45 * math.pi, 1, 1.15, 0.0, 70, 0.8)
        tail = bez2((0.0, 0.07), (0.02, 0.11), (0.035, 0.15), (sp[0][0], sp[0][1]))
        stroke = tail[:-1] + sp
        widths = np.concatenate([np.linspace(0.003, 0.012, len(tail) - 1), np.linspace(0.012, 0.006, len(sp))])
        poly_paint(sub[..., 0], X, Y, stroke, widths, 0.0012, halo=0.6, halo_w=0.012)
        # faint glowing wisps in the bowl (the reference's bowl glows around the spiral)
        poly_paint(sub[..., 0], X, Y, bez2((0.025, 0.06), (0.03, 0.09), (0.022, 0.12), (0.03, 0.15)),
                   [0.001, 0.003, 0.0025, 0.001], 0.0008, halo=0.3, halo_w=0.005, value=0.6)
        # back swirls (back view): a curl high up and a leaf stroke lower down
        sp2 = spiral((-0.004, 0.175), 0.022, 1.0, 0.3 * math.pi, -1, 1.2, 0.0, 50, 0.9)
        poly_paint(sub[..., 1], -X, Y, bez2((0.03, 0.07), (0.02, 0.11), (0.01, 0.14), sp2[0]) + sp2,
                   np.concatenate([np.linspace(0.0012, 0.0042, 20), np.linspace(0.0042, 0.0015, 50)]), 0.0007, halo=0.2, halo_w=0.002)
        poly_paint(sub[..., 1], -X, Y, bez2((-0.035, 0.05), (-0.02, 0.08), (-0.022, 0.11), (-0.03, 0.135)),
                   [0.0008, 0.003, 0.0025, 0.0008], 0.0007, halo=0.2, halo_w=0.002)
        # star specks: uneven sizes, denser toward the top
        for _ in range(200):
            t = rng.random() ** 0.7
            u = rng.uniform(-0.85, 0.85)
            hwv = ear_hw(u, t)
            cx, cy = u * hwv, t * L
            r = 0.6 * rng.choice([0.0005, 0.0006, 0.0008, 0.001, 0.0013, 0.0018]) * (1.0 if rng.random() > 0.08 else 1.8)
            br = rng.uniform(0.5, 1.0)
            sel = (np.abs(X - cx) < 0.004) & (np.abs(Y - cy) < 0.004)
            if not sel.any():
                continue
            d = np.sqrt((X[sel] - cx) ** 2 + (Y[sel] - cy) ** 2)
            v = np.clip((r - d) / 0.0004 + 0.5, 0, 1) * br
            v = np.maximum(v, 0.25 * br * np.exp(-np.maximum(d - r, 0) / 0.001))
            ch = sub[..., 2]
            ch[sel] = np.maximum(ch[sel], v)
        img[:, i0:i1] = sub
    return new_image("LW_ears", W, H, img)


def ear_tufts(side, mat, rng, m_out):
    """Cream fur fan at the inner base of the ear (Review 1): 5 overlapping blades, 25-35 mm wide at the
    root, 60-100 mm long, rising out of the bowl and filling its lower third, each its own length,
    angle and bend."""
    B, a, f, w, L = ear_shape(side)
    objs = []
    for k in range(5):
        # roots along the inner lower bowl, fanning from pointing up-in (k 0) to up-out (k 4)
        # front view: the fan fills the inner lower bowl and its blades point up and a little outward,
        # toward the ear tip (none crosses the inner rim toward the head)
        t0 = 0.03 + 0.018 * abs(k - 1.5) + rng.uniform(-0.005, 0.005)
        x0 = -0.042 + 0.011 * k + rng.uniform(-0.003, 0.003)
        root = B + a * L * t0 + w * x0 - f * 0.013
        ang = math.radians(-4 + 9 * k + rng.uniform(-3, 3))
        d = a * math.cos(ang) + w * math.sin(ang)
        ln = 0.085 + 0.03 * math.sin((k + 0.6) * 0.6) + rng.uniform(0, 0.012)
        p1 = root + d * ln * 0.35 + f * 0.006
        p2 = root + d * ln * 0.72 + f * 0.009
        p3 = root + d * ln + f * 0.008 - w * 0.008 * (k - 2)
        P = np.array(S.bezier(root, p1, p2, p3, 18))
        tt = np.linspace(0, 1, 18)
        wmax = 0.5 * (0.040 + 0.012 * rng.random())
        # feather blade: widest at a third, a notch-free pointed tip, a slight S along its length
        width = wmax * (1 - tt) ** 0.7 * (0.7 + 0.3 * np.sin(np.clip(tt * 2.5, 0, 1) * math.pi * 0.5)) + 1e-5
        width[-1] = 0
        th = 0.0035 * (1 - tt) + 1e-5
        th[-1] = 0
        o, _ = sweep(f"EarTuft_{side}_{k}", P, th, width, 10, mat, hint=np.tile(f, (18, 1)), uv_rect=(0, 0, 1, 1))
        o["keep_uv"] = True
        objs.append(o)
    if side < 0:
        # the far ear's tip is split: a second, smaller point beside the main tip (side view)
        tipb = B + a * L * 0.80 - w * ear_hw(-1, 0.80) * 0.6 - f * 0.004
        P = np.array(S.bezier(tipb, tipb + a * 0.03, tipb + a * 0.055 - w * 0.012, tipb + a * 0.07 - w * 0.022, 12))
        tt = np.linspace(0, 1, 12)
        wd = 0.012 * (1 - tt) ** 0.8 + 1e-5
        wd[-1] = 0
        th = 0.005 * (1 - tt) + 1e-5
        th[-1] = 0
        o, _ = sweep("EarTipSplit", P, th, wd, 8, m_out, hint=np.tile(f, (12, 1)), uv_rect=(0.988, 0.80, 0.996, 0.95))
        o["keep_uv"] = True
        objs.append(o)
    return objs


# ============================================================================ EYES, NOSE
def eye_frame(clay, side):
    e = EYE[side]
    return e["p"], e["n"], e["el"], e["eu"]


def build_eye(clay, side, mat):
    """The eyeball: a flattened ball behind the almond opening, its front 1 mm in front of the skin level so
    the lid folds lap over its edge; iris and highlights come from its own UVs (front projection)."""
    p, n, el, eu = eye_frame(clay, side)
    ra, rc, rb = EYEBALL
    c = p + n * (0.001 - rc)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    uvl = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            lx, ly, lz = loop.vert.co
            loop[uvl].uv = (0.5 + 0.5 * lx, 0.5 + 0.5 * lz)
    for v in bm.verts:
        lx, ly, lz = v.co
        v.co = Vector(c + el * (ra * lx) + n * (rc * ly) + eu * (rb * lz))
    bm.normal_update()
    obj = kit.mesh_object(f"eye_{'left' if side > 0 else 'right'}", bm, mat)
    obj["keep_uv"] = True
    return obj


def build_lid_lines(clay, side, mat):
    """The dark lash lines on the lid margins: a thick upper line (3.5-4 mm) on the upper lid fold that runs
    past the outer corner into a flick rising about 8 mm along the skin, and a thin lower line (1-1.5 mm)
    fading toward the inner corner."""
    e = EYE[side]
    p, n, el, eu = e["p"], e["n"], e["el"], e["eu"]
    # on the lid margin itself (pulled 10 % toward the opening's centre so no skin shows between line and eye)
    U = e["upper"] + (p - e["upper"]) * 0.17 + n * 0.0014
    # the flick: continues from the outer corner out and up, on the skin
    a0, b0 = EYE_RA, 0.0
    fl = np.array([p + el * (a0 + d) + eu * (b0 + h) + n * 0.01 for d, h in ((0.006, 0.0022), (0.012, 0.0055), (0.016, 0.0085))])
    fl, _ = clay.project(fl)
    P = np.concatenate([U[2:], fl + n * 0.0009])
    tt = np.linspace(0, 1, len(P))
    r = np.interp(tt, [0.0, 0.15, 0.55, 0.85, 1.0], [0.0016, 0.0031, 0.0036, 0.0028, 0.0])
    up, _ = sweep(f"eyelid_upper_{'left' if side > 0 else 'right'}", P, r * 0.75, r, 8, mat, hint=np.tile(n, (len(P), 1)))
    Lo = e["lower"][2:-1] + (p - e["lower"][2:-1]) * 0.12 + n * 0.0009
    t2 = np.linspace(0, 1, len(Lo))
    r2 = np.interp(t2, [0.0, 0.5, 1.0], [0.0006, 0.0013, 0.0009])
    lo, _ = sweep(f"eyelid_lower_{'left' if side > 0 else 'right'}", Lo, r2 * 0.8, r2, 8, mat, hint=np.tile(n, (len(Lo), 1)))
    return [up, lo]


def build_mouth(clay, mat):
    """The closed smile as a thin dark line lying in its crease: from under the nose (the philtrum) down,
    out in a soft W and up into the corners, back along the muzzle (both halves one line)."""
    halves = []
    for s in (1, -1):
        P = np.array(S.catmull_rom(mouth_line(s), 6)) if hasattr(S, "catmull_rom") else catmull(np.array(mouth_line(s)), 6)
        halves.append(P)
    P = np.concatenate([halves[1][::-1], halves[0][1:]])
    P, N = clay.project(P)
    P = P + N * 0.0005
    top = np.array([0.0, -0.621, 0.672])
    t, _ = clay.project(np.array([top]))
    mid = len(P) // 2
    tt = np.linspace(0, 1, len(P))
    r = 0.0016 * np.interp(tt, [0.0, 0.08, 0.5, 0.92, 1.0], [0.25, 0.85, 1.0, 0.85, 0.25])
    line, _ = sweep("mouth_line", P, r * 0.8, r, 8, mat, hint=np.tile(np.array([0.0, -1.0, 0.0]), (len(P), 1)), tip=False)
    ph = np.array([t[0] + N[mid] * 0.0005, P[mid]])
    ph = np.stack([np.linspace(ph[0, k], ph[1, k], 8) for k in range(3)], 1)
    phil, _ = sweep("mouth_philtrum", ph, 0.0011, 0.0013, 8, mat, hint=np.tile(np.array([0.0, -1.0, 0.0]), (8, 1)), tip=False)
    return [line, phil]


def build_nose(mat):
    clay = S.Clay((-0.03, -0.655, 0.645), (0.03, -0.59, 0.705), voxel=0.0011)
    clay.add(S.sd_ellipsoid((0, -0.623, 0.680), (0.017, 0.012, 0.0115)))
    clay.add(S.sd_ellipsoid((0, -0.616, 0.688), (0.014, 0.012, 0.008)), blend=0.004)
    clay.intersect(S.sd_halfspace((0, 0, 0.6665), (0, 0.25, -1)), blend=0.003)
    for s in (1, -1):
        clay.sub(S.sd_ellipsoid((s * 0.0075, -0.632, 0.6725), (0.0036, 0.004, 0.0024), rot=(0, 0, s * 25)), blend=0.0015)
    clay.sub(S.sd_cone((0, -0.636, 0.676), (0, -0.632, 0.667), 0.0012, 0.0012), blend=0.001)
    obj = clay.to_object("Nose")
    obj.data.materials.append(mat)
    return obj


# ============================================================================ COLLAR AND GEM
GEM_C = np.array([0.0, -0.548, 0.410])   # y is set on the chest surface in build()


def build_gem(mat):
    bm = bmesh.new()
    cy, cz = GEM_C[1], GEM_C[2]
    hh, hw, dep = 0.056, 0.031, 0.020
    girdle = [bm.verts.new((0, cy, cz + hh)), bm.verts.new((hw, cy, cz)), bm.verts.new((0, cy, cz - hh)), bm.verts.new((-hw, cy, cz))]
    k = 0.42
    table = [bm.verts.new((0, cy - dep, cz + hh * k)), bm.verts.new((hw * k, cy - dep, cz)),
             bm.verts.new((0, cy - dep, cz - hh * k)), bm.verts.new((-hw * k, cy - dep, cz))]
    back = bm.verts.new((0, cy + 0.012, cz))
    for i in range(4):
        i2 = (i + 1) % 4
        bm.faces.new((girdle[i], girdle[i2], table[i2], table[i]))
        bm.faces.new((girdle[i2], girdle[i], back))
    bm.faces.new(list(reversed(table)))
    # a vertical and a horizontal ridge on the table (the reference's facet lines)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mid = bmesh.ops.poke(bm, faces=[f for f in bm.faces if len(f.verts) == 4 and all(v in table for v in f.verts)])
    for v in mid["verts"]:
        v.co.y -= 0.004
    obj = kit.mesh_object("Gem", bm, mat)
    obj["flat_shading"] = True
    return obj


def collar_paths(clay):
    """Silver wire paths (centre lines) and radii (Review 1): a neck ring that dips to a V at the gem top,
    two arched bands per side meeting in a V at the gem, two scroll curls per side, and 4 S-curved
    antler tendrils per side with curled tips rising up and out to z 0.57-0.62. Points near the chest are
    snapped onto the clay surface (half sunk)."""
    paths = []

    def snap(pts, r, lift=0.55):
        P = np.asarray(pts, float)
        S_, N_ = clay.project(P)
        return S_ + N_ * r * lift

    rng = random.Random(55)
    # neck ring: high at the back and the sides (z 0.60), dipping in a V to the gem top (z 0.47)
    ang = np.linspace(-math.pi, math.pi, 96, endpoint=False)
    vee = np.clip(1 - np.abs(ang) / (0.5 * math.pi), 0, 1) ** 1.25
    ring = np.stack([0.112 * np.sin(ang), -0.405 - 0.108 * np.cos(ang), 0.605 - 0.135 * vee], 1)
    paths.append(("neckband", snap(ring, 0.004, lift=0.2), 0.004, True))   # mostly buried in the ruff
    for s in (1, -1):
        j = lambda: rng.uniform(-0.004, 0.004)
        # upper strand: from the gem top curving up and out into the upper scroll curl (no straight band)
        arc1 = bez2((s * 0.088 + 0.021 * math.cos(math.pi * 1.1), -0.515, 0.462 + 0.021 * math.sin(math.pi * 1.1)),
                    (s * 0.085, -0.528, 0.505 + j()), (s * 0.035, -0.548, 0.505), (s * 0.006, -0.552, 0.470), 40)
        paths.append(("branch", snap(arc1, 0.0101), np.linspace(0.0107, 0.0081, 40), False))
        # lower arched band: from the chest side (z 0.53) bowing down to the gem's side corner (z 0.41)
        arc2 = bez2((s * 0.145, -0.42, 0.53), (s * 0.13, -0.48, 0.47 + j()), (s * 0.075, -0.53, 0.415), (s * 0.036, -0.547, 0.412), 40)
        paths.append(("branch", snap(arc2, 0.0094), np.linspace(0.0099, 0.0073, 40), False))
        # scroll curl below the lower arc (C/S curl), 1.4 turns
        sc = spiral((0.0, 0.0), 0.026 + j(), 1.35 + 0.1 * s, math.pi * 0.2, -s, 1.0, 0.0, 64, 0.8)
        pts = [(s * 0.074 + x, -0.53, 0.388 + y) for x, y in sc]
        pts = [(s * 0.042, -0.545, 0.398)] + pts
        paths.append(("scroll", snap(pts, 0.0072), np.linspace(0.0085, 0.0045, len(pts)), False))
        # second C curl above the lower arc, beside the gem
        sc2 = spiral((0.0, 0.0), 0.021, 1.05, math.pi * 1.1, s, 1.0, 0.0, 48, 0.8)
        pts2 = [(s * 0.088 + x, -0.515, 0.462 + y) for x, y in sc2]
        paths.append(("scroll", snap(pts2, 0.0066), np.linspace(0.0076, 0.0040, len(pts2)), False))
        # antler tendrils: S-curved, rising up and out from the arcs, each ending in a half-turn curl
        tendrils = [  # root on the arcs, S control points, tip; curl direction (+1 out, -1 in)
            (((0.125, -0.445, 0.540), (0.15, -0.44, 0.548), (0.145, -0.44, 0.565), (0.172, -0.43, 0.578)), 1),
            (((0.14, -0.435, 0.50), (0.175, -0.425, 0.505), (0.168, -0.425, 0.535), (0.19, -0.415, 0.55)), 1),
            (((0.098, -0.485, 0.530), (0.112, -0.48, 0.555), (0.100, -0.475, 0.570), (0.122, -0.465, 0.585)), -1),
            (((0.108, -0.488, 0.462), (0.135, -0.475, 0.468), (0.13, -0.47, 0.49), (0.16, -0.455, 0.50)), 1),
        ]
        for k, ((a, b, c, d), cd) in enumerate(tendrils):
            jj = (j(), j())
            P = np.array(bez2((s * a[0], a[1], a[2]), (s * b[0], b[1], b[2]), (s * c[0], c[1], c[2]),
                              (s * (d[0] + jj[0]), d[1], d[2] + jj[1]), 34))
            # tip: half a turn of a tightening curl in the frontal plane, turning outward or inward
            t_end = P[-1] - P[-2]
            t_end /= np.linalg.norm(t_end)
            side_dir = np.array([s * cd, 0.0, 0.0])
            rc = 0.011 + 0.003 * rng.random()
            curl = []
            for th in np.linspace(0.15, math.pi * 1.1, 14):
                rr = rc * (1 - 0.35 * th / math.pi)
                curl.append(P[-1] + t_end * rr * math.sin(th) + side_dir * rr * (1 - math.cos(th)))
            P = np.concatenate([P, np.array(curl)])
            P[:5] = snap(P[:5], 0.006)
            rr = np.linspace(0.0107 - 0.001 * k, 0.0045, len(P))
            rr[-4:] *= np.linspace(1.0, 0.4, 4)
            paths.append(("tine", P, rr, False))
            # a small leaf bud on the stem (reference: leaf-tipped branches)
            mid = P[22]
            dirb = P[24] - P[20]
            dirb /= np.linalg.norm(dirb)
            out = np.array([s * cd * 0.6, -0.2, 0.75])
            out /= np.linalg.norm(out)
            leaf = np.array([mid, mid + out * 0.009 + dirb * 0.004, mid + out * 0.018 + dirb * 0.006])
            paths.append(("leaf_tip", leaf, np.array([0.0039, 0.0058, 0.0]), False))
    # gem bezel: closed rhombus loop around the gem girdle
    hh, hw = 0.056 * 1.12, 0.031 * 1.18
    cy, cz = GEM_C[1] + 0.002, GEM_C[2]
    corners = [(0, cy, cz + hh), (hw, cy, cz), (0, cy, cz - hh), (-hw, cy, cz)]
    loop = []
    for i in range(4):
        a, b = np.array(corners[i]), np.array(corners[(i + 1) % 4])
        for f in np.linspace(0, 1, 16, endpoint=False):
            loop.append(a + (b - a) * f)
    paths.append(("gem_setting", np.array(loop), 0.0058, True))
    return paths


def build_collar(clay, mat):
    objs = []
    for k, (kind, P, r, closed) in enumerate(collar_paths(clay)):
        P = np.asarray(P, float)
        # filigree wire: about 6 mm across on the reference (gem setting heavier)
        rr = np.broadcast_to(np.asarray(r, float), (len(P),)).copy() * (1.0 if kind == "gem_setting" else 0.62)
        if not closed and kind in ("scroll", "tine", "leaf_tip"):
            rr[-1] = 0.0
        hint = (0.0, -1.0, 0.0) if kind != "neckband" else (0.0, 0.0, 1.0)
        sides = {"tine": 10, "leaf_tip": 6, "neckband": 10}.get(kind, 12)
        o, _ = sweep(f"collar_{kind}_{k}", P, rr, rr * (0.8 if kind in ("gem_setting", "leaf_tip") else 1.0), sides,
                     mat, hint=hint, closed=closed)
        objs.append(o)
    return objs


# ============================================================================ SHOULDER FEATHERS
# the shoulder fur's locks (side view, Y z): root on the front of the shoulder, tip up and back, width at the
# widest, bow of the lock (convex up); measured tips: the big one at (-0.143, 0.71) rising above the back
# line, the lower ones lying on the shoulder (tips at z 0.47-0.61), two short ones at the nape
SHOULDER_LOCKS = [((-0.435, 0.425), (-0.250, 0.470), 0.050, 0.018),
                  ((-0.432, 0.462), (-0.226, 0.514), 0.060, 0.022),
                  ((-0.425, 0.500), (-0.200, 0.557), 0.068, 0.026),
                  ((-0.416, 0.540), (-0.180, 0.606), 0.074, 0.028),
                  ((-0.405, 0.578), (-0.143, 0.712), 0.080, 0.034),
                  ((-0.405, 0.612), (-0.210, 0.698), 0.054, 0.028),
                  ((-0.415, 0.638), (-0.256, 0.684), 0.042, 0.022)]


def build_shoulder_fur(clay, mat):
    """The shoulder fur: magical flame-shaped locks lying on the shoulder like a folded wing, rooted on its
    front and sweeping up and back in a convex-up bow, the lower locks lying over the upper ones; only the
    tips leave the body, curling up a little, and the top lock rises above the back line behind the head.
    Built as fur locks (Fur.lock: flat, tapering, two strand grooves) on the body clay. One object per side."""
    objs = []
    rng = random.Random(91)
    n = len(SHOULDER_LOCKS)
    for side in (1, -1):
        fur = Fur()
        for k, (r, t, w0, bow) in enumerate(SHOULDER_LOCKS):
            r = np.array(r) + np.array([rng.uniform(-0.006, 0.006), rng.uniform(-0.006, 0.006)])
            t = np.array(t) + np.array([rng.uniform(-0.008, 0.008), rng.uniform(-0.008, 0.008)])
            d = t - r
            perp = np.array([-d[1], d[0]]) / np.linalg.norm(d)
            if perp[1] < 0:
                perp = -perp
            ctrl = (r + t) / 2 + perp * bow * 2.8
            ns = 26
            tt = np.linspace(0, 1, ns)
            YZ = ((1 - tt) ** 2)[:, None] * r + (2 * tt * (1 - tt))[:, None] * ctrl + (tt ** 2)[:, None] * t
            YZ[:, 1] += 0.040 * smoothstep(tt, 0.55, 1.0) ** 2        # the tip curls up
            Q = np.stack([np.full(ns, side * 0.115), YZ[:, 0], YZ[:, 1]], 1)
            Sp, Nr = clay.project(Q)
            out = np.array([side, 0.0, 0.0])
            lift = 0.0015 + 0.004 * (n - 1 - k) / (n - 1) + smoothstep(tt, 0.65, 1.0) * (0.009 + 0.005 * rng.random())
            w8 = 0.5 * smoothstep(tt, 0.55, 0.95)[:, None]
            nrm = Nr * (1 - w8) + out[None, :] * w8
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
            P = Sp + nrm * lift[:, None]
            # where the lock rises above the back it stays where it grows (not pulled down onto the body):
            # it leaves the surface smoothly where the surface falls away from its path
            gap = np.linalg.norm(Sp - Q, axis=1)
            free = smoothstep(gap, 0.015, 0.05)
            free = np.maximum.accumulate(free)[:, None]
            Qx = Q.copy()
            Qx[:, 0] = np.where(free[:, 0] > 0, P[np.argmax(free[:, 0] > 0) - 1 if (free[:, 0] > 0).any() else 0, 0], Q[:, 0])
            P = P * (1 - free) + Qx * free
            # off the body the lock's flat faces turn to the side (no normals from far-off projections)
            nrm = nrm * (1 - free) + out[None, :] * free
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
            for _ in range(3):
                nrm[1:-1] = (nrm[:-2] + 2 * nrm[1:-1] + nrm[2:]) / 4
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
            for _ in range(6):
                P[1:-1] = (P[:-2] + 2 * P[1:-1] + P[2:]) / 4
            w = 1.5 * w0 * rng.uniform(0.92, 1.08)
            # flame outline: from a buried root to the widest point at 0.35, then a long taper to the tip
            width = w * np.where(tt < 0.35, 0.45 + 0.55 * np.sin(tt / 0.35 * math.pi / 2), np.clip((1 - tt) / 0.65, 0, 1) ** 0.85)
            thick = np.minimum(width * 0.12, 0.007) + 0.0015
            fur.lock(P, nrm, width, thick, 0.0, ljit=rng.uniform(-1, 1), M=10, ridge=0.16)
        o = fur.to_object(f"shoulder_fur_{'left' if side > 0 else 'right'}", mat)
        objs.append(o)
    return objs


# ============================================================================ TAILS (fur)
# A tail is a mass of long guard hair over dense underfur. In this style the guard hair groups into broad,
# smooth locks that flow from the root to the tip and lie on the mass: bands of cream, light, mid and dark
# blue, each lock a low lens with a groove to its neighbours, a darker root and a lighter tip, the next lock
# starting under it; only the tips leave the outline, as pointed curling locks. Built so: the fur mass is
# sculpted as clay (signed distance, its outline measured on the reference) and remeshed; the locks are
# relief displaced along the fur's flow (parallel to the plume's outline, along a curl's spiral, along a
# tail with a slow twist), and every vertex carries its lock's colour band, root-to-tip and across-lock
# coordinates for the fur shader; the loose tips are separate tapered locks (Fur.lock).
def catmull(pts, per=8):
    """Catmull-Rom spline through 2D/3D points, ``per`` samples per span."""
    P = np.concatenate([pts[:1] * 2 - pts[1:2], pts, pts[-1:] * 2 - pts[-2:-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def coil(c, n, e_h, R0, phi0, turns, n_pts, shrink=2.0, power=1.0, drift=0.0, sv=1.0):
    """Planar spiral (outer end first) around centre c in the plane with normal n: phi 0 is straight up,
    increasing toward e_h. The radius falls from R0 to 0 over ``shrink`` turns."""
    c, n, e_h = (np.asarray(v, float) for v in (c, n, e_h))
    n = n / np.linalg.norm(n)
    e_h = e_h - (e_h @ n) * n
    e_h /= np.linalg.norm(e_h)
    up = np.array([0.0, 0.0, 1.0])
    up = up - (up @ n) * n
    up /= np.linalg.norm(up)
    out = []
    for i in range(n_pts):
        f = i / (n_pts - 1)
        phi = phi0 + f * turns * 2 * math.pi
        r = R0 * max(1 - f * turns / shrink, 0.0) ** power
        out.append(c + r * (sv * math.cos(phi) * up + math.sin(phi) * e_h) + n * drift * math.sin(f * math.pi))
    return np.array(out)


def resample(P, n):
    """n points evenly spaced along polyline P."""
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, P[:, k]) for k in range(P.shape[1])], 1)


# fur colour bands (the material's ramp): 0 cream, 1 warm cream, 2 light blue, 3 mid blue, 4 dark blue,
# 5 indigo, 6 deep indigo (underfur)
BAND = lambda k: k / 6.0


class Fur:
    """Collects tapered fur locks into one bmesh, with per-vertex attributes for the fur material: lu (0 root
    .. 1 tip), lv (around the lock), band (colour), ljit (per-lock tone), lglow (a glowing streak)."""
    KEYS = ("lu", "lv", "band", "ljit", "lglow")

    def __init__(self):
        self.bm = bmesh.new()
        self.lay = {k: self.bm.verts.layers.float.new(k) for k in self.KEYS}
        self.locks = 0

    def tube(self, C, hint, ru, rv, M, attrs, ridge=0.0, cap=True):
        """Tube through C (n,3): radius ru along the frame normal (from hint), rv along the binormal; a
        zero radius at the end makes a pointed tip. attrs: dict of scalars or per-point arrays."""
        C = np.asarray(C, float)
        n = len(C)
        T, N, B = frames(C, hint)
        ru = np.broadcast_to(np.asarray(ru, float), (n,))
        rv = np.broadcast_to(np.asarray(rv, float), (n,))
        ang = np.arange(M) / M * 2 * math.pi
        rid = 1.0 + ridge * np.where(np.arange(M) % 2 == 0, 1.0, -1.0) * np.abs(np.cos(ang))
        lu = np.linspace(0.0, 1.0, n)
        av = {k: np.broadcast_to(np.asarray(attrs.get(k, 0.0), float), (n,)) for k in self.KEYS if k not in ("lu", "lv")}
        tip = ru[-1] < 1e-5 and rv[-1] < 1e-5
        rows = []
        for i in range(n - 1 if tip else n):
            row = []
            for j in range(M):
                p = C[i] + N[i] * ru[i] * math.cos(ang[j]) * rid[j] + B[i] * rv[i] * math.sin(ang[j])
                v = self.bm.verts.new(p)
                v[self.lay["lu"]] = lu[i]
                v[self.lay["lv"]] = j / M
                for k, arr in av.items():
                    v[self.lay[k]] = arr[i]
                row.append(v)
            rows.append(row)
        for i in range(len(rows) - 1):
            for j in range(M):
                j2 = (j + 1) % M
                self.bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))

        def point(p, i):
            v = self.bm.verts.new(p)
            v[self.lay["lu"]] = lu[i]
            v[self.lay["lv"]] = 0.0
            for k, arr in av.items():
                v[self.lay[k]] = arr[i]
            return v
        if tip:
            tv = point(C[-1], n - 1)
            for j in range(M):
                self.bm.faces.new((rows[-1][j], rows[-1][(j + 1) % M], tv))
        else:
            self.bm.faces.new(list(reversed(rows[-1])))
        if cap:
            cv = point(C[0], 0)
            for j in range(M):
                self.bm.faces.new((rows[0][(j + 1) % M], rows[0][j], cv))

    def lock(self, C, nrm, width, thick, band, ljit=0.0, lglow=0.0, M=8, ridge=0.14):
        """One lock of fur along C lying on a surface with normals nrm: flat (thick along the normal, wide
        across), tapering to a pointed tip; two grooves along its top split it into strand clumps."""
        width = np.asarray(width, float).copy()
        thick = np.asarray(thick, float).copy()
        width[-1] = thick[-1] = 0.0
        self.tube(C, np.asarray(nrm, float), thick * 0.5, width * 0.5, M,
                  dict(band=band, ljit=ljit, lglow=lglow), ridge=ridge)
        self.locks += 1

    def to_object(self, name, mat):
        self.bm.normal_update()
        obj = kit.mesh_object(name, self.bm, mat)
        obj.data.shade_smooth()
        return obj


def tail_lock(fur, cps, r0, hint, band, rng):
    """A loose lock leaving the outline: a main strand clump and one or two thinner ones that part from it
    toward the tip, each tapering to a point."""
    P = np.array(S.bezier(*cps, 26))
    tt = np.linspace(0, 1, len(P))
    hint = np.asarray(hint, float)
    T, N, Bv = frames(P, hint)
    for k in range(3 if r0 > 0.035 else 2):
        sgn = (-1) ** k
        off = np.zeros(len(tt)) if k == 0 else sgn * r0 * (0.35 + 0.25 * k) * smoothstep(tt, 0.35, 1.0)
        shrink = 1.0 if k == 0 else 0.55 - 0.1 * k
        end = 1.0 if k == 0 else 0.82 + rng.uniform(-0.05, 0.05)
        m = tt <= end + 1e-9
        C = P[m] + Bv[m] * off[m][:, None] + N[m] * (0.25 * r0 * k * sgn)
        f = tt[m] / end
        prof = r0 * shrink * np.clip(1 - f, 0, 1) ** (0.85 + 0.2 * rng.random()) * (0.75 + 0.25 * np.clip(f / 0.2, 0, 1))
        fur.lock(C, np.tile(hint, (len(C), 1)), prof * 2.0, prof * 1.1, BAND(band + (1 if k == 2 else 0)),
                 ljit=rng.uniform(-1, 1), M=10, ridge=0.1)


def curl_frame(L):
    n = np.asarray(L["n"], float)
    n = n / np.linalg.norm(n)
    e_h = np.asarray(L["e_h"], float)
    e_h = e_h - (e_h @ n) * n
    e_h /= np.linalg.norm(e_h)
    up = np.array([0.0, 0.0, 1.0]) - n[2] * n
    up /= np.linalg.norm(up)
    return np.asarray(L["c"], float), n, e_h, up


def sd_ellipsoid_axes(c, axes, radii):
    """Ellipsoid with arbitrary orthonormal axes (rows of ``axes``)."""
    c, A, rad = np.asarray(c, float), np.asarray(axes, float), np.asarray(radii, float)

    def fn(x, y, z):
        dx, dy, dz = x - c[0], y - c[1], z - c[2]
        q = [A[i, 0] * dx + A[i, 1] * dy + A[i, 2] * dz for i in range(3)]
        k0 = np.sqrt(sum((q[i] / rad[i]) ** 2 for i in range(3)))
        k1 = np.sqrt(sum((q[i] / rad[i] ** 2) ** 2 for i in range(3)))
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    m = float(rad.max())
    return S.Prim(fn, c - m, c + m)


# ---------------------------------------------------------------- lock relief (shared)
def hash01(*xs):
    v = np.zeros(np.broadcast(*xs).shape) if len(xs) > 1 else np.zeros(np.shape(xs[0]))
    for i, x in enumerate(xs):
        v = v + np.asarray(x, float) * (12.9898 + 41.23 * i)
    return np.mod(np.sin(v) * 43758.5453, 1.0)


def band_pattern(q, pattern):
    """q in pattern repeats; pattern [(width, band)]: -> band colour index, f across the band (0..1), serial k."""
    W = np.array([w for w, _ in pattern], float)
    W /= W.sum()
    E = np.cumsum(W)
    S0 = E - W
    rep = np.floor(q)
    pos = q - rep
    i = np.minimum(np.searchsorted(E, pos, side="right"), len(W) - 1)
    f = np.clip((pos - S0[i]) / W[i], 0, 1)
    band = np.array([b for _, b in pattern], float)[i]
    return band, f, rep * len(W) + i


def set_corner_attr(obj, name, values):
    me = obj.data
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    a = me.attributes.new(name, "FLOAT", "CORNER")
    a.data.foreach_set("value", np.asarray(values, np.float32))


def loop_faces(obj):
    """(vertex index, face index) per face corner."""
    me = obj.data
    vi = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", vi)
    ls = np.empty(len(me.polygons), np.int64)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    return vi, np.repeat(np.arange(len(ls)), lt)


def apply_locks(obj, q, pid, band, f, s_len, amp, lock_len=0.17, gshare=0.0, wrap=None):
    """Displace the fur surface into locks (a lens across each band, grooves between) and write what the
    fur shader needs to draw the same locks per pixel: bq (the continuous band coordinate, in pattern
    repeats; the shader looks its band, slot and across-lock position up in LW_tail_bands row pid), sflow
    (metres along the flow / lock length: lock ends, roots and tips), gshare (share of locks with a glow
    streak). band, f: the band and across-lock position per vertex (for the relief); amp: relief height."""
    co, no = verts_np(obj), vnormals_np(obj)
    prof = np.sin(np.pi * f) ** 0.6
    co = co + no * (amp * (prof - 0.55))[:, None]
    obj.data.vertices.foreach_set("co", co.ravel())
    obj.data.update()
    n = len(co)
    # the band coordinate per face corner: where it comes from an angle (around a curl or a tube) it is
    # unwrapped per face, so the faces across the angle's seam draw their bands without a smear
    vi, fi = loop_faces(obj)
    ql = q[vi]
    if wrap is not None:
        ang, scale = wrap
        fs = np.bincount(fi, np.sin(ang[vi]))
        fc = np.bincount(fi, np.cos(ang[vi]))
        af = np.arctan2(fs, fc)[fi]
        av = ang[vi]
        ql = ql + scale * np.round((af - av) / (2 * math.pi))
    set_corner_attr(obj, "bq", ql)
    set_attr(obj, "pid", np.full(n, float(pid)))
    set_attr(obj, "sflow", s_len / lock_len)
    set_attr(obj, "lut", np.ones(n))
    set_attr(obj, "gshare", np.full(n, gshare))
    tail_projection_attrs(obj, co)
    return co


def tail_projection_attrs(obj, co):
    """Coordinates of the tail marks image (side: Y -0.10..0.92, z; back: X -0.51..0.51, z)."""
    set_attr(obj, "tys", (co[:, 1] + TAIL_Y0) / MARK_SPAN)
    set_attr(obj, "pzs", co[:, 2] / MARK_SPAN)
    set_attr(obj, "pxf", (co[:, 0] + 0.51) / MARK_SPAN)


def remesh_clay(clay, name, faces):
    o = clay.to_object(name, symmetric=False)
    kit.quad_remesh(o, faces)
    close_holes(o)
    o.data.shade_smooth()
    return o


# ---------------------------------------------------------------- the plume (centre tail)
# its outline (Y, z) on the side view's mask (cv: top edge z 0.71 at Y 0.24-0.40, back edge Y 0.62 at
# z 0.34-0.42, inner edge Y 0.25 at z 0.30-0.42), the root inside the rump, the lower edge hidden behind the
# curls; per point the width of the lock zone (from the outline in to the dark starry underfur): broad at
# the outer edge (0.14), thin along the inner edge (0.045)
PLUME = np.array([(-0.05, 0.600), (0.02, 0.608), (0.08, 0.604), (0.12, 0.613), (0.15, 0.636), (0.18, 0.670),
                  (0.21, 0.697), (0.24, 0.709), (0.30, 0.709), (0.36, 0.715), (0.42, 0.703), (0.48, 0.674),
                  (0.53, 0.645), (0.565, 0.600), (0.590, 0.550), (0.605, 0.500), (0.616, 0.440),
                  (0.620, 0.380), (0.613, 0.330), (0.597, 0.292), (0.565, 0.266), (0.505, 0.252),
                  (0.430, 0.250), (0.360, 0.258), (0.300, 0.275), (0.265, 0.292), (0.250, 0.320),
                  (0.250, 0.380), (0.246, 0.420), (0.228, 0.458), (0.190, 0.484), (0.140, 0.500),
                  (0.080, 0.508), (0.020, 0.520), (-0.05, 0.535)])
PLUME_ZONE = np.array([0.06, 0.07, 0.08, 0.10, 0.12, 0.13, 0.14, 0.145, 0.145, 0.145, 0.14, 0.135, 0.13, 0.13,
                       0.13, 0.13, 0.13, 0.13, 0.125, 0.11, 0.10, 0.09, 0.08, 0.07, 0.065, 0.06, 0.05, 0.045,
                       0.045, 0.045, 0.05, 0.05, 0.05, 0.055, 0.06])
def closed_spline(P, per=6):
    """Closed Catmull-Rom curve through P (n, 2)."""
    Q = np.concatenate([P[-1:], P, P[:2]])
    out = []
    for i in range(1, len(P) + 1):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


PLUME_RAW, PLUME_ZONE_RAW = PLUME, PLUME_ZONE
PLUME = closed_spline(PLUME_RAW, 6)
PLUME_ZONE = np.repeat(PLUME_ZONE_RAW, 6) * 0.0 + np.interp(np.arange(len(PLUME)) / 6.0, np.arange(len(PLUME_ZONE_RAW)), PLUME_ZONE_RAW)
PLUME_ROUND = 0.07   # rim rounding (in the plane of the plume)
# lock bands from the rim's crest inward, per face (+X, -X), as shares of the lock zone
PLUME_BANDS = {1: [(0.10, 2), (0.17, 0), (0.15, 2), (0.07, 1), (0.16, 3), (0.11, 0), (0.12, 2), (0.12, 4)],
               -1: [(0.12, 3), (0.18, 0), (0.14, 2), (0.10, 0), (0.17, 3), (0.09, 1), (0.20, 4)]}


def poly_sdf2(P, Y, Z, want_s=False):
    """Signed distance (negative inside) from points (Y, Z) to the closed polygon P (n, 2); with want_s also
    the nearest outline point's arc position (0..1 from P[0]) and the outline's length."""
    Y, Z = np.broadcast_arrays(np.asarray(Y, float), np.asarray(Z, float))
    best = np.full(Y.shape, np.inf)
    sb = np.zeros(Y.shape)
    inside = np.zeros(Y.shape, bool)
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    for i in range(len(P)):
        a, b = Q[i], Q[i + 1]
        ab = b - a
        t = np.clip(((Y - a[0]) * ab[0] + (Z - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        d = np.hypot(Y - (a[0] + t * ab[0]), Z - (a[1] + t * ab[1]))
        m = d < best
        best = np.where(m, d, best)
        sb = np.where(m, cum[i] + t * seg[i], sb)
        inside ^= ((a[1] > Z) != (b[1] > Z)) & (Y < ab[0] * (Z - a[1]) / (ab[1] + 1e-12) + a[0])
    d = np.where(inside, -best, best)
    return (d, sb / cum[-1], cum[-1]) if want_s else d


def plume_T(Y, Z):
    """Half thickness of the plume across (X): thin up top (hidden behind the head in the back view),
    fuller low where it falls into the centre curl, and at the root."""
    return 0.048 + 0.055 * np.clip((0.52 - Z) / 0.24, 0, 1) + 0.016 * np.clip((0.10 - Y) / 0.14, 0, 1)


def plume_xc(Z):
    return -0.018 * np.clip((0.52 - Z) / 0.3, 0, 1)


def plume_h(d, T):
    k = np.clip(d / PLUME_ROUND, 0, 1)
    return T * np.sqrt(np.clip(1 - (1 - k) ** 2, 0, 1)) + np.clip(0.10 * (d - PLUME_ROUND), 0, 0.012)


def rim_arc(d, T):
    """Arc length over the plume's rounded rim from its crest to the place at in-plane depth d."""
    D = PLUME_ROUND
    al = np.arccos(np.clip(1 - np.minimum(d, D) / D, -1, 1))
    ts = np.linspace(0, 1, 25)[None, :] * al[:, None]
    integrand = np.sqrt((D * np.sin(ts)) ** 2 + (T[:, None] * np.cos(ts)) ** 2)
    E = np.trapezoid(integrand, ts, axis=1) if hasattr(np, "trapezoid") else np.trapz(integrand, ts, axis=1)
    return E + np.maximum(d - D, 0)


def sd_plume():
    def fn(x, y, z):
        Y2, Z2 = y[0], z[0]           # (ny, 1), (1, nz)
        d2 = poly_sdf2(PLUME, Y2, Z2)
        Yb, Zb = np.broadcast_arrays(Y2, Z2)
        h = plume_h(np.maximum(-d2, 0), plume_T(Yb, Zb))
        return np.maximum(d2[None], np.abs(x - plume_xc(Zb)[None]) - h[None])
    return S.Prim(fn, (-0.14, -0.08, 0.18), (0.14, 0.66, 0.74))


def build_plume(mat):
    clay = S.Clay((-0.14, -0.08, 0.18), (0.14, 0.66, 0.74), voxel=0.0035)
    clay.add(sd_plume())
    o = remesh_clay(clay, "tail_centre", 10000)
    co = verts_np(o)
    d2, s01, per = poly_sdf2(PLUME, co[:, 1], co[:, 2], want_s=True)
    d = np.maximum(-d2, 0)
    T = plume_T(co[:, 1], co[:, 2])
    zone = np.interp(s01 * per, np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(np.vstack([PLUME, PLUME[:1]]), axis=0), axis=1))])[:-1], PLUME_ZONE)
    u = rim_arc(d, T)
    g = u / rim_arc(zone, T)
    side = np.where(co[:, 0] - plume_xc(co[:, 2]) >= 0, 1, -1)
    sl = s01 * per
    # the bands wave and pinch along the flow (locks narrowing to their ends)
    g = g + 0.05 * np.sin(sl * 21.0 + side) + 0.045 * g * np.sin(sl * 13.0 + 2.0 * side)
    qs = np.clip(side * g, -0.999, 0.999)
    band = np.zeros(len(co))
    f = np.zeros(len(co))
    for sd in (1, -1):
        m = side == sd
        band[m], f[m], _ = band_pattern(np.abs(qs[m]), PLUME_BANDS[sd])
    core = smoothstep(g, 0.97, 1.08)
    amp = 0.0055 * (1 - core) * smoothstep(co[:, 1], 0.0, 0.08)
    apply_locks(o, (qs + 1) / 2, 0, band, f, sl, amp, lock_len=0.19, gshare=0.03)
    # the dark starry underfur inside the lock zone, on both faces
    set_attr(o, "starry", core)
    set_attr(o, "curl_centre", np.zeros(len(co)))
    return o


# ---------------------------------------------------------------- tail curls (the tail ends coiled on the ground)
# the centre curl faces the back (the back view's big centre spiral, x -0.04 z 0.13 r 0.16); the left (+X)
# curl is a long roll turned between the side and the back (side view: the ground sweep Y 0.08-0.54 z 0-0.30
# with its spiral at Y 0.28 z 0.17; back view: x 0.0-0.35); the right (-X) curl faces back-out (back view
# x -0.12..-0.36 z 0.16)
TAIL_CURLS = {
    "centre": dict(c=(-0.035, 0.420, 0.158), n=(0.0, 1.0, 0.0), e_h=(-1.0, 0.0, 0.0), rh=0.152, rv=0.150, rn=0.085, turns=2.2,
                   pattern=[(0.32, 0), (0.10, 2), (0.30, 3), (0.12, 4), (0.16, 2)]),
    1: dict(c=(0.170, 0.275, 0.158), n=(0.80, 0.60, 0.0), e_h=(0.60, -0.80, 0.0), rh=0.165, rv=0.150, rn=0.072, turns=2.3,
            pattern=[(0.34, 0), (0.12, 2), (0.30, 3), (0.08, 4), (0.16, 2)]),
    -1: dict(c=(-0.200, 0.340, 0.158), n=(-0.62, 0.78, 0.0), e_h=(-0.78, -0.62, 0.0), rh=0.140, rv=0.150, rn=0.080, turns=2.2,
             pattern=[(0.30, 0), (0.14, 2), (0.32, 3), (0.10, 4), (0.14, 2)]),
}
SIDE_PATTERN = [(0.30, 0), (0.22, 2), (0.30, 3), (0.18, 2)]
THIN_PATTERN = [(0.35, 2), (0.30, 3), (0.35, 0)]
# rows of the band lookup image: 0 the plume (signed lock-zone coordinate), 1-3 the curls, 4 side tails, 5 thin
CURL_PID = {"centre": 1, 1: 2, -1: 3}


def build_tail_curl(key, mat):
    """One tail curl: the tail's end coiled on the ground, a fat soft mass of fur (clay: a mass in the coil
    plane, a little fuller at its outer turn, seated on the ground) whose locks follow the spiral into the
    centre in interleaved streams (cream, light blue, mid blue, dark), on both faces and over the rim."""
    Bc = TAIL_CURLS[key]
    c, n, e_h, up = curl_frame(Bc)
    rh, rv, rn = Bc["rh"], Bc["rv"], Bc["rn"]
    span = max(rh, rv, rn) + 0.06
    clay = S.Clay(c - span, c + span, voxel=0.0035)
    clay.add(sd_ellipsoid_axes(c, [e_h, up, n], (rh, rv, rn)))
    clay.add(sd_ellipsoid_axes(c + up * 0.03 - e_h * 0.03, [e_h, up, n], (rh * 0.8, rv * 0.82, rn * 1.1)), blend=0.03)
    clay.intersect(S.sd_halfspace((0, 0, 0.002), (0, 0, -1)), blend=0.012)
    name = "tail_curl_centre" if key == "centre" else f"tail_curl_{'left' if key == 1 else 'right'}"
    area = 2 * math.pi * rh * rv + 2 * math.pi * math.sqrt((rh * rh + rv * rv) / 2) * rn * 1.4
    o = remesh_clay(clay, name, int(area / 5.2e-5))
    co = verts_np(o)
    rel = co - c
    a, b = rel @ e_h / rh, rel @ up / rv
    r = np.hypot(a, b)
    phi = np.arctan2(a, b)
    Tn = Bc["turns"]
    q = r * Tn + phi / (2 * math.pi) + 0.03 * np.sin(phi * 3 + r * 9)
    band, f, _ = band_pattern(q, Bc["pattern"])
    phu = 2 * math.pi * Tn * (1 - np.clip(r, 0, 1))
    R = 0.5 * (rh + rv)
    s_len = R * (phu - phu ** 2 / (4 * math.pi * Tn))
    amp = 0.006 * smoothstep(r, 0.06, 0.22)
    apply_locks(o, q, CURL_PID[key], band, f, s_len, amp, lock_len=0.15, gshare=0.0, wrap=(phi, 1.0))
    set_attr(o, "starry", np.zeros(len(co)))
    set_attr(o, "curl_centre", np.ones(len(co)) if key == "centre" else np.zeros(len(co)))
    return o


# ---------------------------------------------------------------- the side and thin tails (tubes of fur)
# the side tails run inside the plume from the rump and leave its lower edge into their curls; the thin
# tails leave the plume's back edge at z 0.40 out sideways to x +-0.35, the tips hanging down (back view
# wisps; side view: the lock tips hanging at the plume's back edge, Y 0.58 z 0.2-0.27)
def tail_tubes():
    out = []
    for side in (1, -1):
        # from inside the plume's back edge (its vertical bands in the side view, clear of the stars) down
        # and out into the curl: the back view's side tails fanning from the rump to the side spirals
        cps = np.array([(side * 0.01, 0.565, 0.52), (side * 0.05, 0.55, 0.45), (side * 0.10, 0.52, 0.37),
                        (side * 0.14, 0.47, 0.30), (side * 0.16, 0.42, 0.25), (side * 0.165, 0.36, 0.21)]) if side > 0 else \
            np.array([(-0.01, 0.565, 0.52), (-0.05, 0.55, 0.45), (-0.11, 0.52, 0.37), (-0.16, 0.48, 0.30),
                      (-0.19, 0.44, 0.25), (-0.20, 0.40, 0.21)])
        P = resample(catmull(cps, 12), 90)
        r = np.interp(np.linspace(0, 1, len(P)), [0, 0.4, 1.0], [0.035, 0.05, 0.06])
        out.append(dict(name=f"tail_side_{'left' if side > 0 else 'right'}", P=P, r=r, K=3, twist=0.35,
                        pid=4, faces=1400))
    for side in (1, -1):
        dz = 0.0 if side > 0 else 0.015
        cps = np.array([(side * 0.03, 0.52, 0.378 + dz), (side * 0.14, 0.55, 0.366 + dz), (side * 0.25, 0.565, 0.348 + dz),
                        (side * 0.32, 0.575, 0.322 + dz), (side * 0.352, 0.58, 0.288 + dz), (side * 0.346, 0.585, 0.248 + dz)])
        P = resample(catmull(cps, 12), 110)
        r = np.interp(np.linspace(0, 1, len(P)), [0, 0.3, 0.7, 0.9, 1.0], [0.026, 0.023, 0.016, 0.009, 0.003])
        out.append(dict(name=f"tail_thin_{'left' if side > 0 else 'right'}", P=P, r=r, K=2, twist=0.3,
                        pid=5, faces=1500))
    return out


def build_tail_tube(t, mat):
    P, r = t["P"], t["r"]
    lo, hi = P.min(0) - r.max() - 0.03, P.max(0) + r.max() + 0.03
    clay = S.Clay(lo, hi, voxel=0.003)
    clay.add(S.sd_tube(list(P[::3]), list(r[::3]), blend=0.01))
    o = remesh_clay(clay, t["name"], t["faces"])
    co = verts_np(o)
    T, N, B = frames(P, (0.0, 0.0, 1.0))
    sl = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    best = np.full(len(co), np.inf)
    idx = np.zeros(len(co), int)
    for i in range(len(P)):
        dd = np.linalg.norm(co - P[i], axis=1)
        m = dd < best
        best[m], idx[m] = dd[m], i
    rel = co - P[idx]
    th = np.arctan2((rel * B[idx]).sum(1), (rel * N[idx]).sum(1))
    s = sl[idx]
    q = t["K"] * (th / (2 * math.pi) + t["twist"] * s / sl[-1]) + 0.04 * np.sin(s * 25)
    band, f, _ = band_pattern(q, SIDE_PATTERN if t["pid"] == 4 else THIN_PATTERN)
    amp = 0.004 * np.clip(r[idx] / 0.03, 0.4, 1.0)
    apply_locks(o, q, t["pid"], band, f, s, amp, lock_len=0.16, gshare=0.12, wrap=(th, float(t["K"])))
    set_attr(o, "starry", np.zeros(len(co)))
    set_attr(o, "curl_centre", np.zeros(len(co)))
    return o


# loose fur locks that leave the tails' outline and taper to curling points (side view unless named): the
# tip curling forward-up on top of the plume (Y 0.21 z 0.71), the tip hooking up at its top back (Y 0.57
# z 0.71), the hook on the inner edge (Y 0.21 z 0.34), the lock hanging off the back edge, the flick at the
# end of the ground sweep (Y 0.56 z 0.05-0.10), the front view's hook rising on the left curl (to z 0.39),
# a lock on the right curl.  (bezier control points, root radius, frame hint, colour band)
TAIL_LOCKS = [
    ([(0.025, 0.34, 0.690), (0.025, 0.262, 0.716), (0.025, 0.214, 0.730), (0.025, 0.200, 0.708)], 0.020, (1, 0, 0), 2),
    ([(0.022, 0.45, 0.688), (0.022, 0.528, 0.668), (0.022, 0.585, 0.672), (0.022, 0.574, 0.714)], 0.021, (1, 0, 0), 2),
    ([(0.045, 0.262, 0.410), (0.045, 0.228, 0.340), (0.045, 0.200, 0.322), (0.046, 0.206, 0.350)], 0.022, (1, 0, 0), 3),
    ([(0.050, 0.555, 0.300), (0.060, 0.598, 0.250), (0.062, 0.600, 0.190), (0.058, 0.585, 0.165)], 0.030, (1, 0, 0), 0),
    ([(-0.010, 0.520, 0.290), (-0.010, 0.560, 0.240), (-0.012, 0.565, 0.180), (-0.012, 0.548, 0.150)], 0.026, (1, 0, 0), 2),
    ([(0.160, 0.34, 0.050), (0.140, 0.47, 0.026), (0.128, 0.576, 0.042), (0.124, 0.560, 0.105)], 0.052, (0, 0, 1), 0),
    ([(0.140, 0.36, 0.070), (0.120, 0.46, 0.050), (0.110, 0.540, 0.070), (0.108, 0.530, 0.112)], 0.034, (0, 0, 1), 3),
    ([(0.262, 0.290, 0.215), (0.318, 0.285, 0.300), (0.290, 0.280, 0.392), (0.196, 0.278, 0.368)], 0.028, (0, 1, 0), 2),
    ([(-0.270, 0.330, 0.220), (-0.335, 0.330, 0.270), (-0.338, 0.335, 0.215), (-0.312, 0.335, 0.190)], 0.034, (0, 1, 0), 1),
]


TAIL_Y0 = 0.10   # the tail marks image covers Y -0.10 .. 0.92 (the body's covers -0.72 .. 0.30)
LUT_W, LUT_H = 1024, 8


def tail_marks_image():
    """Side (Y, Z) and back (X, Z) projections of the constellations' glowing lines: R = side lines on the
    plume, G = back lines on the centre curl."""
    n = MARK_RES
    cc = (np.arange(n) + 0.5) / n * MARK_SPAN
    Ys, Zs = np.meshgrid(cc - TAIL_Y0, cc)
    Xb, Zb = np.meshgrid(cc - 0.51, cc)
    img = np.zeros((n, n, 3), np.float32)
    px = MARK_SPAN / n
    for a, b in CONST_SIDE_LINES:
        poly_paint(img[..., 0], Ys, Zs, [CONST_SIDE[a], CONST_SIDE[b]], [0.0024, 0.0024], 1.5 * px, halo=0.35, halo_w=0.003)
    for a, b in CONST_BACK_LINES:
        poly_paint(img[..., 1], Xb, Zb, [CONST_BACK[a], CONST_BACK[b]], [0.003, 0.003], 1.5 * px, halo=0.5, halo_w=0.004)
    x0, z0 = CONST_BACK[0]
    poly_paint(img[..., 1], Xb, Zb, [(x0, z0), (x0 + 0.012, z0 + 0.03)], [0.0025, 0.0015], 1.5 * px, halo=0.4, halo_w=0.003)
    return new_image("LW_tail_marks", n, n, img)


def band_lut_image():
    """The lock patterns as a lookup image, one row per pattern (pid): R the band's colour (BAND), G its slot
    in the pattern (/16), B the place across the lock (0..1). Row 0, the plume, holds the signed lock-zone
    coordinate (-X face left, +X face right of the middle)."""
    pats = {1: TAIL_CURLS["centre"]["pattern"], 2: TAIL_CURLS[1]["pattern"], 3: TAIL_CURLS[-1]["pattern"],
            4: SIDE_PATTERN, 5: THIN_PATTERN}
    img = np.zeros((LUT_H, LUT_W, 3), np.float32)
    x = (np.arange(LUT_W) + 0.5) / LUT_W
    q = x * 2 - 1
    for sd in (1, -1):
        m = (q >= 0) if sd > 0 else (q < 0)
        b_, f_, k_ = band_pattern(np.clip(np.abs(q[m]), 0, 0.999), PLUME_BANDS[sd])
        img[0, m, 0], img[0, m, 1], img[0, m, 2] = b_ / 6.0, (k_ + (0 if sd > 0 else 8)) / 16.0, f_
    for pid, pat in pats.items():
        b_, f_, k_ = band_pattern(x, pat)
        img[pid, :, 0], img[pid, :, 1], img[pid, :, 2] = b_ / 6.0, k_ / 16.0, f_
    return new_image("LW_tail_bands", LUT_W, LUT_H, img)


def white_noise(nt, inp, dims="1D"):
    nd = nt.node("ShaderNodeTexWhiteNoise", noise_dimensions=dims)
    nt.link(inp, nd.inputs["W" if dims == "1D" else "Vector"])
    return nd.outputs["Value"]


def tail_fur_material(marks, lut):
    """Painted tail fur. Where the tail is a sculpted fur mass (lut = 1) the locks are drawn per pixel from the
    continuous band coordinate bq: the band's colour, its place across the lock (lv) from the lookup row
    pid; along the flow (sflow) each band breaks into locks with a darker root and a lighter tip, each lock
    its own tone (white noise per band and lock); on the loose lock tips (lut = 0) the same comes from their
    vertices. Fine strands along each lock (colour and bump), dark crevices between the locks; the plume's
    starry underfur indigo with star specks; the constellations' glowing lines; glow streaks on a few
    locks."""
    mat, tree, bsdf = kit.principled("M_tail_fur")
    nt = NT(tree)
    use = nt.attr("lut")
    bq, pid, sfl = nt.attr("bq"), nt.attr("pid"), nt.attr("sflow")
    x = nt.math("FRACT", bq)
    v = nt.math("DIVIDE", nt.math("ADD", pid, 0.5), float(LUT_H))
    L = nt.rgb_sep(nt.image(lut, nt.combine(x, v), interp="Closest").outputs["Color"])
    serial = nt.math("ADD", nt.math("MULTIPLY", nt.math("FLOOR", bq), 16.0), nt.math("MULTIPLY", L[1], 16.0))
    su = nt.math("ADD", sfl, white_noise(nt, nt.math("ADD", serial, 0.37)))
    li = nt.math("FLOOR", su)
    lu_l = nt.math("FRACT", su)
    ljit_l = nt.math("SUBTRACT", nt.math("MULTIPLY", white_noise(nt, nt.combine(serial, li), "2D"), 2.0), 1.0)
    glow_l = nt.math("LESS_THAN", white_noise(nt, nt.combine(nt.math("ADD", serial, 0.5), nt.math("ADD", li, 7.5)), "2D"),
                     nt.attr("gshare"))
    band = nt.mixf(use, nt.attr("band"), L[0])
    lu = nt.mixf(use, nt.attr("lu"), lu_l)
    lv = nt.mixf(use, nt.attr("lv"), L[2])
    ljit = nt.mixf(use, nt.attr("ljit"), ljit_l)
    lglow = nt.mixf(use, nt.attr("lglow"), glow_l)
    starry, curlc = nt.attr("starry"), nt.attr("curl_centre")
    base = nt.ramp(nt.math("ADD", band, 0.04), [(0.0, "#e2ddd0"), (BAND(1), "#d0cbbf"), (BAND(2), "#9ec4d8"), (BAND(3), "#80a3c0"),
                          (BAND(4), "#6a82a6"), (BAND(5), "#4f6491"), (1.0, "#3c4b7a")], interp="CONSTANT")
    jit = nt.math("ADD", nt.math("MULTIPLY", ljit, 0.05), 1.0)
    base = nt.mix(1.0, base, nt.combine(jit, jit, jit), "MULTIPLY")
    # root a little darker, tip a little lighter (each lock)
    rootf = nt.maprange(lu, 0.0, 0.2, 0.16, 0.0)
    base = nt.mix(rootf, base, lin("#3f4e80"))
    tipf = nt.maprange(lu, 0.75, 1.0, 0.0, 0.16)
    base = nt.mix(tipf, base, lin("#f2f5f6"))
    # fine strands along the lock
    strands = nt.noise(nt.combine(nt.math("MULTIPLY", lv, 46.0), nt.math("MULTIPLY", lu, 2.2), nt.math("MULTIPLY", ljit, 9.0)), 1.0, 4, 0.6)
    sv = nt.ramp(strands, [(0.3, (0.88, 0.90, 0.93, 1)), (0.5, (1, 1, 1, 1)), (0.7, (1.07, 1.06, 1.04, 1))])
    base = nt.mix(1.0, base, sv, "MULTIPLY")
    # starry underfur (the plume's inner faces): indigo with star specks
    zone_col = nt.mix(nt.maprange(nt.noise(nt.coords("Object"), 9.0, 3, 0.5), 0.35, 0.7), lin("#3f5088"), lin("#4a5f98"))
    base = nt.mix(nt.math("MULTIPLY", starry, 0.92), base, zone_col)
    vor = nt.node("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 190.0
    nt.link(nt.coords("Object"), vor.inputs["Vector"])
    speck = nt.math("MULTIPLY", nt.maprange(vor.outputs["Distance"], 0.07, 0.025), starry)
    # constellation lines from the side / back projections
    ncomp = nt.sep(nt.coords("Normal"))
    mk_s = nt.rgb_sep(nt.image(marks, nt.combine(nt.attr("tys"), nt.attr("pzs"))).outputs["Color"])
    mk_b = nt.rgb_sep(nt.image(marks, nt.combine(nt.attr("pxf"), nt.attr("pzs"))).outputs["Color"])
    line_s = nt.math("MULTIPLY", nt.math("MULTIPLY", mk_s[0], nt.maprange(ncomp[0], 0.1, 0.4)), nt.maprange(starry, 0.2, 0.5))
    line_b = nt.math("MULTIPLY", nt.math("MULTIPLY", mk_b[1], nt.maprange(ncomp[1], 0.1, 0.4)), curlc)
    line = nt.math("MAXIMUM", line_s, line_b)
    # a thin glowing streak along the edge of a few locks, away from root and tip
    top = nt.maprange(nt.math("MINIMUM", lv, nt.math("SUBTRACT", 1.0, lv)), 0.05, 0.0)
    streak = nt.math("MULTIPLY", nt.math("MULTIPLY", top, lglow), nt.math("MULTIPLY", nt.maprange(lu, 0.08, 0.25), nt.maprange(lu, 0.7, 0.45)))
    glow = nt.math("MAXIMUM", nt.math("MAXIMUM", speck, line), nt.math("MULTIPLY", streak, 0.4))
    base = nt.mix(nt.math("MULTIPLY", glow, 0.9), base, lin("#d8f8ff"))
    # crevices between the locks
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.03
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.4, 0.0, 0.25), base, lin("#34426e"))
    emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3fb4ea"), (1.0, "#c4f6ff")])
    rough = nt.mixf(glow, nt.math("ADD", nt.math("MULTIPLY", strands, 0.14), 0.62), 0.4)
    set_bsdf(nt, bsdf, base=base, rough=rough, emis_col=emis, emis_str=2.2, normal=nt.bump(strands, 0.3, 0.0012))
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mat


CONST_SIDE = [(0.290, 0.515), (0.382, 0.539), (0.469, 0.459), (0.392, 0.342), (0.380, 0.401), (0.327, 0.438), (0.22, 0.535)]
CONST_SIDE_LINES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 6)]
# back view (x, z) on the centre curl: 6 stars, 4 lines (Review 1: 5 stars and 4 segments on the reference,
# plus the lone star at the right)
CONST_BACK = [(0.085, 0.217), (0.028, 0.172), (0.015, 0.110), (0.006, 0.104), (-0.111, 0.199), (0.104, 0.248)]
CONST_BACK_LINES = [(0, 1), (1, 2), (2, 3), (5, 0)]


def star_dome(name, p, nrm, r, mat):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
    nv = Vector(nrm).normalized()
    for vtx in bm.verts:
        d = vtx.co.dot(nv)
        vtx.co = vtx.co - nv * d * 0.45 + Vector(p) + nv * r * 0.25
    return kit.mesh_object(name, bm, mat)


def build_tails(star_mat):
    """The five tails as fur: the plume (centre tail), the two side tails and the two thin tails, the three
    curls on the ground, the loose lock tips and the constellation stars."""
    mat = tail_fur_material(tail_marks_image(), band_lut_image())
    rng = random.Random(4242)
    objs = []
    plume = build_plume(mat)
    plume.data.materials.append(mat)
    objs.append(plume)
    for key in ("centre", 1, -1):
        o = build_tail_curl(key, mat)
        o.data.materials.append(mat)
        objs.append(o)
        if key == "centre":
            centre_curl = o
    for i, t in enumerate(tail_tubes()):
        o = build_tail_tube(t, mat)
        o.data.materials.append(mat)
        objs.append(o)
    fur = Fur()
    for cps, r0, hint, band in TAIL_LOCKS:
        tail_lock(fur, cps, r0, hint, band, rng)
    o = fur.to_object("tail_locks", mat)
    co = verts_np(o)
    tail_projection_attrs(o, co)
    set_attr(o, "starry", np.zeros(len(co)))
    set_attr(o, "curl_centre", np.zeros(len(co)))
    objs.append(o)
    # constellation stars: the side constellation on the plume's +X face, the back one on the centre curl;
    # small glowing domes of uneven size
    tree = bvh_of(plume)
    sizes = [0.012, 0.011, 0.013, 0.012, 0.008, 0.009, 0.006]
    for i, (y, z) in enumerate(CONST_SIDE):
        hit = tree.ray_cast(Vector((1.0, y, z)), Vector((-1, 0, 0)))
        if hit[0] is not None:
            objs.append(star_dome(f"constellation_star_side_{i}", np.array(hit[0]), np.array(hit[1]), sizes[i] * rng.uniform(0.9, 1.1), star_mat))
    tree = bvh_of(centre_curl)
    sizes = [0.0072, 0.0058, 0.0052, 0.0040, 0.0060, 0.0048]
    for i, (x, z) in enumerate(CONST_BACK):
        hit = tree.ray_cast(Vector((x, 2.0, z)), Vector((0, -1, 0)))
        if hit[0] is not None:
            objs.append(star_dome(f"constellation_star_back_{i}", np.array(hit[0]), np.array(hit[1]), sizes[i] * rng.uniform(0.9, 1.1), star_mat))
    return objs


# ============================================================================ BODY ATTRIBUTES AND CREAM
def make_cream_field(obj, clay):
    """Cream zones of the fur, as a field for kit.mark. Review 1: the chest ruff is cream only where the
    surface faces forward (normal Y < -0.3), the belly only on the underside plus the tips of the
    fringe locks (jagged), the cheeks only inside |x| < 0.12 and not on their back faces."""
    # the surface normal from the smooth clay (the mesh's face normals are piecewise flat and would cut
    # the cream edge into steps along the faces)
    def field(p):
        x, y, z = p.x, p.y, p.z
        n = Vector(clay.normal(np.array([[x, y, z]]))[0])
        nz = 0.0012 * noise.noise(Vector((x * 55, y * 55, z * 55))) + 0.0008 * noise.noise(Vector((x * 160, y * 160, z * 160)))
        # head: below a line from the nose (z 0.683) under the eye (0.700) back to the cheek (0.655)
        zb = float(np.interp(y, [-0.65, -0.60, -0.55, -0.50, -0.45, -0.40, -0.36, -0.33], [0.656, 0.656, 0.662, 0.676, 0.674, 0.660, 0.645, 0.62]))
        # the cheek fur is cream up toward the outer eye corners (front view), the muzzle middle stays blue
        zb += 0.026 * float(smoothstep(abs(x), 0.06, 0.12))
        head = max(z - zb, y + 0.33, 0.55 - z, abs(x) - 0.15, n.y - 0.35)
        wb = 0.016 + 0.034 * min(1.0, max(0.0, (y + 0.62) / 0.14))
        bridge = max(abs(x) - wb, 0.672 - z, y + 0.44)   # blue nose bridge, narrowing to the nose
        head = max(head, -bridge)
        # throat and chest front: Y before the boundary, |X| within the bib, V point at z 0.25, facing forward
        yb = float(np.interp(z, [0.24, 0.33, 0.40, 0.50, 0.58, 0.66], [-0.46, -0.39, -0.37, -0.355, -0.34, -0.355]))
        wc = float(np.interp(z, [0.24, 0.27, 0.32, 0.38, 0.47, 0.55, 0.62, 0.66], [0.0, 0.04, 0.085, 0.115, 0.115, 0.095, 0.06, 0.08]))
        chest = max(y - yb, abs(x) - wc, 0.245 - z, z - 0.665, (n.y + 0.05) * 0.1)
        # belly: the underside, and the lower ends of the fringe locks (a jagged cream edge in the side view)
        ph = (y * 27.0 + 0.3 * noise.noise(Vector((x * 9, y * 9, 1.0)))) % 1.0
        jag = -0.016 * (1 - abs(2 * ph - 1)) ** 2 + 0.008 + 0.003 * noise.noise(Vector((x * 40, y * 40, 3.0)))
        under = max((n.z + 0.2) * 0.1, z - 0.42, 0.28 - z, y - 0.06, -0.33 - y, abs(x) - 0.085)
        sx = 1.0 if x >= 0 else -1.0
        fringe = max(z - (0.352 + jag), 0.30 - z, y - 0.02, -0.31 - y, abs(x) - 0.075)
        return min(head, chest, under, fringe) + nz
    return field


def close_holes(obj):
    """Fill the few small holes a remesh or a marking cut can leave, so the body stays closed."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.triangulate(bm, faces=res["faces"])
    bad = [e for e in bm.edges if not e.is_manifold and not e.is_boundary]
    if bad:
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def body_attributes(obj):
    co = verts_np(obj)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    set_attr(obj, "zh", z)
    face = smoothstep(-y, 0.36, 0.42) * smoothstep(z, 0.60, 0.66)
    set_attr(obj, "face", face)
    legs = smoothstep(0.36 - z, 0.0, 0.05)
    set_attr(obj, "legs", legs)
    set_attr(obj, "pys", (y + 0.72) / MARK_SPAN)
    set_attr(obj, "pzs", z / MARK_SPAN)
    set_attr(obj, "pxf", (x + 0.51) / MARK_SPAN)
    set_attr(obj, "nobridge", np.maximum(smoothstep(np.abs(x), 0.03, 0.05), smoothstep(y, -0.45, -0.42)))


# ============================================================================ BUILD
def build():
    marks, decal = mark_images()
    m_fur = fur_material("M_fur", marks, decal, cream=False)
    m_cream = fur_material("M_fur_cream", marks, decal, cream=True)
    m_ear_out, m_ear_in = ear_materials(ear_image())
    m_tuft = cream_tuft_material()
    m_feather = shoulder_fur_material()
    m_silver = silver_material()
    m_gem = gem_material()
    m_nose = dark_material("M_nose", "#23222f", 0.28)
    m_liner = dark_material("M_liner", "#1b2142", 0.45)
    m_star = star_material()

    body, clay = body_clay()
    surf, _ = clay.project(np.array([[0.0, -0.60, GEM_C[2]]]))
    GEM_C[1] = surf[0][1] - 0.011     # the gem's back apex sits on the chest ruff
    kit.quad_remesh(body, 26000)
    close_holes(body)
    crease_mouth(body, clay)
    body.data.shade_smooth()
    body.data.materials.append(m_fur)
    kit.mark(body, make_cream_field(body, clay), m_cream)
    close_holes(body)
    body_attributes(body)
    parts = [body]
    for key in LEGS:
        paw = build_paw(key, m_fur)
        body_attributes(paw)
        parts.append(paw)

    rng = random.Random(12)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        parts.append(build_ear(side, m_ear_out, m_ear_in, uoff))
        parts += ear_tufts(side, m_tuft, rng, m_ear_out)
        parts.append(build_eye(clay, side, eye_material(side)))
        parts += build_lid_lines(clay, side, m_liner)
    parts.append(build_nose(m_nose))
    parts += build_mouth(clay, m_liner)
    parts.append(build_gem(m_gem))
    parts += build_collar(clay, m_silver)
    parts += build_shoulder_fur(clay, m_feather)
    parts += build_tails(m_star)
    return parts


if __name__ == "__main__":
    kit.run(build, texture=4096)
