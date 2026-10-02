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
VOXEL = 0.0008
BODY_TRIS = 36000
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

EAR_HALF_W = 0.0370      # ear base half width (Cycle 12: 0.034 -> 0.037: with the deep cup the front view read ~20 % narrow)
EAR_CUP = 0.42            # Cycle 12: the ear is a rolled half-cone: its rims stand forward 0.42 x the local half width
                          # (was 13 u^2, ~5 mm on a 40 mm leaf: the far ear in view 2 projected only ~30 % of its width)
EAR_T = (0.0046, 0.0026)  # thickness base -> tip
# Cycle 12: the bowl opens further out (was (0.60, -0.80)): view 2 (camera az 59) showed the far ear edge-on
# (normal . view -0.10) where the reference shows its back ~0.08 W wide, and view 1 had 6 % extra ear width
EAR_OPEN = (0.85, -0.52)  # after orthogonalising to the outward-tilted ear axis the far ear's back faces view 2 ~25 deg


def ear_frame(side):
    base = np.array([side * 0.032, -0.074, 0.226])   # ear base centre (front view: inner edges 0.02 m apart at the top)
    tip = np.array([side * 0.071, -0.071, 0.315])    # ear tips (view 2 at az 55: Y -0.064, Z 0.29-0.32)
    ev = tip - base
    length = float(np.linalg.norm(ev))
    ev = ev / length
    ew = np.array([side * EAR_OPEN[0], EAR_OPEN[1], 0.06])  # opening faces out-forward (view 2 sees the far ear back)
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


def ear_hw(v, length):
    """Half width of the ear leaf at height v (the pointed arch of ear_d2)."""
    R = (EAR_HALF_W ** 2 + length ** 2) / (2 * EAR_HALF_W)
    return np.maximum(np.sqrt(np.maximum(R * R - np.asarray(v, float) ** 2, 0.0)) - (R - EAR_HALF_W), 0.004)


def ear_cup(u, v, length):
    """Forward offset of the cupped leaf at (u, v) and its slope d/du."""
    hw = ear_hw(np.clip(v, 0.0, length), length)
    return EAR_CUP * u * u / hw, 2.0 * EAR_CUP * u / hw


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
        c, sl = ear_cup(u, v, length)
        d3 = (np.abs(w - c) - th * 0.5) / np.sqrt(1.0 + sl * sl)
        return S.smax(d2, d3, 0.0012)
    m = length + 0.03
    return S.Prim(fn, base - m, base + m)


def ear_point(side, u, v, w_off):
    base, eu, ev, ew, length = ear_frame(side)
    th = EAR_T[0] + (EAR_T[1] - EAR_T[0]) * min(max(v / length, 0), 1)
    w = float(ear_cup(u, v, length)[0]) + th * 0.5 + w_off
    return base + u * eu + v * ev + w * ew


def ear_tuft_locks(side):
    """The cream fur tuft in the ear's bowl: one tuft of three soft lobes fanning up from the inner base,
    lying on the inner face (~2 mm thick), as flat locks (seeded lengths)."""
    rng = random.Random(31 if side > 0 else 47)
    locks = []
    t = np.linspace(0.0, 1.0, 9)
    for (u0, v0, u1, v1, hw) in ((-0.006, 0.003, -0.016, 0.044, 0.0058),
                                 (-0.001, 0.002, 0.000, 0.037, 0.0062),
                                 (0.004, 0.003, 0.012, 0.030, 0.0054),
                                 (0.008, 0.002, 0.019, 0.020, 0.0044)):
        v1 = v1 * (1.0 + rng.uniform(-0.08, 0.08))
        uu = u0 + (u1 - u0) * t
        vv = v0 + (v1 - v0) * t
        w = np.maximum(hw * (0.75 + 0.25 * np.sin(math.pi * np.minimum(t / 0.35, 1.0) * 0.5)) * (1 - smoothstep(0.35, 1.0, t)) ** 0.8, 0.0005)
        th = np.maximum(0.0024 * (1.0 - 0.55 * t), 0.0006)      # Cycle 12: thicker, layered lobes
        lift = 0.0018 * smoothstep(0.3, 1.0, t)                    # the tips stand off the bowl: shadow lines
        P = np.array([ear_point(side, uu[k], vv[k], th[k] - 0.0004 + lift[k]) for k in range(len(t))])
        base, eu, ev, ew, length = ear_frame(side)
        N = np.array([ew - float(ear_cup(uu[k], vv[k], length)[1]) * eu for k in range(len(t))])
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        locks.append(dict(P=P, N=N, w=w, th=th, t=t))
    return locks


def sd_ear_tuft(side):
    segs = [seg for lk in ear_tuft_locks(side) for seg in lock_segments(lk)]
    pts = np.concatenate([lk["P"] for lk in ear_tuft_locks(side)])

    def fn(x, y, z):
        d = None
        for seg in segs:
            ds, _, _ = lock_seg_sd(seg, x, y, z)
            d = ds if d is None else S.smin(d, ds, 0.0010)
        return d
    return S.Prim(fn, pts.min(0) - 0.006, pts.max(0) + 0.006)


# tail centre line (side view, Y, Z) and vertical half-thickness; lateral = 1.12 x
# Cycle 12: the distal part 4-8 mm lower and the end 12 mm further back (view 2 overlay: build too high along the
# distal top, the reference tip further out; views 1/3: the distal tail stood as a dome above the head)
TAIL_PTS = np.array([(0.086, 0.125), (0.097, 0.131), (0.108, 0.137), (0.120, 0.145), (0.135, 0.156),
                     (0.152, 0.171), (0.170, 0.182), (0.188, 0.194), (0.208, 0.205), (0.227, 0.221),
                     (0.246, 0.232), (0.264, 0.236), (0.284, 0.234)])
# vertical half-thickness of the tail's fur (outer surface of the locks); review 1: max thickness 8 % less,
# the distal fifth tapering to a point
# Cycle 12: the end is a broad tongue tapering to a point, not a needle (grid render: at s 0.8-0.9 the reference end is
# ~1.5x thicker than the old 0.026 / 0.012 / 0.007; 0.036 / 0.025 / 0.014 made a blunt club)
TAIL_RZ = np.array([0.024, 0.027, 0.030, 0.035, 0.042, 0.047, 0.049, 0.048, 0.045, 0.034, 0.020, 0.009,
                    0.004])
# lateral / vertical radius per point. Review 1: from behind the tail is 0.76 W wide (render 0.89 W) and the
# front view shows it beside the shoulders at 0.46-0.58 H: widest low (Z 0.14-0.19, half width ~0.053),
# narrower above (half 0.047 at Z 0.19-0.21)
# Cycle 12: x1.06 over the proximal half: the back-view egg is 0.057 m half wide (build 0.054, view 3 w/h -2 %) and
# the front view shows the tail beside the shoulders to |X| ~0.06
# and the root flares: the front view shows the tail beside the shoulders at Z 0.09-0.17 to |X| 0.064 (view 1 missed
# 11-13 % there), the back view's egg is 0.05 half wide at Z 0.125 and 0.057 at Z 0.145
TAIL_W = np.array([1.60, 1.70, 1.70, 1.60, 1.36, 1.22, 1.13, 1.03, 0.98, 1.0, 1.0, 1.0, 1.0])
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

# ---- the tail as fur: dense underfur along the tail bone, guard-hair locks lying on it ------------- #
# A fox tail is a mass of fur round a thin bone: dense short underfur, and over it long guard hairs grouped
# in locks that grow from the root side and flow to the end, each lock wide at its root and tapering to a
# point, lying over the roots of the next locks; lock tips lift off at the outline and the end locks
# converge on the tip. The spiral and the curls are markings painted on the fur.

_TAIL_TAB = {}


def tail_env(s):
    """Tail envelope at arc parameters s (array; beyond 1 it continues along the last tangent):
    centre (n, 3), tangent, up axis, vertical and lateral outer radius."""
    if not _TAIL_TAB:
        C, r, T, ss, L = tail_samples(240)
        seg = np.linalg.norm(np.diff(TAIL_PTS, axis=0), axis=1)
        sp = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
        _TAIL_TAB.update(C=C, r=r, T=T, s=ss, L=L, W=np.interp(ss, sp, TAIL_W))
    t = _TAIL_TAB
    s = np.atleast_1d(np.asarray(s, float))
    sc = np.clip(s, 0.0, 1.0)
    C = np.stack([np.interp(sc, t["s"], t["C"][:, i]) for i in range(3)], 1)
    T = np.stack([np.interp(sc, t["s"], t["T"][:, i]) for i in range(3)], 1)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    over = np.maximum(s - 1.0, 0.0)
    C = C + T * (over * t["L"])[:, None]
    rz = np.interp(sc, t["s"], t["r"]) * np.clip(1.0 - over / 0.12, 0.25, 1.0)
    rx = rz * np.interp(sc, t["s"], t["W"])
    up = np.stack([np.zeros(len(s)), -T[:, 2], T[:, 1]], 1)
    return C, T, up, rz, rx


def tail_surface(s, phi, inset):
    """Points at (s, phi) on the tail envelope pulled in by `inset` (phi 0 top, +pi/2 = +X side), and the
    outward radial direction."""
    C, T, up, rz, rx = tail_env(s)
    X = np.array([1.0, 0.0, 0.0])
    a = np.maximum(rz - inset, 0.0)
    b = np.maximum(rx - inset, 0.0)
    P = C + (a * np.cos(phi))[:, None] * up + (b * np.sin(phi))[:, None] * X
    Nr = (np.cos(phi) / np.maximum(rz, 1e-4))[:, None] * up + (np.sin(phi) / np.maximum(rx, 1e-4))[:, None] * X
    Nr /= np.linalg.norm(Nr, axis=1, keepdims=True)
    return P, Nr, rz, rx


