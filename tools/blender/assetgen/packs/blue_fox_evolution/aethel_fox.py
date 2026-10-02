"""Aethel Fox (Phase 2 evolution of the blue fox): a slim stylised fox on long thin legs, very tall
pointed ears with tan / indigo spiral bowls, a braided leather cord collar with a round blue gem in a
silver bezel, silver-white antler branches over both shoulders, faintly glowing cyan spiral markings
and one huge plume tail curling up over the back into a cream tip.

Coordinates: metres, +Z up, the fox faces -Y, its left side is +X (the side the main side view sees,
az 65). Every size comes from the notes' Analysis (side view 2262 px/m to a 0.50 m total height,
front view 2270 px/m head-based, back view ~1450 px/m).
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




# ============================================================================ BODY CLAY
def leg_defs():
    """Leg joint chains (points, radii): front legs straight under the chest, hind legs in stride."""
    legs = {}
    for s in (1, -1):
        legs[f"fl{s}"] = ([(s * 0.036, -0.118, 0.205), (s * 0.031, -0.112, 0.135), (s * 0.028, -0.114, 0.075),
                           (s * 0.027, -0.113, 0.035), (s * 0.027, -0.112, 0.016)],
                          [0.027, 0.0185, 0.0155, 0.0145, 0.0145])
    # hind: near (+X) paw at Y 0.095, far (-X) paw at Y 0.05 (side-view stride)
    for s, py in ((1, 0.115), (-1, 0.072)):
        legs[f"hl{s}"] = ([(s * 0.040, 0.078, 0.21), (s * 0.041, py - 0.045, 0.135), (s * 0.036, py + 0.018, 0.078),
                           (s * 0.033, py + 0.004, 0.035), (s * 0.033, py, 0.016)],
                          [0.03, 0.021, 0.0145, 0.0135, 0.0145])
    return legs


def body_clay():
    """Signed-distance clay of torso, neck, head, legs, paws and fur locks (sculpting skill)."""
    clay = S.Clay((-0.13, -0.29, -0.01), (0.13, 0.17, 0.40), voxel=0.0021)
    E, C, T = S.sd_ellipsoid, S.sd_cone, S.sd_tube
    # --- torso (side view: chest front Y -0.19, back line Z 0.245, chest bottom Z 0.13, rump Y 0.115)
    clay.add(E((0, -0.126, 0.194), (0.056, 0.064, 0.062)))                     # chest
    clay.add(E((0, -0.065, 0.203), (0.055, 0.075, 0.053)), blend=0.03)        # ribcage
    clay.add(E((0, 0.0, 0.213), (0.045, 0.06, 0.043)), blend=0.03)            # waist / loin (tuck-up)
    clay.add(E((0, 0.078, 0.206), (0.050, 0.058, 0.05)), blend=0.028)       # pelvis / rump
    clay.add(E((0.034, -0.105, 0.208), (0.024, 0.04, 0.05), rot=(12, 0, 0)), blend=0.02, mirror=True)  # shoulders
    clay.add(E((0, -0.162, 0.17), (0.046, 0.034, 0.06)), blend=0.03)        # chest ruff mound
    # --- neck and head (nose Y -0.24 Z 0.30, eye Z 0.318, crown Z 0.36, back of skull Y -0.10)
    clay.add(T([(0, -0.118, 0.213), (0, -0.142, 0.270), (0, -0.148, 0.313)], [0.046, 0.041, 0.037]), blend=0.025)
    clay.add(E((0, -0.154, 0.330), (0.062, 0.052, 0.040)), blend=0.02)       # cranium, crown Z 0.362
    clay.add(E((0, -0.176, 0.334), (0.040, 0.03, 0.024)), blend=0.015)       # brow / frontal plane
    clay.add(E((0.04, -0.172, 0.305), (0.035, 0.034, 0.029)), blend=0.016, mirror=True)  # cheeks
    clay.add(C((0, -0.183, 0.318), (0, -0.236, 0.307), 0.024, 0.008), blend=0.016)       # muzzle
    clay.add(C((0, -0.172, 0.298), (0, -0.226, 0.298), 0.018, 0.006), blend=0.012)         # lower jaw
    clay.add(E((0, -0.118, 0.304), (0.038, 0.036, 0.038)), blend=0.022)      # nape
    for s in (1, -1):                                                            # eye seats
        clay.sub(E((s * 0.03, -0.196, 0.327), (0.013, 0.007, 0.008), rot=(0, s * -14, s * 34)), blend=0.003)
    # mouth corner crease
    for s in (1, -1):
        clay.sub(C((s * 0.006, -0.234, 0.299), (s * 0.02, -0.215, 0.301), 0.0012, 0.0012), blend=0.001)
    rng = random.Random(7)
    for s in (1, -1):
        # cheek tufts: 4 pointed locks sweeping back and out (front view to x +-0.08, z 0.27-0.30)
        cheek = [((0.045, -0.15, 0.308), (0.083, -0.128, 0.296), 0.012),
                 ((0.045, -0.15, 0.298), (0.080, -0.128, 0.276), 0.011),
                 ((0.042, -0.15, 0.288), (0.066, -0.135, 0.263), 0.010),
                 ((0.045, -0.14, 0.313), (0.074, -0.118, 0.312), 0.010)]
        for a, b, r in cheek:
            j = 1.0 + (rng.random() - 0.5) * 0.2
            bb = (a[0] + (b[0] - a[0]) * j, b[1] + rng.uniform(-0.004, 0.004), b[2] + rng.uniform(-0.004, 0.004))
            clay.add(C((s * a[0], a[1], a[2]), (s * bb[0], bb[1], bb[2]), r, 0.0012), blend=0.006)
        # nape locks
        for a, b, r in [((0.035, -0.115, 0.308), (0.060, -0.095, 0.298), 0.011), ((0.035, -0.10, 0.288), (0.058, -0.08, 0.278), 0.01)]:
            clay.add(C((s * a[0], a[1], a[2]), (s * (b[0] + rng.uniform(-0.004, 0.004)), b[1], b[2]), r, 0.0012), blend=0.007)
        # elbow tufts at the back of the front legs (side view z 0.10-0.13)
        clay.add(C((s * 0.034, -0.10, 0.14), (s * 0.036, -0.082, 0.112 + rng.uniform(-0.004, 0.004)), 0.0095, 0.0012), blend=0.006)
        # belly fringe
        for k in range(3):
            y = -0.09 + k * 0.045 + rng.uniform(-0.006, 0.006)
            clay.add(C((s * 0.026, y, 0.150), (s * 0.028, y + 0.016, 0.130 + rng.uniform(-0.006, 0.004)), 0.0095, 0.0012), blend=0.006)
        # ruff locks along the chest side
        for z, l in [(0.205, 0.028), (0.18, 0.032), (0.155, 0.03)]:
            clay.add(C((s * 0.038, -0.172, z), (s * (0.054 + rng.uniform(0, 0.008)), -0.185, z - l), 0.01, 0.0012), blend=0.006)
    # chest ruff spikes: V point at Z 0.105 between the front legs (front view)
    for x, z0, z1, r in [(0.0, 0.15, 0.104, 0.016), (0.017, 0.152, 0.116, 0.013), (-0.018, 0.153, 0.118, 0.012),
                         (0.033, 0.16, 0.13, 0.011), (-0.032, 0.161, 0.128, 0.011)]:
        clay.add(C((x, -0.178, z0), (x * 1.05, -0.177, z1), r, 0.0012), blend=0.006)
    # --- legs, thighs, paws with toes and creases
    for key, (pts, rad) in leg_defs().items():
        clay.add(T(pts, rad), blend=0.008)
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
    st.append((bez2((-0.172, 0.3180), (-0.16, 0.3140), (-0.148, 0.3150), (-0.136, 0.3220)), [0.0008, 0.0026, 0.002, 0.0006]))
    st.append((bez2((-0.168, 0.3080), (-0.156, 0.3040), (-0.146, 0.3040), (-0.136, 0.3080)), [0.0006, 0.002, 0.0016, 0.0005]))
    return st


def front_strokes():
    """Front-projected markings (X, Z): forehead flame, under-eye strokes."""
    st = []
    st.append((bez2((0.0, 0.3440), (0.0015, 0.3490), (-0.001, 0.3540), (0.0, 0.3590)), [0.0008, 0.0038, 0.0026, 0.0004]))
    for s in (1, -1):
        st.append((bez2((s * 0.005, 0.3440), (s * 0.010, 0.3490), (s * 0.011, 0.3530), (s * 0.008, 0.3570)), [0.0005, 0.0016, 0.0012, 0.0004]))
        st.append((bez2((s * 0.018, 0.3130), (s * 0.03, 0.3100), (s * 0.04, 0.3110), (s * 0.05, 0.3170)), [0.0005, 0.0018, 0.0014, 0.0004]))
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
            poly_paint(marks[..., ch], Ys, Zs, pts, np.asarray(w), 1.5 * px, halo=0.16, halo_w=0.0016)
    for pts, w in front_strokes():
        poly_paint(marks[..., 2], Xf, Zf, pts, w, 1.5 * px, halo=0.18, halo_w=0.0015)
    for s in (1, -1):    # cream brow spots, oval, tilted
        d = np.sqrt(((Xf - s * 0.025) / 0.0068) ** 2 + ((Zf - 0.345 + s * 0.0) / 0.0040) ** 2)
        decal[..., 0] = np.maximum(decal[..., 0], np.clip((1 - d) * 8, 0, 1))
    d = np.sqrt(((Ys + 0.193) / 0.0068) ** 2 + ((Zs - 0.346) / 0.004) ** 2)
    decal[..., 1] = np.maximum(decal[..., 1], np.clip((1 - d) * 8, 0, 1))
    for s in (1, -1):    # W smile under the nose
        poly_paint(decal[..., 2], Xf, Zf, bez2((0.0, 0.2990), (s * 0.004, 0.2955), (s * 0.009, 0.2950), (s * 0.016, 0.2995)),
                   [0.0015, 0.0013, 0.0013, 0.0007], 1.5 * px)
    poly_paint(decal[..., 2], Xf, Zf, [(0.0, 0.3035), (0.0, 0.2985)], [0.0013, 0.0013], 1.5 * px)
    return new_image("AF_marks", n, n, marks), new_image("AF_decal", n, n, decal)


# ============================================================================ MATERIALS
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
    creamspot = nt.math("MAXIMUM", nt.math("MULTIPLY", dc_front[0], wfront), nt.math("MULTIPLY", dc_side[1], wside))
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


def ear_materials(img):
    """Ear back (blue fur, darker rim) and inner bowl (tan with blue spirals, indigo upper / inner
    zone where the spiral glows cyan), from the ear UVs (u across 0..0.5 per ear, v along)."""
    out = []
    for inner in (False, True):
        mat, tree, bsdf = kit.principled("M_ear_inner" if inner else "M_ear_outer")
        nt = NT(tree)
        uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
        ch = nt.rgb_sep(nt.image(img, uv).outputs["Color"])
        uvs = nt.sep(uv)
        t = uvs[1]
        ul = nt.math("FRACT", nt.math("MULTIPLY", uvs[0], 2.0))            # 0..1 across this ear
        rim = nt.maprange(nt.math("ABSOLUTE", nt.math("SUBTRACT", ul, 0.5)), 0.36, 0.5)
        strk = nt.noise(nt.scale_vec(uv, 160, 18, 1), 1.0, 4, 0.6)
        blot = nt.noise(nt.coords("Object"), 30.0, 3, 0.5)
        if inner:
            base = nt.ramp(t, [(0.0, "#b8a89e"), (0.3, "#c6b8ad"), (0.7, "#cbbcb0"), (1.0, "#b6aaa6")])
            base = nt.mix(nt.maprange(blot, 0.35, 0.7, 0.0, 0.3), base, lin("#d4c6b8"))
            base = nt.mix(ch[1], base, lin("#46577d"))                       # indigo zone
            base = nt.mix(ch[0], base, lin("#6f86ad"))                       # blue spiral strokes
            glow = nt.math("MULTIPLY", ch[0], ch[1])
            base = nt.mix(nt.math("MULTIPLY", glow, 0.9), base, lin("#a8e2f0"))
            base = nt.mix(nt.math("MULTIPLY", rim, 0.9), base, lin("#5d7398"))
            rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.15), 0.62)
        else:
            base = nt.ramp(t, [(0.0, "#87abc4"), (0.5, "#93bad0"), (0.9, "#8aaecb"), (1.0, "#6d86ad")])
            sv = nt.ramp(strk, [(0.3, (0.92, 0.93, 0.95, 1)), (0.7, (1.07, 1.06, 1.04, 1))])
            base = nt.mix(1.0, base, sv, "MULTIPLY")
            base = nt.mix(nt.math("MULTIPLY", rim, 0.75), base, lin("#647ea6"))
            glow = nt.math("MULTIPLY", ch[0], 0.0)
            rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.12), 0.74)
        emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3aa8d8"), (1.0, "#b0f2ff")])
        set_bsdf(nt, bsdf, base=base, rough=rough, emis_col=emis, emis_str=0.9, normal=nt.bump(strk, 0.25, 0.0006))
        out.append(mat)
    return out


def cream_blade_material():
    mat, tree, bsdf = kit.principled("M_cream_blade")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    strk = nt.noise(nt.scale_vec(uv, 6, 60, 1), 1.0, 4, 0.6)
    base = nt.ramp(uvs[0], [(0.0, "#a9a3a6"), (0.3, "#d0c6bd"), (0.7, "#ddd5ca"), (1.0, "#e6dfd4")])
    sv = nt.ramp(strk, [(0.3, (0.88, 0.89, 0.93, 1)), (0.7, (1.05, 1.04, 1.03, 1))])
    base = nt.mix(1.0, base, sv, "MULTIPLY")
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", strk, 0.1), 0.78), normal=nt.bump(strk, 0.3, 0.0006))
    return mat


def silver_material():
    mat, tree, bsdf = kit.principled("M_silver")
    nt = NT(tree)
    co = nt.coords("Object")
    nz = nt.noise(co, 140.0, 4, 0.6)
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.006
    base = nt.ramp(nz, [(0.3, "#a9aeb9"), (0.5, "#c4c8d1"), (0.7, "#d8dbe2")])
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.9, 0.4), base, lin("#4d5266"))
    rough = nt.ramp(nz, [(0.3, (0.16, 0.16, 0.16, 1)), (0.7, (0.34, 0.34, 0.34, 1))])
    set_bsdf(nt, bsdf, base=base, rough=nt.rgb_sep(rough)[0], metal=1.0, normal=nt.bump(nz, 0.15, 0.0003))
    return mat


def antler_material():
    """Pale silver-white with a blue tint: light tops, blue-grey undersides, glossy, faint streaks
    along each branch, darker in the forks."""
    mat, tree, bsdf = kit.principled("M_antler")
    nt = NT(tree)
    co = nt.coords("Object")
    nz = nt.noise(nt.scale_vec(co, 300, 300, 300), 1.0, 3, 0.5)
    up = nt.sep(nt.coords("Normal"))[2]
    base = nt.ramp(nt.math("ADD", nt.math("MULTIPLY", up, 0.5), 0.5),
                   [(0.0, "#7d9cc2"), (0.35, "#a3bfdb"), (0.6, "#c9dcec"), (0.85, "#e3eef7"), (1.0, "#eef6fb")])
    sv = nt.ramp(nz, [(0.3, (0.94, 0.95, 0.97, 1)), (0.7, (1.04, 1.03, 1.02, 1))])
    base = nt.mix(1.0, base, sv, "MULTIPLY")
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.006
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.92, 0.5, 0.0, 0.6), base, lin("#5e7499"))
    rough = nt.math("ADD", nt.math("MULTIPLY", nz, 0.12), 0.16)
    set_bsdf(nt, bsdf, base=base, rough=rough, metal=0.0, normal=nt.bump(nz, 0.1, 0.0002))
    bsdf.inputs["Specular IOR Level"].default_value = 0.7
    return mat


def cord_material():
    """Braided leather: brown strands, dark grooves (strand-angle mask from the UVs), fine grain,
    worn shinier strand tops."""
    mat, tree, bsdf = kit.principled("M_cord")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    ring = nt.math("ABSOLUTE", nt.math("SUBTRACT", nt.math("FRACT", uvs[1]), 0.5))   # 0 = strand top, 0.5 = groove
    grain = nt.noise(nt.scale_vec(nt.coords("Object"), 900, 900, 900), 1.0, 3, 0.6)
    streak = nt.noise(nt.scale_vec(uv, 400, 6, 1), 1.0, 3, 0.5)
    base = nt.ramp(ring, [(0.0, "#a0735c"), (0.25, "#8a5f4b"), (0.5, "#74513f")])
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.004
    base = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.5, 0.0, 0.85), base, lin("#3b2e2b"))
    sv = nt.ramp(grain, [(0.3, (0.88, 0.88, 0.9, 1)), (0.7, (1.08, 1.06, 1.04, 1))])
    base = nt.mix(1.0, base, sv, "MULTIPLY")
    base = nt.mix(nt.maprange(streak, 0.55, 0.7, 0.0, 0.25), base, lin("#b08470"))
    rough = nt.math("ADD", nt.math("MULTIPLY", ring, 0.5), 0.5)
    set_bsdf(nt, bsdf, base=base, rough=rough, normal=nt.bump(grain, 0.25, 0.0003))
    return mat


def gem_material():
    """Deep blue cabochon: dark core, lighter lower rim, white spec spot, faint inner glow (UVs:
    u, v across the dome face 0..1)."""
    mat, tree, bsdf = kit.principled("M_gem")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    dx = nt.math("SUBTRACT", uvs[0], 0.5)
    dy = nt.math("SUBTRACT", uvs[1], 0.5)
    r = nt.math("SQRT", nt.math("ADD", nt.math("POWER", dx, 2.0), nt.math("POWER", dy, 2.0)))
    low = nt.math("SUBTRACT", 0.5, uvs[1])
    base = nt.ramp(nt.math("ADD", nt.math("MULTIPLY", r, 1.2), nt.math("MULTIPLY", low, 0.6)),
                   [(0.0, "#1a3f9e"), (0.35, "#1f50b8"), (0.6, "#3d7fe0"), (0.85, "#6eaef5"), (1.0, "#4f86d8")])
    spot = nt.math("SQRT", nt.math("ADD", nt.math("POWER", nt.math("ADD", dx, 0.13), 2.0),
                                   nt.math("POWER", nt.math("SUBTRACT", dy, 0.15), 2.0)))
    sm = nt.maprange(spot, 0.085, 0.05)
    base = nt.mix(sm, base, lin("#f4fbff"))
    sparkle = nt.noise(nt.scale_vec(nt.coords("Object"), 800, 800, 800), 1.0, 2, 0.5)
    base = nt.mix(nt.math("MULTIPLY", nt.maprange(sparkle, 0.6, 0.72), 0.3), base, lin("#8fc4ff"))
    emis = nt.mix(sm, lin("#1f5fe0"), lin("#ffffff"))
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", sparkle, 0.08), 0.04), emis_col=emis, emis_str=0.7)
    return mat


def eye_material():
    """Anime eye from its own UVs: grey-blue iris dark at the top, light below, dark pupil and rim,
    white catch light, pale corners."""
    mat, tree, bsdf = kit.principled("M_eye")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    uvs = nt.sep(uv)
    ra, rb = 0.0132, 0.0102
    x = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[0], 0.5), 2 * ra)
    y = nt.math("MULTIPLY", nt.math("SUBTRACT", uvs[1], 0.5), 2 * rb)
    dx = nt.math("SUBTRACT", x, 0.0008)
    r = nt.math("DIVIDE", nt.math("SQRT", nt.math("ADD", nt.math("POWER", dx, 2.0), nt.math("POWER", y, 2.0))), 0.0094)
    vert = nt.math("ADD", nt.math("DIVIDE", y, 0.016), 0.5)
    iris = nt.ramp(vert, [(0.0, "#aab8d2"), (0.35, "#7d8fb4"), (0.65, "#53648e"), (1.0, "#323c62")])
    col = nt.mix(nt.maprange(r, 0.36, 0.30), iris, lin("#161b30"))
    col = nt.mix(nt.maprange(r, 0.86, 0.97), col, lin("#262c4c"))
    col = nt.mix(nt.maprange(r, 1.02, 1.10), col, lin("#c9d3e2"))
    hl = nt.math("SQRT", nt.math("ADD", nt.math("POWER", nt.math("ADD", x, 0.0022), 2.0),
                                 nt.math("POWER", nt.math("SUBTRACT", y, 0.0024), 2.0)))
    hlm = nt.maprange(hl, 0.0017, 0.0011)
    col = nt.mix(hlm, col, lin("#fbfdff"))
    sparkle = nt.noise(uv, 30.0, 2, 0.5)
    col = nt.mix(nt.math("MULTIPLY", nt.maprange(sparkle, 0.55, 0.7), 0.2), col, lin("#c3d1ea"))
    set_bsdf(nt, bsdf, base=col, rough=nt.math("ADD", nt.math("MULTIPLY", sparkle, 0.1), 0.12),
             emis_col=nt.mix(hlm, lin("#000000"), lin("#ffffff")), emis_str=0.6)
    return mat


def dark_material(name, hexcol, rough, hi="#4a4458"):
    mat, tree, bsdf = kit.principled(name)
    nt = NT(tree)
    nz = nt.noise(nt.coords("Object"), 400.0, 3, 0.5)
    base = nt.ramp(nz, [(0.3, hexcol), (0.7, hi)])
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", nz, 0.15), rough), normal=nt.bump(nz, 0.2, 0.0002))
    return mat


def tail_material(col_img, emi_img):
    mat, tree, bsdf = kit.principled("M_tail")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    col = nt.image(col_img, uv).outputs["Color"]
    emi = nt.rgb_sep(nt.image(emi_img, uv).outputs["Color"])
    strk = nt.noise(nt.scale_vec(uv, 160, 12, 1), 1.0, 4, 0.6)
    sv = nt.ramp(strk, [(0.3, (0.91, 0.92, 0.95, 1)), (0.5, (1, 1, 1, 1)), (0.7, (1.07, 1.06, 1.04, 1))])
    col = nt.mix(1.0, col, sv, "MULTIPLY")
    glow = emi[0]
    col = nt.mix(nt.math("MULTIPLY", glow, 0.85), col, lin("#c9f4ff"))
    emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3fb4ea"), (1.0, "#b8f2ff")])
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.02
    col = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.5, 0.0, 0.4), col, lin("#4a5a85"))
    rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.12), 0.72)
    set_bsdf(nt, bsdf, base=col, rough=rough, emis_col=emis, emis_str=1.4, normal=nt.bump(strk, 0.3, 0.0012))
    return mat


# ============================================================================ EARS
def ear_shape(side):
    """Leaf-shaped ear frame for side +1 (+X) or -1: base B, axis a, bowl normal f, width w, length L."""
    j = 0.002 * side
    B = np.array([side * 0.044, -0.150, 0.340])
    Tp = np.array([side * (0.108 + j), -0.160 + 0.003 * side, 0.475 - abs(j)])
    L = float(np.linalg.norm(Tp - B))
    a = (Tp - B) / L
    f0 = np.array([side * 0.55, -1.0, 0.10])
    f = f0 - (f0 @ a) * a
    f /= np.linalg.norm(f)
    w = np.cross(a, f)
    if w[0] * side < 0:
        w = -w
    return B, a, f, w, L


def ear_hw(u_sign, t):
    """Half-width at fraction t: outer edge (u >= 0) convex, pulled in at the base; inner straighter."""
    t = np.asarray(t, float)
    outer = 0.040 * (1 - t) ** 0.85 * (1 + 0.95 * t) * (0.6 + 0.4 * np.clip(t / 0.22, 0, 1) ** 0.7)
    inner = 0.030 * (1 - t) ** 0.9 * (1 + 0.5 * t)
    out = np.where(np.asarray(u_sign) >= 0, outer, inner)
    return float(out) if out.ndim == 0 else out


def build_ear(side, m_out, m_in, uoff):
    B, a, f, w, L = ear_shape(side)
    Nt, Nu = 30, 15
    us = -np.cos(np.linspace(0, math.pi, Nu))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for it in range(Nt):
        t = it / (Nt - 1) * 0.985
        c = B + a * L * t - f * 0.010 * math.sin(math.pi * t) * 0.7
        D = 0.016 * (1 - t) ** 0.7
        th = 0.0035 + 0.004 * (1 - t)
        front, back = [], []
        for u in us:
            hw = ear_hw(u, t)
            x = u * hw
            bowl = D * (1 - u * u)
            p = c + w * x - f * bowl
            q = c + w * x - f * (bowl * 0.9 + th + 0.003 * (1 - u * u) * (1 - t))
            front.append(bm.verts.new(p))
            back.append(bm.verts.new(q))
        rings.append((front, back, t))
    tipv = bm.verts.new(B + a * L * 1.0 - f * 0.002)
    basev = bm.verts.new(B - a * 0.006 - f * 0.008)

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
            inner = k < Nu - 1 and abs(uu[k]) <= 0.84 and abs(uu[k2]) <= 0.84
            face.material_index = 1 if inner else 0
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
    """Ear inner texture: R = blue spiral strokes (S: an upper and a lower curl on the outer half),
    G = indigo zone (upper third and the inner strip, soft edged)."""
    W, H = 1024, 1024
    img = np.zeros((H, W, 3), np.float32)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        B, a, f, w, L = ear_shape(side)
        i0, i1 = int(uoff * W), int((uoff + 0.5) * W)
        uu = ((np.arange(i0, i1) + 0.5) / W - uoff) / 0.25 - 1
        tt = (np.arange(H) + 0.5) / H
        Ug, Tg = np.meshgrid(uu, tt)
        hw = ear_hw(Ug, Tg)
        X = Ug * hw
        Y = Tg * L
        sub = img[:, i0:i1]
        j = 0.002 * side
        # upper curl (outer side, t ~0.66) and lower curl (outer side, t ~0.36) joined by an S line
        up = spiral((0.010 + j, 0.092), 0.0105, 1.25, -0.25 * math.pi, 1, 1.15, 0.0, 50, 0.85)
        lo = spiral((0.012 - j, 0.052), 0.0095, 1.2, 0.75 * math.pi, -1, 1.15, 0.0, 50, 0.85)
        sline = bez2(lo[0], (0.026, 0.062), (0.024, 0.085), up[0], 24)
        stroke = list(reversed(lo)) + sline[1:-1] + up
        widths = np.concatenate([np.linspace(0.0012, 0.0034, len(lo)), np.full(len(sline) - 2, 0.0036),
                                 np.linspace(0.0034, 0.0012, len(up))])
        poly_paint(sub[..., 0], X, Y, stroke, widths, 0.0004)
        poly_paint(sub[..., 0], X, Y, bez2((-0.004, 0.02), (0.0, 0.03), (0.006, 0.038), lo[0]), [0.0008, 0.0022, 0.0026, 0.003], 0.0004)
        # indigo zone: upper part of the bowl and a strip along the inner edge, soft
        zone = np.clip((Tg - 0.62) / 0.12, 0, 1)
        zone = np.maximum(zone, np.clip((-Ug - 0.35) / 0.25, 0, 1) * np.clip((Tg - 0.15) / 0.2, 0, 1))
        sub[..., 1] = zone
        img[:, i0:i1] = sub
    return new_image("AF_ears", W, H, img)


def ear_blades(side, mat, rng):
    """Cream fur blades at the inner base of the ear, fanning up out of the bowl (4-5, each different)."""
    B, a, f, w, L = ear_shape(side)
    objs = []
    for k in range(5):
        t0 = 0.02 + 0.03 * k + rng.uniform(-0.006, 0.006)
        x0 = -0.017 + 0.007 * k + rng.uniform(-0.002, 0.002)
        root = B + a * L * t0 + w * x0 - f * 0.011
        ang = math.radians(-14 + 12 * k + rng.uniform(-5, 5))
        d = a * math.cos(ang) + w * math.sin(ang)
        ln = 0.024 + 0.008 * math.sin(k * 1.2) + rng.uniform(0, 0.007)
        p1 = root + d * ln * 0.4 + f * 0.004
        p2 = root + d * ln * 0.75 + f * 0.006
        p3 = root + d * ln + f * 0.004 - w * 0.002
        P = np.array(S.bezier(root, p1, p2, p3, 14))
        tt = np.linspace(0, 1, 14)
        width = 0.0085 * np.sin(np.clip(tt, 0.02, 1) * math.pi * 0.5 + 0.25) * (1 - tt ** 1.6) + 1e-5
        width[-1] = 0
        th = 0.0016 * (1 - tt) + 1e-5
        th[-1] = 0
        o, _ = sweep(f"EarBlade_{side}_{k}", P, th, width, 8, mat, hint=np.tile(f, (14, 1)), uv_rect=(0, 0, 1, 1))
        o["keep_uv"] = True
        objs.append(o)
    return objs


# ============================================================================ EYES, NOSE
def eye_frame(clay, side):
    p, n = clay.project(np.array([[side * 0.030, -0.197, 0.327]]))
    p, n = p[0], n[0]
    n = n + np.array([side * 0.25, -0.1, 0.0])
    n /= np.linalg.norm(n)
    up = np.array([0.0, 0.0, 1.0])
    e_up = up - (up @ n) * n
    e_up /= np.linalg.norm(e_up)
    e_long = np.cross(e_up, n)
    if e_long[0] * side < 0:
        e_long = -e_long
    sl = math.radians(12)
    e_l = e_long * math.cos(sl) + e_up * math.sin(sl)
    e_u = -e_long * math.sin(sl) + e_up * math.cos(sl)
    return p, n, e_l, e_u


def build_eye(clay, side, mat):
    p, n, el, eu = eye_frame(clay, side)
    ra, rb, rc = 0.0132, 0.0102, 0.0048
    c = p - n * 0.0008
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=18, radius=1.0)
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
    ra, rb = 0.0132, 0.0102
    c = p - n * 0.0008
    pts = []
    for th in np.linspace(math.pi + 0.3, 0.08, 24):
        pts.append(c + el * ra * 1.03 * math.cos(th) + eu * rb * 1.12 * math.sin(th) + n * 0.0018)
    pts.append(c + el * ra * 1.25 + eu * rb * 0.5 + n * 0.001)
    pts.append(c + el * ra * 1.48 + eu * rb * 0.95)
    P = np.array(pts)
    tt = np.linspace(0, 1, len(P))
    r = 0.0006 + 0.0009 * np.sin(np.clip(tt, 0, 1) * math.pi) ** 0.6
    r[-1] = 0.0
    o, _ = sweep(f"Liner_{side}", P, r * 0.7, r, 8, mat, hint=np.tile(n, (len(P), 1)))
    return o


def build_nose(mat):
    clay = S.Clay((-0.015, -0.252, 0.293), (0.015, -0.222, 0.320), voxel=0.0008)
    clay.add(S.sd_ellipsoid((0, -0.2385, 0.3075), (0.0078, 0.0058, 0.0052)))
    clay.add(S.sd_ellipsoid((0, -0.2355, 0.3105), (0.0064, 0.0055, 0.0036)), blend=0.002)
    clay.intersect(S.sd_halfspace((0, 0, 0.3025), (0, 0.25, -1)), blend=0.0014)
    for s in (1, -1):
        clay.sub(S.sd_ellipsoid((s * 0.0036, -0.2435, 0.3045), (0.0017, 0.0019, 0.0011), rot=(0, 0, s * 25)), blend=0.0007)
    obj = clay.to_object("Nose", symmetric=False)
    obj.data.materials.append(mat)
    return obj


# ============================================================================ COLLAR: CORD, PENDANT, ANTLERS
GEM_C = np.array([0.0, -0.200, 0.172])   # y set on the chest surface in build()


def cord_ring(clay):
    """Centre line of the braided cord around the neck: front low (Z 0.192), back high (Z 0.29),
    snapped onto the neck surface and lifted by the cord radius."""
    ang = np.linspace(0, 2 * math.pi, 120, endpoint=False)
    ring = np.stack([0.05 * np.sin(ang), -0.153 - 0.05 * np.cos(ang), 0.241 - 0.049 * np.cos(ang)], 1)
    S_, N_ = clay.project(ring)
    return S_ + N_ * 0.0031, N_


def build_cord(clay, mat):
    C_, N_ = cord_ring(clay)
    n = len(C_)
    T = np.roll(C_, -1, 0) - np.roll(C_, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Nn = N_ - (N_ * T).sum(1, keepdims=True) * T
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    Bn = np.cross(T, Nn)
    # dense resample for the strands
    k = 3
    idx = np.arange(n * k) / k
    i0 = np.floor(idx).astype(int) % n
    i1 = (i0 + 1) % n
    tt = (idx - np.floor(idx))[:, None]
    P = C_[i0] * (1 - tt) + C_[i1] * tt
    NN = Nn[i0] * (1 - tt) + Nn[i1] * tt
    BB = Bn[i0] * (1 - tt) + Bn[i1] * tt
    length = float(np.linalg.norm(np.diff(np.concatenate([C_, C_[:1]]), axis=0), axis=1).sum())
    twists = round(length / 0.011)
    s = np.arange(n * k) / (n * k)
    objs = []
    for strand in range(3):
        th = 2 * math.pi * (twists * s + strand / 3.0)
        Q = P + (NN * np.cos(th)[:, None] + BB * np.sin(th)[:, None]) * 0.0016
        hint = np.concatenate([NN[-1:], NN, NN[:1]])
        o, _ = sweep(f"Cord_{strand}", Q, 0.0019, 0.0019, 8, mat, hint=hint, closed=True,
                     uv_rect=(0.0, 0.0, float(twists), 1.0))
        o["keep_uv"] = True
        objs.append(o)
    front = C_[0]
    return objs, front


def build_pendant(m_silver, m_gem, cord_front):
    objs = []
    gc = GEM_C.copy()
    # bail: a flat loop from the cord down to the bezel top, facing forward
    top = cord_front + np.array([0.0, -0.002, -0.001])
    bot = gc + np.array([0.0, 0.0015, 0.0165])
    mid = (top + bot) / 2
    hh = float(np.linalg.norm(top - bot)) / 2 + 0.0015
    loop = [mid + np.array([0.0035 * math.sin(a), 0.0, hh * math.cos(a)]) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    o, _ = sweep("Bail", np.array(loop), 0.0013, 0.0011, 8, m_silver, hint=(0, -1, 0), closed=True)
    objs.append(o)
    # bezel ring around the gem, facing forward and tilted down 12 deg (on the sloping chest)
    tilt = math.radians(12)
    ex = np.array([1.0, 0.0, 0.0])
    ez = np.array([0.0, math.sin(tilt), math.cos(tilt)])
    ny = np.cross(ez, ex)
    ring = [gc + ex * 0.0152 * math.cos(a) + ez * 0.0152 * math.sin(a) for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
    o, _ = sweep("Bezel", np.array(ring), 0.0026, 0.0034, 12, m_silver, hint=ny, closed=True)
    objs.append(o)
    # back plate
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0158, radius2=0.0158, depth=0.003)
    for v in bm.verts:
        p = np.array(v.co)
        v.co = Vector(gc + ex * p[0] + ez * p[1] + (-ny) * (p[2] - 0.0025))
    bm.normal_update()
    objs.append(kit.mesh_object("BezelPlate", bm, m_silver))
    # gem dome
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)
    uvl = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for lp in face.loops:
            lx, ly, lz = lp.vert.co
            lp[uvl].uv = (0.5 + 0.5 * lx, 0.5 + 0.5 * lz)
    for v in bm.verts:
        lx, ly, lz = v.co
        v.co = Vector(gc + ex * 0.0128 * lx + ez * 0.0128 * lz + ny * (0.0058 * ly - 0.0004))
    bm.normal_update()
    o = kit.mesh_object("Gem", bm, m_gem)
    o["keep_uv"] = True
    objs.append(o)
    return objs


def antler_defs(clay, side, rng):
    """Branch centre lines (N,3) and root/tip radii for one side's antler: a beam from beside the
    pendant up along the chest side over the shoulder, with tines out, up and back."""
    s = side
    j = lambda a=0.004: rng.uniform(-a, a)
    gc = GEM_C
    beam_ctrl = np.array([(s * 0.013, gc[1] + 0.004, gc[2] - 0.004), (s * 0.03, -0.193, 0.183), (s * 0.05, -0.178, 0.202),
                          (s * 0.064, -0.152, 0.219), (s * 0.072, -0.122, 0.233), (s * 0.074, -0.095, 0.243 + j(0.003))])
    beam = catmull(beam_ctrl, 12)
    Sb, Nb = clay.project(beam)
    beam = Sb + Nb * 0.0044
    branches = [("beam", beam, 0.0046, 0.0036)]

    def at(f):
        i = int(f * (len(beam) - 1))
        return beam[i], Nb[i]

    # tines: (fraction along beam, control offsets relative to the root, root r)
    tines = [
        (0.36, [(s * 0.02, 0.0, 0.01), (s * 0.04, 0.004, 0.025), (s * (0.05 + j()), 0.008, 0.045), (s * 0.045, 0.01, 0.058)], 0.0034),   # outer front tine to X 0.10
        (0.55, [(s * 0.008, 0.01, 0.02), (s * 0.014, 0.022, 0.045), (s * 0.016, 0.03, 0.065 + j()), (s * 0.01, 0.04, 0.072)], 0.0033),    # top tine up and back
        (0.70, [(s * 0.015, 0.004, 0.0), (s * 0.03, 0.01, -0.004), (s * (0.04 + j()), 0.016, -0.002), (s * 0.042, 0.022, 0.008)], 0.003),  # lower outer tine, hooks up
        (0.86, [(s * 0.006, 0.012, 0.006), (s * 0.01, 0.026, 0.014), (s * 0.01, 0.038, 0.024 + j()), (s * 0.004, 0.044, 0.034)], 0.003),  # rear tine along the back
        (0.24, [(s * 0.006, 0.0, 0.012), (s * 0.012, -0.002, 0.022), (s * 0.02, -0.004, 0.03 + j()), (s * 0.026, -0.002, 0.032)], 0.0027), # small up tine
    ]
    for f, offs, r0 in tines:
        root, nrm = at(f)
        cps = [root] + [root + np.array(o) for o in offs]
        P = catmull(np.array(cps), 9)
        branches.append(("tine", P, r0, 0.0021))
    # scroll curl beside the gem and the drop under it
    sp = spiral((0.0, 0.0), 0.0085, 1.05, math.pi * 0.35, -s, 1.0, 0.0, 26, 0.8)
    pts = [(s * 0.012, gc[1] + 0.003, gc[2] - 0.006)] + [(s * 0.030 + x, gc[1] + 0.004, gc[2] - 0.020 + y) for x, y in sp]
    P = np.array(pts)
    Sp, Np = clay.project(P)
    P = Sp + Np * 0.003
    branches.append(("curl", P, 0.0028, 0.0012))
    drop = np.array(bez2((s * 0.009, gc[1] + 0.002, gc[2] - 0.013), (s * 0.010, gc[1] + 0.003, gc[2] - 0.026),
                         (s * 0.006, gc[1] + 0.006, gc[2] - 0.038), (0.0, gc[1] + 0.008, gc[2] - 0.048), 16))
    Sd, Nd = clay.project(drop)
    drop = Sd + Nd * 0.0025
    branches.append(("drop", drop, 0.0026, 0.0009))
    return branches


def build_antlers(clay, mat):
    objs = []
    rng = random.Random(31)
    for side in (1, -1):
        for k, (kind, P, r0, r1) in enumerate(antler_defs(clay, side, rng)):
            n = len(P)
            tt = np.linspace(0, 1, n)
            rr = r0 + (r1 - r0) * tt ** 0.8
            if kind != "beam":
                rr[-1] = 0.0
                rr[-2] = rr[-3] * 0.8
            o, _ = sweep(f"Antler_{side}_{kind}_{k}", P, rr, rr, 12, mat, hint=(0, 0, 1),
                         tip=kind != "beam", start_cap=True)
            objs.append(o)
            if kind == "beam":   # rounded end of the beam
                end = P[-1]
                bm = bmesh.new()
                bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r1 * 1.05)
                bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(end))
                objs.append(kit.mesh_object(f"Antler_{side}_beamtip", bm, mat))
    return objs


# ============================================================================ TAIL
def tail_path():
    """Centre line (Y, Z at X ~0) of the plume: root at the rump, swelling up and back, the top
    curling over backward into the cream tip; radius profile in plane (rv) and across (ru)."""
    cps = np.array([(0.08, 0.228), (0.108, 0.26), (0.138, 0.30), (0.158, 0.348), (0.172, 0.392), (0.192, 0.428),
                    (0.228, 0.448), (0.268, 0.442), (0.302, 0.418), (0.328, 0.385), (0.35, 0.352), (0.368, 0.33)])
    P2 = catmull(cps, 16)
    P = np.stack([np.zeros(len(P2)), P2[:, 0] + 0.015 * np.clip(np.linspace(0, 1, len(P2)) * 4, 0, 1), P2[:, 1]], 1)
    tt = np.linspace(0, 1, len(P))
    rv = np.interp(tt, [0, 0.06, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.93, 1.0],
                   [0.024, 0.045, 0.078, 0.094, 0.090, 0.075, 0.058, 0.045, 0.034, 0.022, 0.012, 0.0])
    ru = rv * np.interp(tt, [0, 0.3, 0.7, 1.0], [1.0, 1.05, 0.9, 0.8])
    return P, ru, rv


def build_tail_mesh(name, P, ru, rv, M, mat, ripple=0.035, nflutes=9, seed=0):
    """Swept plume with fur-lock flutes: the radius ripples around the section (nflutes lobes whose
    phase drifts along the tail) and the ripple fades at the root and the tip. UVs u along, v around
    (v = 0 on the +X side)."""
    rng = np.random.default_rng(seed)
    P = np.asarray(P, float)
    n = len(P)
    T, N, B = frames(P, (1.0, 0.0, 0.0))
    tt = np.linspace(0, 1, n)
    ang = np.arange(M) / M * 2 * math.pi
    fade = np.clip(tt / 0.12, 0, 1) * np.clip((1 - tt) / 0.15, 0, 1)
    drift = np.cumsum(rng.normal(0, 0.03, n))
    rip = 1 + ripple * fade[:, None] * (np.sin(nflutes * ang[None, :] + drift[:, None] + 2.0 * tt[:, None])
                                        + 0.4 * np.sin(2 * nflutes * ang[None, :] + 1.3 + drift[:, None] * 2))
    rings = P[:, None, :] + N[:, None, :] * (ru[:, None] * rip * np.cos(ang))[..., None] + B[:, None, :] * (rv[:, None] * rip * np.sin(ang))[..., None]
    nrm = N[:, None, :] * (np.cos(ang) / np.maximum(ru[:, None], 1e-6))[..., None] + B[:, None, :] * (np.sin(ang) / np.maximum(rv[:, None], 1e-6))[..., None]
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-12
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    s /= s[-1]
    vs = [[bm.verts.new(rings[i, j]) for j in range(M)] for i in range(n - 1)]
    tipv = bm.verts.new(P[-1])
    startv = bm.verts.new(P[0] - T[0] * 0.004)
    for i in range(n - 2):
        for j in range(M):
            j2 = (j + 1) % M
            f = bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
            for lp, c in zip(f.loops, [(s[i], j / M), (s[i], (j + 1) / M), (s[i + 1], (j + 1) / M), (s[i + 1], j / M)]):
                lp[uvl].uv = c
    for j in range(M):
        j2 = (j + 1) % M
        f = bm.faces.new((vs[n - 2][j], vs[n - 2][j2], tipv))
        for lp, c in zip(f.loops, [(s[n - 2], j / M), (s[n - 2], (j + 1) / M), (1.0, (j + 0.5) / M)]):
            lp[uvl].uv = c
        f = bm.faces.new((vs[0][j2], vs[0][j], startv))
        for lp, c in zip(f.loops, [(0.0, (j + 1) / M), (0.0, j / M), (0.0, (j + 0.5) / M)]):
            lp[uvl].uv = c
    bm.normal_update()
    obj = kit.mesh_object(name, bm, mat)
    obj["keep_uv"] = True
    return obj, (rings, nrm, s)


def tail_flicks(P, ru, rv, rng):
    """Pointed fur flicks: two on the lower back edge of the plume, three at the curled tip."""
    out = []
    n = len(P)
    T, N, B = frames(P, (1.0, 0.0, 0.0))

    def surf(f, a, inset=0.85):
        i = int(f * (n - 1))
        return P[i] + (N[i] * ru[i] * math.cos(a) + B[i] * rv[i] * math.sin(a)) * inset, i
    specs = [(0.30, math.pi / 2 - 0.25, 0.035, 0.012, (0.0, 0.010, -0.03)),
             (0.40, math.pi / 2 + 0.15, 0.03, 0.010, (0.0, 0.022, -0.018)),
             (0.86, -math.pi / 2 - 0.2, 0.03, 0.008, (0.004, 0.026, -0.012)),
             (0.90, 0.3, 0.028, 0.007, (0.012, 0.024, -0.004)),
             (0.88, -0.6, 0.026, 0.007, (-0.012, 0.022, -0.006))]
    for k, (f, a, ln, w0, d) in enumerate(specs):
        root, i = surf(f, a)
        dvec = np.array(d) / np.linalg.norm(d)
        bend = np.array([0.0, 0.0, -1.0]) * 0.25 + B[i] * 0.2
        p1 = root + dvec * ln * 0.35
        p2 = root + dvec * ln * 0.7 + bend * ln * 0.15
        p3 = root + dvec * ln + bend * ln * 0.35
        Q = np.array(S.bezier(root, p1, p2, p3, 14))
        tt = np.linspace(0, 1, 14)
        width = w0 * (1 - tt ** 1.3) + 1e-5
        width[-1] = 0
        th = w0 * 0.45 * (1 - tt) + 1e-5
        th[-1] = 0
        out.append((f"TailFlick_{k}", Q, th, width, f))
    return out


TAIL_W, TAIL_H = 2048, 1024


def tail_images(grid, flick_n):
    """Tail colour and emission atlas (u along the tail 0..1, v around, v = 0 on the +X side):
    light / deep blue base, cream flame swirls with curled ends (each different), cream curled tip
    with a jagged edge, glowing cyan swirls and dots in the lower third, glowing dots at the tip edge.
    A strip at the top of the atlas (v 0.94..1) holds the flick blades' cream colour."""
    rings, nrm, s = grid
    W, H = TAIL_W, TAIL_H
    rng = np.random.default_rng(77)
    U = (np.arange(W) + 0.5) / W
    A = (np.arange(H) + 0.5) / H
    Ug, Ag = np.meshgrid(U, A)
    pos, nn = bilinear_grid(rings, nrm, s, Ug, np.clip(Ag, 0, 0.9999))
    # metric canvas: x = around (metres at a reference radius 0.085), y = along (metres)
    Lt = 0.62
    Xc = Ag * 2 * math.pi * 0.085
    Yc = Ug * Lt
    circ = 2 * math.pi * 0.085
    light, deep, violet = (np.array(hexrgb(h)) for h in ("#9cc7e0", "#7e9ccc", "#7084bd"))
    cream, cream_sh = np.array(hexrgb("#ddd4c7")), np.array(hexrgb("#bdb6b2"))
    # base: lighter on the upper / outer side, deeper and violet toward the lower inner side
    upw = np.clip(nn[..., 2] * 0.5 + 0.5, 0, 1)
    c = deep[None, None, :] * (1 - upw[..., None]) + light[None, None, :] * upw[..., None]
    low = np.clip((0.4 - Ug) / 0.3, 0, 1) * np.clip(0.5 - nn[..., 2], 0, 1)
    c = c * (1 - low[..., None] * 0.6) + violet * (low[..., None] * 0.6)
    cr = np.zeros(Ug.shape, np.float32)      # cream mask
    lt = np.zeros(Ug.shape, np.float32)      # light streak mask
    gl = np.zeros(Ug.shape, np.float32)      # glow
    prng = random.Random(9)
    # cream flame swirls: rise along the tail with a sway around it and end in a curl
    for k in range(14):
        x0 = (k / 14.0 + prng.uniform(-0.025, 0.025)) * circ
        y0 = prng.uniform(0.08, 0.30) * Lt
        y1 = min(y0 + prng.uniform(0.18, 0.32) * Lt, 0.68 * Lt)
        sway = prng.uniform(-0.05, 0.05)
        pts = [(x0 + sway * math.sin(f * 2.4) + 0.02 * f, y0 + (y1 - y0) * f) for f in np.linspace(0, 1, 24)]
        d = 1 if prng.random() > 0.5 else -1
        rr = prng.uniform(0.014, 0.022)
        cen = (pts[-1][0] - d * rr, pts[-1][1])
        sp = spiral(cen, rr, prng.uniform(0.9, 1.3), 0.0 if d > 0 else math.pi, d, 1.0, 0.0, 40, 0.8)
        stroke = pts + sp
        wmax = prng.uniform(0.015, 0.024)
        widths = np.concatenate([np.linspace(0.002, wmax, 24), np.linspace(wmax * 0.8, 0.002, 40)])
        for off in (-circ, 0.0, circ):
            poly_paint(cr, Xc, Yc, [(x + off, y) for x, y in stroke], widths, 0.0012)
    # thin light streaks
    for k in range(14):
        x0 = prng.uniform(0, circ)
        y0 = prng.uniform(0.04, 0.3) * Lt
        y1 = y0 + prng.uniform(0.08, 0.2) * Lt
        pts = [(x0 + 0.01 * math.sin(f * 3), y0 + (y1 - y0) * f) for f in np.linspace(0, 1, 14)]
        for off in (-circ, 0.0, circ):
            poly_paint(lt, Xc, Yc, [(x + off, y) for x, y in pts], [0.001, 0.005, 0.004, 0.001], 0.0012)
    # glowing cyan swirls and dots in the lower third (both flanks: around v = 0 and v = 0.5)
    for k, x0 in enumerate([0.02, 0.48, 0.10, 0.56, 0.93]):
        xc = x0 * circ
        yc = prng.uniform(0.12, 0.30) * Lt
        sp = spiral((xc, yc), prng.uniform(0.012, 0.018), 1.3, prng.uniform(0, 6.28), 1 if k % 2 else -1, 1.0, 0.0, 40, 0.85)
        tail = [(xc - 0.03 + 0.03 * f, yc - 0.04 + 0.04 * f * f) for f in np.linspace(0, 1, 10)]
        stroke = tail + sp
        widths = np.concatenate([np.linspace(0.001, 0.005, 10), np.linspace(0.005, 0.0015, 40)])
        for off in (-circ, 0.0, circ):
            poly_paint(gl, Xc, Yc, [(x + off, y) for x, y in stroke], widths, 0.001, halo=0.3, halo_w=0.004)
    for k in range(26):
        xc = prng.choice([prng.uniform(-0.12, 0.14), prng.uniform(0.38, 0.62)]) * circ
        yc = prng.uniform(0.08, 0.36) * Lt
        r = prng.choice([0.0015, 0.002, 0.0025, 0.003])
        for off in (-circ, 0.0, circ):
            poly_paint(gl, Xc, Yc, [(xc + off, yc), (xc + off + 1e-4, yc)], [r * 2, r * 2], 0.0008, halo=0.35, halo_w=0.003)
    # cream tip: last part of the tail, jagged edge (lobes around the section)
    edge = 0.66 + 0.035 * np.sin(Ag * 2 * math.pi * 5 + 0.7) + 0.02 * np.sin(Ag * 2 * math.pi * 11 + 2.1)
    tipm = np.clip((Ug - edge) / 0.02 + 0.5, 0, 1)
    cr = np.maximum(cr, tipm)
    # cream on the outer / upper side of the upper plume (the back view's cream egg top, the side
    # view's cream outer curl), with a flame-jagged edge
    outer = nn[..., 1] * 0.55 + nn[..., 2] * 0.83
    thr = 0.42 + 0.14 * np.sin(Ag * 2 * math.pi * 4 + Ug * 23) + 0.06 * np.sin(Ag * 2 * math.pi * 9 + Ug * 41)
    zone = np.clip((outer - thr) / 0.05, 0, 1) * np.clip((Ug - 0.40) / 0.08, 0, 1)
    cr = np.maximum(cr, zone)
    # glowing dots where the blue meets the cream tip
    for k in range(18):
        xc = prng.uniform(0, circ)
        yc = (0.62 + prng.uniform(0.0, 0.08)) * Lt
        r = prng.choice([0.0015, 0.002, 0.003])
        for off in (-circ, 0.0, circ):
            poly_paint(gl, Xc, Yc, [(xc + off, yc), (xc + off + 1e-4, yc)], [r * 2, r * 2], 0.0008, halo=0.35, halo_w=0.0025)
    gl = gl * (1 - tipm * 0.9) * (1 - cr * 0.7)
    cream_col = cream[None, None, :] * (0.92 + 0.08 * upw[..., None]) + (cream_sh - cream)[None, None, :] * (1 - upw[..., None]) * 0.4
    c = c * (1 - lt[..., None] * 0.6) + np.array(hexrgb("#bfe6f6")) * (lt[..., None] * 0.6)
    c = c * (1 - cr[..., None]) + cream_col * cr[..., None]
    # flick blades: cream strip
    col = c.astype(np.float32)
    emi = np.zeros_like(col)
    emi[..., 0] = gl
    return new_image("AF_tail_col", W, H, col), new_image("AF_tail_emi", W, H, emi)


