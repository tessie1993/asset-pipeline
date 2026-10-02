"""The tail: underfur round the bone, guard-hair locks in layers, painted atlas, cream tip."""
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
from aethel_fox_parts.common import NT, bilinear_grid, catmull, frames, hexrgb, lin, new_image, poly_paint, set_attr, set_bsdf, spiral  # noqa: E402

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
    rt = nt.ramp(ft, [(0.0, (0.86, 0.89, 0.95, 1)), (0.3, (0.95, 0.96, 0.98, 1)), (0.6, (1, 1, 1, 1)), (1.0, (1.08, 1.07, 1.05, 1))])
    col = nt.mix(1.0, col, rt, "MULTIPLY")
    edge = nt.maprange(nt.math("ABSOLUTE", fw), 0.55, 1.0, 1.0, 0.94)
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
    col = nt.mix(nt.maprange(ao.outputs["AO"], 0.95, 0.45, 0.0, 0.25), col, lin("#5a6c98"))
    rough = nt.math("ADD", nt.math("MULTIPLY", strand, 0.14), nt.maprange(ft, 0.0, 1.0, 0.82, 0.66))
    height = nt.math("ADD", nt.math("MULTIPLY", groove, 0.6), nt.math("MULTIPLY", strand, 0.4))
    set_bsdf(nt, bsdf, base=col, rough=rough, emis_col=emis, emis_str=1.4, normal=nt.bump(height, 0.35, 0.0012))
    return mat


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


# (cycle 4: root narrower (rb/rf at tk 0.06-0.14) so the plume hangs from a slimmer root as in the side drawing;
# the curl's underside fuller (rb tk 0.58-0.95) to fill the drawing's lower tip; the tip narrower across (ru))
TAIL_RB = [0.028, 0.044, 0.068, 0.0722, 0.0684, 0.066, 0.0640, 0.0600, 0.055, 0.045, 0.026, 0.0]
TAIL_RF = [0.024, 0.031, 0.062, 0.0808, 0.0882, 0.074, 0.054, 0.0394, 0.031, 0.024, 0.016, 0.0]
TAIL_RU = [0.03, 0.06, 0.0835, 0.0942, 0.0965, 0.08, 0.07, 0.0536, 0.036, 0.024, 0.014, 0.0]
TAIL_CREAM_W = (0.8, 0.6, 0.45)   # cream crest: weight of facing back (Y), facing up (Z), threshold
TAIL_LIFT = (0.0, 0.004)          # tip lift range of the layered locks
TAIL_WIDTH_K = 1.0                 # width factor of the layered locks
TAIL_EXTRA_LOCKS = [(0.80, 0.97, 1.35, 0.06, 0.040)]   # the second point under the curled tip
TAIL_LOCK_CREAM = (0.62, 0.25)
TAIL_FLAMES = (11, 0.016, 0.026)    # cream flame strokes of the atlas: count, widest width range (m)
TAIL_ZONE_U0 = 0.48               # the cream crest starts this far along the tail       # a lock turns cream past this much atlas cream (threshold, ramp)              # extra edge locks (s0, s1, a0, lift, width)


# The tail's centre line (Y, Z at X 0) as one smooth cubic B-spline with 7 control points (cycle 6, user:
# "Smoothen model ... too literal copy" and "Don't use masks"): the earlier 12-knot Catmull-Rom path was fitted
# to the side view's silhouette rows and carried their wobble (a back-and-forth at Z 0.32-0.39 and a kink over
# the curl). Read from the full-resolution side drawing: the plume rises from the rump, swells forward over its
# lower half, sweeps up and back over the top in one arc and runs down and back into the cream tip.
TAIL_CTRL = [(0.11, 0.199), (0.1214, 0.2387), (0.1372, 0.2899), (0.1192, 0.4326), (0.2604, 0.4340),
             (0.2833, 0.3495), (0.328, 0.348)]
TAIL_RADIUS_SMOOTH = 9.0   # Gaussian smoothing of the radius profiles, in path samples (was 4: bumps at the knots)


def bspline(ctrl, n):
    """Clamped uniform cubic B-spline through the control polygon ctrl, n samples (de Boor)."""
    k = 3
    m = len(ctrl)
    kn = np.concatenate([np.zeros(k), np.linspace(0, 1, m - k + 1), np.ones(k)])
    u = np.clip(np.linspace(0, 1, n), 0, 1 - 1e-12)
    B = np.zeros((n, len(kn) - 1))
    for i in range(len(kn) - 1):
        B[:, i] = (kn[i] <= u) & (u < kn[i + 1])
    for d in range(1, k + 1):
        Bn = np.zeros((n, len(kn) - 1 - d))
        for i in range(len(kn) - 1 - d):
            a = (u - kn[i]) / (kn[i + d] - kn[i]) if kn[i + d] > kn[i] else 0.0
            b = (kn[i + d + 1] - u) / (kn[i + d + 1] - kn[i + 1]) if kn[i + d + 1] > kn[i + 1] else 0.0
            Bn[:, i] = a * B[:, i] + b * B[:, i + 1]
        B = Bn
    out = B @ ctrl
    out[-1] = ctrl[-1]
    return out