# rings of guard-hair locks: (start s, length in s, count)
TAIL_RINGS = [(0.00, 0.30, 10), (0.09, 0.30, 11), (0.18, 0.30, 12), (0.27, 0.29, 12), (0.36, 0.28, 12),
              (0.45, 0.27, 12), (0.54, 0.26, 11), (0.63, 0.25, 10)]
# end locks: (start s, phi, end s, half width) with a fixed width; they converge on the tip
# Cycle 12: (start s, phi, end s, half width, flick, converge). The guard hairs converge to a soft point carried by
# the top lock; the outline breaks into tongues at two notches (view 2): a tuft flicking off the top edge near
# s 0.86 and a lower tongue ending early (s 0.94) with its tip lifting off back-down
# build 13: the top tuft's 7.8 mm lift stood as a horn from behind and the five roots at s 0.60-0.70 made a ring
# crease: roots staggered (0.55-0.70) and sunk deeper, top tuft lift 2.6 -> 0.9
TAIL_END_LOCKS = [(0.62, 0.10, 1.01, 0.013, 0.0, True), (0.70, 1.45, 1.00, 0.011, 0.0, True),
                  (0.66, -1.45, 1.00, 0.011, 0.0, True), (0.55, 0.30, 0.86, 0.011, 0.9, False),
                  (0.59, math.pi - 0.15, 0.94, 0.012, 2.0, False)]
TAIL_LOCKS = []
# Cycle 12: this style draws the tail's fur as soft streaks, not scales: low lock relief
TAIL_LOCK_TH = 0.12      # lock half thickness / half width (was 0.25)
TAIL_SINK = 0.0006       # how far a lock's root dives under the fur (was 2.4 mm)
TAIL_LOCK_BLEND = 0.0025  # smooth union of the locks with the fur (was 0.9 mm)


def tail_locks():
    """Centre lines, normals, half widths and half thicknesses of every guard-hair lock (seeded)."""
    if TAIL_LOCKS:
        return TAIL_LOCKS
    rng = random.Random(23)
    npts = 20
    t = np.linspace(0.0, 1.0, npts)
    prof = (0.55 + 0.45 * np.sin(0.5 * math.pi * np.minimum(t / 0.3, 1.0))) * (1.0 - smoothstep(0.3, 1.0, t)) ** 0.75
    specs = []
    for ri, (s0, ln, m) in enumerate(TAIL_RINGS):
        off = (0.5 if ri % 2 else 0.0) * 2 * math.pi / m
        phis = [off + 2 * math.pi * k / m + rng.uniform(-0.18, 0.18) * 2 * math.pi / m for k in range(m)]
        big = None
        if abs(s0 - 0.54) < 1e-6:
            big = int(np.argmin([abs(math.atan2(math.sin(ph), math.cos(ph))) for ph in phis]))
        if abs(s0 - 0.63) < 1e-6:
            big = int(np.argmin([abs(abs(math.atan2(math.sin(ph), math.cos(ph))) - math.pi) for ph in phis]))
        for k, ph in enumerate(phis):
            flick = 0.0 if k != big else 0.35
            specs.append(dict(s0=s0 + rng.uniform(-0.015, 0.015), s1=None, ln=ln * rng.uniform(0.92, 1.08), phi=ph,
                              drift=rng.uniform(-0.1, 0.1), flick=flick, wj=rng.uniform(0.88, 1.12), m=m, fixed=None))
    for (s0, ph, s1, hw, fl, conv) in TAIL_END_LOCKS:
        specs.append(dict(s0=s0, s1=s1, ln=s1 - s0, phi=ph, drift=0.0, flick=fl, wj=1.0, m=None, fixed=hw, conv=conv))
    for sp in specs:
        ss = sp["s0"] + sp["ln"] * t
        ph = sp["phi"] + sp["drift"] * t
        if sp["fixed"] is not None:                  # end locks converge on the tail's end (the notch locks do not)
            if sp.get("conv", True):
                ph = sp["phi"] * (1.0 - smoothstep(0.5, 1.0, t))
            _, _, _, rz, rx = tail_env(ss)
            w = sp["fixed"] * prof
        else:
            _, _, _, rz, rx = tail_env(ss)
            w = math.pi * np.sqrt(rz * rx) / sp["m"] * 1.35 * sp["wj"] * prof
        w = np.maximum(w, 0.0020 if sp["fixed"] is not None else 0.00035)   # Cycle 12: a soft point, not a needle
        # flat locks lying like shingles: the root dives under the locks rooted behind it, the tip lies on top
        th = np.clip(TAIL_LOCK_TH * w, 0.0004, 0.0022)
        if sp["fixed"] is not None:
            th = np.minimum(th, 0.5 * rz + 0.0005)
        sink = (TAIL_SINK if sp["fixed"] is None else 3.0 * TAIL_SINK) * (1.0 - t) ** 1.2   # rises to the tip: it lies over younger roots
        lift = np.where(t > 0.6, 0.003 * sp["flick"] * ((t - 0.6) / 0.4) ** 2, 0.0)
        P, Nr, rz, rx = tail_surface(ss, ph, th + sink - lift)
        R = np.maximum(np.sqrt((rz * np.cos(ph)) ** 2 + (rx * np.sin(ph)) ** 2) - th - sink, 0.003)
        w = np.minimum(w, np.maximum(1.3 * R, 0.0012))     # a lock never wraps further than ~75 deg round
        TAIL_LOCKS.append(dict(P=P, N=Nr, w=w, th=th, t=t, s=ss, phi=ph, R=R))
    return TAIL_LOCKS


def lock_segments(lk):
    """Per segment of a lock: start, tangent, normal, binormal, length, half widths and thicknesses."""
    P, N = lk["P"], lk["N"]
    out = []
    for i in range(len(P) - 1):
        d = P[i + 1] - P[i]
        ln = float(np.linalg.norm(d))
        if ln < 1e-7:
            continue
        T = d / ln
        n = N[i] + N[i + 1]
        n = n - T * (n @ T)
        n /= np.linalg.norm(n)
        B = np.cross(T, n)
        R = lk.get("R")
        out.append((P[i], T, n, B, ln, lk["w"][i], lk["w"][i + 1], lk["th"][i], lk["th"][i + 1],
                    lk["t"][i], lk["t"][i + 1], 1e3 if R is None else R[i], 1e3 if R is None else R[i + 1]))
    return out


def lock_seg_sd(seg, x, y, z):
    """Signed distance (approx.) to one lock segment: an elliptical cross-section (lateral half width w,
    radial half thickness th) swept along it and bent round the surface it lies on (radius R), with rounded
    caps beyond its ends. Returns d, tau, qb/w."""
    p0, T, n, B, ln, w0, w1, h0, h1 = seg[:9]
    rx_, ry_, rz_ = x - p0[0], y - p0[1], z - p0[2]
    along = rx_ * T[0] + ry_ * T[1] + rz_ * T[2]
    tau = np.clip(along / ln, 0.0, 1.0)
    qt = along - tau * ln
    qn = rx_ * n[0] + ry_ * n[1] + rz_ * n[2]
    qb = rx_ * B[0] + ry_ * B[1] + rz_ * B[2]
    w = w0 + (w1 - w0) * tau
    th = h0 + (h1 - h0) * tau
    R = seg[11] + (seg[12] - seg[11]) * tau
    qc = np.minimum(np.abs(qb), R)                  # the lock wraps round the tail: follow its curvature
    qn = qn + (R - np.sqrt(np.maximum(R * R - qc * qc, 0.0)))
    # Cycle 12: the cap beyond each segment end is short (half a segment + the thickness), not the half width:
    # a cap as long as w (up to 17 mm) runs straight on along the tangent where the lock bends round the
    # tapering envelope and stood out of the fur as a thin fin.
    cap = np.minimum(w, 0.6 * ln + th)
    k0 = np.sqrt((qb / w) ** 2 + (qn / th) ** 2 + (qt / cap) ** 2)
    k1 = np.sqrt((qb / (w * w)) ** 2 + (qn / (th * th)) ** 2 + (qt / (cap * cap)) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), tau, qb / w


def tail_clay():
    clay = S.Clay((-0.075, 0.055, 0.085), (0.075, 0.315, 0.300), voxel=TAIL_VOXEL, far=0.008)
    for p in tail_underfur_prims(0.88):
        clay.add(p, blend=0.010)
    blend = TAIL_LOCK_BLEND
    margin = blend + 3 * TAIL_VOXEL
    for lk in tail_locks():
        ext = (lk["w"].max() + lk["th"].max())
        lo, hi = lk["P"].min(0) - ext, lk["P"].max(0) + ext
        sl, _, _, _ = clay._box(lo, hi, margin)
        if any(q.stop <= q.start for q in sl):
            continue
        Dl = np.full(tuple(q.stop - q.start for q in sl), clay.far, np.float32)
        for seg in lock_segments(lk):
            p0, T, ln = seg[0], seg[1], seg[4]
            e = max(seg[5], seg[6], seg[7], seg[8])
            slo = np.minimum(p0, p0 + T * ln) - e
            shi = np.maximum(p0, p0 + T * ln) + e
            ss_, x, y, z = clay._box(slo, shi, margin)
            if any(q.stop <= q.start for q in ss_):
                continue
            d, _, _ = lock_seg_sd(seg, x, y, z)
            loc = tuple(slice(max(a.start, b.start) - b.start, min(a.stop, b.stop) - b.start) for a, b in zip(ss_, sl))
            src = tuple(slice(max(a.start, b.start) - a.start, min(a.stop, b.stop) - a.start) for a, b in zip(ss_, sl))
            Dl[loc] = np.minimum(Dl[loc], np.broadcast_to(d, tuple(q.stop - q.start for q in ss_))[src])
        clay.D[sl] = np.clip(S.smin(clay.D[sl], Dl, blend), -clay.far, clay.far)
    return clay