def build_tail(mat_holder):
    P, ru, rv = tail_path()
    placeholder = bpy.data.materials.new("M_tail_tmp")
    tail, grid = build_tail_mesh("Tail", P, ru, rv, 64, placeholder, ripple=0.025, seed=3)
    objs = [tail]
    rng = random.Random(41)
    for name, Q, th, width, f in tail_flicks(P, ru, rv, rng):
        # UVs of a flick sit on the tail's own atlas at its root (same colour as where it grows)
        o, _ = sweep(name, Q, th, width, 8, placeholder, hint=(1.0, 0.0, 0.0), uv_rect=(f, 0.70, min(f + 0.06, 0.999), 0.80))
        o["keep_uv"] = True
        objs.append(o)
    col_img, emi_img = tail_images(grid, len(objs) - 1)
    mat = tail_material(col_img, emi_img)
    for o in objs:
        o.data.materials[0] = mat
    bpy.data.materials.remove(placeholder)
    return objs


# ============================================================================ BODY ATTRIBUTES AND CREAM
def cream_field(p):
    x, y, z = p.x, p.y, p.z
    nz = 0.0016 * noise.noise(Vector((x * 90, y * 90, z * 90))) + 0.0012 * noise.noise(Vector((x * 260, y * 260, z * 260)))
    # head: below a line from the nose under the eye back to the cheek tufts
    zb = float(np.interp(y, [-0.25, -0.225, -0.205, -0.185, -0.165, -0.145, -0.125, -0.105, -0.09],
                         [0.301, 0.302, 0.305, 0.31, 0.311, 0.306, 0.298, 0.286, 0.273]))
    head = max(z - zb, y + 0.09, 0.248 - z)
    wb = 0.004 + 0.012 * min(1.0, max(0.0, (y + 0.24) / 0.05))
    bridge = max(abs(x) - wb, 0.3005 - z, y + 0.20)
    head = max(head, -bridge)
    # throat and chest front: cream in front of the boundary, within the bib, V point at Z 0.105
    yb = float(np.interp(z, [0.10, 0.13, 0.16, 0.20, 0.24, 0.28, 0.30], [-0.175, -0.165, -0.152, -0.138, -0.125, -0.11, -0.10]))
    wc = float(np.interp(z, [0.104, 0.115, 0.14, 0.18, 0.22, 0.26, 0.29, 0.30], [0.0, 0.010, 0.032, 0.046, 0.048, 0.05, 0.06, 0.06]))
    chest = max(y - yb, abs(x) - wc, 0.104 - z, z - 0.30)
    # belly underside and inner thighs
    belly = max(z - 0.152, 0.11 - z, y - 0.045, -0.115 - y, abs(x) - 0.032)
    # patch under the tail
    patch = max(abs(x) - 0.019, 0.118 - z, z - 0.195, 0.088 - y)
    return min(head, chest, belly, patch) + nz


