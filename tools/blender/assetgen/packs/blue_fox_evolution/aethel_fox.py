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
    # --- neck and head (nose Y -0.24 Z 0.30, eye Z 0.318, crown Z 0.36, back of skull Y -0.10)
    clay.add(T([(0, -0.106, 0.205), (0, -0.136, 0.268), (0, -0.147, 0.313)], [0.044, 0.039, 0.037]), blend=0.025)
    clay.add(E((0, -0.154, 0.334), (0.062, 0.052, 0.042)), blend=0.02)       # cranium, crown Z 0.376 (side: forehead higher)
    clay.add(E((0, -0.176, 0.334), (0.040, 0.03, 0.024)), blend=0.015)       # brow / frontal plane
    clay.add(E((0.04, -0.172, 0.305), (0.035, 0.034, 0.029)), blend=0.016, mirror=True)  # cheeks
    clay.add(C((0, -0.183, 0.318), (0, -0.236, 0.307), 0.024, 0.008), blend=0.016)       # muzzle
    clay.add(C((0, -0.172, 0.293), (0, -0.226, 0.294), 0.020, 0.0065), blend=0.012)        # lower jaw (side: muzzle bottom lower)
    clay.add(E((0, -0.118, 0.304), (0.038, 0.036, 0.038)), blend=0.022)      # nape
    for s in (1, -1):                                                            # eye seats: a shallow bed for the eye lens
        clay.sub(E((s * EYE_X, -0.199, 0.327), (0.0135, 0.0018, 0.0095), rot=(0, s * -12, s * 30)), blend=0.004)
    # stop / bridge between the eyes: the forehead runs down into the muzzle in front of the eyes, so
    # from the side the far eye hides behind it (side drawing: only its lashes show at the profile)
    clay.add(E((0, -0.199, 0.326), (0.012, 0.011, 0.017)), blend=0.010)
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
        # (no nape locks: the side view's neck is smooth behind the ears)
        # elbow tufts at the back of the front legs (side view z 0.10-0.13)
        clay.add(C((s * 0.034, -0.10, 0.14), (s * 0.036, -0.082, 0.112 + rng.uniform(-0.004, 0.004)), 0.0095, 0.0012), blend=0.006)
        # belly fringe: small locks swept back along the chest-belly edge (serrated, not bumps)
        for k in range(2):
            y = -0.075 + k * 0.035 + rng.uniform(-0.005, 0.005)
            clay.add(C((s * 0.03, y, 0.152), (s * 0.031, y + 0.024, 0.141 + rng.uniform(-0.004, 0.003)), 0.0065, 0.001), blend=0.006)
        # ruff locks along the chest side, swept down and back
        for z, l in [(0.20, 0.024), (0.178, 0.028), (0.155, 0.026)]:
            clay.add(C((s * 0.038, -0.150, z), (s * (0.050 + rng.uniform(0, 0.006)), -0.150 + rng.uniform(-0.004, 0.006), z - l), 0.0085, 0.0012), blend=0.006)
    # chest ruff spikes: V point at Z 0.105 between the front legs (front view)
    for x, z0, z1, r in [(0.0, 0.15, 0.104, 0.015), (0.017, 0.152, 0.116, 0.012), (-0.018, 0.153, 0.118, 0.0115),
                         (0.033, 0.16, 0.13, 0.010), (-0.032, 0.161, 0.128, 0.0105)]:
        clay.add(C((x, -0.160, z0), (x * 1.05, -0.152, z1), r, 0.0012), blend=0.006)
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
    for s in (1, -1):    # W smile under the nose
        poly_paint(decal[..., 2], Xf, Zf, bez2((0.0, 0.2990), (s * 0.004, 0.2955), (s * 0.009, 0.2950), (s * 0.016, 0.2995)),
                   [0.0015, 0.0013, 0.0013, 0.0007], 1.5 * px)
    poly_paint(decal[..., 2], Xf, Zf, [(0.0, 0.3035), (0.0, 0.2985)], [0.0013, 0.0013], 1.5 * px)
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
    co = nt.sep(nt.coords("Object"))
    mirrored = nt.combine(nt.math("ABSOLUTE", co[0]), co[1], co[2])
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
            base = nt.ramp(t, [(0.0, "#87abc4"), (0.5, "#93bad0"), (0.72, "#8cb0cc"), (0.84, "#7090b6"), (1.0, "#566f9b")])   # navy tip
            sv = nt.ramp(strk, [(0.3, (0.92, 0.93, 0.95, 1)), (0.7, (1.07, 1.06, 1.04, 1))])
            base = nt.mix(1.0, base, sv, "MULTIPLY")
            base = nt.mix(nt.math("MULTIPLY", rim, 0.75), base, lin("#647ea6"))
            glow = nt.math("MULTIPLY", ch[0], 0.0)
            rough = nt.math("ADD", nt.math("MULTIPLY", strk, 0.12), 0.74)
        emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3aa8d8"), (1.0, "#b0f2ff")])
        set_bsdf(nt, bsdf, base=base, rough=rough, emis_col=emis, emis_str=0.9, normal=nt.bump(strk, 0.25, 0.0006))
        out.append(mat)
    return out


def ear_tuft_material():
    mat, tree, bsdf = kit.principled("M_ear_tuft")
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
    sclera = nt.ramp(yf, [(0.0, "#cfcac4"), (0.3, "#d9d4ce"), (0.62, "#cdc8c3"), (0.82, "#a9a6ad"), (1.0, "#77768a")])
    duct = nt.maprange(x, -EYE_A * 0.95, -EYE_A * 0.6)                           # tear duct: inner corner warmer
    sclera = nt.mix(nt.math("MULTIPLY", duct, 0.6), sclera, lin("#c9b7b2"))
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