def tail_path():
    """Centre line (Y, Z at X 0) of the plume, fitted in numbers to the side view's outline rows in
    the kit camera's normalised frame (work/tailfit2.py + tailopt.py: every row within 0.01 of the
    reference, plume top 1.15 x the ear tips, background kept under the plume): the root on the rump, a fat lower plume that hangs
    back to Y 0.23, the upper part bending back into a thick curl and tapering to the cream tip at
    Y 0.335 Z 0.34. Radii: ru across (X), rb toward +B (back / down / inside of the curl), rf toward
    -B (front / up). Profiles smoothed so the surface has no rings at the knots."""
    D = bspline(np.array(TAIL_CTRL), 2000)      # dense, then even arc-length samples (even rings along the tail)
    dl = np.r_[0, np.cumsum(np.linalg.norm(np.diff(D, axis=0), axis=1))]
    se = np.linspace(0, dl[-1], 177)
    P2 = np.stack([np.interp(se, dl, D[:, 0]), np.interp(se, dl, D[:, 1])], 1)
    P = np.stack([np.zeros(len(P2)), P2[:, 0], P2[:, 1]], 1)
    tt = np.linspace(0, 1, len(P))
    tk = [0, 0.06, 0.14, 0.25, 0.36, 0.47, 0.58, 0.68, 0.78, 0.88, 0.95, 1.0]
    # (cycle 2: the cream tip fatter toward its end; the lower plume fuller in front (rf); X kept: wider
    # showed the tail beside the body in the front view)
    rb = np.interp(tt, tk, TAIL_RB)
    rf = np.interp(tt, tk, TAIL_RF)
    ru = np.interp(tt, tk, TAIL_RU)
    ru, rb, rf = (np.maximum(smooth1d(r, TAIL_RADIUS_SMOOTH), 0.0) for r in (ru, rb, rf))
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
    for k in range(TAIL_FLAMES[0]):
        x0 = (k / float(TAIL_FLAMES[0]) + prng.uniform(-0.02, 0.02)) * circ
        y0 = prng.uniform(0.04, 0.22) * Lt
        y1 = min(y0 + prng.uniform(0.26, 0.42) * Lt, 0.64 * Lt)
        sway = prng.uniform(0.03, 0.07) * (1 if k % 2 else -1)
        pts = [(x0 + sway * math.sin(f * 2.6 + 0.4), y0 + (y1 - y0) * f) for f in np.linspace(0, 1, 28)]
        d = 1 if prng.random() > 0.5 else -1
        rr = prng.uniform(0.018, 0.03)
        cen = (pts[-1][0] - d * rr, pts[-1][1])
        sp = spiral(cen, rr, prng.uniform(1.0, 1.45), 0.0 if d > 0 else math.pi, d, 1.0, 0.0, 44, 0.8)
        stroke = pts + sp
        wmax = prng.uniform(TAIL_FLAMES[1], TAIL_FLAMES[2])
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
    outer = nn[..., 1] * TAIL_CREAM_W[0] + nn[..., 2] * TAIL_CREAM_W[1]      # facing back / up: the curl's outer side, not the plume's front
    thr = TAIL_CREAM_W[2] + 0.14 * np.sin(Ag * 2 * math.pi * 4 + Ug * 23) + 0.06 * np.sin(Ag * 2 * math.pi * 9 + Ug * 41)
    zone = np.clip((outer - thr) / 0.05, 0, 1) * np.clip((Ug - TAIL_ZONE_U0) / 0.08, 0, 1)
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
TAIL_ROOT_RHO = 0.95     # lock roots lie at this fraction of the fur radius
TAIL_UNDER = 0.97        # underfur radius as a fraction of the fur radius
TAIL_UNDER_T = 0.55      # root-to-tip shading value of the underfur (0 dark root .. 1 light tip)
TAIL_KEEP_LAYERS = (0, 1, 2, 3, 4, 5)   # which lock layers are built (5 = the edge locks)


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