_LOCKF = {}


def lock_fields(P):
    """Per point: the visible lock (index, -1 = underfur), its t along the lock, the lateral coordinate,
    the nearest and second-nearest lock distance."""
    key = len(P)
    if key in _LOCKF:
        return _LOCKF[key]
    n = len(P)
    d1 = np.full(n, np.inf)
    d2 = np.full(n, np.inf)
    own = np.full(n, -1, dtype=np.int64)
    tt = np.zeros(n)
    lat = np.zeros(n)
    for li, lk in enumerate(tail_locks()):
        ext = lk["w"].max() + lk["th"].max() + 0.002
        lo, hi = lk["P"].min(0) - ext, lk["P"].max(0) + ext
        sel = np.nonzero(np.all((P >= lo) & (P <= hi), axis=1))[0]
        if not len(sel):
            continue
        Q = P[sel]
        best = np.full(len(sel), np.inf)
        bt = np.zeros(len(sel))
        bl = np.zeros(len(sel))
        for seg in lock_segments(lk):
            d, tau, ql = lock_seg_sd(seg, Q[:, 0], Q[:, 1], Q[:, 2])
            b = d < best
            best[b] = d[b]
            bt[b] = (seg[9] + (seg[10] - seg[9]) * tau)[b]
            bl[b] = ql[b]
        cur1, cur2 = d1[sel], d2[sel]
        new_first = best < cur1
        d2[sel] = np.where(new_first, cur1, np.minimum(cur2, best))
        d1[sel] = np.where(new_first, best, cur1)
        own[sel] = np.where(new_first, li, own[sel])
        tt[sel] = np.where(new_first, bt, tt[sel])
        lat[sel] = np.where(new_first, bl, lat[sel])
    own[d1 > 0.0007] = -1
    _LOCKF[key] = (own, tt, lat, d1, d2)
    return _LOCKF[key]


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

MOUTH_S = {}     # surface points of the carved mouth lines (filled by body_clay, painted by body_color)


def mouth_line(side, n=28):
    """The smile as a smooth curve (Catmull-Rom through MOUTH, the mirrored second point as the phantom before the
    centre so both halves meet with one tangent: a soft wave, no kink under the nose)."""
    P = np.array([(side * p[0], p[1], p[2]) for p in MOUTH])
    ph0 = P[1] * np.array([-1, 1, 1])
    ph1 = P[-1] + (P[-1] - P[-2])
    Q = np.vstack([ph0, P, ph1])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0, 1, n // (len(Q) - 3), endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return np.array(out)


# ----------------------------------------------------------------------------------------- #
# the snout: rostrum + upper lips, lower jaw, nose leather
# ----------------------------------------------------------------------------------------- #
# A fox's snout is the long narrow rostrum of the skull under short fur: the nasal bones make a straight
# bridge from the stop (between the eyes' inner corners, just below their height) down to the nose; the
# maxillae slope out and down to the upper lips, so a cross-section is a rounded trapezoid, narrow on top
# and widest at the lip line; the upper lips hang a little over the narrow lower jaw (mandible), whose small
# chin sits behind and below the nose; the nose leather (rhinarium) caps the tip, its top continuing the
# bridge. This style keeps that build, shortened a little and rounded: a straight bridge, a tapering wedge
# seen from above, a dark rounded-triangle nose at the very tip, a smile running from under the nose back to
# below the eye's inner corner, a small cream chin. Measured (Cycle 14) on view 2 (0.307 mm/px) relative to
# the near eye's inner corner (X 0.015, Y -0.1405, Z 0.201) and on view 1 (0.448 mm/px).
# the root is as wide as the eyes' inner corners (X 0.015 at Y -0.1405): the face there carries the eyes
SN_Y = np.array([-0.120, -0.130, -0.140, -0.150, -0.161, -0.168, -0.174])   # stations, back -> tip
SN_ZT = np.array([0.2080, 0.2060, 0.2045, 0.2020, 0.1975, 0.1945, 0.1918])  # bridge top (midline)
SN_ZB = np.array([0.1810, 0.1800, 0.1790, 0.1777, 0.1776, 0.1780, 0.1800])  # lower edge of the upper lips
SN_WT = np.array([0.0190, 0.0175, 0.0155, 0.0110, 0.0074, 0.0060, 0.0050])  # half width where the top rounds
SN_WB = np.array([0.0230, 0.0215, 0.0195, 0.0158, 0.0112, 0.0086, 0.0064])  # half width at the lip line
# front of the clay snout by height: inside the nose leather at its height, then the upper lip (philtrum)
# leaning back under the nose to the mouth (view 2: nose bottom Y -0.171 Z 0.184, mouth start -0.167 Z 0.178)
SN_TIP_Z = np.array([0.1760, 0.1785, 0.1840, 0.1900])
SN_TIP_Y = np.array([-0.1655, -0.1672, -0.1702, -0.1738])
JAW_Y = np.array([-0.112, -0.128, -0.140, -0.150, -0.158, -0.1645])
JAW_ZB = np.array([0.1580, 0.1625, 0.1655, 0.1680, 0.1710, 0.1745])         # underside of the lower jaw
JAW_W = np.array([0.0190, 0.0162, 0.0135, 0.0110, 0.0090, 0.0066])          # its half width
JAW_TIP = -0.1660         # front of the chin
# nose leather: front view 13.0 x 8.2 mm rounded triangle, top 0.1912 at the front, its top following the bridge
NOSE_FRONT, NOSE_TOP, NOSE_HW, NOSE_H = -0.1764, 0.1916, 0.0080, 0.0086
NOSE_DEPTH = 0.0070       # the pad's top runs 7 mm back before it dives under the bridge fur
# the mouth: from under the nose back to the corners below the eyes' inner corners, lowest 10 mm out, corners up
MOUTH = [(0.0, -0.1656, 0.1771), (0.0052, -0.1622, 0.1772), (0.0105, -0.1580, 0.1774), (0.0150, -0.1500, 0.1780),
         (0.0177, -0.1440, 0.1797)]


def sd_trapezoid2(px, pz, r1, r2, he):
    """Exact 2D distance to an isosceles trapezoid centred at 0: half width r1 at the bottom (z = -he), r2 at
    the top (z = he) (Inigo Quilez)."""
    px = np.abs(px)
    k1x, k1z = r2, he
    k2x, k2z = r2 - r1, 2.0 * he
    cax = px - np.minimum(px, np.where(pz < 0.0, r1, r2))
    caz = np.abs(pz) - he
    t = np.clip(((k1x - px) * k2x + (k1z - pz) * k2z) / (k2x * k2x + k2z * k2z), 0.0, 1.0)
    cbx, cbz = px - k1x + k2x * t, pz - k1z + k2z * t
    s = np.where((cbx < 0.0) & (caz < 0.0), -1.0, 1.0)
    return s * np.sqrt(np.minimum(cax * cax + caz * caz, cbx * cbx + cbz * cbz))


def _section_sd(x, z, zt, zb, wt, wb, rr, bulge=0.0):
    """Rounded-trapezoid cross-section (narrow top wt, wide bottom wb, from zb to zt), rounded by rr, its sides
    swelling out by `bulge` at mid height (cheek-side muscle and fur over the bone, never flat planes)."""
    he = np.maximum(0.5 * (zt - zb) - rr, 1e-4)
    zc = 0.5 * (zt + zb)
    s = np.clip((z - zc) / np.maximum(0.5 * (zt - zb), 1e-4), -1, 1)
    return sd_trapezoid2(x, z - zc, np.maximum(wb - rr, 1e-4), np.maximum(wt - rr, 1e-4), he) - rr \
        - bulge * (1 - s * s)


def sd_muzzle():
    """The rostrum with the upper lips: rounded-trapezoid sections along Y, rounded front under the nose."""
    def fn(x, y, z):
        yc = np.clip(y, SN_Y[-1], SN_Y[0])
        yi = -yc        # np.interp needs increasing x
        Yi = -SN_Y
        zt, zb = np.interp(yi, Yi, SN_ZT), np.interp(yi, Yi, SN_ZB)
        wt, wb = np.interp(yi, Yi, SN_WT), np.interp(yi, Yi, SN_WB)
        rr = np.minimum(np.minimum(0.0075, 0.95 * wt), 0.45 * (zt - zb))
        d = _section_sd(x, z, zt, zb, wt, wb, rr, bulge=0.0015)
        d = S.smax(d, np.interp(z, SN_TIP_Z, SN_TIP_Y) - y, 0.0040)            # the tip, rounded
        return S.smax(d, y - SN_Y[0], 0.004)
    return S.Prim(fn, np.array([-0.028, SN_TIP_Y[-1] - 0.003, 0.170]), np.array([0.028, SN_Y[0] + 0.002, 0.214]))


def sd_jaw():
    """The lower jaw: a narrow rounded wedge under the upper lips ending in a small chin behind the nose."""
    def fn(x, y, z):
        yc = np.clip(y, JAW_Y[-1], JAW_Y[0])
        yi, Yi = -yc, -JAW_Y
        zb = np.interp(yi, Yi, JAW_ZB)
        zt = np.interp(yi, -SN_Y, SN_ZB) + 0.0035          # tucked under the upper lips
        w = np.interp(yi, Yi, JAW_W)
        rr = np.minimum(0.0045, 0.8 * w)
        d = _section_sd(x, z, zt, zb, 0.85 * w, w, rr, bulge=0.0008)
        d = S.smax(d, JAW_TIP - y, 0.0050)
        return S.smax(d, y - JAW_Y[0], 0.010)
    return S.Prim(fn, np.array([-0.024, JAW_TIP - 0.002, 0.152]), np.array([0.024, JAW_Y[0] + 0.002, 0.188]))


