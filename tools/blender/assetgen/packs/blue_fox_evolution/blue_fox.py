"""Blue Fox Creature (Phase 1): pack blue_fox_evolution, object blue_fox.

A stylised light-blue fox standing on four legs (~0.30 m to the ear tips): one sculpted body
(signed-distance clay: head, ears with inner fur tufts, cheek tufts, neck, torso, legs, paws, the
big plume tail and its tip tufts), separate eyes and nose, a two-strand braided leather cord collar
and a silver-set blue cabochon pendant. Every marking (cream muzzle/chest/belly, dark lower legs,
ear inner tan, ear spirals, tail flame pattern and cream tip, undertail patch, brow dots, mouth
line) is painted into the body's own UV texture from procedural 3D fields evaluated at each
texel's position (bx_materials.TexelMap), never from the reference image.

Measurements (metres) come from the side view (0.287 mm/px, see the notes' Analysis);
`# inferred` marks what no view shows.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # tools/blender

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from assetgen import kit  # noqa: E402

S = kit.skill("scenario-blender-sculpting", "bx_sculpt")
M = kit.skill("scenario-blender-texturing-shading", "bx_materials")

REPO = Path(__file__).resolve().parents[5]
WORK = REPO / ".scratch/assetgen/work/blue_fox_evolution/blue_fox"
WORK.mkdir(parents=True, exist_ok=True)
FINAL = "--final" in sys.argv
PAINT_RES = 4096 if FINAL else 2048
VOXEL = 0.001
BODY_TRIS = 31000
RNG = random.Random(7)


# ----------------------------------------------------------------------------------------- #
# small numpy helpers
# ----------------------------------------------------------------------------------------- #

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def lerp(a, b, t):
    t = np.asarray(t, dtype=np.float32)
    if t.ndim == 1:
        t = t[:, None]
    return a + (b - a) * t


def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761 + 1013904223)
    h = h & 0xFFFFFFFF
    h = h ^ (h >> 13)
    h = (h * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h.astype(np.float32) / np.float32(4294967295.0)) * 2.0 - 1.0


def vnoise(P, seed=0):
    """3D value noise in [-1, 1] at points P (N, 3)."""
    f = np.floor(P)
    i = f.astype(np.int64)
    t = (P - f).astype(np.float32)
    t = t * t * (3.0 - 2.0 * t)
    out = np.zeros(len(P), dtype=np.float32)
    for dx in (0, 1):
        wx = t[:, 0] if dx else 1.0 - t[:, 0]
        for dy in (0, 1):
            wy = t[:, 1] if dy else 1.0 - t[:, 1]
            for dz in (0, 1):
                wz = t[:, 2] if dz else 1.0 - t[:, 2]
                out += wx * wy * wz * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, scale, octaves=3, seed=0):
    total, amp, norm = np.zeros(len(P), dtype=np.float32), 1.0, 0.0
    for o in range(octaves):
        total += amp * vnoise(P * (scale * 2.0 ** o), seed + 17 * o)
        norm += amp
        amp *= 0.5
    return total / norm


def polyline_dist(Q, pts):
    """Distance from 2D or 3D points Q (N, d) to a polyline pts (M, d), and the arc parameter
    (0..1) of the nearest point."""
    pts = np.asarray(pts, dtype=np.float64)
    seg = pts[1:] - pts[:-1]
    seglen = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seglen)])
    total = cum[-1]
    best = np.full(len(Q), np.inf)
    par = np.zeros(len(Q))
    for k in range(len(seg)):
        d = Q - pts[k]
        t = np.clip((d @ seg[k]) / max(seglen[k] ** 2, 1e-12), 0.0, 1.0)
        dist = np.linalg.norm(d - t[:, None] * seg[k], axis=1)
        better = dist < best
        best[better] = dist[better]
        par[better] = (cum[k] + t[better] * seglen[k]) / total
    return best, par


def spiral_pts(radius, turns, n=90, inner=0.12, phase=0.0, sense=1.0):
    """Archimedean spiral from the centre outward (2D points)."""
    th = np.linspace(0.0, turns * 2 * math.pi, n)
    r = radius * (inner + (1 - inner) * th / th[-1])
    return np.stack([sense * r * np.cos(th + phase), r * np.sin(th + phase)], 1)


def stroke_mask(Q, pts, w0, w1, soft=0.0004, taper_end=0.25):
    """Mask (0..1) of a stroke along a polyline whose half-width goes w0 -> w1, with the last
    `taper_end` of its length tapered to a point."""
    d, t = polyline_dist(Q, pts)
    w = w0 + (w1 - w0) * t
    w = w * np.clip((1.0 - t) / taper_end, 0.0, 1.0) ** 0.6
    return smoothstep(soft, -soft, d - w)


# ----------------------------------------------------------------------------------------- #
# design (metres; front -Y, +X = the fox's left = the side seen in view 2)
# ----------------------------------------------------------------------------------------- #

EAR_HALF_W = 0.0340      # ear base half width (front view: ear base 0.046 m across where it meets the head)
EAR_CUP = 13.0            # rim bends forward 5 mm: the cupped leaf
EAR_T = (0.0046, 0.0026)  # thickness base -> tip


def ear_frame(side):
    base = np.array([side * 0.032, -0.074, 0.226])   # ear base centre (front view: inner edges 0.02 m apart at the top)
    tip = np.array([side * 0.071, -0.071, 0.315])    # ear tips (view 2 at az 55: Y -0.064, Z 0.29-0.32)
    ev = tip - base
    length = float(np.linalg.norm(ev))
    ev = ev / length
    ew = np.array([side * 0.60, -0.80, 0.06])           # opening faces out-forward (view 2 sees the far ear back)
    ew = ew - ev * (ew @ ev)
    ew /= np.linalg.norm(ew)
    eu = np.cross(ev, ew)
    if eu[0] * side < 0:
        eu = -eu
    return base, eu, ev, ew, length


def ear_local(P, side):
    base, eu, ev, ew, length = ear_frame(side)
    d = P - base
    return d @ eu, d @ ev, d @ ew, length


def ear_d2(u, v, length):
    R = (EAR_HALF_W ** 2 + length ** 2) / (2 * EAR_HALF_W)
    dA = np.sqrt((u + (R - EAR_HALF_W)) ** 2 + v ** 2) - R
    dB = np.sqrt((u - (R - EAR_HALF_W)) ** 2 + v ** 2) - R
    return np.maximum(dA, dB)


def sd_ear(side):
    base, eu, ev, ew, length = ear_frame(side)

    def fn(x, y, z):
        dx, dy, dz = x - base[0], y - base[1], z - base[2]
        u = dx * eu[0] + dy * eu[1] + dz * eu[2]
        v = dx * ev[0] + dy * ev[1] + dz * ev[2]
        w = dx * ew[0] + dy * ew[1] + dz * ew[2]
        d2 = np.maximum(ear_d2(u, v, length), -v - 0.016)
        th = EAR_T[0] + (EAR_T[1] - EAR_T[0]) * np.clip(v / length, 0.0, 1.0)
        d3 = np.abs(w - EAR_CUP * u * u) - th * 0.5
        return S.smax(d2, d3, 0.0012)
    m = length + 0.03
    return S.Prim(fn, base - m, base + m)


def ear_point(side, u, v, w_off):
    base, eu, ev, ew, length = ear_frame(side)
    th = EAR_T[0] + (EAR_T[1] - EAR_T[0]) * min(max(v / length, 0), 1)
    w = EAR_CUP * u * u + th * 0.5 + w_off
    return base + u * eu + v * ev + w * ew


def ear_tufts(side):
    """Three cream fur spikes rising from the inner base of the ear (seeded lengths)."""
    rng = random.Random(31 if side > 0 else 47)
    spikes = []
    for (u0, v0, u1, v1, r0) in ((-0.009, 0.002, -0.014, 0.034, 0.0068),
                                 (-0.001, 0.001, 0.000, 0.028, 0.0062),
                                 (0.008, 0.004, 0.012, 0.022, 0.0052)):
        v1 = v1 * (1.0 + rng.uniform(-0.08, 0.08))
        a = ear_point(side, u0, v0, -0.0012)
        b = ear_point(side, u1, v1, 0.0022)
        spikes.append(S.sd_cone(tuple(a), tuple(b), r0, 0.0005))
    return spikes


# tail centre line (side view, Y, Z) and vertical half-thickness; lateral = 1.12 x
TAIL_PTS = np.array([(0.086, 0.125), (0.097, 0.131), (0.108, 0.137), (0.120, 0.145), (0.135, 0.156),
                     (0.152, 0.171), (0.170, 0.182), (0.188, 0.195), (0.206, 0.209), (0.224, 0.2275),
                     (0.242, 0.240), (0.258, 0.240), (0.272, 0.232)])
# vertical half-thickness of the tail's fur (outer surface of the locks); review 1: max thickness 8 % less,
# the distal fifth tapering to a point
TAIL_RZ = np.array([0.024, 0.027, 0.030, 0.035, 0.042, 0.047, 0.049, 0.048, 0.043, 0.026, 0.012, 0.007,
                    0.004])
# lateral / vertical radius per point. Review 1: from behind the tail is 0.76 W wide (render 0.89 W) and the
# front view shows it beside the shoulders at 0.46-0.58 H: widest low (Z 0.14-0.19, half width ~0.053),
# narrower above (half 0.047 at Z 0.19-0.21)
TAIL_W = np.array([1.08, 1.19, 1.33, 1.37, 1.26, 1.15, 1.08, 1.0, 0.98, 1.0, 1.0, 1.0, 1.0])
TAIL_VOXEL = 0.0007
TAIL_TRIS = 26000


def tail_samples(n=48):
    """Dense samples of the tail centre line: position (n, 3), radius, tangent, arc parameter."""
    seg = np.linalg.norm(np.diff(TAIL_PTS, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, cum[-1], n)
    y = np.interp(u, cum, TAIL_PTS[:, 0])
    z = np.interp(u, cum, TAIL_PTS[:, 1])
    r = np.interp(u, cum, TAIL_RZ)
    C = np.stack([np.zeros(n), y, z], 1)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    s = u / cum[-1]
    return C, r, T, s, cum[-1]


def tail_underfur_prims(scale=0.80, s_max=0.92):
    """The tail's dense underfur along the tail bone: a chain of ellipsoids at `scale` of the fur's outer
    radius; the guard-hair locks lie on it."""
    C, r, T, s, _ = tail_samples(30)
    seg = np.linalg.norm(np.diff(TAIL_PTS, axis=0), axis=1)
    sp = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
    wide = np.interp(s, sp, TAIL_W)
    prims = []
    spacing = np.linalg.norm(C[1] - C[0])
    for k in range(len(C)):
        if r[k] * scale < 0.004 or s[k] > s_max:
            continue
        rr = r[k] * scale
        ang = math.degrees(math.atan2(T[k][2], T[k][1]))
        prims.append(S.sd_ellipsoid(tuple(C[k]), (rr * wide[k], max(rr * 0.75, spacing * 1.6), rr),
                                    rot=(ang, 0, 0)))
    return prims

FRONT_PAW_Y = {1: -0.067, -1: -0.068}   # view 2 at az 55 el 13: the paws need no stagger
HIND_PAW_Y = {1: 0.057, -1: 0.056}
HO = np.array([0.0, -0.008, 0.012])      # head offset from build 1 (skull top Z 0.241, nose Y -0.156)


HEAD_PIV = np.array([0.0, -0.075, 0.195])  # head scale pivot (back of the skull, eye height)
HS = np.array([1.14, 1.05, 1.12])           # Cycle 6: reference head 14 % wider (front) and 12 % taller (side)
HSR = 1.12


def h(*p):
    return tuple(HEAD_PIV + (np.array(p, dtype=float) - HEAD_PIV) * HS + HO)


def hr(*r):
    return tuple(np.array(r, dtype=float) * HS)
FRONT_X, HIND_X = 0.0200, 0.0265       # paw X: the front and back views draw the paws closer than the shoulders/hips

# the mouth: a soft smile line 33 mm wide, a slight rise in the middle, 1.5 mm dips, corners turned up
MOUTH = [h(0.0, -0.1405, 0.1727), h(0.0040, -0.1392, 0.1714), h(0.0080, -0.1354, 0.1713),
         h(0.0115, -0.1302, 0.1729), h(0.0145, -0.1245, 0.1750)]


MOUTH_S = {}     # surface points of the carved mouth lines (filled by body_clay, painted by body_color)


def mouth_line(side):
    return np.array([(side * p[0], p[1], p[2]) for p in MOUTH])


# ----------------------------------------------------------------------------------------- #
# the body clay
# ----------------------------------------------------------------------------------------- #

def body_clay():
    clay = S.Clay((-0.082, -0.172, -0.004), (0.082, 0.302, 0.312), voxel=VOXEL, far=0.022)
    E, C, T, R = S.sd_ellipsoid, S.sd_cone, S.sd_tube, S.sd_sphere

    # torso: chest, ribcage, loin, hips, belly keel (side view landmarks)
    clay.add(E((0, -0.066, 0.110), (0.033, 0.035, 0.041)))
    clay.add(E((0, -0.086, 0.122), (0.025, 0.020, 0.032)), blend=0.014)   # full cream chest pushing forward
    clay.add(E((0, -0.014, 0.113), (0.034, 0.056, 0.040)), blend=0.02)
    clay.add(E((0, 0.038, 0.114), (0.030, 0.043, 0.033)), blend=0.02)
    clay.add(E((0, 0.057, 0.114), (0.033, 0.030, 0.032)), blend=0.02)
    clay.add(E((0, -0.040, 0.149), (0.028, 0.034, 0.022)), blend=0.018)   # nape / withers mass
    clay.add(E((0, 0.000, 0.085), (0.022, 0.055, 0.019)), blend=0.016)
    # neck (thicker: the reference head sits on a short full neck)
    clay.add(C((0, -0.056, 0.128), (0, -0.082, 0.190), 0.035, 0.029), blend=0.016)

    # head: cranium, brow mass, muzzle, lower jaw, cheeks
    clay.add(E(h(0, -0.078, 0.201), hr(0.038, 0.043, 0.035)), blend=0.012)
    clay.add(E(h(0, -0.108, 0.207), hr(0.029, 0.023, 0.021)), blend=0.011)
    clay.add(C(h(0, -0.104, 0.188), h(0, -0.141, 0.1825), 0.0205 * HSR, 0.0105 * HSR), blend=0.009)
    clay.add(C(h(0, -0.102, 0.172), h(0, -0.134, 0.1740), 0.0175 * HSR, 0.0085 * HSR), blend=0.008)
    clay.add(E(h(0.027, -0.090, 0.181), hr(0.025, 0.026, 0.020)), blend=0.012, mirror=True)
    # cheek ruff: three fluffy pointed tufts per side, out and back (front view: fluff to |X| 0.06)
    for side in (1, -1):
        rng = random.Random(5 if side > 0 else 9)
        for (a, b, r0) in (((0.028, -0.074, 0.182), (0.046, -0.058, 0.184), 0.0120),
                           ((0.027, -0.072, 0.172), (0.045, -0.056, 0.170), 0.0110),
                           ((0.024, -0.072, 0.163), (0.039, -0.058, 0.158), 0.0090)):
            j = rng.uniform(-0.0025, 0.0025)
            clay.add(C(h(side * a[0], a[1], a[2]), h(side * (b[0] + j), b[1] + j * 0.5, b[2] + j), r0 * HSR, 0.0010),
                     blend=0.006)

    # ears with their inner fur tufts
    for side in (1, -1):
        clay.add(sd_ear(side), blend=0.008)
        for spike in ear_tufts(side):
            clay.add(spike, blend=0.0012)

    # front legs: shoulder, upper arm, elbow, forearm, wrist, paw
    for side in (1, -1):
        y0, x0 = FRONT_PAW_Y[side], side * FRONT_X
        clay.add(E((side * 0.026, -0.049, 0.110), (0.013, 0.021, 0.031)), blend=0.010)
        clay.add(T([(side * 0.025, y0 + 0.015, 0.103), (side * 0.0230, y0 + 0.011, 0.066), (x0, y0 + 0.004, 0.032),
                    (x0, y0 + 0.001, 0.016)], [0.0155, 0.0127, 0.0098, 0.0090], blend=0.006), blend=0.010)
        clay.add(E((x0, y0 - 0.005, 0.0088), (0.0116, 0.0152, 0.0098)), blend=0.006)
        # elbow tuft pointing back-down
        clay.add(C((x0, y0 + 0.015, 0.076), (x0 + side * 0.001, y0 + 0.026, 0.061), 0.0050, 0.0007),
                 blend=0.003)
    # hind legs: thigh, stifle, hock, paw
    for side in (1, -1):
        y0, x0 = HIND_PAW_Y[side], side * HIND_X
        clay.add(E((side * 0.028, 0.050, 0.095), (0.018, 0.031, 0.036), rot=(-18, 0, 0)), blend=0.012)
        clay.add(T([(side * 0.029, 0.050, 0.090), (side * 0.0270, 0.046, 0.058), (x0, y0 + 0.015, 0.030),
                    (x0, y0 + 0.006, 0.014)], [0.0165, 0.0125, 0.0090, 0.0082], blend=0.006), blend=0.010)
        clay.add(E((x0, y0 - 0.004, 0.0088), (0.0124, 0.0152, 0.0098)), blend=0.006)

    # the tail's root: the croup flows into it; the tail itself (underfur + fur locks) is its own object
    stub = None
    for p in tail_underfur_prims(0.85, s_max=0.16):
        stub = p if stub is None else stub.add(p, 0.010)
    clay.add(stub, blend=0.018)
    # chest fur tufts on the cream edge (seeded)
    rng = random.Random(3)
    for side in (1, -1):
        for k in range(2):
            z = 0.090 + 0.016 * k + rng.uniform(-0.003, 0.003)
            clay.add(C((side * 0.020, -0.075, z), (side * 0.023, -0.074 + 0.004, z - 0.016), 0.0050, 0.0006),
                     blend=0.003)

    # the eyes: sockets, openings, eyelids and lash lines; then toe grooves and the mouth line
    carve_eyes(clay)
    for side in (1, -1):
        for y0, x0 in ((FRONT_PAW_Y[side], side * FRONT_X), (HIND_PAW_Y[side], side * HIND_X)):
            for dx in (-0.0034, 0.0034):
                clay.sub(E((x0 + dx, y0 - 0.016, 0.011), (0.0006, 0.0065, 0.0055)), blend=0.0008)
    for side in (1, -1):
        S_, _ = clay.stroke(mouth_line(side), 0.0010, 0.0005, op="sub", blend=0.0006)
        MOUTH_S[side] = np.asarray(S_)

    clay.intersect(S.sd_halfspace((0, 0, 0), (0, 0, -1)))   # flat soles on the ground
    return clay


EYE_START = {1: (0.010, -0.098, 0.2030), -1: (-0.010, -0.098, 0.2030)}


def eye_dir(side):
    """Direction the eye faces (out of the face, 18 deg outward)."""
    d = np.array([side * 0.31, -0.95, 0.04])
    return d / np.linalg.norm(d)


_EYE_CACHE = {}


def brow_anchor(side):
    return eye_centre(side)


def eye_centre(side):
    """Point where the old eye's line of sight leaves the head surface (cranium + brow + cheek only);
    it anchors the brow dots (they passed review and stay where they are)."""
    if side in _EYE_CACHE:
        return _EYE_CACHE[side]
    E = S.sd_ellipsoid
    head = E(h(0, -0.078, 0.201), hr(0.038, 0.043, 0.035)).add(E(h(0, -0.108, 0.207), hr(0.029, 0.023, 0.021)), 0.011)
    head = head.add(E(h(side * 0.027, -0.090, 0.181), hr(0.025, 0.026, 0.020)), 0.012)
    p = np.array(EYE_START[side], dtype=float)
    d = eye_dir(side)
    for _ in range(400):
        val = head(np.array([p[0]]), np.array([p[1]]), np.array([p[2]]))
        if float(np.asarray(val).ravel()[0]) > 0:
            break
        p = p + d * 0.0002
    _EYE_CACHE[side] = p
    return p


# ----------------------------------------------------------------------------------------- #
# the eyes: an eyeball sitting in its socket, wrapped by the upper and the lower eyelid
# ----------------------------------------------------------------------------------------- #
# A living eye is a ball (white sclera, the iris disc with the pupil, under a wet clear cornea) in a
# socket of the skull; the eyelids are skin over the ball and their edges make the almond opening.
# The upper lid is thicker, carries the lash line and shades the top of the ball; the lower lid is a
# thin rim. This style keeps that build and exaggerates it: a big almond opening, an iris filling its
# height, a thick dark lash line with a wing at the outer corner, a thin lower line, a big pupil and a
# white catch light. Front view (0.433 mm/px): opening 24 x 20 mm, centres 120 px apart (X +-0.026),
# outer corner ~3.5 mm higher than the inner, iris ~19 mm across set 3.5 mm toward the nose (the fox
# looks at the viewer while its eyes face 18 deg outward).
EYE_X, EYE_Z = 0.0262, 0.2040
EYE_A, EYE_B = 0.0117, 0.0098            # half width / half height of the eye opening seen from the front
EYE_TILT = math.radians(9.0)              # outer corner higher than the inner corner
EYEBALL_R = np.array([0.0170, 0.0145, 0.0115])   # eyeball radii: across (outward), up, along its facing
EYEBALL_PROUD = 0.0008                    # the eyeball's front stands this far out of the face
LID_T = (0.0009, 0.0017)                  # lower / upper eyelid thickness over the eyeball
EYE = {}                                  # per side: eyeball centre and axes, the face's height map


def eye_local(side, X, Z):
    """Front-view coordinates of the eye opening: a toward the outer corner, b up (metres)."""
    ar = side * X - EYE_X
    br = Z - EYE_Z
    c, s = math.cos(EYE_TILT), math.sin(EYE_TILT)
    return ar * c + br * s, -ar * s + br * c


def eye_world2d(side, a, b):
    c, s = math.cos(EYE_TILT), math.sin(EYE_TILT)
    ar, br = a * c - b * s, a * s + b * c
    return side * (EYE_X + ar), EYE_Z + br


def eye_opening_field(a, b):
    """Distance-like field of the eye opening seen from the front (< 0 inside): an almond, round at
    the inner corner, pointed at the outer corner."""
    o = np.clip(a / EYE_A, 0.0, 1.0) ** 3
    aa = a / (EYE_A * (1.0 + 0.05 * o))
    bb = b / (EYE_B * (1.0 - 0.42 * o))
    return (np.sqrt(aa * aa + bb * bb) - 1.0) * EYE_B


def eye_outline(grow=0.0, n=120, th0=0.0, th1=2 * math.pi):
    th = np.linspace(th0, th1, n)
    c, s = np.cos(th), np.sin(th)
    o = np.maximum(c, 0.0) ** 3
    return (EYE_A * (1.0 + 0.05 * o) + grow) * c, (EYE_B * (1.0 - 0.42 * o) + grow) * s


def face_height_map(clay, side, half=(0.024, 0.020), step=0.0004):
    """Y of the face surface seen from the front over the eye region (before the socket is cut)."""
    xs = np.arange(side * EYE_X - half[0], side * EYE_X + half[0] + 1e-9, step)
    zs = np.arange(EYE_Z - half[1], EYE_Z + half[1] + 1e-9, step)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    X, Z = X.ravel(), Z.ravel()
    hit = np.full(len(X), np.nan)
    y0, dy = -0.170, 0.0002
    for k in range(600):
        y = y0 + k * dy
        inside = clay.sample(np.stack([X, np.full(len(X), y), Z], 1)) < 0
        new = inside & np.isnan(hit)
        hit[new] = y
        if not np.isnan(hit).any():
            break
    hit[np.isnan(hit)] = y0 + 600 * dy
    a, b = hit - dy, hit.copy()
    for _ in range(8):
        m = 0.5 * (a + b)
        inside = clay.sample(np.stack([X, m, Z], 1)) < 0
        b = np.where(inside, m, b)
        a = np.where(inside, a, m)
    return xs, zs, (0.5 * (a + b)).reshape(len(xs), len(zs))


def face_y(hm, X, Z):
    xs, zs, Yg = hm
    X, Z = np.broadcast_arrays(np.asarray(X, float), np.asarray(Z, float))
    fx = np.clip((X - xs[0]) / (xs[1] - xs[0]), 0, len(xs) - 1.0001)
    fz = np.clip((Z - zs[0]) / (zs[1] - zs[0]), 0, len(zs) - 1.0001)
    i, k = fx.astype(int), fz.astype(int)
    tx, tz = fx - i, fz - k
    return (Yg[i, k] * (1 - tx) * (1 - tz) + Yg[i + 1, k] * tx * (1 - tz) + Yg[i, k + 1] * (1 - tx) * tz
            + Yg[i + 1, k + 1] * tx * tz)


def eyeball_setup(clay, side):
    hm = face_height_map(clay, side)
    d, up, out = eye_frame(side)
    X0, Z0 = side * EYE_X, EYE_Z
    front = np.array([X0, float(face_y(hm, X0, Z0)), Z0])
    centre = front + (EYEBALL_PROUD - EYEBALL_R[2]) * d
    EYE[side] = dict(hm=hm, centre=centre, axes=np.stack([out, up, d]), front=front)


def eyeball_fn(side, grow=0.0):
    e = EYE[side]
    c, A = e["centre"], e["axes"]
    r = EYEBALL_R + grow

    def fn(x, y, z):
        px, py, pz = x - c[0], y - c[1], z - c[2]
        u = (px * A[0, 0] + py * A[0, 1] + pz * A[0, 2]) / r[0]
        v = (px * A[1, 0] + py * A[1, 1] + pz * A[1, 2]) / r[1]
        w = (px * A[2, 0] + py * A[2, 1] + pz * A[2, 2]) / r[2]
        k0 = np.sqrt(u * u + v * v + w * w)
        k1 = np.sqrt((u / r[0]) ** 2 + (v / r[1]) ** 2 + (w / r[2]) ** 2)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    return fn


def sd_eye_socket(side):
    """The socket the eyeball sits in (the eyeball plus a 0.2 mm gap)."""
    c = EYE[side]["centre"]
    m = EYEBALL_R.max() + 0.003
    return S.Prim(eyeball_fn(side, 0.0002), c - m, c + m)


def sd_eye_opening(side):
    """The opening between the eyelids, seen from the front: everything in front of the eyeball
    inside the almond is cleared so the eyeball shows."""
    c = EYE[side]["centre"]

    def fn(x, y, z):
        a, b = eye_local(side, x, z)
        return np.maximum(eye_opening_field(a, b), y - c[1])
    x0, x1 = sorted((side * (EYE_X - 0.02), side * (EYE_X + 0.02)))
    return S.Prim(fn, np.array([x0, -0.18, EYE_Z - 0.016]), np.array([x1, c[1], EYE_Z + 0.016]))


def sd_eyelids(side):
    """The upper and lower eyelid: skin over the eyeball outside the opening, thicker above."""
    ball = eyeball_fn(side)
    c = EYE[side]["centre"]

    def fn(x, y, z):
        a, b = eye_local(side, x, z)
        f = eye_opening_field(a, b)
        d0 = ball(x, y, z)
        t = LID_T[0] + (LID_T[1] - LID_T[0]) * smoothstep(-0.4 * EYE_B, 0.4 * EYE_B, b)
        shell = np.maximum(d0 - t, 0.0002 - d0)
        return np.maximum(shell, -f)
    m = EYEBALL_R.max() + 0.004
    return S.Prim(fn, c - m, c + m)


def lash_line_points(side):
    """The upper eyelid's edge from the wing tip over the top to the inner corner (front-view a, b)."""
    a, b = eye_outline(0.0007, 40, -0.08, math.pi + 0.05)
    ac = EYE_A * 1.05
    wa = np.array([ac + 0.0034, ac + 0.0018])
    wb = np.array([0.0021, 0.0010])
    return np.concatenate([wa, a]), np.concatenate([wb, b])


