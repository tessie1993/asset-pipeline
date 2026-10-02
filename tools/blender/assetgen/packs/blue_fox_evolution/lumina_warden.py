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
EYE = {}   # side -> (centre on surface, normal)


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
    # eye sockets: shallow seats for the eyes
    for s in (1, -1):
        clay.sub(E((s * 0.064, -0.502, 0.718), (0.029, 0.015, 0.015), rot=(0, s * -16, s * 35)), blend=0.006)
    # --- fur locks (cones): cheek tufts, cheek/nape ruff, chest ruff spikes, elbow tufts, belly fringe
    rng = random.Random(7)
    for s in (1, -1):
        cheek = [((0.095, -0.43, 0.660), (0.185, -0.40, 0.628), 0.03),
                 ((0.095, -0.42, 0.645), (0.175, -0.39, 0.592), 0.028),
                 ((0.090, -0.43, 0.630), (0.150, -0.41, 0.565), 0.024),
                 ((0.075, -0.44, 0.625), (0.115, -0.44, 0.552), 0.02),
                 ((0.090, -0.40, 0.680), (0.170, -0.37, 0.672), 0.026)]
        for a, b, r in cheek:
            j = 1.1 + (rng.random() - 0.5) * 0.18 * s
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
    # mouth: a smile crease cut along a W under the nose that runs back along the jaw (Review 1)
    for s in (1, -1):
        clay.stroke(mouth_line(s), [0.0032, 0.0034, 0.0034, 0.0032, 0.003, 0.0028, 0.0024, 0.0018],
                    [0.0028, 0.003, 0.003, 0.003, 0.0028, 0.0024, 0.0018, 0.001], op="sub", blend=0.0015, n=40)
    obj = clay.to_object("Body", symmetric=False)
    return obj, clay


def mouth_line(s):
    return [(0.0, -0.614, 0.662), (s * 0.006, -0.612, 0.6555), (s * 0.016, -0.606, 0.655), (s * 0.026, -0.596, 0.659),
            (s * 0.036, -0.580, 0.662), (s * 0.044, -0.555, 0.661), (s * 0.050, -0.525, 0.664), (s * 0.056, -0.500, 0.671)]


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
        st.append((bez2((s * 0.04, 0.700), (s * 0.06, 0.696), (s * 0.08, 0.698), (s * 0.098, 0.708)), [0.0012, 0.0045, 0.0035, 0.001]))
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
    # mouth: W-shaped smile line under the nose
    for s in (1, -1):
        poly_paint(decal[..., 2], Xf, Zf, bez2((0.0, 0.664), (s * 0.008, 0.657), (s * 0.02, 0.655), (s * 0.034, 0.664)),
                   [0.0035, 0.003, 0.003, 0.0015], 1.5 * px)
    poly_paint(decal[..., 2], Xf, Zf, [(0.0, 0.676), (0.0, 0.664)], [0.003, 0.003], 1.5 * px)
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


def feather_material():
    """Iridescent shoulder locks: blue base -> mint/cyan streaks -> lavender tips and edges."""
    mat, tree, bsdf = kit.principled("M_feather")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    u, v = uvs[0], uvs[1]
    lu = nt.math("FRACT", u)  # along the blade (each blade has its own u range of width 1)
    streak = nt.noise(nt.scale_vec(uv, 3, 22, 1), 1.0, 3, 0.5)
    base = nt.ramp(lu, [(0.0, "#86b0cc"), (0.18, "#93cbe0"), (0.36, "#9eeedd"), (0.52, "#a6c6f2"), (0.68, "#b3a0ec"), (1.0, "#c6b0f6")])
    mint = nt.maprange(streak, 0.5, 0.65)
    base = nt.mix(nt.math("MULTIPLY", mint, 0.6), base, lin("#9ff2d6"))
    edge = nt.maprange(nt.math("ABSOLUTE", nt.math("SUBTRACT", nt.math("FRACT", nt.math("MULTIPLY", v, 2.0)), 0.5)), 0.32, 0.5)
    base = nt.mix(nt.math("MULTIPLY", edge, 0.5), base, lin("#b9a9ec"))
    vor = nt.node("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 140.0
    nt.link(nt.coords("Object"), vor.inputs["Vector"])
    speck = nt.maprange(vor.outputs["Distance"], 0.06, 0.02)
    base = nt.mix(nt.math("MULTIPLY", speck, 0.8), base, lin("#f2fbff"))
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


def eye_material():
    """Anime eye from the eye's own UVs (u along the eye, v up): blue iris dark at the top, light
    below, navy pupil and rim, white catch light."""
    mat, tree, bsdf = kit.principled("M_eye")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    x = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[0], 0.5), 2 * 0.031)
    y = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[1], 0.5), 2 * 0.0155)
    dx = nt.math("SUBTRACT", x, 0.002)
    r = nt.math("DIVIDE", nt.math("SQRT", nt.math("ADD", nt.math("POWER", dx, 2.0), nt.math("POWER", y, 2.0))), 0.0158)
    vert = nt.math("ADD", nt.math("DIVIDE", y, 0.030), 0.5)
    iris = nt.ramp(vert, [(0.0, "#bfe8ff"), (0.3, "#86c0f0"), (0.62, "#4f80cc"), (1.0, "#2b4590")])
    col = nt.mix(nt.maprange(r, 0.33, 0.27), iris, lin("#141c45"))            # pupil
    col = nt.mix(nt.maprange(r, 0.86, 0.97), col, lin("#1e2d62"))             # dark rim
    col = nt.mix(nt.maprange(r, 1.02, 1.10), col, lin("#9fbfdc"))             # pale-blue corners (no white sclera)
    hl = nt.math("SQRT", nt.math("ADD", nt.math("POWER", nt.math("ADD", x, 0.0045), 2.0),
                                 nt.math("POWER", nt.math("SUBTRACT", y, 0.0042), 2.0)))
    hlm = nt.maprange(hl, 0.0032, 0.0021)
    col = nt.mix(hlm, col, lin("#f7fdff"))
    sparkle = nt.noise(uv, 30.0, 2, 0.5)
    col = nt.mix(nt.math("MULTIPLY", nt.maprange(sparkle, 0.55, 0.7), 0.25), col, lin("#a6e4ff"))
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
    mat, tree, bsdf = kit.principled("M_star")
    nt = NT(tree)
    nz = nt.noise(nt.coords("Object"), 200.0, 2, 0.5)
    col = nt.ramp(nz, [(0.3, "#d8f6ff"), (0.7, "#ffffff")])
    set_bsdf(nt, bsdf, base=col, rough=0.3, emis_col=nt.ramp(nz, [(0.3, "#9fe8ff"), (0.7, "#e8fbff")]), emis_str=6.0)
    return mat