def dark_material(name, hexcol, rough, hi="#4a4458"):
    mat, tree, bsdf = kit.principled(name)
    nt = NT(tree)
    nz = nt.noise(nt.coords("Object"), 400.0, 3, 0.5)
    base = nt.ramp(nz, [(0.3, hexcol), (0.7, hi)])
    set_bsdf(nt, bsdf, base=base, rough=nt.math("ADD", nt.math("MULTIPLY", nz, 0.15), rough), normal=nt.bump(nz, 0.2, 0.0002))
    return mat


def tail_material(col_img, emi_img):
    """The tail's fur: the painted atlas (blue, cream flames, glowing swirls, cream tip) on every lock,
    each lock darker and bluer at its root and lighter at its tip (guard hairs lighten toward the
    ends, the underfur between them stays dark), strand grooves running along each lock, the lock's
    edges a little darker where it overlaps the next, per-lock tone variation."""
    mat, tree, bsdf = kit.principled("M_tail")
    nt = NT(tree)
    uv = nt.node("ShaderNodeUVMap", uv_map=kit.UV_LAYER).outputs[0]
    ci = nt.image(col_img, uv)
    ci.extension = "REPEAT"
    ei = nt.image(emi_img, uv)
    ei.extension = "REPEAT"
    col = ci.outputs["Color"]
    emi = nt.rgb_sep(ei.outputs["Color"])
    ft, fw, fid = nt.attr("fur_t"), nt.attr("fur_w"), nt.attr("fur_id")
    # cream locks (fur_cream): warm cream, a little cooler and greyer toward the root
    creamc = nt.ramp(ft, [(0.0, "#b9b6bd"), (0.45, "#d8d0c4"), (1.0, "#e6dfd3")])
    col = nt.mix(nt.attr("fur_cream"), col, creamc)
    # strands: fine noise stretched along the lock (across: fur_w, along: fur_t), offset per lock
    strand = nt.noise(nt.combine(nt.math("ADD", nt.math("MULTIPLY", fw, 9.0), nt.math("MULTIPLY", fid, 37.0)),
                                 nt.math("MULTIPLY", ft, 0.7), fid), 3.0, 3, 0.55)
    groove = nt.math("ABSOLUTE", nt.math("SINE", nt.math("ADD", nt.math("MULTIPLY", fw, 7.5), nt.math("MULTIPLY", fid, 6.0))))
    strk = nt.noise(nt.scale_vec(uv, 160, 12, 1), 1.0, 4, 0.6)
    sv = nt.ramp(strk, [(0.3, (0.93, 0.94, 0.96, 1)), (0.5, (1, 1, 1, 1)), (0.7, (1.05, 1.04, 1.03, 1))])
    col = nt.mix(1.0, col, sv, "MULTIPLY")
    # root dark and bluer, tip light
    rt = nt.ramp(ft, [(0.0, (0.62, 0.68, 0.82, 1)), (0.25, (0.86, 0.89, 0.95, 1)), (0.6, (1, 1, 1, 1)), (1.0, (1.12, 1.11, 1.08, 1))])
    col = nt.mix(1.0, col, rt, "MULTIPLY")
    edge = nt.maprange(nt.math("ABSOLUTE", fw), 0.55, 1.0, 1.0, 0.82)
    st = nt.maprange(strand, 0.35, 0.65, 0.9, 1.08)
    shade = nt.math("MULTIPLY", nt.math("MULTIPLY", edge, st), nt.maprange(groove, 0.0, 0.5, 0.93, 1.0))
    col = nt.mix(1.0, col, nt.combine(shade, shade, shade), "MULTIPLY")
    tone = nt.maprange(fid, 0.0, 1.0, 0.95, 1.05, smooth=False)
    col = nt.mix(1.0, col, nt.combine(tone, tone, tone), "MULTIPLY")
    glow = emi[0]
    col = nt.mix(nt.math("MULTIPLY", glow, 0.85), col, lin("#c9f4ff"))
    emis = nt.ramp(glow, [(0.0, "#000000"), (0.3, "#3fb4ea"), (1.0, "#b8f2ff")])
    ao = nt.node("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.02
    col = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.45, 0.0, 0.5), col, lin("#3e4c78"))
    rough = nt.math("ADD", nt.math("MULTIPLY", strand, 0.14), nt.maprange(ft, 0.0, 1.0, 0.82, 0.66))
    height = nt.math("ADD", nt.math("MULTIPLY", groove, 0.6), nt.math("MULTIPLY", strand, 0.4))
    set_bsdf(nt, bsdf, base=col, rough=rough, emis_col=emis, emis_str=1.4, normal=nt.bump(height, 0.35, 0.0012))
    return mat


# ============================================================================ EARS
def ear_shape(side):
    """Leaf-shaped ear frame for side +1 (+X) or -1: base B, axis a, bowl normal f, width w, length L."""
    j = 0.002 * side
    B = np.array([side * 0.044, -0.155, 0.341])
    # (cycle 2: tips 0.013 higher, 0.006 forward, 0.004 more splay: side drawing ear tip / tail top
    # 0.95, back drawing's ears wider)
    Tp = np.array([side * (0.104 + j), -0.156 + 0.003 * side, 0.458 - abs(j)])   # side: tips ~0.90 of the tail top; front wants taller (views disagree)
    L = float(np.linalg.norm(Tp - B))
    a = (Tp - B) / L
    f0 = np.array([side * 0.45, -1.0, 0.10])
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
        D = 0.027 * (1 - t) ** 0.6   # deep cone: the far ear keeps its width seen edge-on
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


def build_ear_tufts(side, mat, rng):
    """The ear tufts: cream fur locks at the inner base of the ear, fanning up out of the bowl (4-5, each different)."""
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
        o, _ = sweep(f"ear_tuft_{side}_{k}", P, th, width, 8, mat, hint=np.tile(f, (14, 1)), uv_rect=(0, 0, 1, 1))
        o["keep_uv"] = True
        objs.append(o)
    return objs