def carve_eyes(clay):
    """Socket, opening, eyelids and lash-line ridge for both eyes (the face is read before cutting)."""
    for side in (1, -1):
        eyeball_setup(clay, side)
    for side in (1, -1):
        clay.sub(sd_eye_opening(side), blend=0.0010)
        clay.sub(sd_eye_socket(side), blend=0.0004)
        clay.add(sd_eyelids(side), blend=0.0009)
        a, b = lash_line_points(side)
        X, Z = eye_world2d(side, a, b)
        Y = face_y(EYE[side]["hm"], X, Z) - 0.001
        n = len(a)
        radii = np.interp(np.arange(n), [0, 2, 12, 30, n - 1], [0.0004, 0.0009, 0.0011, 0.0009, 0.0005])
        clay.stroke(np.stack([X, Y, Z], 1), radii, 0.00045, op="add", blend=0.0005, n=60)


def eyelid_marks(P):
    """Masks of the lash line (upper eyelid edge and its wing) and the lower eyelid line on the face."""
    lash = np.zeros(len(P), dtype=np.float32)
    lower = np.zeros(len(P), dtype=np.float32)
    for side, e in EYE.items():
        sel = np.nonzero((np.abs(P[:, 0] - side * EYE_X) < 0.024) & (np.abs(P[:, 2] - EYE_Z) < 0.019)
                         & (P[:, 1] < -0.09))[0]
        if not len(sel):
            continue
        Ps = P[sel]
        a, b = eye_local(side, Ps[:, 0], Ps[:, 2])
        f = eye_opening_field(a, b)
        front = (Ps[:, 1] < face_y(e["hm"], Ps[:, 0], Ps[:, 2]) + 0.0045).astype(np.float32)
        up_w = smoothstep(-0.30 * EYE_B, 0.10 * EYE_B, b)
        w_up = 0.0012 + 0.0007 * smoothstep(-EYE_A, EYE_A, a)
        m = smoothstep(w_up + 0.00025, w_up - 0.00025, f) * up_w
        ac = EYE_A * 1.05
        wing = np.array([(ac - 0.0012, 0.0004), (ac + 0.0016, 0.0012), (ac + 0.0036, 0.0023)])
        m = np.maximum(m, stroke_mask(np.stack([a, b], 1), wing, 0.0009, 0.0004, soft=0.00015, taper_end=0.45))
        lo = smoothstep(0.0008, 0.0005, f) * (1.0 - up_w)
        lash[sel] = np.maximum(lash[sel], m * front)
        lower[sel] = np.maximum(lower[sel], lo * front)
    return lash, lower