def tail_material(col_img, emi_img):
    mat, tree, bsdf = kit.principled("M_tail")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    col = nt.image(col_img, uv).outputs["Color"]
    emi = nt.rgb_sep(nt.image(emi_img, uv).outputs["Color"])
    strk = nt.noise(nt.scale_vec(uv, 220, 9, 1), 1.0, 4, 0.6)
    sv = nt.ramp(strk, [(0.3, (0.90, 0.91, 0.94, 1)), (0.5, (1, 1, 1, 1)), (0.7, (1.07, 1.06, 1.04, 1))])
    col = nt.mix(1.0, col, sv, "MULTIPLY")
    glow = emi[0]
    col = nt.mix(nt.math("MULTIPLY", glow, 0.9), col, lin("#d6f8ff"))
    emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3fb4ea"), (1.0, "#c4f6ff")])
    rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.12), 0.74)
    set_bsdf(nt, bsdf, base=col, rough=rough, emis_col=emis, emis_str=2.0, normal=nt.bump(strk, 0.3, 0.0015))
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
        sc = (0.004 * side + 0.004, 0.165 + 0.006 * side)
        sp = spiral(sc, 0.026 + 0.003 * side, 1.15, -0.4 * math.pi, 1, 1.25, 0.0, 60, 0.85)
        tail = bez2((0.0, 0.07), (0.018, 0.10), (0.03, 0.13), (sp[0][0], sp[0][1]))
        stroke = tail[:-1] + sp
        # Review 1: a bold glowing curl (stroke 6-10 mm) with a soft glow around it
        widths = np.concatenate([np.linspace(0.002, 0.0095, len(tail) - 1), np.linspace(0.0095, 0.0035, len(sp))])
        poly_paint(sub[..., 0], X, Y, stroke, widths, 0.0009, halo=0.42, halo_w=0.007)
        poly_paint(sub[..., 0], X, Y, bez2((-0.02, 0.10), (-0.012, 0.14), (-0.01, 0.17), (-0.016, 0.20)),
                   [0.0015, 0.005, 0.004, 0.0015], 0.0008, halo=0.35, halo_w=0.004)
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
        for _ in range(420):
            t = rng.random() ** 0.7
            u = rng.uniform(-0.85, 0.85)
            hwv = ear_hw(u, t)
            cx, cy = u * hwv, t * L
            r = rng.choice([0.0005, 0.0006, 0.0008, 0.001, 0.0013, 0.0018]) * (1.0 if rng.random() > 0.08 else 1.8)
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
        t0 = 0.05 + 0.025 * abs(k - 2) + rng.uniform(-0.008, 0.008)
        x0 = -0.034 + 0.016 * k + rng.uniform(-0.003, 0.003)
        root = B + a * L * t0 + w * x0 - f * 0.016
        ang = math.radians(-30 + 14 * k + rng.uniform(-5, 5))
        d = a * math.cos(ang) + w * math.sin(ang)
        ln = 0.065 + 0.03 * math.sin((k + 0.5) * 0.62) + rng.uniform(0, 0.012)
        p1 = root + d * ln * 0.35 + f * 0.010
        p2 = root + d * ln * 0.72 + f * 0.016
        p3 = root + d * ln + f * 0.014 - w * 0.006 * (k - 2)
        P = np.array(S.bezier(root, p1, p2, p3, 16))
        tt = np.linspace(0, 1, 16)
        wmax = 0.5 * (0.025 + 0.010 * rng.random())
        width = wmax * (1 - tt) ** 0.75 * (0.75 + 0.25 * np.sin(np.clip(tt * 3, 0, 1) * math.pi * 0.5)) + 1e-5
        width[-1] = 0
        th = 0.003 * (1 - tt) + 1e-5
        th[-1] = 0
        o, _ = sweep(f"EarTuft_{side}_{k}", P, th, width, 8, mat, hint=np.tile(f, (16, 1)), uv_rect=(0, 0, 1, 1))
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
    p, n = clay.project(np.array([[side * 0.064, -0.502, 0.718]]))
    p, n = p[0], n[0]
    n = n + np.array([side * 0.3, 0.0, 0.0])   # turned a little outward: the side view sees the almond
    n /= np.linalg.norm(n)
    up = np.array([0.0, 0.0, 1.0])
    e_up = up - (up @ n) * n
    e_up /= np.linalg.norm(e_up)
    e_long = np.cross(e_up, n)
    if e_long[0] * side < 0:
        e_long = -e_long
    sl = math.radians(16)
    e_l = e_long * math.cos(sl) + e_up * math.sin(sl)
    e_u = -e_long * math.sin(sl) + e_up * math.cos(sl)
    return p, n, e_l, e_u