def nose_top(y):
    return NOSE_TOP + 0.45 * (y - NOSE_FRONT)


def sd_nose():
    """Nose leather: a rounded triangle seen from the front (wide top, point down toward the lip), its top
    following the bridge, its front domed and leaning back toward the bottom."""
    def tri(px, pz):
        # isosceles triangle, top edge at pz = 0 (half width NOSE_HW), apex at pz = -NOSE_H; rounded by rn
        rn = 0.0024
        hw, hh = NOSE_HW - 1.7 * rn, NOSE_H - 2.4 * rn
        return sd_trapezoid2(px, pz + rn + 0.5 * hh, 0.0002, hw, 0.5 * hh) - rn

    def fn(x, y, z):
        zt = nose_top(y) + 0.0004 - 0.0010 * np.clip(x / NOSE_HW, -1, 1) ** 2    # domed across, like the bridge
        d2 = tri(x, z - zt)
        yf = NOSE_FRONT + 0.0030 * np.clip((zt - z) / NOSE_H, 0, 1.2) ** 1.5 + 0.0040 * (x / NOSE_HW) ** 2
        d = S.smax(d2, yf - y, 0.0034)
        # the back of the pad dives under the fur: its top falls away behind NOSE_DEPTH
        d = S.smax(d, (y - (NOSE_FRONT + NOSE_DEPTH)) * 0.6 + (z - zt) * 0.8, 0.002)
        return S.smax(d, y - (NOSE_FRONT + 0.0110), 0.001)
    return S.Prim(fn, np.array([-0.009, NOSE_FRONT - 0.002, NOSE_TOP - NOSE_H - 0.003]),
                  np.array([0.009, NOSE_FRONT + 0.011, NOSE_TOP + 0.007]))


def build_nose(clay):
    """The nose leather as its own mesh (moist dark leather), meshed from its SDF at 0.2 mm."""
    nc = S.Clay((-0.010, NOSE_FRONT - 0.003, NOSE_TOP - NOSE_H - 0.004), (0.010, NOSE_FRONT + 0.012, NOSE_TOP + 0.008),
                voxel=0.0002, far=0.003)
    nc.add(sd_nose())
    nose = nc.to_object("nose")
    kit.clean(nose)
    decimate(nose, 1600)
    nose.data.shade_smooth()
    nose["keep_shading"] = True
    # nose_t: 0 low / under, 1 the lit top (a soft highlight band on top, as the reference paints it)
    kit.attribute(nose, "nose_t", lambda p: max(0.0, min(1.0, 1.0 - (nose_top(p.y) - p.z) / 0.0045)) * 0.85
                  + 0.15 * max(0.0, min(1.0, (p.y - NOSE_FRONT) / 0.004)))
    nose.data.materials.append(ramp_material("M_nose", "nose_t",
                                             [(0.0, "#36292c"), (0.55, "#4e3b3e"), (0.92, "#7a6a6c")],
                                             rough=0.34, rough_var=0.06, bump=0.00012, noise_scale=900))
    return nose


# ----------------------------------------------------------------------------------------- #
# the body clay
# ----------------------------------------------------------------------------------------- #