def body_attributes(obj):
    co = verts_np(obj)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    set_attr(obj, "zh", z)
    face = smoothstep(-y, 0.14, 0.17) * smoothstep(z, 0.288, 0.318)
    set_attr(obj, "face", face)
    legs = smoothstep(0.14 - z, 0.0, 0.02)
    set_attr(obj, "legs", legs)
    set_attr(obj, "tan", smoothstep(0.17 - z, 0.0, 0.025) * smoothstep(y, -0.13, -0.09) * smoothstep(0.06 - y, 0.0, 0.02))
    set_attr(obj, "patch", smoothstep(y, 0.085, 0.11) * smoothstep(z, 0.12, 0.14) * smoothstep(0.022 - np.abs(x), 0.0, 0.008))
    set_attr(obj, "pys", (y - SIDE_Y0) / MARK_SPAN)
    set_attr(obj, "pzs", z / MARK_SPAN)
    set_attr(obj, "pxf", (x - FRONT_X0) / MARK_SPAN)


# ============================================================================ BUILD
def build():
    marks, decal = mark_images()
    m_fur = fur_material("M_fur", marks, decal, cream=False)
    m_cream = fur_material("M_fur_cream", marks, decal, cream=True)
    m_ear_out, m_ear_in = ear_materials(ear_image())
    m_blade = cream_blade_material()
    m_silver = silver_material()
    m_antler = antler_material()
    m_cord = cord_material()
    m_gem = gem_material()
    m_eye = eye_material()
    m_nose = dark_material("M_nose", "#2c2428", 0.3, "#544650")
    m_liner = dark_material("M_liner", "#1d2036", 0.45)

    body, clay = body_clay()
    surf, _ = clay.project(np.array([[0.0, -0.215, GEM_C[2]]]))
    GEM_C[1] = surf[0][1] - 0.0075
    kit.quad_remesh(body, 18000)
    close_holes(body)
    body.data.shade_smooth()
    body.data.materials.append(m_fur)
    kit.mark(body, cream_field, m_cream)
    close_holes(body)
    body_attributes(body)
    parts = [body]
    rng = random.Random(12)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        parts.append(build_ear(side, m_ear_out, m_ear_in, uoff))
        parts += ear_blades(side, m_blade, rng)
        parts.append(build_eye(clay, side, m_eye))
        parts.append(build_liner(clay, side, m_liner))
    parts.append(build_nose(m_nose))
    cords, front = build_cord(clay, m_cord)
    parts += cords
    parts += build_pendant(m_silver, m_gem, front)
    parts += build_antlers(clay, m_antler)
    parts += build_tail(None)
    return parts


if __name__ == "__main__":
    kit.run(build, texture=4096)