def build_eye(clay, side, mat):
    p, n, el, eu = eye_frame(clay, side)
    ra, rb, rc = 0.031, 0.0155, 0.009
    c = p - n * 0.0015
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1.0)
    uvl = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            lx, ly, lz = loop.vert.co
            loop[uvl].uv = (0.5 + 0.5 * lx, 0.5 + 0.5 * lz)
    for v in bm.verts:
        lx, ly, lz = v.co
        v.co = Vector(c + el * (ra * lx) + n * (rc * ly) + eu * (rb * lz))
    bm.normal_update()
    obj = kit.mesh_object(f"Eye_{side}", bm, mat)
    obj["keep_uv"] = True
    return obj


def build_liner(clay, side, mat):
    p, n, el, eu = eye_frame(clay, side)
    ra, rb = 0.031, 0.0155
    c = p - n * 0.0015
    pts = []
    for th in np.linspace(math.pi + 0.35, 0.05, 26):
        pts.append(c + el * ra * 1.02 * math.cos(th) + eu * rb * 1.12 * math.sin(th) + n * 0.0035)
    pts.append(c + el * ra * 1.22 + eu * rb * 0.55 + n * 0.002)
    pts.append(c + el * ra * 1.42 + eu * rb * 0.95 + n * 0.0)
    P = np.array(pts)
    tt = np.linspace(0, 1, len(P))
    r = 0.0013 + 0.0019 * np.sin(np.clip(tt, 0, 1) * math.pi) ** 0.6
    r[-1] = 0.0
    o, _ = sweep(f"Liner_{side}", P, r * 0.7, r, 8, mat, hint=np.tile(n, (len(P), 1)))
    return o


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
    paths.append(("ring", snap(ring, 0.0062), 0.0062, True))
    for s in (1, -1):
        j = lambda: rng.uniform(-0.004, 0.004)
        # upper arched band: from the side of the neck (z 0.57) down in a slight arch to the gem top
        arc1 = bez2((s * 0.128, -0.43, 0.572), (s * 0.10, -0.49, 0.565 + j()), (s * 0.045, -0.535, 0.505), (s * 0.006, -0.552, 0.470), 40)
        paths.append(("arc", snap(arc1, 0.0078), np.linspace(0.0082, 0.0062, 40), False))
        # lower arched band: from the chest side (z 0.53) bowing down to the gem's side corner (z 0.41)
        arc2 = bez2((s * 0.145, -0.42, 0.53), (s * 0.13, -0.48, 0.47 + j()), (s * 0.075, -0.53, 0.415), (s * 0.036, -0.547, 0.412), 40)
        paths.append(("arc", snap(arc2, 0.0072), np.linspace(0.0076, 0.0056, 40), False))
        # scroll curl below the lower arc (C/S curl), 1.4 turns
        sc = spiral((0.0, 0.0), 0.026 + j(), 1.35 + 0.1 * s, math.pi * 0.2, -s, 1.0, 0.0, 64, 0.8)
        pts = [(s * 0.074 + x, -0.53, 0.388 + y) for x, y in sc]
        pts = [(s * 0.042, -0.545, 0.398)] + pts
        paths.append(("curl", snap(pts, 0.0058), np.linspace(0.0068, 0.0036, len(pts)), False))
        # second C curl above the lower arc, beside the gem
        sc2 = spiral((0.0, 0.0), 0.021, 1.05, math.pi * 1.1, s, 1.0, 0.0, 48, 0.8)
        pts2 = [(s * 0.088 + x, -0.515, 0.462 + y) for x, y in sc2]
        paths.append(("curl", snap(pts2, 0.0052), np.linspace(0.006, 0.0032, len(pts2)), False))
        # antler tendrils: S-curved, rising up and out from the arcs, each ending in a half-turn curl
        tendrils = [  # root on the arcs, S control points, tip; curl direction (+1 out, -1 in)
            (((0.125, -0.445, 0.552), (0.15, -0.44, 0.565), (0.14, -0.44, 0.60), (0.168, -0.43, 0.618)), 1),
            (((0.14, -0.435, 0.51), (0.175, -0.425, 0.52), (0.165, -0.425, 0.565), (0.19, -0.415, 0.585)), 1),
            (((0.098, -0.485, 0.552), (0.112, -0.48, 0.585), (0.098, -0.475, 0.605), (0.118, -0.465, 0.628)), -1),
            (((0.108, -0.488, 0.462), (0.135, -0.475, 0.468), (0.13, -0.47, 0.50), (0.155, -0.455, 0.52)), 1),
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
            rr = np.linspace(0.0082 - 0.0008 * k, 0.0036, len(P))
            rr[-4:] *= np.linspace(1.0, 0.4, 4)
            paths.append(("tendril", P, rr, False))
            # a small leaf bud on the stem (reference: leaf-tipped branches)
            mid = P[22]
            dirb = P[24] - P[20]
            dirb /= np.linalg.norm(dirb)
            out = np.array([s * cd * 0.6, -0.2, 0.75])
            out /= np.linalg.norm(out)
            leaf = np.array([mid, mid + out * 0.009 + dirb * 0.004, mid + out * 0.018 + dirb * 0.006])
            paths.append(("leaf", leaf, np.array([0.003, 0.0045, 0.0]), False))
    # gem bezel: closed rhombus loop around the gem girdle
    hh, hw = 0.056 * 1.12, 0.031 * 1.18
    cy, cz = GEM_C[1] + 0.002, GEM_C[2]
    corners = [(0, cy, cz + hh), (hw, cy, cz), (0, cy, cz - hh), (-hw, cy, cz)]
    loop = []
    for i in range(4):
        a, b = np.array(corners[i]), np.array(corners[(i + 1) % 4])
        for f in np.linspace(0, 1, 16, endpoint=False):
            loop.append(a + (b - a) * f)
    paths.append(("bezel", np.array(loop), 0.0058, True))
    return paths


def build_collar(clay, mat):
    objs = []
    for k, (kind, P, r, closed) in enumerate(collar_paths(clay)):
        P = np.asarray(P, float)
        rr = np.broadcast_to(np.asarray(r, float), (len(P),)).copy()
        if not closed and kind in ("curl", "tendril", "leaf"):
            rr[-1] = 0.0
        hint = (0.0, -1.0, 0.0) if kind != "ring" else (0.0, 0.0, 1.0)
        sides = {"tendril": 10, "leaf": 6, "ring": 12}.get(kind, 12)
        o, _ = sweep(f"Collar_{kind}_{k}", P, rr, rr * (0.8 if kind in ("bezel", "leaf") else 1.0), sides,
                     mat, hint=hint, closed=closed)
        objs.append(o)
    return objs


# ============================================================================ SHOULDER FEATHERS
def build_feathers(clay, mat):
    """Shoulder locks (Review 1): 7 broad locks per side (50-80 mm wide) whose root and first third lie on
    the shoulder (projected onto the body, under 5 mm off it) and flow back over the shoulder, lifting
    away from the body only toward the tip, which curls up. Lowest lock runs back along the body, the
    highest rises up-back to z ~0.72 (side view). Every lock its own length, width, lift and curl."""
    objs = []
    rng = random.Random(91)
    for side in (1, -1):
        n = 7
        for k in range(n):
            f = k / (n - 1)
            root_s = np.array([side * 0.10, -0.385 + 0.045 * f + rng.uniform(-0.008, 0.008),
                               0.44 + 0.12 * f + rng.uniform(-0.008, 0.008)])
            elev = math.radians(-14 + 60 * f + rng.uniform(-5, 5))
            d = np.array([0.0, math.cos(elev), math.sin(elev)])
            L = 0.17 + 0.09 * math.sin(math.pi * (0.25 + 0.6 * f)) + rng.uniform(-0.02, 0.02)
            ns = 30
            tt = np.linspace(0, 1, ns)
            # centre line: along d, bending upward toward the tip
            up = np.array([0.0, 0.2, 1.0])
            up /= np.linalg.norm(up)
            curl = (0.10 + 0.08 * rng.random()) * L
            Q = root_s[None, :] + tt[:, None] * d[None, :] * L + (tt ** 2.6)[:, None] * up[None, :] * curl
            # first third on the surface, then lifting off the body
            Sp, Nr = clay.project(Q)
            out = np.array([side, 0.0, 0.0])
            lift = 0.004 + 0.003 * (k % 2) + smoothstep(tt, 0.3, 1.0) * (0.022 + 0.03 * f + 0.012 * rng.random())
            nrm = Nr * (1 - smoothstep(tt, 0.3, 0.8))[:, None] + out[None, :] * smoothstep(tt, 0.3, 0.8)[:, None]
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
            P = Sp + nrm * lift[:, None]
            # where the lock rises above the back it stays where it is drawn (not pulled down onto the body)
            free = smoothstep(clay.sample(Q) - lift, 0.0, 0.012)[:, None]
            P = P * (1 - free) + Q * free
            # a smooth centre line (projection noise off)
            for _ in range(2):
                P[1:-1] = (P[:-2] + 2 * P[1:-1] + P[2:]) / 4
            w0 = 0.5 * (0.05 + 0.03 * rng.random())
            width = w0 * np.sin(np.clip(tt * 0.92 + 0.14, 0, 1) * math.pi) ** (0.5 + 0.25 * rng.random())
            width[-1] = 0.0
            th = 0.0042 * (1 - tt * 0.7)
            th[-1] = 0.0
            tw = math.radians(rng.uniform(-14, 14))
            hint = np.array([nrm[i] * math.cos(tw * t) + np.cross(d, nrm[i]) * math.sin(tw * t) for i, t in enumerate(tt)])
            o, _ = sweep(f"Feather_{side}_{k}", P, th, width, 10, mat, hint=hint,
                         uv_rect=(float(k), 0.0, float(k) + 0.999, 1.0))
            o["keep_uv"] = True
            objs.append(o)
    return objs


# ============================================================================ TAILS
TAIL_STRIPS = []   # (name, v0, v1)


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


def tail_paths():
    """Centre lines (N,3) and radii (ru = in the curl plane normal, rv = across) of the tails."""
    tails = []
    # A: centre tail with the constellation: a broad ribbon rising from the rump, arcing up and back
    # (top z 0.73), down the back (Y 0.62) to the ground, then curling forward and up into the coil centre
    # control points (Y, Z) read off the side view; Catmull-Rom through them
    cps = [(0.10, 0.535), (0.20, 0.575), (0.30, 0.585), (0.39, 0.555), (0.425, 0.48), (0.432, 0.395), (0.418, 0.30),
           (0.385, 0.20), (0.31, 0.135), (0.22, 0.115), (0.17, 0.15), (0.19, 0.215), (0.25, 0.245), (0.31, 0.235), (0.33, 0.20)]
    P = catmull(np.array(cps), 9)
    xs = np.linspace(0.034, 0.026, len(P))   # a little toward +X: the lateral tails run down behind it
    P = np.stack([xs, P[:, 0], P[:, 1]], 1)
    tt = np.linspace(0, 1, len(P))
    rv = np.interp(tt, [0, 0.05, 0.1, 0.16, 0.25, 0.45, 0.55, 0.63, 0.7, 0.8, 0.9, 1.0],
                   [0.05, 0.075, 0.10, 0.135, 0.175, 0.17, 0.14, 0.11, 0.08, 0.065, 0.05, 0.0])   # in plane
    ru = np.interp(tt, [0, 0.05, 0.2, 0.36, 0.46, 0.58, 0.7, 0.8, 0.9, 1.0], [0.045, 0.05, 0.05, 0.055, 0.09, 0.15, 0.155, 0.12, 0.06, 0.0])    # across (X)
    tails.append(("TailA", P, ru, rv, 40, 0.0))
    # B: lateral tails, out and down to coiled ground lobes at x +-0.22 (back view lobes r 0.13)
    for side in (1, -1):
        cx, cy, cz = side * 0.195, 0.37 + 0.015 * side, 0.145
        # root runs inside tail A's ribbon (hidden in the side view, as drawn) and leaves it below the starry zone
        xo = 0.0 if side > 0 else -0.03
        root = catmull(np.array([(0.10, 0.535), (0.20, 0.565), (0.30, 0.572), (0.38, 0.54), (0.412, 0.46), (0.418, 0.37), (0.40, 0.30)]), 3)
        pts = [(xo + side * 0.004 * i / len(root), yy, zz) for i, (yy, zz) in enumerate(root)] + [(side * 0.08, 0.395, 0.255)]
        ph = np.linspace(0.0, 2 * math.pi * 1.55, 90)
        rr0 = 0.077
        for phi in ph:
            r = rr0 * (1 - phi / (2 * math.pi * 1.75)) ** 1.1
            x = cx + r * math.sin(phi) * side
            z = cz + r * math.cos(phi)
            y = cy + 0.03 * math.sin(phi * 0.5)
            pts.append((x, y, z))
        P = np.array(pts)
        tt = np.linspace(0, 1, len(P))
        prof = np.interp(tt, [0, 0.12, 0.17, 0.3, 0.45, 0.62, 0.8, 0.92, 0.98, 1.0], [0.032, 0.036, 0.06, 0.072, 0.074, 0.066, 0.052, 0.04, 0.03, 0.0])
        tails.append((f"TailB{'L' if side > 0 else 'R'}", P, prof * 1.25, prof, 28, side))
    # C: wisp tails sideways, tips curling up (back view x +-0.36 at z 0.30)
    for side in (1, -1):
        P = np.array(bez2((side * 0.01, 0.12, 0.48), (side * 0.03, 0.30, 0.38), (side * 0.20, 0.33, 0.28),
                          (side * 0.305, 0.25 + 0.02 * side, 0.26), 40))
        tip = np.array(bez2(tuple(P[-1]), (side * 0.325, 0.245, 0.26), (side * 0.333, 0.24, 0.285), (side * (0.322 + 0.004 * side), 0.235, 0.315), 14))
        P = np.concatenate([P, tip[1:]])
        tt = np.linspace(0, 1, len(P))
        prof = np.interp(tt, [0, 0.1, 0.4, 0.7, 0.9, 1.0], [0.035, 0.05, 0.045, 0.03, 0.012, 0.0])
        tails.append((f"TailC{'L' if side > 0 else 'R'}", P, prof, prof * 0.85, 16, side))
    # D: curl tips: two on top of the arc, one hanging into the gap, the bottom flick, the front hook
    curls = [
        ("CurlTop1", [(0.015, 0.18, 0.62), (0.015, 0.17, 0.68), (0.012, 0.13, 0.71), (0.01, 0.11, 0.695)], 0.022),
        ("CurlTop2", [(0.012, 0.50, 0.58), (0.012, 0.56, 0.64), (0.01, 0.60, 0.69), (0.012, 0.585, 0.725)], 0.024),
        ("CurlHang", [(0.03, 0.31, 0.44), (0.035, 0.265, 0.41), (0.035, 0.24, 0.36), (0.04, 0.262, 0.325)], 0.02),
        ("CurlFlick", [(0.06, 0.42, 0.10), (0.07, 0.52, 0.03), (0.07, 0.60, 0.045), (0.065, 0.61, 0.10)], 0.05),
        ("CurlHook", [(0.20, 0.27, 0.22), (0.215, 0.27, 0.30), (0.225, 0.275, 0.37), (0.195, 0.28, 0.395)], 0.03),
    ]
    for name, cps, r0 in curls:
        P = np.array(S.bezier(*cps, 24))
        tt = np.linspace(0, 1, 24)
        prof = r0 * np.sin(np.clip(tt * 0.9 + 0.12, 0, 1) * math.pi * 0.5 + 0.2) * (1 - tt ** 1.5)
        prof[-1] = 0.0
        tails.append((name, P, prof, prof, 12, 0))
    return tails


def bilinear_grid(rings, nrm, s, U, A):
    """World position and normal on a swept tube for texels at path fraction U and angle fraction A."""
    N, M = rings.shape[:2]
    fi = np.interp(U, s, np.arange(N))
    i0 = np.clip(np.floor(fi).astype(int), 0, N - 2)
    ti = (fi - i0)[..., None]
    fj = A * M
    j0 = np.floor(fj).astype(int) % M
    j1 = (j0 + 1) % M
    tj = (fj - np.floor(fj))[..., None]
    def g(arr):
        a = arr[i0, j0] * (1 - tj) + arr[i0, j1] * tj
        b = arr[i0 + 1, j0] * (1 - tj) + arr[i0 + 1, j1] * tj
        return a * (1 - ti) + b * ti
    p = g(rings)
    n = g(nrm)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    return p, n


CONST_SIDE = [(0.290, 0.515), (0.382, 0.539), (0.469, 0.459), (0.392, 0.342), (0.380, 0.401), (0.327, 0.438), (0.22, 0.535)]
CONST_SIDE_LINES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 6)]
CONST_BACK = [(0.087, 0.213), (0.028, 0.169), (0.015, 0.105), (0.006, 0.098), (-0.107, 0.196)]
CONST_BACK_LINES = [(0, 1), (1, 2), (2, 3)]