def body_clay():
    clay = S.Clay((-0.082, -0.184, -0.004), (0.082, 0.302, 0.312), voxel=VOXEL, far=0.022)
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
    clay.add(sd_muzzle(), blend=0.009)     # Cycle 14: the rostrum and upper lips (was a round cone)
    clay.add(sd_jaw(), blend=0.012)        # Cycle 14: the lower jaw with its small chin (was a round cone)
    clay.add(E(h(0.027, -0.090, 0.181), hr(0.025, 0.026, 0.020)), blend=0.012, mirror=True)
    # cheek ruff: three fluffy pointed tufts per side, out and back (front view: fluff to |X| 0.06)
    for side in (1, -1):
        rng = random.Random(5 if side > 0 else 9)
        # Cycle 12: the front view's cheek tufts reach |X| 0.064 (view 1 missed 11-13 % middle left/right)
        for (a, b, r0) in (((0.028, -0.074, 0.182), (0.055, -0.060, 0.181), 0.0120),
                           ((0.027, -0.072, 0.172), (0.052, -0.058, 0.167), 0.0110),
                           ((0.024, -0.072, 0.163), (0.042, -0.059, 0.156), 0.0090)):
            j = rng.uniform(-0.0025, 0.0025)
            # Cycle 14+: soft fur tufts, not spikes (view 2): rounded tips, softer blend
            clay.add(C(h(side * a[0], a[1], a[2]), h(side * (b[0] + j), b[1] + j * 0.5, b[2] + j), r0 * HSR, 0.0028),
                     blend=0.009)

    # ears with their inner fur tufts
    for side in (1, -1):
        clay.add(sd_ear(side), blend=0.008)
        clay.add(sd_ear_tuft(side), blend=0.0010)

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
        clay.add(T([(side * 0.029, 0.050, 0.090), (side * 0.0270, 0.046, 0.058), (x0, y0 + 0.0105, 0.030),
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
        # the centre is shallow: the two lip halves meet in a soft wave, not a notch
        S_, _ = clay.stroke(mouth_line(side), 0.0010, [0.0002, 0.0004, 0.0005, 0.0005, 0.0005], op="sub", blend=0.0006)
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
EYE_TILT = 0.0                            # the measured outline below carries the tilt (outer corner 2 mm up)
EYE = {}                                  # per side: the face's height map over the eye region
# The opening between the eyelids seen from the front (view 1, 0.433 mm/px, traced on the line centre):
# a toward the outer corner, b up, metres from the opening centre. Upper lid edge U(a) and lower lid edge
# L(a); the inner side is a near-vertical edge at a = -EYE_AIN; the outer corner is a point 2 mm up.
EYE_AOUT, EYE_AIN = 0.0115, 0.0112
_EA = np.array([-0.0112, -0.0100, -0.0087, -0.0061, -0.0035, -0.0009, 0.0017, 0.0043, 0.0069, 0.0095, 0.0115])
_EU = np.array([0.0005, 0.0015, 0.0040, 0.0070, 0.0088, 0.0096, 0.0096, 0.0088, 0.0069, 0.0040, 0.0019]) * np.array([1.0, 1.0, 1.06, 1.10, 1.12, 1.12, 1.12, 1.12, 1.10, 1.06, 1.0])
_EL = np.array([-0.0065, -0.0075, -0.0083, -0.0092, -0.0096, -0.0096, -0.0095, -0.0089, -0.0065, -0.0013, 0.0019])
EYE_A, EYE_B = 0.5 * (EYE_AOUT + EYE_AIN), 0.0096


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


def eye_parts(a, b):
    """The three edges' fields (> 0 outside): upper lid, lower lid, inner side."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    fu = b - np.interp(a, _EA, _EU)
    fl = np.interp(a, _EA, _EL) - b
    fi = -(a + EYE_AIN)
    fo = a - EYE_AOUT
    return fu, fl, fi, fo


def eye_opening_field(a, b):
    """Distance-like field of the eye opening seen from the front (< 0 inside, metres): the traced almond,
    pointed at the outer corner, a rounded vertical edge on the inner side."""
    fu, fl, fi, fo = eye_parts(a, b)
    f = S.smax(fu * 0.80, fl * 0.80, 0.0012)
    f = S.smax(f, fi, 0.0024)
    return np.maximum(f, fo)


def eye_upper_weight(a, b):
    """1 where the nearest eyelid edge is the upper lid or the inner side (the lash line), 0 on the lower."""
    fu, fl, fi, fo = eye_parts(a, b)
    w = smoothstep(-0.0008, 0.0008, fu - fl)
    return np.maximum(w, smoothstep(-EYE_AIN + 0.0035, -EYE_AIN + 0.0010, a))


def eye_outline(grow=0.0, n=120, th0=0.0, th1=2 * math.pi):
    """The opening's outline (a, b) grown by `grow`, from the outer corner over the top, down the inner
    side and back along the lower lid; th0/th1 pick a part of it as a fraction of 2 pi."""
    au = np.linspace(EYE_AOUT, -EYE_AIN, 60)
    ub = np.interp(au, _EA, _EU) + grow
    ai = np.full(12, -EYE_AIN - grow)
    bi = np.linspace(_EU[0], _EL[0], 12)
    al = np.linspace(-EYE_AIN, EYE_AOUT, 60)
    lb = np.interp(al, _EA, _EL) - grow
    A = np.concatenate([au, ai, al])
    B = np.concatenate([ub, bi, lb])
    k0, k1 = int(len(A) * th0 / (2 * math.pi)), int(len(A) * th1 / (2 * math.pi))
    return A[k0:k1], B[k0:k1]


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


IRIS_C = (-0.0042, -0.0006)              # iris centre in the opening (a, b): 4.2 mm toward the nose, 0.6 mm low
R_IRIS = 0.0075                            # Cycle 12: 15 mm across (the reference iris is ~65 % of the eye width; 16.6 mm read 77 %)
EYE_GROW = 0.0016                          # the eye's front runs this far under the eyelids


def eyeball_setup(clay, side):
    """Read the face over the eye region before cutting (the eye's front and the eyelids follow it)."""
    EYE[side] = dict(hm=face_height_map(clay, side))


def eye_front_y(side, X, Z):
    """Y of the eyeball's visible front (sclera, iris under the cornea) at front-view X, Z: just under the
    face in the middle, 0.7 mm under it at the eyelid edges (the lid margin), diving under the lids beyond
    the opening; the cornea bulges a little over the iris."""
    a, b = eye_local(side, X, Z)
    f = eye_opening_field(a, b)
    fy = face_y(EYE[side]["hm"], X, Z)
    inside = 0.0007 - 0.0006 * smoothstep(0.0, 0.004, -f)
    inset = np.where(f < 0, inside, 0.0007 + 1.0 * f)
    ri = np.sqrt((a - IRIS_C[0]) ** 2 + (b - IRIS_C[1]) ** 2)
    cornea = 0.0004 * smoothstep(R_IRIS, 0.3 * R_IRIS, ri) * smoothstep(0.0, -0.0015, f)
    return fy + inset - cornea


def sd_eye_opening(side):
    """The opening between the eyelids: the skin in front of the eye's front inside the almond is cleared
    (to 1.2 mm behind it, so the eye surface stands clear of the clay)."""
    def fn(x, y, z):
        a, b = eye_local(side, x, z)
        return np.maximum(eye_opening_field(a, b), y - (eye_front_y(side, x, z) + 0.0012))
    x0, x1 = sorted((side * (EYE_X - EYE_AIN - 0.002), side * (EYE_X + EYE_AOUT + 0.002)))
    return S.Prim(fn, np.array([x0, -0.18, EYE_Z - 0.012]), np.array([x1, -0.09, EYE_Z + 0.012]))


def eyeball_mesh(side, name):
    """The eyeball's visible front as a closed thin shell: polar rings from the iris side of the opening out
    to the outline grown under the lids, a back 1 mm behind, the rim bridged."""
    A, B = eye_outline(EYE_GROW)
    seg = np.hypot(np.diff(A, append=A[:1]), np.diff(B, append=B[:1]))
    cum = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, cum[-1], 65)[:-1]
    A = np.interp(u, cum, np.append(A, A[0]))
    B = np.interp(u, cum, np.append(B, B[0]))
    ca, cb = 0.5 * (EYE_AOUT - EYE_AIN), 0.0
    rhos = np.linspace(0.0, 1.0, 14)[1:] ** 0.85
    bm = bmesh.new()
    rings_f, rings_b = [], []
    for back in (0, 1):
        rows = []
        for r in rhos:
            aa, bb = ca + r * (A - ca), cb + r * (B - cb)
            X, Z = eye_world2d(side, aa, bb)
            Y = eye_front_y(side, X, Z) + 0.0010 * back
            rows.append([bm.verts.new((float(X[k]), float(Y[k]), float(Z[k]))) for k in range(len(A))])
        X, Z = eye_world2d(side, np.array([ca]), np.array([cb]))
        Y = eye_front_y(side, X, Z) + 0.0010 * back
        cen = bm.verts.new((float(X[0]), float(Y[0]), float(Z[0])))
        n = len(A)
        for k in range(n):
            q = (cen, rows[0][k], rows[0][(k + 1) % n])
            bm.faces.new(q if back else q[::-1])
            for i in range(len(rows) - 1):
                q = (rows[i][k], rows[i + 1][k], rows[i + 1][(k + 1) % n], rows[i][(k + 1) % n])
                bm.faces.new(q if back else q[::-1])
        (rings_b if back else rings_f).append(rows[-1])
    n = len(A)
    for k in range(n):
        fr, bk = rings_f[0], rings_b[0]
        bm.faces.new((fr[k], fr[(k + 1) % n], bk[(k + 1) % n], bk[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def lash_line_points(side):
    """The upper eyelid's edge from the wing tip over the top and down the inner side (front-view a, b)."""
    a, b = eye_outline(0.0006)
    a, b = a[:72], b[:72]
    wa = np.array([EYE_AOUT + 0.0016, EYE_AOUT + 0.0007])
    wb = np.array([0.0019 + 0.0009, 0.0019 + 0.0004])
    return np.concatenate([wa, a]), np.concatenate([wb, b])


def carve_eyes(clay):
    """The eye openings and the lash-line ridge on the upper eyelid edge (the face is read before cutting)."""
    for side in (1, -1):
        eyeball_setup(clay, side)
    for side in (1, -1):
        clay.sub(sd_eye_opening(side), blend=0.0005)
        a, b = lash_line_points(side)
        X, Z = eye_world2d(side, a, b)
        Y = face_y(EYE[side]["hm"], X, Z) - 0.001
        n = len(a)
        radii = np.interp(np.arange(n), [0, 2, 12, 30, n - 1], [0.0005, 0.0010, 0.0012, 0.0010, 0.0006])
        clay.stroke(np.stack([X, Y, Z], 1), radii, 0.00045, op="add", blend=0.0006, n=120)   # Cycle 12: smoother


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
        up_w = eye_upper_weight(a, b)
        w_up = 0.0010 + 0.0004 * smoothstep(-EYE_AIN, EYE_AOUT, a)
        m = smoothstep(w_up + 0.00025, w_up - 0.00025, f) * up_w
        wing = np.array([(EYE_AOUT - 0.0010, 0.0021), (EYE_AOUT + 0.0008, 0.0024), (EYE_AOUT + 0.0020, 0.0029)])
        m = np.maximum(m, stroke_mask(np.stack([a, b], 1), wing, 0.0008, 0.0003, soft=0.00015, taper_end=0.45))
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
        bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=200)   # Cycle 12: build 12 left a 7-edge... larger hole open
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
C_LEG, C_PAW = hexc("#6c90b3"), hexc("#5a7aa4")       # review 1 Fix 8: lower legs 0.06 lighter
C_CREAM, C_CREAM_CHEEK, C_CREAM_DARK = hexc("#e6d6c4"), hexc("#eee2d3"), hexc("#cdb9a5")
C_BELLY = hexc("#b19c89")
C_BROW = hexc("#ddd6cc")
C_TAIL_TIP, C_TAIL_CREAM, C_TAIL_FOLD = hexc("#dfd9d4"), hexc("#d2c9c2"), hexc("#b5aca8")
C_TAIL_UNDER = hexc("#4d6c94")
TAIL_UNDER_W = 0.60      # Cycle 12: from behind the underside is #6586a0 / #486586 (0.70: 0.12 too dark; 0.45: far too light)
C_EAR_TAN, C_EAR_DEEP, C_EAR_RIMTAN = hexc("#dcc6b4"), hexc("#b89c8b"), hexc("#e6d3c2")
C_EAR_TUFT = hexc("#e8d9c6")
C_EAR_RIM = hexc("#8cb3cb")
C_DARK_MARK, C_EAR_TIP = hexc("#3d5585"), hexc("#4a6a9a")
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


def tail_pattern(P, side_seed, split=False):
    """Cream mask (0..1), tip mask, underside mask, tail membership and arc parameter, from the
    tail coordinates (evaluated only near the tail)."""
    n = len(P)
    out = [np.zeros(n, dtype=np.float32) for _ in range(6 if split else 5)]
    near = np.nonzero((P[:, 1] > 0.07) & (P[:, 2] > 0.105))[0]
    if len(near) == 0:
        return out
    Pn = P[near]
    s, r, dist, phi, L = tail_coords(Pn)
    on_tail = ((dist < np.maximum(r * 1.48, 0.012 + 0.024 * smoothstep(0.85, 1.0, s)) + 0.004) & (s > 0.03)).astype(np.float32)
    aphi = np.abs(phi)
    # Cycle 13: smooth brush-stroke edges as on the reference (the fbm 90/300 jag frayed every cream edge)
    jag = 0.014 * fbm(Pn, 60, 2, seed=21) + 0.003 * fbm(Pn, 200, 2, seed=22)
    # Cycle 7: the reference tail is mostly blue with cream markings; only the last ~18 % is all cream
    # Cycle 12: on the sides and underside the cream end starts earlier (back view: the top third of the egg is cream)
    tip = smoothstep(0.012, -0.012, (0.80 - 0.08 * smoothstep(1.3, 2.2, np.abs(phi)) - s) + jag * 1.4)
    # Cycle 12, placed with the (s, phi) grid render against view 2: the cream end is solid on top from s ~0.5 with
    # thin cream flame tongues reaching back to ~0.35; a blue tongue at phi ~0.9 runs up to s ~0.8 between the top
    # cream and the spiral; the spiral sits at s 0.54, phi 1.1, its outer arm sweeping down (phi ~1.9) and back
    # toward the base along the lower side as a tapered band ending near s 0.33
    tongue = -0.12 * np.maximum(0.0, np.cos(aphi * 9.0 + 0.6)) ** 6 * (aphi < 0.50)
    # Cycle 15: back toward the build-12 boundary (view 2 reference: the top cream band from s ~0.4 is about a third of
    # the tail's depth, phi 0-0.65; Cycles 13-14 pushed it to s 0.56-0.83 there and the band read thin)
    s_b = np.interp(aphi, [0.0, 0.20, 0.45, 0.65, 0.85, 1.20, 1.50, 1.80],
                    [0.40, 0.42, 0.46, 0.55, 0.72, 0.86, 0.88, 0.90]) + tongue
    blaze = smoothstep(0.010, -0.010, (s_b - s) + jag) * (aphi < 1.95)
    Q = np.stack([phi * 0.045, s * L], 1)          # chart: angle x 45 mm around, arc length along
    curls = np.zeros(len(Pn), dtype=np.float32)
    for sg in (1.0, -1.0):
        # the spiral (centre s 0.50, phi 1.25) winds out to its underside and its outer arm sweeps on toward the
        # tip as a broad band (phi 1.45 at s 0.62, 1.15 at 0.72, 0.85 at 0.80) into the cream end, enclosing the
        # blue tongue above it (reference points read through the (s, phi) grid render, view 2)
        big = 0.0255 if sg > 0 else 0.0245          # t3 render: spiral 0.6x the reference's
        turns = 1.25
        cen = np.array([sg * 1.25 * 0.045, 0.50 * L])
        pts = spiral_pts(big, turns, n=90, inner=0.10, phase=-turns * 2 * math.pi, sense=sg) + cen
        ctrl = np.array([pts[-1], [sg * 1.47 * 0.045, 0.60 * L], [sg * 1.18 * 0.045, 0.71 * L],
                         [sg * 0.85 * 0.045, 0.80 * L], [sg * 0.60 * 0.045, 0.88 * L]])
        tt = np.linspace(0.0, 1.0, 30)
        kk = np.linspace(0.0, 1.0, len(ctrl))
        arm = np.stack([np.interp(tt, kk, ctrl[:, 0]), np.interp(tt, kk, ctrl[:, 1])], 1)
        for _ in range(3):
            arm[1:-1] = 0.5 * arm[1:-1] + 0.25 * (arm[:-2] + arm[2:])
        stroke = np.concatenate([pts, arm[1:]])
        sel = np.abs(Q[:, 0] - cen[0]) < 0.08
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], stroke, 0.0030, 0.0075, soft=0.0005,
                                                            taper_end=0.04))
        # the lower band: from under the spiral back toward the base along the lower side, tapering to a point
        band = np.array([[sg * 1.55 * 0.045, 0.62 * L], [sg * 1.62 * 0.045, 0.52 * L], [sg * 1.66 * 0.045, 0.42 * L],
                         [sg * 1.68 * 0.045, 0.34 * L]])
        sel = np.abs(Q[:, 0] - band[1, 0]) < 0.03
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], band, 0.0048, 0.0040, soft=0.0005, taper_end=0.6))
        # a small wave hook on the top cream edge (view 2: hooked crests at the upper left of the cream)
        hcen = np.array([sg * 0.62 * 0.045, 0.45 * L])
        hk = spiral_pts(0.0060, 0.80, n=30, inner=0.25, phase=math.pi * 0.2, sense=sg) + hcen
        sel = np.abs(Q[:, 0] - hcen[0]) < 0.02
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], hk, 0.0010, 0.0024, soft=0.0005, taper_end=0.2))
        # underside curls left and right of the underside blaze (back view)
        ucen = np.array([sg * 2.5 * 0.045, 0.60 * L])
        up = spiral_pts(0.012 if sg > 0 else 0.011, 1.3, n=60, inner=0.12, phase=math.pi * 1.4, sense=-sg) + ucen
        sel = np.abs(Q[:, 0] - ucen[0]) < 0.03
        if sel.any():
            curls[sel] = np.maximum(curls[sel], stroke_mask(Q[sel], up, 0.0012, 0.0032, soft=0.0005, taper_end=0.15))
    # underside blaze from the tip toward the middle, with tongues (back view)
    au = math.pi - aphi
    tongue_u = -0.10 * np.maximum(0.0, np.cos(au * 5.0 + 0.3)) ** 3
    s_u = 0.58 + 0.30 * (au / 0.80) ** 1.5 + tongue_u
    blaze_u = smoothstep(0.010, -0.010, (s_u - s) + jag) * (au < 0.80)
    zone = np.maximum(np.maximum(blaze, blaze_u), tip) * on_tail
    cream = np.maximum(zone, curls) * on_tail
    tip = tip * on_tail
    under = smoothstep(1.6, 2.9, aphi) * on_tail
    vals_all = (zone, curls * on_tail, tip, under, on_tail, s) if split else (cream, tip, under, on_tail, s)
    for arr, vals in zip(out, vals_all):
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
        ws = w - ear_cup(u, v, L)[0]
        d2 = ear_d2(u, v, L)
        on = (np.abs(ws) < th * 0.5 + 0.0035) & (d2 < 0.0025) & (v > -0.002)
        inner = ((ws > 0) & on).astype(np.float32)
        jag = 0.0012 * fbm(Pn, 400, 2, seed=40 + side)
        # Cycle 12: the tan inner skin is a long pointed teardrop (the ear outline shrunk to 72 % of its length,
        # 3 mm blue rim) reaching up to the spiral, not a blob cut at mid height
        d2t = ear_d2(u * 1.08, v, L * 0.72)
        tan = inner * smoothstep(0.0, -0.0010, d2 + 0.0030 + jag) * smoothstep(0.0006, -0.0006, d2t + 0.0010 + jag)
        deep = smoothstep(-0.006, -0.016, d2) * smoothstep(0.05, 0.015, v)
        Q = np.stack([u, v], 1)
        cen = np.array([0.0025, 0.0640])
        sp = spiral_pts(0.0095, 1.5, n=80, inner=0.12, phase=math.pi * 0.9, sense=-1.0) + cen
        tl = np.array([sp[-1] + np.array([0.0060 * t, -0.017 * t + 0.002 * t * t]) for t in np.linspace(0, 1, 10)])
        stroke = np.concatenate([sp, tl[1:]])
        sel = on & (np.abs(v - 0.06) < 0.03)
        dark = np.zeros(len(Pn), dtype=np.float32)
        if sel.any():
            dark[sel] = stroke_mask(Q[sel], stroke, 0.0012, 0.0019, soft=0.0003, taper_end=0.25)   # 3 mm stroke
        dark *= (ws > 0)
        back = ((ws <= 0) & on).astype(np.float32)
        cap = smoothstep(-0.0012, 0.0012, v - 0.031 - 0.012 * (u / EAR_HALF_W) ** 2 + jag * 2)   # 60 % of the back
        patch = back * cap
        light = np.zeros(len(Pn), dtype=np.float32)
        sp2 = spiral_pts(0.0092, 1.6, n=80, inner=0.12, phase=math.pi * 0.3, sense=1.0) + np.array([0.0010, 0.0625])
        if sel.any():
            light[sel] = stroke_mask(Q[sel], sp2, 0.0010, 0.0019, soft=0.0003, taper_end=0.2)
        light *= back
        tipd = on * smoothstep(0.062, 0.090, v)
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
    col = lerp(col, C_TAIL_UNDER, under_t * TAIL_UNDER_W * (1 - tip_t))
    col = lerp(col, C_UNDER, on_tail * smoothstep(0.25, 0.05, s_t) * 0.25)
    tcol = lerp(C_TAIL_CREAM, C_TAIL_TIP, tip_t)
    tcol = lerp(tcol, C_TAIL_FOLD, np.clip(-nz, 0, 1) * 0.45 * tip_t)
    col = lerp(col, tcol, cream_t)
    # cream face, throat, chest, belly
    jag = 0.0022 * fbm(P, 160, 2, seed=11) + 0.0010 * fbm(P, 520, 2, seed=12)
    jag_c = 0.0040 * fbm(P * np.array([1.0, 1.0, 0.35]), 140, 2, seed=13) + jag
    # Cycle 12: 8 mm lower under the eyes: the front close-up showed the cream touching the eye's lower edge
    # (reference: the lower lid line, then a ~3 mm blue skin band, then cream)
    zb = 0.1835 + 0.0030 * np.clip(np.abs(X) / 0.02, 0, 1) + 0.26 * np.clip(Y + 0.108, 0, 0.034)
    # Cycle 14: on the snout the cream climbs the sides to just under the bridge (view 2: the blue is only the
    # bridge's top band, the cream reaches the nose's top at the tip and ~0.196 halfway)
    zc = np.interp(-Y, [0.145, 0.157, 0.170, 0.180], [0.1962, 0.1956, 0.1920, 0.1905])
    wm = smoothstep(-0.141, -0.152, Y) * smoothstep(0.024, 0.016, np.abs(X))
    zb = zb + (zc - zb) * wm
    yhead = 0.066 - 0.008 * smoothstep(0.170, 0.180, Z) * smoothstep(0.015, 0.03, np.abs(X))
    head_cream = smoothstep(0.0006, -0.0006, Z - zb + jag) * smoothstep(0.0006, -0.0006, Y + yhead + jag_c)
    head_cream *= (Z > 0.160)
    yb = np.interp(Z, [0.055, 0.075, 0.095, 0.120, 0.150, 0.172, 0.200], [-0.030, -0.046, -0.060, -0.068, -0.072, -0.076, -0.078])
    xw = np.interp(Z, [0.055, 0.080, 0.095, 0.100, 0.120, 0.140, 0.190], [0.012, 0.014, 0.024, 0.032, 0.040, 0.046, 0.052])
    chest = smoothstep(0.0007, -0.0007, Y - yb + jag_c) * smoothstep(0.0007, -0.0007, np.abs(X) - xw + jag)
    chest *= (Z > 0.058) * (Z < 0.196)
    belly = smoothstep(0.0008, -0.0008, Z - 0.084 + jag) * smoothstep(0.0008, -0.0008, np.abs(X) - 0.024 + jag)
    belly *= smoothstep(-0.064, -0.058, Y) * smoothstep(0.040, 0.032, Y) * smoothstep(-0.05, -0.30, nz) * (Z > 0.052)
    cream_col = lerp(C_CREAM, C_CREAM_CHEEK, smoothstep(0.16, 0.18, Z))
    cream_col = lerp(cream_col, C_CREAM_DARK, smoothstep(0.10, 0.07, Z) * 0.6)
    col = lerp(col, cream_col, np.maximum(head_cream, chest))
    col = lerp(col, C_BELLY, belly)
    # undertail patch
    ut = (np.linalg.norm((P - np.array([0.0, 0.094, 0.076])) / np.array([0.020, 0.024, 0.027]), axis=1) - 1.0) * 0.022 + jag * 1.5
    utm = smoothstep(0.0015, -0.0015, ut) * (Y > 0.060)
    col = lerp(col, lerp(C_UNDERTAIL, C_UNDERTAIL_RIM, smoothstep(-0.008, 0.0, ut)), utm)
    # brow dots
    for side in (1, -1):
        e = eye_centre(side)
        # Cycle 12: measured in the front close-up: dot centres +-25 mm (were +-18) and 2 mm higher, 12 x 5.4 mm
        bd = np.sqrt(((X - side * (abs(e[0]) + 0.0052)) / 0.0058) ** 2 + ((Z - (e[2] + 0.0225)) / 0.0027) ** 2) - 1.0
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
        for tuft in (sd_ear_tuft(side),):
            dd = tuft(Pn[:, 0], Pn[:, 1], Pn[:, 2])
            tm = smoothstep(0.0009, 0.0002, dd)
            tuftc = lerp(C_EAR_TUFT, C_EAR_RIMTAN, np.clip(-nz[idx], 0, 1) * 0.5)
            col[idx] = lerp(col[idx], tuftc, tm)
    # eyelid edges: the lash line (with its wing) and the thin lower lid line
    lash_m, lower_m = eyelid_marks(P)
    col = lerp(col, hexc("#241e24"), lash_m)
    col = lerp(col, hexc("#4a3a3a"), lower_m * 0.85)
    # mouth line
    for side in (1, -1):          # review 1: no philtrum line, only the smile
        d, _ = polyline_dist(P, MOUTH_S[side] if side in MOUTH_S else mouth_line(side))
        col = lerp(col, C_MOUTH, smoothstep(0.0010, 0.0005, d) * (Y < -0.11))
    # fur streaks along the flow
    tail_w = (1.0 - 0.4 * on_tail) * (1.0 - np.maximum(lash_m, lower_m))   # Cycle 12: the painted lid lines stay crisp
    col = col * (1.0 + 0.05 * tail_w * fur_streaks(P))[:, None]
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
    Q = P - f * along * 0.92                 # stretch 12x along the flow (review 1 Fix 11: coarser, longer grain)
    val = 0.65 * fbm(Q, 600, 2, seed=5) + 0.35 * fbm(Q, 1400, 2, seed=6)
    _STREAK[key] = val
    return val