# ============================================================================ EYES, NOSE
# The eye of an anime-style fox, measured on the front and side drawings (cycle 2): the opening is
# 0.029 long and 0.021 tall (front: 60 x 53 px seen obliquely, side: 59 x 41 px), its long axis
# rising 20 deg from the low, pointed inner corner (tear duct) to the higher outer corner, which the
# upper eyelid line carries on into a wing. A big grey iris (0.016 x 0.020, upper lid over its top)
# sits toward the nose, the warm grey eye white shows behind it, a white catch light on the pupil's
# upper inner side. Upper eyelid line thick, lower eyelid line thin, both run the whole opening.
EYE_A, EYE_BT, EYE_BB = 0.0135, 0.0108, 0.0084   # opening half-length, upper and lower half-height
EYE_TILT = 20.0                                   # deg, outer corner up
IRIS_C = (-0.0036, 0.0004)                        # iris centre in the eye (x outward, y up)
IRIS_R = (0.0082, 0.0097)                         # iris half-width, half-height
EYE_X = 0.0278                                    # eye centre X (pre-scale), projected on the head
EYE_TURN = 0.25                                   # how far the eye normal turns outward from the face normal
EYE_DOME = 0.0012                                 # lens dome height at the centre


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
    y = np.where(top, y * (1 - 0.15 * np.clip(-c, 0, 1)) + 0.9 * EYE_BT * s_ * np.clip(c, 0, 1) * (1 - c * c), y) - 0.0026 * np.clip(-c, 0, 1) ** 2 + 0.0008 * np.clip(c, 0, 1) ** 2
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
    pts += [(EYE_A * 1.14, EYE_BT * 0.13), (EYE_A * 1.30, EYE_BT * 0.25), (EYE_A * 1.46, EYE_BT * 0.35), (EYE_A * 1.60, EYE_BT * 0.43)]
    tt = np.linspace(0, 1, len(pts))
    rv = 0.00045 + 0.00135 * np.sin(np.clip(tt * 1.12, 0, 1) * math.pi * 0.92) ** 0.55
    rv[-5:] = [0.0016, 0.0013, 0.0009, 0.00045, 0.0]
    # lower eyelid: from the outer corner along the bottom to the tear duct
    th2 = np.linspace(-0.05, -math.pi - 0.12, 26)
    bx2, by2 = eye_opening(th2)
    pts2 = [(x * 1.01, y * 1.02 - 0.0002) for x, y in zip(bx2, by2)]
    t2 = np.linspace(0, 1, len(pts2))
    rv2 = 0.00028 + 0.00012 * np.sin(t2 * math.pi) + 0.00045 * t2 ** 4
    rv2[0] = 0.0
    for part, pp, rr in (("upper", pts, rv), ("lower", pts2, rv2)):
        X = np.array([q[0] for q in pp])
        Y = np.array([q[1] for q in pp])
        k = np.array([float(np.hypot(x / EYE_A, y / (EYE_BT if y > 0 else EYE_BB))) for x, y in zip(X, Y)])
        hb = bed.body_h(X, Y)
        hl = np.where(k < 1.35, bed.lens_h(X, Y), -1.0)
        ru = np.asarray(rr) * 0.5
        h = np.maximum(hb, hl) + ru * 0.6 + 0.00015
        P = bed.point(X, Y, h)
        o, _ = sweep(f"eyelid_{part}_{name}", P, ru, np.asarray(rr), 8, mat, hint=np.tile(bed.n, (len(P), 1)))
        out.append(o)
    return out


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
    ring = np.stack([0.05 * np.sin(ang), -0.141 - 0.05 * np.cos(ang), 0.239 - 0.049 * np.cos(ang)], 1)   # neck moved back 0.012
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
    k = 2.0     # 240 rings: 7 per twist, enough for round strands
    idx = np.arange(int(n * k)) / k
    i0 = np.floor(idx).astype(int) % n
    i1 = (i0 + 1) % n
    tt = (idx - np.floor(idx))[:, None]
    P = C_[i0] * (1 - tt) + C_[i1] * tt
    NN = Nn[i0] * (1 - tt) + Nn[i1] * tt
    BB = Bn[i0] * (1 - tt) + Bn[i1] * tt
    length = float(np.linalg.norm(np.diff(np.concatenate([C_, C_[:1]]), axis=0), axis=1).sum())
    twists = round(length / 0.011)
    s = np.arange(int(n * k)) / int(n * k)
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
    # gem: the BlendKit cabochon's dome (round cabochon, flat back), else a procedural dome
    o = blendkit_cabochon(m_gem, gc, ex, ez, -ny)
    if o is None:
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


BLENDKIT_CABOCHON = "c8aac119-f6bb-4648-8cb2-10cdd6e63d18"   # "Gem Turquoise Cabochon Round", royalty_free, free plan