def tail_images(tails_built, star_pts, star_lines):
    """Tail colour (bands cream / blue / indigo along each tail, dark starry zones) and emission
    (constellation lines, glowing streaks), painted in each tail's UV strip."""
    W = 2048
    rows = sum(h for *_, h in tails_built)
    col = np.zeros((rows, W, 3), np.float32)
    emi = np.zeros((rows, W, 3), np.float32)
    cream, cream_sh = np.array(hexrgb("#e2dacb")), np.array(hexrgb("#c3c0bb"))
    lblue, mblue, dblue, indigo = (np.array(hexrgb(h)) for h in ("#a2c6db", "#86aecb", "#6585ae", "#45588a"))
    row0 = 0
    seg_a = np.array([star_pts[a] for a, b in star_lines]) if star_lines else np.zeros((0, 3))
    seg_b = np.array([star_pts[b] for a, b in star_lines]) if star_lines else np.zeros((0, 3))
    for k, (name, grid, h) in enumerate(tails_built):
        rings, nrm, s = grid
        rng = np.random.default_rng(300 + k)
        U = (np.arange(W) + 0.5) / W
        A = (np.arange(h) + 0.5) / h
        Ug, Ag = np.meshgrid(U, A)
        pos, nn = bilinear_grid(rings, nrm, s, Ug, Ag)
        # bands along the tail: 3 per circumference, drifting and of uneven width
        nb = 3 if not name.startswith("Curl") else 2
        ph = rng.uniform(0, 1)
        drift = 0.10 * np.sin(2 * math.pi * (Ug * 1.3 + ph)) + 0.05 * np.sin(2 * math.pi * (Ug * 3.7 + ph * 2))
        b = (Ag * nb + drift * nb + ph) % 1.0
        wob = 0.04 * np.sin(Ug * 23 + Ag * 7) + 0.03 * np.sin(Ug * 41 + 1.3)
        # band layout per unit: cream 0-0.30, light blue 0.30-0.42, mid 0.42-0.62, dark 0.62-0.80, mid 0.80-1.0
        e1, e2, e3, e4 = 0.40 + wob, 0.51 + wob * 0.5, 0.70 + wob, 0.83 + wob * 0.6
        if name == "TailA":   # root and arc top: blue with thin cream streaks
            e1 = e1 - 0.22 * np.clip((0.40 - Ug) / 0.15, 0, 1)
        soft = 0.025
        c = np.where((b < e1)[..., None], cream, mblue)
        c = np.where(((b >= e1) & (b < e2))[..., None], lblue, c)
        c = np.where(((b >= e3) & (b < e4))[..., None], dblue, c)
        # soften band edges
        for e, ca, cb in ((e1, cream, lblue), (e2, lblue, mblue), (e3, mblue, dblue), (e4, dblue, mblue)):
            m = np.clip(1 - np.abs(b - e) / soft, 0, 1)[..., None] * 0.5
            c = c * (1 - m) + (ca * 0.5 + cb * 0.5) * m
        # shadowed cream toward the tail underside and darker tips
        c = c * (0.92 + 0.08 * np.clip(nn[..., 2] + 0.5, 0, 1))[..., None]
        tipdark = np.clip((Ug - 0.85) / 0.15, 0, 1)[..., None] * 0.15
        c = c * (1 - tipdark) + dblue * tipdark
        glow = np.zeros(Ug.shape, np.float32)
        if name == "TailA":
            # dark indigo starry zone: the coil's inner turns on the +X side and the centre of the coil
            dyz = np.sqrt(((pos[..., 1] - 0.37) / 0.165) ** 2 + ((pos[..., 2] - 0.42) / 0.185) ** 2)
            zone = np.clip((1.15 - dyz) / 0.25, 0, 1) * np.clip((nn[..., 0] + 0.1) / 0.4, 0, 1)
            band_keep = np.clip(1 - np.abs(b - 0.15) / 0.12, 0, 1) * 0.35   # thin cream edges remain inside the zone
            z3 = (zone * (1 - band_keep))[..., None]
            c = c * (1 - z3) + indigo * (0.9 + 0.2 * rng.random(Ug.shape))[..., None] * z3
            # star specks in the zone
            nst = 900
            iu = rng.integers(0, W, nst)
            ia = rng.integers(0, h, nst)
            for x, y in zip(iu, ia):
                if zone[y, x] < 0.3:
                    continue
                rad = rng.choice([0.6, 0.8, 1.0, 1.3, 1.8])
                br = rng.uniform(0.5, 1.0)
                y0, y1, x0, x1 = max(0, y - 3), min(h, y + 4), max(0, x - 3), min(W, x + 4)
                yy, xx = np.mgrid[y0:y1, x0:x1]
                d = np.sqrt((yy - y) ** 2 + ((xx - x) * 0.6) ** 2)
                v = np.clip(rad - d + 0.5, 0, 1) * br
                c[y0:y1, x0:x1] = np.maximum(c[y0:y1, x0:x1], (np.array([0.85, 0.95, 1.0]) * v[..., None]))
                glow[y0:y1, x0:x1] = np.maximum(glow[y0:y1, x0:x1], v * 0.6)
        if name.startswith("TailB") or name == "TailA":
            # dark eye at the coil centre: last part of the tail darker
            eye = np.clip((Ug - 0.86) / 0.1, 0, 1)[..., None] * 0.5
            c = c * (1 - eye) + indigo * eye
        # glowing streaks near the root (back view), thin and along the tail
        for _ in range((6 if name == "TailA" else 3) if not name.startswith("Curl") else 0):
            a0 = rng.uniform(0, 1)
            u0, u1 = rng.uniform(0.02, 0.1), rng.uniform(0.22, 0.38)
            dA = np.abs(((Ag - a0 - 0.02 * np.sin(Ug * 20)) + 0.5) % 1.0 - 0.5)
            along = np.clip((Ug - u0) / 0.04, 0, 1) * np.clip((u1 - Ug) / 0.08, 0, 1)
            glow = np.maximum(glow, np.clip(1 - dA / 0.012, 0, 1) * along * 0.9)
        # constellation lines (world-space segments on the surface)
        if len(seg_a):
            dmin = np.full(Ug.shape, 1e9)
            for a, bb in zip(seg_a, seg_b):
                dmin = np.minimum(dmin, seg_dist(pos, a, bb))
            line = np.clip((0.0022 - dmin) / 0.0008 + 0.5, 0, 1)
            halo = 0.35 * np.exp(-np.maximum(dmin - 0.0015, 0) / 0.003) * (dmin < 0.02)
            glow = np.maximum(glow, np.maximum(line, halo))
            c = c * (1 - line[..., None]) + np.array([0.85, 0.97, 1.0]) * line[..., None]
        col[row0:row0 + h] = c
        emi[row0:row0 + h, :, 0] = glow
        row0 += h
    return new_image("LW_tail_col", W, rows, col), new_image("LW_tail_emi", W, rows, emi)