# ---- tail fields --------------------------------------------------------------------------- #

def tail_color(P, Nn):
    """The tail's painted flame zones (cream end, tongues, curls and the spiral) over blue fur. Cycle 12: the
    reference paints the zones softly over the fur, lock outlines are invisible: the zone colour leads (75 %)
    and each lock only bends the zone edge a little (25 %); lock shading is faint; fine streaks run along the
    flow. Underside lighter (view 3 centre measured #6586a0), cream duller on the lit top (view 2 #dbdbdb)."""
    nz = Nn[:, 2]
    zone, curls, tip, under, on_tail, s_t = tail_pattern(P, 0, split=True)
    own, tt, lat, d1, d2 = lock_fields(P)
    locks = tail_locks()
    mids = np.array([lk["P"][int(round(0.45 * (len(lk["P"]) - 1)))] + lk["N"][int(round(0.45 * (len(lk["P"]) - 1)))]
                     * lk["th"][int(round(0.45 * (len(lk["P"]) - 1)))] for lk in locks])
    zl, _, tipl, _, onl, _ = tail_pattern(mids, 0, split=True)
    lz = np.maximum(zl, tipl)
    on_lock = own >= 0
    cream = np.where(on_lock, 0.75 * zone + 0.25 * lz[np.maximum(own, 0)], zone)
    blue = lerp(C_SIDE, C_TOP, np.clip(nz, 0, 1) * 0.6)
    blue = lerp(blue, C_TAIL_UNDER, under * TAIL_UNDER_W * (1 - tip))
    blue = blue * (1.0 + 0.035 * fbm(P, 28, 3, seed=2))[:, None]
    cr = lerp(C_TAIL_CREAM, C_TAIL_TIP, tip)
    cr = lerp(cr, C_TAIL_FOLD, np.clip(-nz, 0, 1) * 0.45 * tip)
    cr = lerp(cr, C_TAIL_FOLD, np.clip(nz, 0, 1) * 0.25)          # the lit top would blow out
    col = lerp(blue, cr, cream)
    col = lerp(col, cr, curls)
    shade = np.where(on_lock, 0.975 + 0.025 * smoothstep(0.0, 0.5, tt), 0.97)
    gap = np.where(np.isfinite(d2) & np.isfinite(d1), d2 - d1, 1.0)
    shade = shade * (1.0 - 0.025 * smoothstep(0.0008, 0.0, gap) * on_lock)
    shade = shade * (1.0 + 0.10 * fur_streaks(P))     # Cycle 12: the reference tail shows clear strand streaks
    return col * shade[:, None]