# Cycle 6 (user: "Smoothen model"; the tail is fur made of locks that read as smooth, flowing locks without
# gaps): fewer, broader locks (8-9 per layer, was 10-13) that lie flush on the underfur, their side edges sunk
# into it (TAIL_EDGE_SINK) so no shelf, slit or dark seam shows between them; edge locks lower and fewer.
TAIL_LAYERS = [  # s0 range, s1 range, count, width range (m), twist
    ((0.00, 0.05), (0.30, 0.42), 8, (0.084, 0.104), 0.30),
    ((0.13, 0.22), (0.47, 0.60), 9, (0.084, 0.104), 0.26),
    ((0.34, 0.44), (0.68, 0.80), 8, (0.076, 0.094), 0.22),
    ((0.55, 0.64), (0.86, 0.96), 7, (0.064, 0.080), 0.18),
    ((0.72, 0.80), (1.00, 1.035), 4, (0.056, 0.070), 0.12),
]
TAIL_EDGE_LOCKS = [(0.04, 0.34, 1.45, 0.05, 0.050), (0.12, 0.42, 1.70, 0.06, 0.048),   # lower back edge
                   (0.52, 0.78, -1.45, 0.05, 0.046), (0.60, 0.86, -1.80, 0.045, 0.042),   # top of the cream crown
                   (0.70, 1.02, 1.6, 0.04, 0.040)]                                         # under the curled tip
TAIL_EDGE_SINK = 0.07     # how far (fraction of the fur radius) a lock's side edges sink under its middle


def tail_fur_lock_specs(rng):
    """The guard-hair locks of the tail, layered root to tip (each layer's roots lie under the
    locks of the layer before, the way fur grows toward the tip): (s0, s1, a0, twist, sway, width,
    thickness, tip lift, tip hook). Layers interleave like bricks; every lock its own length, width,
    twist and lift."""
    specs = []
    layers = TAIL_LAYERS
    for li, ((a0_, a1_), (b0_, b1_), cnt, (w0, w1), tw) in enumerate(layers):
        for k in range(cnt):
            a0 = 2 * math.pi * (k + 0.5 * (li % 2) + rng.uniform(-0.25, 0.25)) / cnt
            s0 = rng.uniform(a0_, a1_)
            s1 = rng.uniform(b0_, b1_)
            # S flow: every lock bows one way over its lower half and back over its upper half
            specs.append(dict(s0=s0, s1=s1, a0=a0, twist=tw * rng.uniform(0.6, 1.3),
                              sway=rng.uniform(-0.12, 0.12), s_flow=rng.uniform(0.18, 0.32),
                              width=rng.uniform(w0, w1) * TAIL_WIDTH_K,
                              thick=rng.uniform(0.008, 0.012) * (1.0 - 0.3 * li / 4),
                              lift=rng.uniform(*TAIL_LIFT), hook=rng.uniform(-0.2, 0.2), layer=li))
    # locks that stand out of the outline: three on the lower back edge behind the rump (side
    # drawing's points), three along the top edge of the cream crown, one under the curled tip
    for s0, s1, a0, lift, w in list(TAIL_EDGE_LOCKS) + list(TAIL_EXTRA_LOCKS):
        specs.append(dict(s0=s0, s1=s1, a0=a0, twist=0.15, sway=rng.uniform(-0.1, 0.1), s_flow=0.12, width=w,
                          thick=0.008, lift=lift, hook=rng.uniform(-0.1, 0.1), layer=5))
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
         + 0.5 * sp["hook"] * np.clip((t - 0.8) / 0.2, 0, 1) ** 2)
    rho = TAIL_ROOT_RHO + 0.05 * t ** 0.9 + sp["lift"] * np.clip((t - 0.72) / 0.28, 0, 1) ** 2
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
    # domed on top, flatter below, the side edges sunk into the underfur so neighbouring locks meet
    # without a shelf or a slit (the sink fades out toward the free tip, where the lock lifts off)
    sink = TAIL_EDGE_SINK * (1.0 - 0.5 * np.clip((t - 0.75) / 0.25, 0, 1))   # tips stay laid down (cycle 6)
    dr = (th / r_loc)[:, None] * np.where(sph > 0, 0.5 * sph, 0.25 * sph)[None, :] - sink[:, None] * (cph ** 2)[None, :]
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
        fc = np.clip((np.maximum.accumulate(smooth1d(raw, 1.5)) - TAIL_LOCK_CREAM[0]) / TAIL_LOCK_CREAM[1], 0, 1)   # only clear flames
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
    set_attr(under, "fur_t", np.full(len(under.data.vertices), TAIL_UNDER_T))
    objs = [under]
    col_img, emi_img, cream = tail_images(grid, 0)
    set_attr(under, "fur_cream", np.zeros(len(under.data.vertices)))
    rng = random.Random(41)
    specs = tail_fur_lock_specs(rng)
    specs = [sp for sp in specs if sp["layer"] in TAIL_KEEP_LAYERS]
    for k, sp in enumerate(specs):
        objs.append(build_tail_fur_lock(f"tail_fur_lock_{k:02d}", body, sp, rng.random(), placeholder, cream=cream))
    mat = tail_material(col_img, emi_img)
    for o in objs:
        o.data.materials[0] = mat
    bpy.data.materials.remove(placeholder)
    return objs