def build_tails(body_bvh_obj, star_mat):
    defs = tail_paths()
    strip_h = {"TailA": 512}
    rows = [strip_h.get(n, 256 if not n.startswith("Curl") else 128) for n, *_ in defs]
    total = sum(rows)
    objs, built = [], []
    v = 0
    placeholder = bpy.data.materials.new("M_tail_tmp")
    for (name, P, ru, rv, M, side), h in zip(defs, rows):
        v0, v1 = v / total, (v + h) / total
        hint = (1.0, 0.0, 0.0) if name in ("TailA", "CurlTop1", "CurlTop2", "CurlHang", "CurlFlick") else (0.0, 1.0, 0.0)
        o, grid = sweep(name, P, ru, rv, M, placeholder, hint=hint, uv_rect=(0.0, v0, 1.0, v1))
        o["keep_uv"] = True
        objs.append(o)
        built.append((name, grid, h))
        if name.startswith("TailB"):
            # plug at the coil centre: the spiral's last turns leave a tunnel there otherwise
            c = P[-12:].mean(0)
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
            uvl = bm.loops.layers.uv.new("UVMap")
            for face in bm.faces:
                for loop in face.loops:
                    lx, ly, lz = loop.vert.co
                    a = (math.atan2(lz, lx) / (2 * math.pi)) % 1.0
                    loop[uvl].uv = (0.86 + 0.12 * (1 - abs(ly)), v0 + (v1 - v0) * (0.02 + 0.96 * a))
            for vt in bm.verts:
                vt.co = Vector((c[0] + 0.041 * vt.co.x, c[1] + 0.024 * vt.co.y, c[2] + 0.041 * vt.co.z))
            bm.normal_update()
            plug = kit.mesh_object(f"{name}_coilplug", bm, placeholder)
            plug["keep_uv"] = True
            objs.append(plug)
        v += h
    # constellation stars: raycast the side-view points from +X, the back-view points from behind
    bm = bmesh.new()
    bm.from_mesh(objs[0].data)          # tail A carries the constellation
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    star_pts = []
    for (y, z) in CONST_SIDE:
        hit = tree.ray_cast(Vector((1.0, y, z)), Vector((-1, 0, 0)))
        star_pts.append(np.array(hit[0]) if hit[0] is not None else None)
    lines = [(a, b) for a, b in CONST_SIDE_LINES if star_pts[a] is not None and star_pts[b] is not None]
    off = len(star_pts)
    for (x, z) in CONST_BACK:
        hit = tree.ray_cast(Vector((x, 2.0, z)), Vector((0, -1, 0)))
        star_pts.append(np.array(hit[0]) if hit[0] is not None else None)
    lines += [(a + off, b + off) for a, b in CONST_BACK_LINES if star_pts[a + off] is not None and star_pts[b + off] is not None]
    pts_dict = {i: p for i, p in enumerate(star_pts) if p is not None}
    col_img, emi_img = tail_images(built, pts_dict, lines)
    mat = tail_material(col_img, emi_img)
    for o in objs:
        o.data.materials[0] = mat
    bpy.data.materials.remove(placeholder)
    # star dots: small glowing domes, sizes differ (6 in the side constellation + 5 on the back lobe)
    rng = random.Random(5)
    sizes = [0.012, 0.011, 0.013, 0.012, 0.008, 0.009, 0.006, 0.010, 0.008, 0.007, 0.005, 0.009]
    for i, p in pts_dict.items():
        hitn = tree.find_nearest(Vector(p))
        n = np.array(hitn[1]) if hitn[1] is not None else np.array([1.0, 0, 0])
        r = sizes[i % len(sizes)] * rng.uniform(0.85, 1.1)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
        # flatten along the surface normal: a dome
        nv = Vector(n).normalized()
        for vtx in bm.verts:
            d = vtx.co.dot(nv)
            vtx.co = vtx.co - nv * d * 0.45 + Vector(p) - nv * r * 0.15
        o = kit.mesh_object(f"Star_{i}", bm, star_mat)
        objs.append(o)
    return objs