def blendkit_cabochon(m_gem, gc, ex, ez, out, radius=0.0128, height=0.0068):
    """The pendant gem from BlendKit's free round cabochon (licence royalty_free, checked at run
    time): only its geometry is used (a smooth dome with a flat back and a girdle), scaled to the
    reference gem (0.0256 m across, 0.0068 m high), facing ``out`` from the bezel; its turquoise
    material is replaced by the deep-blue gem shader and its UVs by a planar map across the face.
    Returns None when BlendKit is unavailable, so the build falls back to a procedural dome."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "plugins" / "blendkit"))
        import headless
        headless.enable()
        asset = headless.asset(BLENDKIT_CABOCHON)
        if asset.get("license") not in ("royalty_free", "cc_zero"):
            print(f"BLENDKIT cabochon licence {asset.get('license')!r} not usable: procedural gem")
            return None
        appended = headless.append(asset)
    except Exception as exc:   # no login, no network, no add-on
        print(f"BLENDKIT cabochon unavailable ({exc}): procedural gem")
        return None
    src = next((o for o in appended if o.type == "MESH"), None)
    if src is None:
        return None
    co = np.array([src.matrix_world @ v.co for v in src.data.vertices])
    polys = [tuple(p.vertices) for p in src.data.polygons]
    for o in appended:
        mats = list(o.data.materials) if o.type == "MESH" else []
        bpy.data.objects.remove(o, do_unlink=True)
        for m in mats:
            if m is not None and m.users == 0:
                bpy.data.materials.remove(m)
    c = co.mean(0)
    ext = co.max(0) - co.min(0)
    ax = int(np.argmin(ext))                    # the thin axis is the dome's height
    others = [i for i in range(3) if i != ax]
    h = co[:, ax] - co[:, ax].min()
    h /= h.max()
    r = np.linalg.norm(co[:, others] - c[others], axis=1)
    if r[h > 0.9].mean() > r[h < 0.1].mean():   # dome on the low side: flip
        h = 1.0 - h
    lx = (co[:, others[0]] - c[others[0]]) / (ext[others[0]] / 2)
    lz = (co[:, others[1]] - c[others[1]]) / (ext[others[1]] / 2)
    bm = bmesh.new()
    verts = [bm.verts.new(Vector(gc + ex * radius * x + ez * radius * z + out * (height * hh - 0.0004)))
             for x, z, hh in zip(lx, lz, h)]
    uvl = bm.loops.layers.uv.new("UVMap")
    for poly in polys:
        try:
            f = bm.faces.new([verts[i] for i in poly])
        except ValueError:
            continue
        for lp in f.loops:
            i = lp.vert.index
            lp[uvl].uv = (0.5 + 0.5 * lx[i], 0.5 + 0.5 * lz[i])
    bm.verts.index_update()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    print(f"BLENDKIT cabochon used: {asset['name']} ({asset['license']}), {len(bm.faces)} faces")
    return kit.mesh_object("Gem", bm, m_gem)


def antler_defs(clay, side, rng):
    """Branch centre lines (N,3) and root/tip radii for one side's antler: a beam from beside the
    pendant up along the chest side over the shoulder, with tines out, up and back."""
    s = side
    j = lambda a=0.004: rng.uniform(-a, a)
    gc = GEM_C
    beam_ctrl = np.array([(s * 0.013, gc[1] + 0.004, gc[2] - 0.004), (s * 0.03, -0.178, 0.181), (s * 0.05, -0.163, 0.199),
                          (s * 0.064, -0.138, 0.214), (s * 0.072, -0.110, 0.226), (s * 0.074, -0.084, 0.235 + j(0.003))])   # chest / back moved
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
            o, _ = sweep(f"Antler_{side}_{kind}_{k}", P, rr, rr, 10, mat, hint=(0, 0, 1),
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
def smooth1d(a, sigma):
    """Gaussian smoothing of a 1D profile with the end values held (no kinks at the knots)."""
    a = np.asarray(a, float)
    k = int(3 * sigma)
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
    w /= w.sum()
    pad = np.concatenate([np.full(k, a[0]), a, np.full(k, a[-1])])
    out = np.convolve(pad, w, mode="valid")
    out[0], out[-1] = a[0], a[-1]
    return out


def tail_path():
    """Centre line (Y, Z at X 0) of the plume, fitted in numbers to the side view's outline rows in
    the kit camera's normalised frame (work/tailfit2.py + tailopt.py: every row within 0.01 of the
    reference, plume top 1.15 x the ear tips, background kept under the plume): the root on the rump, a fat lower plume that hangs
    back to Y 0.23, the upper part bending back into a thick curl and tapering to the cream tip at
    Y 0.335 Z 0.34. Radii: ru across (X), rb toward +B (back / down / inside of the curl), rf toward
    -B (front / up). Profiles smoothed so the surface has no rings at the knots."""
    cps = np.array([(0.1100, 0.1990), (0.1180, 0.2380), (0.1320, 0.2750), (0.1320, 0.3160), (0.1260, 0.3570), (0.1400, 0.3940), (0.1720, 0.4220), (0.2090, 0.4230), (0.2350, 0.4140), (0.2510, 0.3920), (0.2850, 0.3700), (0.3280, 0.3480)])   # (cycle 2: tip end raised 0.02)
    P2 = catmull(cps, 16)
    P = np.stack([np.zeros(len(P2)), P2[:, 0], P2[:, 1]], 1)
    tt = np.linspace(0, 1, len(P))
    tk = [0, 0.06, 0.14, 0.25, 0.36, 0.47, 0.58, 0.68, 0.78, 0.88, 0.95, 1.0]
    # (cycle 2: the cream tip fatter toward its end; the lower plume fuller in front (rf); X kept: wider
    # showed the tail beside the body in the front view)
    rb = np.interp(tt, tk, [0.034, 0.066, 0.0746, 0.0722, 0.0684, 0.066, 0.0596, 0.0476, 0.035, 0.026, 0.012, 0.0])
    rf = np.interp(tt, tk, [0.03, 0.047, 0.071, 0.0808, 0.0882, 0.074, 0.054, 0.0394, 0.031, 0.024, 0.016, 0.0])
    ru = np.interp(tt, tk, [0.03, 0.0648, 0.0835, 0.0942, 0.0965, 0.08, 0.07, 0.0536, 0.038, 0.028, 0.018, 0.0])
    ru, rb, rf = (np.maximum(smooth1d(r, 4.0), 0.0) for r in (ru, rb, rf))
    ru[-1] = rb[-1] = rf[-1] = 0.0
    return P, ru, rb, rf


def build_tail_mesh(name, P, ru, rb, rf, M, mat, ripple=0.035, nflutes=9, seed=0):
    """Swept plume with fur-lock flutes and an asymmetric section (rb toward +B, rf toward -B): the
    radius ripples around the section (nflutes lobes whose phase drifts along the tail) and the
    ripple fades at the root and the tip. UVs u along, v around (v = 0 on the +X side). Normals of
    the grid come from the surface itself (for painting the atlas by facing)."""
    rng = np.random.default_rng(seed)
    P = np.asarray(P, float)
    n = len(P)
    T, N, B = frames(P, (1.0, 0.0, 0.0))
    tt = np.linspace(0, 1, n)
    ang = np.arange(M) / M * 2 * math.pi
    fade = np.clip(tt / 0.12, 0, 1) * np.clip((1 - tt) / 0.15, 0, 1)
    drift = smooth1d(np.cumsum(rng.normal(0, 0.03, n)), 3.0)
    rip = 1 + ripple * fade[:, None] * (np.sin(nflutes * ang[None, :] + drift[:, None] + 2.0 * tt[:, None])
                                        + 0.4 * np.sin(2 * nflutes * ang[None, :] + 1.3 + drift[:, None] * 2))
    sa = np.sin(ang)
    rv = np.where(sa[None, :] > 0, rb[:, None], rf[:, None])
    rings = P[:, None, :] + N[:, None, :] * (ru[:, None] * rip * np.cos(ang))[..., None] + B[:, None, :] * (rv * rip * sa[None, :])[..., None]
    di = np.gradient(rings, axis=0)
    dj = np.roll(rings, -1, axis=1) - np.roll(rings, 1, axis=1)
    nrm = np.cross(dj, di)
    outward = rings - P[:, None, :]
    flip = (nrm * outward).sum(-1) < 0
    nrm[flip] *= -1
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-12
    nrm[-1] = T[-1]
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
    centre = rings.mean(axis=1)
    Lt = float(np.linalg.norm(np.diff(centre, axis=0), axis=1).sum())
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
    # side view: 5-6 wide S-shaped cream bands rising from the lower plume, each ending in a curl of
    # its own size and turn; flame-pointed starts (narrow) and the widest part before the curl
    for k in range(12):
        x0 = (k / 12.0 + prng.uniform(-0.02, 0.02)) * circ
        y0 = prng.uniform(0.04, 0.22) * Lt
        y1 = min(y0 + prng.uniform(0.26, 0.42) * Lt, 0.64 * Lt)
        sway = prng.uniform(0.03, 0.07) * (1 if k % 2 else -1)
        pts = [(x0 + sway * math.sin(f * 2.6 + 0.4), y0 + (y1 - y0) * f) for f in np.linspace(0, 1, 28)]
        d = 1 if prng.random() > 0.5 else -1
        rr = prng.uniform(0.018, 0.03)
        cen = (pts[-1][0] - d * rr, pts[-1][1])
        sp = spiral(cen, rr, prng.uniform(1.0, 1.45), 0.0 if d > 0 else math.pi, d, 1.0, 0.0, 44, 0.8)
        stroke = pts + sp
        wmax = prng.uniform(0.02, 0.032)
        widths = np.concatenate([np.linspace(0.0015, wmax, 28) ** 1.0, np.linspace(wmax * 0.75, 0.0025, 44)])
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
    # pale cyan leaf-shaped highlights on the front / upper side of the plume (around v = 0.75)
    for k in range(7):
        xc = (0.75 + prng.uniform(-0.17, 0.17)) * circ
        y0 = prng.uniform(0.2, 0.5) * Lt
        ln = prng.uniform(0.05, 0.09)
        pts = [(xc + 0.012 * math.sin(f * 2.0), y0 + ln * f) for f in np.linspace(0, 1, 12)]
        w = prng.uniform(0.008, 0.013)
        for off in (-circ, 0.0, circ):
            poly_paint(lt, Xc, Yc, [(x + off, y) for x, y in pts], [0.001, w * 0.8, w, w * 0.7, 0.001], 0.0012)
    # cream jagged strokes on the lower back edge (v ~0.25), where the lower flicks grow
    for k, (u0, u1) in enumerate([(0.03, 0.16), (0.08, 0.24), (0.15, 0.32)]):
        xc = (0.25 + prng.uniform(-0.05, 0.05)) * circ
        pts = [(xc + 0.01 * math.sin(f * 3 + k), (u0 + (u1 - u0) * f) * Lt) for f in np.linspace(0, 1, 14)]
        poly_paint(cr, Xc, Yc, pts, [0.002, 0.012, 0.014, 0.008, 0.001], 0.0012)
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
    edge = 0.62 + 0.035 * np.sin(Ag * 2 * math.pi * 5 + 0.7) + 0.02 * np.sin(Ag * 2 * math.pi * 11 + 2.1)
    tipm = np.clip((Ug - edge) / 0.02 + 0.5, 0, 1)
    cr = np.maximum(cr, tipm)
    # cream on the outer / upper side of the upper plume (the back view's cream egg top, the side
    # view's cream outer curl), with a flame-jagged edge
    outer = nn[..., 1] * 0.8 + nn[..., 2] * 0.6      # facing back / up: the curl's outer side, not the plume's front
    thr = 0.45 + 0.14 * np.sin(Ag * 2 * math.pi * 4 + Ug * 23) + 0.06 * np.sin(Ag * 2 * math.pi * 9 + Ug * 41)
    zone = np.clip((outer - thr) / 0.05, 0, 1) * np.clip((Ug - 0.48) / 0.08, 0, 1)
    cr = np.maximum(cr, zone)
    # glowing dots on the blue underside of the curl (inside of the bend, +B side: v 0.1..0.4)
    for k in range(18):
        xc = prng.uniform(0.1, 0.4) * circ
        yc = (0.52 + prng.uniform(0.0, 0.14)) * Lt
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
    return new_image("AF_tail_col", W, H, col), new_image("AF_tail_emi", W, H, emi), cr


TAIL_TIP_CURL = 14.0     # past the end the tip's centre line bends up (Z += k * over^2): the hook
TAIL_ROOT_RHO = 0.90     # lock roots lie at this fraction of the fur radius
TAIL_UNDER = 0.92        # underfur radius as a fraction of the fur radius


class TailBody:
    """The tail's path and its fur volume: P (centre line over the tail bone), frames, the outer fur
    radii (ru across X, rb toward +B, rf toward -B) and the arc-length fraction s of every sample.
    surface(s, a, rho) = a point at arc fraction s, angle a around the tail (0 = +X side) and rho x
    the outer fur radius; past s = 1 the centre line runs on along the curled tip."""

    def __init__(self):
        self.P, self.ru, self.rb, self.rf = tail_path()
        self.T, self.N, self.B = frames(self.P, (1.0, 0.0, 0.0))
        d = np.linalg.norm(np.diff(self.P, axis=0), axis=1)
        self.L = float(d.sum())
        self.s = np.concatenate([[0], np.cumsum(d)]) / self.L
        self.idx = np.arange(len(self.P))

    def _at(self, arr, s):
        fi = np.interp(np.clip(s, 0, 1), self.s, self.idx)
        i0 = np.clip(np.floor(fi).astype(int), 0, len(self.P) - 2)
        t = fi - i0
        return arr[i0] * (1 - t) + arr[i0 + 1] * t if np.ndim(arr) == 1 else arr[i0] * (1 - t)[..., None] + arr[i0 + 1] * t[..., None]

    def surface(self, s, a, rho):
        s, a, rho = (np.asarray(v, float) for v in np.broadcast_arrays(s, a, rho))
        P, N, B, T = (self._at(v, s) for v in (self.P, self.N, self.B, self.T))
        ru, rb, rf = (self._at(v, s) for v in (self.ru, self.rb, self.rf))
        sa, ca = np.sin(a), np.cos(a)
        rv = np.where(sa > 0, rb, rf)
        over = np.clip(s - 1.0, 0, None) * self.L          # the curled tip runs on past the end
        P = P + T * over[..., None] + np.array([0.0, 0.0, 1.0]) * (TAIL_TIP_CURL * over ** 2)[..., None]
        return P + (N * (ru * ca * rho)[..., None] + B * (rv * sa * rho)[..., None])

    def radius(self, s, a):
        ru, rb, rf = (self._at(v, s) for v in (self.ru, self.rb, self.rf))
        rv = np.where(np.sin(a) > 0, rb, rf)
        return np.sqrt((ru * np.cos(a)) ** 2 + (rv * np.sin(a)) ** 2)


def tail_fur_lock_specs(rng):
    """The guard-hair locks of the tail, layered root to tip (each layer's roots lie under the
    locks of the layer before, the way fur grows toward the tip): (s0, s1, a0, twist, sway, width,
    thickness, tip lift, tip hook). Layers interleave like bricks; every lock its own length, width,
    twist and lift."""
    specs = []
    layers = [  # s0 range, s1 range, count, width range (m), twist
        ((0.00, 0.05), (0.30, 0.42), 12, (0.060, 0.078), 0.35),
        ((0.13, 0.22), (0.47, 0.60), 13, (0.062, 0.080), 0.30),
        ((0.34, 0.44), (0.68, 0.80), 12, (0.054, 0.072), 0.25),
        ((0.55, 0.64), (0.86, 0.96), 10, (0.044, 0.060), 0.20),
        ((0.72, 0.80), (1.00, 1.045), 4, (0.045, 0.060), 0.15),
    ]
    for li, ((a0_, a1_), (b0_, b1_), cnt, (w0, w1), tw) in enumerate(layers):
        for k in range(cnt):
            a0 = 2 * math.pi * (k + 0.5 * (li % 2) + rng.uniform(-0.25, 0.25)) / cnt
            s0 = rng.uniform(a0_, a1_)
            s1 = rng.uniform(b0_, b1_)
            # S flow: every lock bows one way over its lower half and back over its upper half
            specs.append(dict(s0=s0, s1=s1, a0=a0, twist=tw * rng.uniform(0.6, 1.3),
                              sway=rng.uniform(-0.12, 0.12), s_flow=rng.uniform(0.18, 0.32),
                              width=rng.uniform(w0, w1),
                              thick=rng.uniform(0.008, 0.012) * (1.0 - 0.3 * li / 4),
                              lift=rng.uniform(0.005, 0.02), hook=rng.uniform(-0.2, 0.2), layer=li))
    # locks that stand out of the outline: three on the lower back edge behind the rump (side
    # drawing's points), three along the top edge of the cream crown, one under the curled tip
    for s0, s1, a0, lift, w in [(0.04, 0.33, 1.45, 0.16, 0.040), (0.10, 0.40, 1.75, 0.2, 0.038),
                                (0.17, 0.46, 1.25, 0.15, 0.036), (0.50, 0.74, -1.35, 0.12, 0.034),
                                (0.56, 0.80, -1.65, 0.13, 0.032), (0.62, 0.86, -1.95, 0.10, 0.03),
                                (0.70, 1.02, 1.6, 0.08, 0.03)]:
        specs.append(dict(s0=s0, s1=s1, a0=a0, twist=0.15, sway=rng.uniform(-0.1, 0.1), s_flow=0.12, width=w,
                          thick=0.008, lift=lift, hook=rng.uniform(-0.2, 0.2), layer=5))
    return specs


def build_tail_fur_lock(name, body, sp, lock_id, mat, n=22, K=10, cream=None):
    """One lock of guard hair: a clump that lies on the tail from its root (buried in the underfur)
    to its pointed tip, wrapping the tail's curve (its section is laid out in angle and radius, so it
    hugs the round form), widest a third of the way, tapering to a point; the tip lifts off the
    fur and hooks a little. UVs sample the tail atlas where the lock lies; fur_t (root 0 -> tip 1),
    fur_w (-1..1 across) and fur_id carry the root-to-tip shading and strand grooves."""
    t = np.linspace(0, 1, n)
    s = sp["s0"] + (sp["s1"] - sp["s0"]) * t
    a = (sp["a0"] + sp["twist"] * t + sp["sway"] * np.sin(math.pi * t) + sp["s_flow"] * np.sin(2 * math.pi * t)
         + sp["hook"] * np.clip((t - 0.8) / 0.2, 0, 1) ** 2)
    rho = TAIL_ROOT_RHO + 0.11 * t ** 0.9 + sp["lift"] * np.clip((t - 0.72) / 0.28, 0, 1) ** 2
    # a clump of hair: full from the root, widest a third of the way, then drawn to a point
    w = sp["width"] * (0.7 + 0.3 * np.sin(np.clip(t / 0.35, 0, 1) * math.pi / 2)) * np.clip(1 - t, 0, 1) ** 0.9
    th = sp["thick"] * (0.75 + 0.25 * np.clip(t / 0.3, 0, 1)) * np.clip(1 - t, 0, 1) ** 0.5
    r_loc = np.maximum(body.radius(s, a), 0.012)
    over = s > 1.0
    phi = np.arange(K) / K * 2 * math.pi
    cph, sph = np.cos(phi), np.sin(phi)
    # section: across the lock in angle (half-width / local radius), out of the fur in radius;
    # the upper face domed, the underside flatter (a clump of hair lies flat on the hair below)
    da = (0.5 * w / r_loc)[:, None] * cph[None, :]
    dr = (th / r_loc)[:, None] * np.where(sph > 0, 0.5 * sph, 0.25 * sph)[None, :]
    S_ = np.repeat(s[:, None], K, 1)
    A_ = a[:, None] + da
    R_ = rho[:, None] + dr
    pts = body.surface(S_, A_, R_)
    # past the end of the tail the fur volume is gone: spread the tip locks around the centre line
    if over.any():
        off = (np.cos(a) * 0.006)[:, None, None] * body._at(body.N, np.ones(n))[:, None, :] \
            + (np.sin(a) * 0.006)[:, None, None] * body._at(body.B, np.ones(n))[:, None, :]
        width_vec = (np.cos(a + math.pi / 2)[:, None] * body._at(body.N, np.ones(n))
                     + np.sin(a + math.pi / 2)[:, None] * body._at(body.B, np.ones(n)))
        norm_vec = (np.cos(a)[:, None] * body._at(body.N, np.ones(n)) + np.sin(a)[:, None] * body._at(body.B, np.ones(n)))
        alt = body.surface(s, a, np.zeros(n))[:, None, :] + off \
            + width_vec[:, None, :] * (0.5 * w[:, None] * cph[None, :])[..., None] \
            + norm_vec[:, None, :] * (th[:, None] * 0.5 * sph[None, :])[..., None]
        blend = np.clip((s - 0.97) / 0.03, 0, 1)[:, None, None]
        pts = pts * (1 - blend) + alt * blend
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    lt = bm.verts.layers.float.new("fur_t")
    lw = bm.verts.layers.float.new("fur_w")
    li = bm.verts.layers.float.new("fur_id")
    lc = bm.verts.layers.float.new("fur_cream")
    # cream locks: where the lock's middle line runs into a cream flame of the painted atlas the whole
    # lock turns cream from there to its tip (a flame is a cream lock, not a stripe across blue ones)
    fc = np.zeros(n)
    if cream is not None:
        Hc, Wc = cream.shape
        ui = np.clip((np.clip(s, 0, 0.998) * Wc).astype(int), 0, Wc - 1)
        vi = np.clip((((a / (2 * math.pi)) % 1.0) * Hc).astype(int), 0, Hc - 1)
        raw = cream[vi, ui] * np.clip((t - 0.12) / 0.2, 0, 1)
        fc = np.clip((np.maximum.accumulate(smooth1d(raw, 1.5)) - 0.45) / 0.3, 0, 1)   # only clear flames
    vs = []
    for i in range(n - 1):
        row = []
        for j in range(K):
            v = bm.verts.new(Vector(pts[i, j]))
            v[lt], v[lw], v[li], v[lc] = float(t[i]), float(cph[j]), lock_id, float(fc[i])
            row.append(v)
        vs.append(row)
    tip = bm.verts.new(Vector(pts[n - 1].mean(axis=0)))
    tip[lt], tip[lw], tip[li], tip[lc] = 1.0, 0.0, lock_id, float(fc[-1])
    root = bm.verts.new(Vector(pts[0].mean(axis=0)))
    root[lt], root[lw], root[li], root[lc] = 0.0, 0.0, lock_id, float(fc[0])
    U = np.clip(s, 0, 0.998)
    V = A_ / (2 * math.pi)

    def setuv(f, ij):
        for lp, (i, j) in zip(f.loops, ij):
            lp[uvl].uv = (float(U[min(i, n - 1)]), float(V[min(i, n - 1), j % K]))
    for i in range(n - 2):
        for j in range(K):
            j2 = (j + 1) % K
            f = bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
            setuv(f, [(i, j), (i, j2 if j2 else K), (i + 1, j2 if j2 else K), (i + 1, j)])
    for j in range(K):
        j2 = (j + 1) % K
        f = bm.faces.new((vs[n - 2][j], vs[n - 2][j2], tip))
        setuv(f, [(n - 2, j), (n - 2, j2), (n - 1, j)])
        f = bm.faces.new((vs[0][j2], vs[0][j], root))
        setuv(f, [(0, j2), (0, j), (0, j)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    obj = kit.mesh_object(name, bm, mat)
    obj["keep_uv"] = True
    return obj


def build_tail(mat_holder):
    """The tail (a fox's brush): the underfur, a dense inner mass of short fur round the tail bone
    (darker, smaller than the outline), under ~70 guard-hair locks in five overlapping layers that
    flow from the root on the rump to the cream tip, whose tips break the outline. The painted atlas
    (cream flames, glowing swirls and dots, cream tip) is shared: every lock samples it where it lies."""
    body = TailBody()
    placeholder = bpy.data.materials.new("M_tail_tmp")
    keep = np.arange(0, len(body.P), 2)
    if keep[-1] != len(body.P) - 1:
        keep = np.r_[keep, len(body.P) - 1]
    under, grid = build_tail_mesh("tail_underfur", body.P[keep], body.ru[keep] * TAIL_UNDER, body.rb[keep] * TAIL_UNDER,
                                  body.rf[keep] * TAIL_UNDER, 40, placeholder, ripple=0.03, nflutes=11, seed=3)
    set_attr(under, "fur_t", np.full(len(under.data.vertices), 0.12))
    objs = [under]
    col_img, emi_img, cream = tail_images(grid, 0)
    set_attr(under, "fur_cream", np.zeros(len(under.data.vertices)))
    rng = random.Random(41)
    specs = tail_fur_lock_specs(rng)
    for k, sp in enumerate(specs):
        objs.append(build_tail_fur_lock(f"tail_fur_lock_{k:02d}", body, sp, rng.random(), placeholder, cream=cream))
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
                         [0.301, 0.303, 0.309, 0.313, 0.313, 0.307, 0.298, 0.286, 0.273]))   # cheeks cream up to just under the eyes (front drawing)
    zb += 0.006 * float(smoothstep(abs(x), 0.036, 0.056))      # outer cheeks: cream up to the eye's outer corner
    head = max(z - zb, y + 0.09, 0.248 - z)
    wb = 0.004 + 0.012 * min(1.0, max(0.0, (y + 0.24) / 0.05))
    bridge = max(abs(x) - wb, 0.3005 - z, y + 0.20)
    head = max(head, -bridge)
    # throat and chest front: cream in front of the boundary, within the bib, V point at Z 0.105
    yb = float(np.interp(z, [0.10, 0.13, 0.16, 0.20, 0.24, 0.28, 0.30], [-0.157, -0.147, -0.136, -0.124, -0.115, -0.105, -0.10]))   # follows the chest (moved back 0.018)
    wc = float(np.interp(z, [0.104, 0.115, 0.14, 0.18, 0.22, 0.26, 0.29, 0.30], [0.0, 0.010, 0.032, 0.046, 0.048, 0.05, 0.06, 0.06]))
    chest = max(y - yb, abs(x) - wc, 0.104 - z, z - 0.30)
    # belly underside and inner thighs
    belly = max(z - 0.152, 0.11 - z, y - 0.045, -0.115 - y, abs(x) - 0.032)
    # patch under the tail
    patch = max(abs(x) - 0.019, 0.118 - z, z - 0.195, 0.068 - y)
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
    set_attr(obj, "patch", smoothstep(y, 0.066, 0.09) * smoothstep(z, 0.12, 0.14) * smoothstep(0.022 - np.abs(x), 0.0, 0.008))
    set_attr(obj, "pys", (y - SIDE_Y0) / MARK_SPAN)
    set_attr(obj, "pzs", z / MARK_SPAN)
    set_attr(obj, "pxf", (x - FRONT_X0) / MARK_SPAN)


# ============================================================================ BUILD
def build():
    marks, decal = mark_images()
    m_fur = fur_material("M_fur", marks, decal, cream=False)
    m_cream = fur_material("M_fur_cream", marks, decal, cream=True)
    m_ear_out, m_ear_in = ear_materials(ear_image())
    m_ear_tuft = ear_tuft_material()
    m_silver = silver_material()
    m_antler = antler_material()
    m_cord = cord_material()
    m_gem = gem_material()
    m_eye = eye_material()
    m_nose = dark_material("M_nose", "#2c2428", 0.3, "#544650")
    m_eyelid = dark_material("M_eyelid", "#1b1d30", 0.6, "#2c2e44")

    body, clay = body_clay()
    surf, _ = clay.project(np.array([[0.0, -0.215, GEM_C[2]]]))
    GEM_C[1] = surf[0][1] - 0.0075
    kit.quad_remesh(body, 16500)
    close_holes(body)
    body.data.shade_smooth()
    body.data.materials.append(m_fur)
    kit.mark(body, cream_field, m_cream)
    close_holes(body)
    body_attributes(body)
    parts = [body]
    body_bvh = bvh_of(body)
    rng = random.Random(12)
    for side, uoff in ((1, 0.0), (-1, 0.5)):
        parts.append(build_ear(side, m_ear_out, m_ear_in, uoff))
        parts += build_ear_tufts(side, m_ear_tuft, rng)
        bed = EyeBed(body_bvh, clay, side)
        parts.append(build_eye(bed, m_eye))
        parts += build_eyelids(bed, m_eyelid)
    parts.append(build_nose(m_nose))
    cords, front = build_cord(clay, m_cord)
    parts += cords
    parts += build_pendant(m_silver, m_gem, front)
    parts += build_antlers(clay, m_antler)
    parts += build_tail(None)
    # size anchor: the sheet's "approx. 50 cm" is the overall height (tail top); the side-view metric
    # frame the parts are built in puts the tail top at ~0.465, so scale everything about the origin
    top = max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in parts)
    f = 0.50 / top
    for o in parts:
        o.data.transform(Matrix.Scale(f, 4))
        o.data.update()
    print(f"SCALE to 0.50 m: x{f:.4f} (tail top {top:.4f})")
    loc, rot, sc = brow_frame(clay, body_bvh)
    for mp in BROW_NODES:
        mp.inputs["Location"].default_value = loc * f
        mp.inputs["Rotation"].default_value = rot
        mp.inputs["Scale"].default_value = sc * f
    return parts


if __name__ == "__main__":
    kit.run(build, texture=4096)