def tail_rough(P, Nn, col):
    return 0.86 + 0.05 * fur_streaks(P) + 0.03 * fbm(P, 40, 2, seed=8)


def tail_height(P, Nn):
    own, tt, lat, d1, d2 = lock_fields(P)
    on_lock = own >= 0
    grooves = 0.07 * np.cos(3.0 * math.pi * np.clip(lat, -1, 1)) * smoothstep(0.0, 0.15, tt)   # Cycle 12: faint
    return np.where(on_lock, 0.5 + 0.32 * fur_streaks(P) + grooves, 0.45 + 0.28 * fur_streaks(P))


def build_tail():
    clay = tail_clay()
    tail = clay.to_object("tail", symmetric=False)
    kit.clean(tail)
    decimate(tail, TAIL_TRIS)
    make_manifold(tail)
    tail.data.shade_smooth()
    tail["keep_shading"] = True
    smart_uv(tail)
    imgs = paint(tail, PAINT_RES, tail_color, tail_rough, tail_height, "tail")
    tail.data.materials.append(image_material("M_tail_fur", *imgs, bump_dist=0.0005))
    return tail


def body_rough(P, Nn, col):
    lum = col.mean(axis=1)
    return 0.86 + 0.05 * fur_streaks(P) + 0.04 * fbm(P, 40, 2, seed=8) - 0.05 * smoothstep(0.75, 0.85, lum)


def body_height(P, Nn):
    lash_m, lower_m = eyelid_marks(P)          # Cycle 12: no fur grain across the painted lid lines
    return 0.5 + 0.22 * fur_streaks(P) * (1.0 - np.maximum(lash_m, lower_m))


# ---- eye --------------------------------------------------------------------------------- #

def eyeball_color_fn(side):
    """The eyeball's paint in front-view coordinates (the fox looks at the viewer): sclera, the iris disc
    with its limbal ring and radial fibres, the pupil and the catch lights; the strip of eye right under the
    eyelid edges is dark (it continues the lash line and the lower lid line); the back is dark."""
    # Cycle 12: warmer (front close-up: reference sclera warm cream, iris warm grey-brown)
    sclera, sclera_edge, sclera_lid = hexc("#eadfcf"), hexc("#cbbcae"), hexc("#bbab9f")
    iris_top, iris_mid, iris_bot = hexc("#5a4f52"), hexc("#8e8080"), hexc("#b9aaa3")
    limbal, pupil, pupil_bot = hexc("#463d42"), hexc("#2c2a31"), hexc("#3d3a44")
    lash, lower = hexc("#241e24"), hexc("#4a3a3a")
    white, white2 = np.array([1.0, 1.0, 1.0], dtype=np.float32), hexc("#e6e3e8")

    def fn(P, Nn):
        a, b = eye_local(side, P[:, 0], P[:, 2])
        u, v = a - IRIS_C[0], b - IRIS_C[1]          # u outward, v up, from the iris centre
        f = eye_opening_field(a, b)
        upw = eye_upper_weight(a, b)
        col = np.tile(sclera, (len(P), 1))
        col = lerp(col, sclera_edge, smoothstep(-0.0030, -0.0006, f) * 0.8)
        col = lerp(col, sclera_lid, smoothstep(-0.0045, -0.0010, f) * upw)
        col = col * (1.0 + 0.02 * fbm(P, 2500, 2, seed=61))[:, None]
        ri = np.sqrt(u * u + v * v)
        ang = np.arctan2(v, u)
        tv = np.clip(v / R_IRIS, -1, 1)
        irisc = lerp(iris_mid, iris_top, smoothstep(0.0, 0.85, tv))
        irisc = lerp(irisc, iris_bot, smoothstep(0.0, -0.85, tv))
        fib = 0.03 * np.sin(ang * 37.0 + 3.0 * np.sin(ang * 5.0)) * smoothstep(0.3 * R_IRIS, 0.6 * R_IRIS, ri)
        irisc = irisc * (1.0 + fib + 0.03 * fbm(P, 4000, 2, seed=62))[:, None]
        irisc = lerp(irisc, limbal, smoothstep(0.80 * R_IRIS, 0.90 * R_IRIS, ri))
        col = lerp(col, irisc, smoothstep(R_IRIS + 0.0002, R_IRIS - 0.0002, ri))
        pe = np.sqrt((u / 0.0043) ** 2 + ((v - 0.0003) / 0.0056) ** 2)
        pc = lerp(pupil, pupil_bot, smoothstep(0.0, -0.0064, v - 0.0003) * 0.8)
        col = lerp(col, pc, smoothstep(1.04, 0.96, pe))
        h1 = np.sqrt((u + 0.0010) ** 2 + (v - 0.0038) ** 2)
        col = lerp(col, white, smoothstep(0.0023, 0.0019, h1))
        h2 = np.sqrt((u - 0.0045) ** 2 + (v + 0.0050) ** 2)
        col = lerp(col, white2, smoothstep(0.0011, 0.0007, h2) * 0.6)     # small second catch light
        col = lerp(col, lash, smoothstep(-0.0011, -0.0006, f) * upw)
        col = lerp(col, lower, smoothstep(-0.0007, -0.0003, f) * (1.0 - upw))
        col[Nn[:, 1] > 0.3] = hexc("#2a2a32")
        return col
    return fn