# ----------------------------------------------------------------------------------------- #
# meshes
# ----------------------------------------------------------------------------------------- #

def select_only(obj):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def decimate(obj, tris):
    obj.data.calc_loop_triangles()
    have = len(obj.data.loop_triangles)
    if have > tris:
        mod = obj.modifiers.new("Decimate", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = tris / have
        select_only(obj)
        bpy.ops.object.modifier_apply(modifier=mod.name)


def make_manifold(obj):
    """Delete vertices on edges with more than two faces, then fill the holes (decimation can pinch
    the thin ear rims)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for _ in range(4):
        bad = [e for e in bm.edges if not e.is_manifold]
        if not bad:
            break
        verts = {v for e in bad if len(e.link_faces) > 2 for v in e.verts}
        verts |= {v for v in bm.verts if not v.is_manifold and v.link_faces and all(len(e.link_faces) == 2 for e in v.link_edges)}
        if verts:
            bmesh.ops.delete(bm, geom=list(verts), context="VERTS")
        bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=16)
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def smart_uv(obj, margin=0.003):
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj["keep_uv"] = True


def uv_sphere(name, segs, rings, radius=1.0):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius, calc_uvs=True)
    return bm


def sweep_tube(name, path, radius, ring=10, closed=True, normals=None):
    """A tube of `radius` along `path` (N, 3): frames from `normals` (made perpendicular to the
    path) when given, else parallel transport."""
    path = np.asarray(path, dtype=float)
    n = len(path)
    T = np.roll(path, -1, 0) - np.roll(path, 1, 0) if closed else np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ref = np.array([0, 0, 1.0])
    N0 = np.cross(T[0], ref)
    N0 /= np.linalg.norm(N0)
    frames = []
    Nk = N0
    for k in range(n):
        if normals is not None:
            Nk = np.asarray(normals[k], dtype=float)
        Nk = Nk - T[k] * (Nk @ T[k])
        Nk /= np.linalg.norm(Nk)
        frames.append((Nk, np.cross(T[k], Nk)))
    bm = bmesh.new()
    rows = []
    for k in range(n):
        Nk, Bk = frames[k]
        row = []
        for j in range(ring):
            a = 2 * math.pi * j / ring
            row.append(bm.verts.new(tuple(path[k] + radius * (math.cos(a) * Nk + math.sin(a) * Bk))))
        rows.append(row)
    last = n if closed else n - 1
    for k in range(last):
        r0, r1 = rows[k], rows[(k + 1) % n]
        for j in range(ring):
            bm.faces.new((r0[j], r0[(j + 1) % ring], r1[(j + 1) % ring], r1[j]))
    if not closed:
        bm.faces.new(list(reversed(rows[0])))
        bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def surface_along(clay, start, direction, step=0.0003, limit=0.08):
    p = np.array(start, dtype=float)
    d = np.asarray(direction, dtype=float)
    d = d / np.linalg.norm(d)
    for _ in range(int(limit / step)):
        if clay.sample(p[None, :])[0] > 0:
            return p
        p = p + d * step
    return p


# ----------------------------------------------------------------------------------------- #
# materials
# ----------------------------------------------------------------------------------------- #

def node(tree, kind, **props):
    n = tree.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def image_material(name, color_img, rough_img, height_img, bump_dist, metallic=0.0, spec=0.5):
    mat, tree, bsdf = kit.principled(name)
    uv = kit.uv_node(tree)
    links = tree.links
    tc = node(tree, "ShaderNodeTexImage", image=color_img, interpolation="Cubic")
    links.new(uv.outputs["UV"], tc.inputs["Vector"])
    links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    tr = node(tree, "ShaderNodeTexImage", image=rough_img, interpolation="Cubic")
    links.new(uv.outputs["UV"], tr.inputs["Vector"])
    links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    th = node(tree, "ShaderNodeTexImage", image=height_img, interpolation="Cubic")
    links.new(uv.outputs["UV"], th.inputs["Vector"])
    bump = node(tree, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = bump_dist
    bump.inputs["Strength"].default_value = 1.0
    links.new(th.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = spec
    return mat


def save_img(name, arr, res, colorspace):
    img = bpy.data.images.new(name, res, res, alpha=True)
    img.colorspace_settings.name = colorspace
    M.write_pixels(img, arr)
    path = str(WORK / f"{name}.png")
    M.save_image(img, path)
    img.filepath = path
    img.reload()
    return img


def paint(obj, res, color_fn, rough_fn, height_fn, prefix):
    """Evaluate the field functions at every texel of obj's UVs and save colour (sRGB), roughness and
    height (Non-Color) images."""
    tm = M.TexelMap(obj, res)
    P = tm.pos[tm.valid].astype(np.float64)
    Nn = tm.nrm[tm.valid].astype(np.float64)
    col = np.clip(color_fn(P, Nn), 0, 1)
    rough = np.clip(rough_fn(P, Nn, col), 0, 1)
    hgt = np.clip(height_fn(P, Nn), 0, 1)
    out = []
    for nm, vals, cs in ((f"{prefix}_color", col, "sRGB"), (f"{prefix}_rough", rough, "Non-Color"),
                         (f"{prefix}_height", hgt, "Non-Color")):
        arr = np.zeros((res, res, 4), dtype=np.float32)
        arr[..., 3] = 1.0
        if vals.ndim == 1:
            arr[tm.valid, 0:3] = vals[:, None]
        else:
            arr[tm.valid, 0:3] = vals
        arr = M.dilate(arr, tm.valid, 6)
        arr[..., 3] = 1.0
        out.append(save_img(nm, arr, res, cs))
    return out


# ---- body fields -------------------------------------------------------------------------- #

C_TOP, C_SIDE, C_UNDER = hexc("#9cc3d6"), hexc("#88b0c6"), hexc("#6689ad")
C_HEAD = hexc("#a7cde0")
C_LEG, C_PAW = hexc("#5f83aa"), hexc("#4f6f9a")
C_CREAM, C_CREAM_CHEEK, C_CREAM_DARK = hexc("#e6d6c4"), hexc("#eee2d3"), hexc("#cdb9a5")
C_BELLY = hexc("#b19c89")
C_BROW = hexc("#ddd6cc")
C_TAIL_TIP, C_TAIL_CREAM, C_TAIL_FOLD = hexc("#dfd9d4"), hexc("#d2c9c2"), hexc("#b5aca8")
C_TAIL_UNDER = hexc("#4d6c94")
C_EAR_TAN, C_EAR_DEEP, C_EAR_RIMTAN = hexc("#dcc6b4"), hexc("#b89c8b"), hexc("#e6d3c2")
C_EAR_TUFT = hexc("#e8d9c6")
C_EAR_RIM = hexc("#8cb3cb")
C_DARK_MARK, C_EAR_TIP = hexc("#3d5585"), hexc("#5b7ea9")
C_BACK_PATCH, C_BACK_SPIRAL = hexc("#4f6c9b"), hexc("#97bcd5")
C_UNDERTAIL, C_UNDERTAIL_RIM = hexc("#b7a28f"), hexc("#9c8675")
C_MOUTH = hexc("#3b3032")


def tail_coords(P):
    """For points P: continuous arc parameter s (nearest point on the tail centre line), radius r,
    distance to the axis, angle phi around the axis (0 = top, +pi/2 = +X side)."""
    C, r, T, s, L = tail_samples(64)
    n = len(P)
    best = np.full(n, np.inf)
    seg = np.zeros(n, dtype=np.int64)
    tt = np.zeros(n)
    for k in range(len(C) - 1):
        d = C[k + 1] - C[k]
        t = np.clip(((P - C[k]) @ d) / (d @ d), 0.0, 1.0)
        dist = np.linalg.norm(P - (C[k] + t[:, None] * d), axis=1)
        b = dist < best
        best[b] = dist[b]
        seg[b] = k
        tt[b] = t[b]
    w = tt[:, None]
    Cp = C[seg] * (1 - w) + C[seg + 1] * w
    Tk = T[seg] * (1 - w) + T[seg + 1] * w
    Tk /= np.linalg.norm(Tk, axis=1, keepdims=True)
    sp = s[seg] * (1 - tt) + s[seg + 1] * tt
    rp = r[seg] * (1 - tt) + r[seg + 1] * tt
    rel = P - Cp
    rel = rel - Tk * np.sum(rel * Tk, axis=1, keepdims=True)
    up = np.stack([np.zeros(n), -Tk[:, 2], Tk[:, 1]], 1)
    up *= np.sign(up[:, 2:3] + 1e-9)
    phi = np.arctan2(rel[:, 0], np.sum(rel * up, axis=1))
    return sp, rp, np.linalg.norm(rel, axis=1), phi, L


def tail_pattern(P, side_seed):
    """Cream mask (0..1), tip mask, underside mask, tail membership and arc parameter, from the
    tail coordinates (evaluated only near the tail)."""
    n = len(P)
    out = [np.zeros(n, dtype=np.float32) for _ in range(5)]
    near = np.nonzero((P[:, 1] > 0.07) & (P[:, 2] > 0.105))[0]
    if len(near) == 0:
        return out
    Pn = P[near]
    s, r, dist, phi, L = tail_coords(Pn)
    on_tail = ((dist < np.maximum(r * 1.48, 0.012 + 0.024 * smoothstep(0.85, 1.0, s)) + 0.004) & (s > 0.03)).astype(np.float32)
    aphi = np.abs(phi)
    jag = 0.035 * fbm(Pn, 90, 2, seed=21) + 0.015 * fbm(Pn, 300, 2, seed=22)
    # Cycle 7: the reference tail is mostly blue with cream markings; only the last ~18 % is all cream
    tip = smoothstep(0.012, -0.012, (0.80 - s) + jag * 1.4)
    tongue = -0.12 * np.maximum(0.0, np.cos(aphi * 5.5 + 0.4)) ** 3
    s_b = np.interp(aphi, [0.0, 0.45, 0.85, 1.20, 1.50, 1.80], [0.40, 0.44, 0.50, 0.62, 0.74, 0.86]) + tongue
    blaze = smoothstep(0.010, -0.010, (s_b - s) + jag) * (aphi < 1.80)
    Q = np.stack([phi * 0.045, s * L], 1)          # chart: angle x 45 mm around, arc length along
    curls = np.zeros(len(Pn), dtype=np.float32)
    for sg in (1.0, -1.0):
        big = 0.0190 if sg > 0 else 0.0178
        cen = np.array([sg * 1.55 * 0.045, 0.57 * L])
        pts = spiral_pts(big, 1.45, n=80, inner=0.10, phase=math.pi * 0.55, sense=sg) + cen
        end = pts[-1]
        arc = np.array([end + np.array([-sg * 0.006 * t, 0.012 * t + 0.004 * t * t]) for t in np.linspace(0, 1, 8)])
        stroke = np.concatenate([pts, arc[1:]])
        sel = np.abs(Q[:, 0] - cen[0]) < 0.05
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], stroke, 0.0020, 0.0052, soft=0.0005,
                                                            taper_end=0.12))
        hcen = np.array([sg * 0.046, 0.47 * L])
        hk = spiral_pts(0.0055, 0.75, n=30, inner=0.25, phase=math.pi * 0.2, sense=sg) + hcen
        sel = np.abs(Q[:, 0] - hcen[0]) < 0.02
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], hk, 0.0010, 0.0022, soft=0.0005, taper_end=0.2))
        sw = np.array([(sg * 0.084, 0.36 * L), (sg * 0.090, 0.50 * L), (sg * 0.090, 0.64 * L),
                       (sg * 0.081, 0.77 * L), (sg * 0.064, 0.87 * L)])
        sel = (Q[:, 0] * sg) > 0.05
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], sw[::-1], 0.0046, 0.0008, soft=0.0006,
                                                            taper_end=0.3))
        # underside curls left and right of the underside blaze (back view)
        ucen = np.array([sg * 0.108, 0.66 * L])
        up = spiral_pts(0.0105, 1.3, n=60, inner=0.12, phase=math.pi * 1.4, sense=-sg) + ucen
        sel = np.abs(Q[:, 0] - ucen[0]) < 0.03
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], up, 0.0012, 0.0032, soft=0.0005, taper_end=0.15))
        sel = np.zeros(len(Q), dtype=bool)
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], sw[::-1], 0.0046, 0.0008, soft=0.0006,
                                                            taper_end=0.3))
    # underside blaze from the tip toward the middle, with tongues (back view)
    au = math.pi - aphi
    tongue_u = -0.10 * np.maximum(0.0, np.cos(au * 5.0 + 0.3)) ** 3
    s_u = 0.50 + 0.30 * (au / 0.80) ** 1.5 + tongue_u
    blaze_u = smoothstep(0.010, -0.010, (s_u - s) + jag) * (au < 0.80)
    cream = np.maximum(np.maximum(np.maximum(blaze, blaze_u), curls), tip) * on_tail
    tip = tip * on_tail
    under = smoothstep(1.6, 2.9, aphi) * on_tail
    for arr, vals in zip(out, (cream, tip, under, on_tail, s)):
        arr[near] = vals
    return out


def ear_fields(P):
    """Per side (on the points near that ear): indices and masks for inner tan, rim, dark marking,
    back patch, light spiral, tip darkening."""
    res = {}
    for side in (1, -1):
        base, eu, ev, ew, L = ear_frame(side)
        idx = np.nonzero(np.linalg.norm(P - base, axis=1) < L + 0.012)[0]
        Pn = P[idx]
        u, v, w, L = ear_local(Pn, side)
        th = EAR_T[0] + (EAR_T[1] - EAR_T[0]) * np.clip(v / L, 0, 1)
        ws = w - EAR_CUP * u * u
        d2 = ear_d2(u, v, L)
        on = (np.abs(ws) < th * 0.5 + 0.0035) & (d2 < 0.0025) & (v > -0.002)
        inner = ((ws > 0) & on).astype(np.float32)
        jag = 0.0012 * fbm(Pn, 400, 2, seed=40 + side)
        tan = inner * smoothstep(0.0, -0.0010, d2 + 0.0042 + jag) * smoothstep(0.0012, -0.0012, v - 0.047 - 0.004 * np.cos(u / EAR_HALF_W * 3.0) + jag * 2)
        deep = smoothstep(-0.006, -0.016, d2) * smoothstep(0.05, 0.015, v)
        Q = np.stack([u, v], 1)
        cen = np.array([0.0025, 0.0640])
        sp = spiral_pts(0.0095, 1.5, n=80, inner=0.12, phase=math.pi * 0.9, sense=-1.0) + cen
        tl = np.array([sp[-1] + np.array([0.0060 * t, -0.017 * t + 0.002 * t * t]) for t in np.linspace(0, 1, 10)])
        stroke = np.concatenate([sp, tl[1:]])
        sel = on & (np.abs(v - 0.06) < 0.03)
        dark = np.zeros(len(Pn), dtype=np.float32)
        if sel.any():
            dark[sel] = stroke_mask(Q[sel], stroke, 0.0008, 0.0017, soft=0.0003, taper_end=0.25)
        dark *= (ws > 0)
        back = ((ws <= 0) & on).astype(np.float32)
        cap = smoothstep(-0.0012, 0.0012, v - 0.042 - 0.010 * (u / EAR_HALF_W) ** 2 + jag * 2)
        patch = back * cap
        light = np.zeros(len(Pn), dtype=np.float32)
        sp2 = spiral_pts(0.0092, 1.6, n=80, inner=0.12, phase=math.pi * 0.3, sense=1.0) + np.array([0.0010, 0.0625])
        if sel.any():
            light[sel] = stroke_mask(Q[sel], sp2, 0.0010, 0.0019, soft=0.0003, taper_end=0.2)
        light *= back
        tipd = on * smoothstep(0.068, 0.088, v)
        res[side] = dict(idx=idx, on=on, inner=inner, tan=tan, deep=deep, dark=dark, patch=patch, light=light,
                         tip=tipd, d2=d2)
    return res


def body_color(P, Nn):
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    nz = Nn[:, 2]
    col = lerp(C_SIDE, C_TOP, np.clip(nz, 0, 1) * 0.85)
    col = lerp(col, C_UNDER, np.clip(-nz, 0, 1) * 0.8)
    head = smoothstep(-0.060, -0.078, Y) * smoothstep(0.160, 0.182, Z)
    col = lerp(col, C_HEAD, head * 0.3)
    patches = fbm(P, 28, 3, seed=2)
    col = col * (1.0 + 0.035 * patches)[:, None]
    # dark lower legs and paws
    leg = smoothstep(0.078, 0.036, Z) * (1 - smoothstep(0.010, 0.0, np.abs(X) - 0.010) * smoothstep(-0.03, -0.02, Y)
                                          * smoothstep(0.062, 0.052, Y))
    col = lerp(col, C_LEG, leg)
    col = lerp(col, C_PAW, smoothstep(0.022, 0.008, Z) * 0.8)
    # tail: underside darker, pattern
    cream_t, tip_t, under_t, on_tail, s_t = tail_pattern(P, 0)
    col = lerp(col, C_TAIL_UNDER, under_t * 0.70 * (1 - tip_t))
    col = lerp(col, C_UNDER, on_tail * smoothstep(0.25, 0.05, s_t) * 0.25)
    tcol = lerp(C_TAIL_CREAM, C_TAIL_TIP, tip_t)
    tcol = lerp(tcol, C_TAIL_FOLD, np.clip(-nz, 0, 1) * 0.45 * tip_t)
    col = lerp(col, tcol, cream_t)
    # cream face, throat, chest, belly
    jag = 0.0022 * fbm(P, 160, 2, seed=11) + 0.0010 * fbm(P, 520, 2, seed=12)
    jag_c = 0.0040 * fbm(P * np.array([1.0, 1.0, 0.35]), 140, 2, seed=13) + jag
    zb = 0.1915 + 0.0045 * np.clip(np.abs(X) / 0.02, 0, 1) + 0.26 * np.clip(Y + 0.108, 0, 0.034)
    yhead = 0.066 - 0.008 * smoothstep(0.170, 0.180, Z) * smoothstep(0.015, 0.03, np.abs(X))
    head_cream = smoothstep(0.0006, -0.0006, Z - zb + jag) * smoothstep(0.0006, -0.0006, Y + yhead + jag_c)
    head_cream *= (Z > 0.160)
    yb = np.interp(Z, [0.055, 0.075, 0.095, 0.120, 0.150, 0.172, 0.200], [-0.030, -0.046, -0.060, -0.068, -0.072, -0.076, -0.078])
    xw = np.interp(Z, [0.055, 0.080, 0.095, 0.100, 0.120, 0.140, 0.190], [0.012, 0.014, 0.024, 0.032, 0.040, 0.046, 0.052])
    chest = smoothstep(0.0007, -0.0007, Y - yb + jag_c) * smoothstep(0.0007, -0.0007, np.abs(X) - xw + jag)
    chest *= (Z > 0.058) * (Z < 0.196)
    belly = smoothstep(0.0008, -0.0008, Z - 0.0735 + jag) * smoothstep(0.0008, -0.0008, np.abs(X) - 0.019 + jag)
    belly *= smoothstep(-0.064, -0.058, Y) * smoothstep(0.050, 0.042, Y) * smoothstep(-0.05, -0.30, nz) * (Z > 0.052)
    cream_col = lerp(C_CREAM, C_CREAM_CHEEK, smoothstep(0.16, 0.18, Z))
    cream_col = lerp(cream_col, C_CREAM_DARK, smoothstep(0.10, 0.07, Z) * 0.6)
    col = lerp(col, cream_col, np.maximum(head_cream, chest))
    col = lerp(col, C_BELLY, belly)
    # undertail patch
    ut = np.linalg.norm((P - np.array([0.0, 0.094, 0.084])) * np.array([1.0, 1.2, 1.0]), axis=1) - 0.023 + jag * 1.5
    utm = smoothstep(0.0015, -0.0015, ut) * (Y > 0.072)
    col = lerp(col, lerp(C_UNDERTAIL, C_UNDERTAIL_RIM, smoothstep(-0.008, 0.0, ut)), utm)
    # brow dots
    for side in (1, -1):
        e = eye_centre(side)
        bd = np.sqrt(((X - side * (abs(e[0]) - 0.0015)) / 0.0049) ** 2 + ((Z - (e[2] + 0.0205)) / 0.0025) ** 2) - 1.0
        col = lerp(col, C_BROW, smoothstep(0.08, -0.08, bd + 0.25 * jag / 0.003) * (Y < -0.09))
    # ears
    ef = ear_fields(P)
    for side, f in ef.items():
        idx, on = f["idx"], f["on"]
        ecol = col[idx].copy()
        tanc = lerp(C_EAR_RIMTAN, C_EAR_TAN, smoothstep(-0.003, -0.007, f["d2"]))
        tanc = lerp(tanc, C_EAR_DEEP, f["deep"] * 0.75)
        ecol = lerp(ecol, hexc("#7e9fc2"), f["inner"] * 0.55)   # inner upper ear: mid blue around the spiral
        ecol = lerp(ecol, tanc, f["tan"])
        ecol = lerp(ecol, C_EAR_TIP, f["tip"] * 0.75)
        ecol = lerp(ecol, C_BACK_PATCH, f["patch"])
        ecol = lerp(ecol, C_BACK_SPIRAL, f["light"])
        ecol = lerp(ecol, C_DARK_MARK, f["dark"])
        col[idx] = np.where(on[:, None], ecol, col[idx])
        Pn = P[idx]
        for spike in ear_tufts(side):
            dd = spike(Pn[:, 0], Pn[:, 1], Pn[:, 2])
            tm = smoothstep(0.0009, 0.0002, dd)
            tuftc = lerp(C_EAR_TUFT, C_EAR_RIMTAN, np.clip(-nz[idx], 0, 1) * 0.5)
            col[idx] = lerp(col[idx], tuftc, tm)
    # mouth line
    for side in (1, -1):          # review 1: no philtrum line, only the smile
        d, _ = polyline_dist(P, MOUTH_S[side] if side in MOUTH_S else mouth_line(side))
        col = lerp(col, C_MOUTH, smoothstep(0.0010, 0.0005, d) * (Y < -0.11))
    # fur streaks along the flow
    tail_w = 1.0 - 0.4 * on_tail
    col = col * (1.0 + 0.06 * tail_w * fur_streaks(P))[:, None]
    return col


def flow_dir(P):
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    n = len(P)
    body = np.tile(np.array([0.0, 1.0, -0.15]), (n, 1))
    leg = np.tile(np.array([0.0, 0.05, 1.0]), (n, 1))
    head = np.tile(np.array([0.0, 0.9, 0.45]), (n, 1))
    wl = smoothstep(0.095, 0.070, Z)[:, None]
    wh = (smoothstep(-0.062, -0.082, Y) * smoothstep(0.16, 0.18, Z))[:, None]
    f = body * (1 - wl) + leg * wl
    f = f * (1 - wh) + head * wh
    C, r, T, s, L = tail_samples(24)
    tdir = T[np.clip(((Y - 0.09) / 0.19 * 23).astype(int), 0, 23)]
    wt = smoothstep(0.095, 0.115, Y)[:, None] * (Z > 0.11)[:, None]
    f = f * (1 - wt) + tdir * wt
    return f / np.linalg.norm(f, axis=1, keepdims=True)


_STREAK = {}


def fur_streaks(P):
    key = len(P)
    if key in _STREAK:
        return _STREAK[key]
    f = flow_dir(P)
    along = np.sum(P * f, axis=1, keepdims=True)
    Q = P - f * along * 0.85                 # stretch 6.7x along the flow
    val = 0.65 * fbm(Q, 900, 2, seed=5) + 0.35 * fbm(Q, 2200, 2, seed=6)
    _STREAK[key] = val
    return val


def body_rough(P, Nn, col):
    lum = col.mean(axis=1)
    return 0.86 + 0.05 * fur_streaks(P) + 0.04 * fbm(P, 40, 2, seed=8) - 0.05 * smoothstep(0.75, 0.85, lum)


def body_height(P, Nn):
    return 0.5 + 0.40 * fur_streaks(P)


# ---- eye --------------------------------------------------------------------------------- #

def eye_frame(side):
    d = eye_dir(side)
    up = np.array([0, 0, 1.0]) - d * d[2]
    up /= np.linalg.norm(up)
    out = np.cross(up, d)          # horizontal, pointing to the fox's outer side
    if out[0] * side < 0:
        out = -out
    return d, up, out


def eye_color_fn(side, centre, radius):
    d, up, out = eye_frame(side)

    def fn(P, Nn):
        rel = P - centre
        a = rel @ out / radius
        b = rel @ up / radius
        sclera, iris_top, iris_bot = hexc("#e3dacf"), hexc("#4e4a52"), hexc("#8f878a")
        ring, pupil, lid = hexc("#3b3840"), hexc("#26242b"), hexc("#241e22")
        ai, bi = a + 0.10, b + 0.02           # iris shifted to the inner side: gaze at the viewer
        ri = np.sqrt(ai ** 2 + bi ** 2) * 0.84  # iris radius ~0.80 of the eye: it fills the eye height
        col = np.tile(sclera, (len(P), 1))
        col = lerp(col, hexc("#c9bfb5"), smoothstep(0.55, 0.95, np.sqrt(a * a + b * b)) * 0.6)
        irisc = lerp(iris_top, iris_bot, smoothstep(0.45, -0.55, bi))
        irisc = lerp(irisc, ring, smoothstep(0.50, 0.66, ri))
        col = lerp(col, irisc, smoothstep(0.71, 0.67, ri))
        col = lerp(col, pupil, smoothstep(0.44, 0.40, ri))
        for (ha, hb, hr) in ((-0.26, 0.26, 0.17), (0.22, -0.30, 0.075)):
            hd = np.sqrt((ai - ha) ** 2 + (bi - hb) ** 2)
            col = lerp(col, np.array([1.0, 1.0, 1.0], dtype=np.float32), smoothstep(hr + 0.02, hr - 0.02, hd))
        rr = np.sqrt(a * a + (b / 0.86) ** 2)
        upper = smoothstep(0.76, 0.84, rr) * smoothstep(-0.10, 0.20, b + 0.15 * a)
        wing = smoothstep(0.06, 0.0, np.abs(b - 0.25 - 0.5 * (a - 0.75))) * smoothstep(0.6, 0.8, a) * (a < 1.05)
        lower = smoothstep(0.90, 0.96, rr) * (b < 0.05)
        col = lerp(col, lid, np.maximum(np.maximum(upper, wing), lower * 0.8))
        back = (rel @ d) < -0.3 * radius
        col[back] = hexc("#2a2a32")
        return col
    return fn


# ----------------------------------------------------------------------------------------- #
# procedural materials (nose, cord, silver, gem)
# ----------------------------------------------------------------------------------------- #

def ramp_material(name, attr, stops, rough, rough_var=0.05, bump=0.0, noise_scale=400.0, metallic=0.0):
    mat, tree, bsdf = kit.principled(name)
    links = tree.links
    at = node(tree, "ShaderNodeAttribute", attribute_name=attr)
    rp = node(tree, "ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*srgb(stops[0][1]), 1)
    els[1].position, els[1].color = stops[-1][0], (*srgb(stops[-1][1]), 1)
    for pos, hx in stops[1:-1]:
        e = els.new(pos)
        e.color = (*srgb(hx), 1)
    links.new(at.outputs["Fac"], rp.inputs["Fac"])
    tc = node(tree, "ShaderNodeTexCoord")
    nz = node(tree, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = noise_scale
    nz.inputs["Detail"].default_value = 4.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = node(tree, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix.inputs["Factor"].default_value = 0.12
    links.new(rp.outputs["Color"], mix.inputs[6])
    links.new(nz.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    mr = node(tree, "ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - rough_var
    mr.inputs["To Max"].default_value = rough + rough_var
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = metallic
    if bump > 0:
        bp = node(tree, "ShaderNodeBump")
        bp.inputs["Distance"].default_value = bump
        bp.inputs["Strength"].default_value = 1.0
        links.new(nz.outputs["Fac"], bp.inputs["Height"])
        links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def srgb(hx):
    c = hexc(hx)
    return tuple(float(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92) for v in c)


# ----------------------------------------------------------------------------------------- #
# build
# ----------------------------------------------------------------------------------------- #

def build():
    clay = body_clay()
    body = clay.to_object("FoxBody", symmetric=False)
    kit.clean(body)
    decimate(body, BODY_TRIS)
    make_manifold(body)
    body.data.shade_smooth()
    body["keep_shading"] = True
    smart_uv(body)
    imgs = paint(body, PAINT_RES, body_color, body_rough, body_height, "fox_body")
    body.data.materials.append(image_material("M_fox_fur", *imgs, bump_dist=0.0005))

    parts = [body]

    # eyes: flattened spheres set into the sockets, painted
    for side in (1, -1):
        e = eye_centre(side)
        d, up, out = eye_frame(side)
        bm = uv_sphere("eye", 32, 16)
        rad = 0.0110                 # Cycle 7: reference eye width 0.16 of the head width, 1.16 x wider than tall
        centre = e - 0.0050 * d
        mat_l = np.stack([out, up, d], 1) * np.array([rad, rad * 0.86, 0.0078])  # local x->out, y->up, z->d
        for v in bm.verts:
            v.co = Vector(tuple(mat_l @ np.array(v.co[:]) + centre))
        me = bpy.data.meshes.new(f"FoxEye_{side}")
        bm.to_mesh(me)
        bm.free()
        eye = bpy.data.objects.new(f"FoxEye_{'L' if side > 0 else 'R'}", me)
        bpy.context.scene.collection.objects.link(eye)
        eye.data.shade_smooth()
        eye["keep_shading"] = True
        eye["keep_uv"] = True
        front_c = centre + 0.0078 * d
        ims = paint(eye, 512, eye_color_fn(side, centre, rad),
                    lambda P, N, c: 0.10 + 0.25 * smoothstep(0.30, 0.15, c.mean(axis=1)) * 0 + 0.04 * fbm(P, 3000, 1, 3),
                    lambda P, N: 0.5 + 0.0 * P[:, 0], f"fox_eye_{'L' if side > 0 else 'R'}")
        eye.data.materials.append(image_material(f"M_fox_eye_{'L' if side > 0 else 'R'}", *ims, bump_dist=0.0001))
        parts.append(eye)

    # nose: rounded triangle, wider at the top
    sn = surface_along(clay, h(0, -0.125, 0.1830), (0, -1, 0))
    nc = sn + np.array([0, 0.0020, 0.0006])
    bm = uv_sphere("nose", 24, 12)
    for v in bm.verts:
        x, y, z = v.co
        wide = 1.0 + 0.30 * z
        v.co = Vector((nc[0] + x * 0.0052 * wide, nc[1] + y * 0.0040, nc[2] + z * 0.0035))
    nose = kit.mesh_object("FoxNose", bm)
    kit.attribute(nose, "nose_t", lambda p: (p.z - nc[2]) / 0.0035 * 0.5 + 0.5 + 0.25 * (nc[1] - p.y) / 0.004)
    nose.data.materials.append(ramp_material("M_fox_nose", "nose_t",
                                             [(0.0, "#2e2628"), (0.55, "#3e3436"), (0.95, "#6f6062")],
                                             rough=0.36, rough_var=0.06, bump=0.00015, noise_scale=900))
    nose.data.shade_smooth()
    nose["keep_shading"] = True
    parts.append(nose)

    parts += collar(clay)
    return parts


def collar(clay):
    """Two-strand braided leather cord around the neck and the silver-set gem pendant."""
    centre = np.array([0.0, -0.070, 0.146])
    vhat = np.array([0.0, 0.814, 0.581])           # loop plane: nape (Y -0.044 Z 0.166) high, front (-0.098, 0.123) low
    xhat = np.array([1.0, 0.0, 0.0])
    cord_r = 0.0034
    loop = []
    for a in np.linspace(0, 2 * math.pi, 97)[:-1]:
        dirn = math.cos(a) * xhat + math.sin(a) * vhat
        p = surface_along(clay, centre, dirn, step=0.0002, limit=0.07)
        loop.append(p + dirn * (cord_r * 0.85))
    loop = np.array(loop)
    # smooth the loop
    for _ in range(4):
        loop = 0.5 * loop + 0.25 * (np.roll(loop, 1, 0) + np.roll(loop, -1, 0))
    # densify
    dense = []
    for k in range(len(loop)):
        a, b = loop[k], loop[(k + 1) % len(loop)]
        for t in np.linspace(0, 1, 4)[:-1]:
            dense.append(a + (b - a) * t)
    dense = np.array(dense)
    n = len(dense)
    T = np.roll(dense, -1, 0) - np.roll(dense, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    outward = dense - centre
    outward -= T * np.sum(outward * T, axis=1, keepdims=True)
    outward /= np.linalg.norm(outward, axis=1, keepdims=True)
    binorm = np.cross(T, outward)
    seglen = np.linalg.norm(np.roll(dense, -1, 0) - dense, axis=1)
    L = float(seglen.sum())
    twists = round(L / 0.0045)                 # one lozenge per ~4.5 mm (collar crop)
    cum = np.concatenate([[0], np.cumsum(seglen)[:-1]]) / L
    rng = random.Random(11)
    jitter = np.array([rng.uniform(-0.15, 0.15) for _ in range(12)])
    wob = np.interp(cum * 12, np.arange(12), jitter)
    strand_r, offset = 0.0019, 0.0015
    parts = []
    leather = cord_material()
    for k in range(2):
        ang = 2 * math.pi * twists * cum + k * math.pi + wob
        path = dense + offset * (np.cos(ang)[:, None] * outward + np.sin(ang)[:, None] * binorm)
        obj = sweep_tube(f"FoxCord_{k}", path, strand_r, ring=8, normals=outward)
        kit.attribute(obj, "cord_lobe", _lobe_field(dense, outward, offset, path))
        obj.data.materials.append(leather)
        obj.data.shade_smooth()
        obj["keep_shading"] = True
        parts.append(obj)

    # pendant at the lowest front point of the loop: the bail ring threads the cord there
    low = int(np.argmin(dense[:, 2] + 0.2 * dense[:, 1]))
    face = np.array([0.0, -0.93, -0.25])
    face /= np.linalg.norm(face)
    upv = np.array([0, 0, 1.0]) - face * face[2]
    upv /= np.linalg.norm(upv)
    bc = dense[low] + upv * 0.0005
    pc = bc - upv * 0.0128
    for _ in range(40):                       # rest the bezel's back on the chest, not inside it
        if clay.sample((pc - face * 0.0014)[None, :])[0] > 0:
            break
        pc = pc + face * 0.0003
    silver = silver_material()
    rot = Vector((0, 0, 1)).rotation_difference(Vector(tuple(face))).to_matrix().to_4x4()
    bez = kit.lathe("FoxPendantBezel", [(0.0094, -0.0012), (0.0105, -0.0002), (0.0106, 0.0012),
                                        (0.0098, 0.0021), (0.0086, 0.0018), (0.0082, 0.0006)],
                    mat=silver, segments=40, cap_bottom=True, cap_top=True)
    bez.matrix_world = Matrix.Translation(Vector(tuple(pc))) @ rot
    gem_mat = gem_material()
    gem = kit.lathe("FoxPendantGem", [(0.0083, 0.0004), (0.0080, 0.0016), (0.0068, 0.0029),
                                      (0.0042, 0.0038), (0.0016, 0.0042)], mat=gem_mat, segments=40,
                    cap_bottom=True, cap_top=True)
    gem.matrix_world = Matrix.Translation(Vector(tuple(pc))) @ rot
    kit.attribute(gem, "gem_r", lambda p: (Vector(tuple(pc)) - p).length / 0.0083)
    bc = pc + upv * 0.0128
    ring = np.array([bc + 0.0030 * (math.cos(a) * upv + math.sin(a) * face)
                     for a in np.linspace(0, 2 * math.pi, 17)[:-1]])
    bail = sweep_tube("FoxPendantBail", ring, 0.0010, ring=6, normals=[r - bc for r in ring])
    bail.data.materials.append(silver)
    for o in (bez, gem, bail):
        o.data.shade_smooth()
        o["keep_shading"] = True
    parts += [bez, gem, bail]
    return parts


def _lobe_field(dense, outward, offset, path):
    from mathutils.kdtree import KDTree
    kd = KDTree(len(path))
    for i, p in enumerate(path):
        kd.insert(Vector(tuple(p)), i)
    kd.balance()

    def fn(p):
        _, i, _ = kd.find(p)
        q = np.array(p[:]) - path[i]
        q /= max(np.linalg.norm(q), 1e-9)
        strand_out = path[i] - dense[i]
        strand_out /= max(np.linalg.norm(strand_out), 1e-9)
        return float(0.5 + 0.35 * (q @ strand_out) + 0.25 * (q @ outward[i]))
    return fn


def cord_material():
    mat, tree, bsdf = kit.principled("M_fox_cord_leather")
    links = tree.links
    at = node(tree, "ShaderNodeAttribute", attribute_name="cord_lobe")
    rp = node(tree, "ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = 0.05, (*srgb("#45291b"), 1)
    els[1].position, els[1].color = 0.95, (*srgb("#b27a55"), 1)
    e = els.new(0.55)
    e.color = (*srgb("#8a5a3d"), 1)
    links.new(at.outputs["Fac"], rp.inputs["Fac"])
    tc = node(tree, "ShaderNodeTexCoord")
    grain = node(tree, "ShaderNodeTexVoronoi")
    grain.inputs["Scale"].default_value = 2500.0
    links.new(tc.outputs["Object"], grain.inputs["Vector"])
    nz = node(tree, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 300.0
    nz.inputs["Detail"].default_value = 3.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = node(tree, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix.inputs["Factor"].default_value = 0.18
    links.new(rp.outputs["Color"], mix.inputs[6])
    links.new(nz.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    mr = node(tree, "ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.42
    mr.inputs["To Max"].default_value = 0.66
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bp = node(tree, "ShaderNodeBump")
    bp.inputs["Distance"].default_value = 0.00012
    links.new(grain.outputs["Distance"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def silver_material():
    mat, tree, bsdf = kit.principled("M_fox_silver")
    links = tree.links
    tc = node(tree, "ShaderNodeTexCoord")
    nz = node(tree, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 600.0
    nz.inputs["Detail"].default_value = 4.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = node(tree, "ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (*srgb("#9fa1a9"), 1)
    rp.color_ramp.elements[1].color = (*srgb("#e3e4ea"), 1)
    links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    links.new(rp.outputs["Color"], bsdf.inputs["Base Color"])
    mr = node(tree, "ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.18
    mr.inputs["To Max"].default_value = 0.36
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 1.0
    sc = node(tree, "ShaderNodeMapping")
    sc.inputs["Scale"].default_value = (1.0, 1.0, 40.0)
    links.new(tc.outputs["Object"], sc.inputs["Vector"])
    scr = node(tree, "ShaderNodeTexNoise")
    scr.inputs["Scale"].default_value = 3000.0
    links.new(sc.outputs["Vector"], scr.inputs["Vector"])
    bp = node(tree, "ShaderNodeBump")
    bp.inputs["Distance"].default_value = 0.00003
    links.new(scr.outputs["Fac"], bp.inputs["Height"])
    links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def gem_material():
    mat, tree, bsdf = kit.principled("M_fox_gem")
    links = tree.links
    at = node(tree, "ShaderNodeAttribute", attribute_name="gem_r")
    rp = node(tree, "ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*srgb("#4a72d6"), 1)
    els[1].position, els[1].color = 1.0, (*srgb("#0c1a5c"), 1)
    e = els.new(0.45)
    e.color = (*srgb("#1f3a99"), 1)
    links.new(at.outputs["Fac"], rp.inputs["Fac"])
    tc = node(tree, "ShaderNodeTexCoord")
    nz = node(tree, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1200.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = node(tree, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix.inputs["Factor"].default_value = 0.10
    links.new(rp.outputs["Color"], mix.inputs[6])
    links.new(nz.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    mr = node(tree, "ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.03
    mr.inputs["To Max"].default_value = 0.08
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.8
    return mat


if __name__ == "__main__":
    kit.run(build, texture=4096)