# ============================================================================ BODY ATTRIBUTES AND CREAM
def make_cream_field(obj):
    """Cream zones of the fur, as a field for kit.mark. Review 1: the chest ruff is cream only where the
    surface faces forward (normal Y < -0.3), the belly only on the underside plus the tips of the
    fringe locks (jagged), the cheeks only inside |x| < 0.12 and not on their back faces."""
    tree = bvh_of(obj)

    def field(p):
        x, y, z = p.x, p.y, p.z
        hit = tree.find_nearest(p)
        n = hit[1] if hit[1] is not None else Vector((0, 0, 1))
        nz = 0.0022 * noise.noise(Vector((x * 55, y * 55, z * 55))) + 0.0008 * noise.noise(Vector((x * 160, y * 160, z * 160)))
        # head: below a line from the nose (z 0.683) under the eye (0.700) back to the cheek (0.655)
        zb = float(np.interp(y, [-0.65, -0.60, -0.55, -0.50, -0.45, -0.40, -0.36, -0.33], [0.676, 0.676, 0.680, 0.684, 0.676, 0.660, 0.645, 0.62]))
        head = max(z - zb, y + 0.33, 0.55 - z, abs(x) - 0.12, n.y - 0.35)
        wb = 0.012 + 0.02 * min(1.0, max(0.0, (y + 0.62) / 0.15))
        bridge = max(abs(x) - wb, 0.672 - z, y + 0.44)   # blue nose bridge, narrowing to the nose
        head = max(head, -bridge)
        # throat and chest front: Y before the boundary, |X| within the bib, V point at z 0.25, facing forward
        yb = float(np.interp(z, [0.24, 0.33, 0.40, 0.50, 0.58, 0.66], [-0.46, -0.42, -0.40, -0.385, -0.37, -0.355]))
        wc = float(np.interp(z, [0.24, 0.27, 0.32, 0.38, 0.47, 0.55, 0.62, 0.66], [0.0, 0.04, 0.085, 0.115, 0.115, 0.09, 0.085, 0.11]))
        chest = max(y - yb, abs(x) - wc, 0.245 - z, z - 0.665, (n.y + 0.3) * 0.1)
        # belly: the underside, and the lower ends of the fringe locks (a jagged cream edge in the side view)
        jag = 0.006 * abs(math.sin(y * 95.0)) + 0.004 * noise.noise(Vector((x * 40, y * 40, 3.0)))
        under = max((n.z + 0.2) * 0.1, z - 0.42, 0.28 - z, y - 0.06, -0.33 - y, abs(x) - 0.085)
        sx = 1.0 if x >= 0 else -1.0
        fringe = max(z - (0.352 + jag), 0.30 - z, y - 0.02, -0.31 - y, abs(x) - 0.075, (-(n.x * sx) - 0.3) * 0.1)
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
    m_feather = feather_material()
    m_silver = silver_material()
    m_gem = gem_material()
    m_eye = eye_material()
    m_nose = dark_material("M_nose", "#23222f", 0.28)
    m_liner = dark_material("M_liner", "#1b2142", 0.45)
    m_star = star_material()

    body, clay = body_clay()
    surf, _ = clay.project(np.array([[0.0, -0.60, GEM_C[2]]]))
    GEM_C[1] = surf[0][1] - 0.011     # the gem's back apex sits on the chest ruff
    kit.quad_remesh(body, 14500)
    close_holes(body)
    body.data.shade_smooth()
    body.data.materials.append(m_fur)
    kit.mark(body, make_cream_field(body), m_cream)
    close_holes(body)
    body_attributes(body)
    parts = [body]

    rng = random.Random(12)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        parts.append(build_ear(side, m_ear_out, m_ear_in, uoff))
        parts += ear_tufts(side, m_tuft, rng, m_ear_out)
        parts.append(build_eye(clay, side, m_eye))
        parts.append(build_liner(clay, side, m_liner))
    parts.append(build_nose(m_nose))
    parts.append(build_gem(m_gem))
    parts += build_collar(clay, m_silver)
    parts += build_feathers(clay, m_feather)
    parts += build_tails(body, m_star)
    return parts


if __name__ == "__main__":
    kit.run(build, texture=4096)