def eyeball_rough(side):
    """Wet and glossy over the opening (the cornea); matte where the ball meets the eyelid edges."""
    def fn(P, Nn, col):
        a, b = eye_local(side, P[:, 0], P[:, 2])
        f = eye_opening_field(a, b)
        return 0.08 + 0.42 * smoothstep(-0.0012, -0.0006, f) + 0.02 * fbm(P, 3000, 1, seed=63)
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
    body = clay.to_object("body", symmetric=False)
    kit.clean(body)
    decimate(body, BODY_TRIS)
    make_manifold(body)
    body.data.shade_smooth()
    body["keep_shading"] = True
    smart_uv(body)
    imgs = paint(body, PAINT_RES, body_color, body_rough, body_height, "body")
    body.data.materials.append(image_material("M_body_fur", *imgs, bump_dist=0.0005))

    parts = [body, build_tail()]

    # eyeballs: the visible front of each eye, lying just under the eyelids, painted in front-view coordinates
    for side in (1, -1):
        nm = "eyeball_left" if side > 0 else "eyeball_right"
        eye = eyeball_mesh(side, nm)
        eye.data.shade_smooth()
        eye["keep_shading"] = True
        smart_uv(eye, margin=0.01)
        ims = paint(eye, 1024, eyeball_color_fn(side), eyeball_rough(side), lambda P, N: 0.5 + 0.0 * P[:, 0], nm)
        eye.data.materials.append(image_material(f"M_{nm}", *ims, bump_dist=0.0001))
        parts.append(eye)

    parts.append(build_nose(clay))     # Cycle 14: nose leather at the tip of the bridge

    parts += collar(clay)
    return parts


def collar(clay):
    """Two-strand braided leather cord around the neck and the silver-set gem pendant."""
    centre = np.array([0.0, -0.070, 0.152])          # Cycle 12: 6 mm higher (view 1: cord sides 6 mm, pendant 10 mm low)
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
    # the cord hangs by gravity: a V toward the pendant at the front, resting on the chest
    front = loop[:, 1] < centre[1]
    # Cycle 12: the pendant's weight pulls the cord straight from where it rests on the neck sides (under the cheek
    # tufts, |X| 0.037, Z 0.154 in view 1) down to a V at the bail (Z 0.131): a V, not a U round the neck
    ax = np.abs(loop[:, 0])
    zv = 0.131 + (0.154 - 0.131) * np.clip(ax / 0.037, 0.0, 1.0) ** 1.15
    wv = (1.0 - smoothstep(0.030, 0.044, ax)) * front
    loop[:, 2] = loop[:, 2] * (1.0 - wv) + zv * wv
    for k in np.nonzero(front)[0]:
        dirn = loop[k] - centre
        dirn[2] = 0.0
        dirn /= np.linalg.norm(dirn)
        for _ in range(60):
            if clay.sample(loop[k][None, :])[0] > 0.85 * cord_r:
                break
            loop[k] = loop[k] + dirn * 0.0002
    for _ in range(2):
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
    twists = round(L / 0.0090)                 # review 1: lozenges as long as the reference's
    cum = np.concatenate([[0], np.cumsum(seglen)[:-1]]) / L
    rng = random.Random(11)
    jitter = np.array([rng.uniform(-0.15, 0.15) for _ in range(12)])
    wob = np.interp(cum * 12, np.arange(12), jitter)
    strand_r, offset = 0.0020, 0.0018
    parts = []
    leather = cord_material()
    for k in range(2):
        ang = 2 * math.pi * twists * cum + k * math.pi + wob
        path = dense + offset * (np.cos(ang)[:, None] * outward + np.sin(ang)[:, None] * binorm)
        obj = sweep_tube(f"collar_cord_strand_{k}", path, strand_r, ring=8, normals=outward)
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
    bc = dense[low] - upv * 0.0030             # the bail loop's centre, 3 mm under the cord it threads
    pc = bc - upv * (0.0042 + 0.0121 - 0.0010)  # the bezel hangs under the bail
    for _ in range(40):                       # rest the bezel's back on the chest, not inside it
        if clay.sample((pc - face * 0.0014)[None, :])[0] > 0:
            break
        pc = pc + face * 0.0003
    silver = silver_material()
    rot = Vector((0, 0, 1)).rotation_difference(Vector(tuple(face))).to_matrix().to_4x4()
    bez = kit.lathe("pendant_bezel", [(0.0108, -0.0012), (0.0119, -0.0002), (0.0121, 0.0012),
                                        (0.0113, 0.0022), (0.0090, 0.0019), (0.0083, 0.0006)],
                    mat=silver, segments=40, cap_bottom=True, cap_top=True)
    bez.matrix_world = Matrix.Translation(Vector(tuple(pc))) @ rot
    gem_mat = gem_material()
    # Cycle 12: a higher cabochon dome (5.3 mm, was 4.2): the flat dome caught no highlight (reference: a large
    # white catch light on a bright domed gem)
    gem = kit.lathe("pendant_gem", [(0.0083, 0.0004), (0.0081, 0.0018), (0.0070, 0.0034),
                                      (0.0046, 0.0047), (0.0018, 0.0053)], mat=gem_mat, segments=40,
                    cap_bottom=True, cap_top=True)
    gem.matrix_world = Matrix.Translation(Vector(tuple(pc))) @ rot
    # Cycle 15: radial distance from the gem's axis (the 3D distance from the base put the dome's top at 0.64 of the
    # ramp, so the light centre never showed and the gem read navy)
    fv, pv = Vector(tuple(face)), Vector(tuple(pc))
    kit.attribute(gem, "gem_r", lambda p: ((p - pv) - fv * (p - pv).dot(fv)).length / 0.0083)
    # the cabochon's catch light, as this style paints it (reference: a large soft white spot upper-centre on the dome)
    hl = Vector(tuple(pc + face * 0.0049 + upv * 0.0030 + np.array([0.0012, 0.0, 0.0])))
    kit.attribute(gem, "gem_hl", lambda p: (p - hl).length / 0.0030)
    bc = pc + upv * (0.0042 + 0.0121 - 0.0010)
    ring = np.array([bc + 0.0042 * math.cos(a) * upv + 0.0026 * math.sin(a) * face
                     for a in np.linspace(0, 2 * math.pi, 25)[:-1]])
    bail = sweep_tube("pendant_bail", ring, 0.0011, ring=8, normals=[r - bc for r in ring])
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
    mat, tree, bsdf = kit.principled("M_collar_leather")
    links = tree.links
    at = node(tree, "ShaderNodeAttribute", attribute_name="cord_lobe")
    rp = node(tree, "ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = 0.05, (*srgb("#3a2016"), 1)     # Cycle 12: darker reddish leather
    els[1].position, els[1].color = 0.92, (*srgb("#94603f"), 1)
    e = els.new(0.5)
    e.color = (*srgb("#5f3726"), 1)
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
    mat, tree, bsdf = kit.principled("M_pendant_silver")
    links = tree.links
    tc = node(tree, "ShaderNodeTexCoord")
    nz = node(tree, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 600.0
    nz.inputs["Detail"].default_value = 4.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = node(tree, "ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (*srgb("#b9bcc5"), 1)    # Cycle 15: the reference bezel is a bright
    rp.color_ramp.elements[1].color = (*srgb("#f0f1f5"), 1)    # light-grey ring (#c8ccd4-#f2f3f6), not dark chrome
    links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    links.new(rp.outputs["Color"], bsdf.inputs["Base Color"])
    mr = node(tree, "ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.30     # Cycle 12: satin, not mirror: the reference bezel is light grey
    mr.inputs["To Max"].default_value = 0.46     # (the mirror-like 0.18-0.36 reflected the dark studio and read dark)
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.25    # Cycle 15: full metal mirrored the dark studio and read dark;
    # the reference paints the bezel as light polished silver (light grey body, white glints, dark outline)
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
    mat, tree, bsdf = kit.principled("M_pendant_gem")
    links = tree.links
    at = node(tree, "ShaderNodeAttribute", attribute_name="gem_r")
    rp = node(tree, "ShaderNodeValToRGB")
    els = rp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*srgb("#9fc0ff"), 1)      # Cycle 15: the reference's bright centre
    els[1].position, els[1].color = 1.0, (*srgb("#1a2f96"), 1)
    for pos, hx in ((0.30, "#5a86f0"), (0.68, "#2f55d0")):
        e = els.new(pos)
        e.color = (*srgb(hx), 1)
    links.new(at.outputs["Fac"], rp.inputs["Fac"])
    tc = node(tree, "ShaderNodeTexCoord")
    nz = node(tree, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1200.0
    links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = node(tree, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix.inputs["Factor"].default_value = 0.10
    links.new(rp.outputs["Color"], mix.inputs[6])
    links.new(nz.outputs["Color"], mix.inputs[7])
    ah = node(tree, "ShaderNodeAttribute", attribute_name="gem_hl")
    hr_ = node(tree, "ShaderNodeMapRange")
    hr_.inputs["From Min"].default_value = 0.55
    hr_.inputs["From Max"].default_value = 1.0
    hr_.inputs["To Min"].default_value = 0.92
    hr_.inputs["To Max"].default_value = 0.0
    links.new(ah.outputs["Fac"], hr_.inputs["Value"])
    hl_mix = node(tree, "ShaderNodeMix", data_type="RGBA", blend_type="MIX")
    links.new(hr_.outputs["Result"], hl_mix.inputs["Factor"])
    links.new(mix.outputs[2], hl_mix.inputs[6])
    hl_mix.inputs[7].default_value = (*srgb("#f4f8ff"), 1)
    links.new(hl_mix.outputs[2], bsdf.inputs["Base Color"])
    # Cycle 15: the style paints the cabochon lit from within (bright centre, saturated rim): a soft emission of its
    # own colour, baked into the emission texture
    links.new(hl_mix.outputs[2], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.45
    mr = node(tree, "ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.03
    mr.inputs["To Max"].default_value = 0.08
    links.new(nz.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.8
    return mat


if __name__ == "__main__":
    kit.run(build, texture=4096)
