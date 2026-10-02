"""The ears: cartilage leaves furred outside, indigo bowl with the painted spiral inside, cream tufts."""
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
from aethel_fox_parts.common import NT, S, bez2, lin, new_image, poly_paint, set_bsdf, spiral, sweep  # noqa: E402

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
            base = nt.ramp(t, EAR_IN_RAMP)
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


# ============================================================================ EARS
EAR_TIP = (0.104, -0.151, 0.452)   # ear tip (X for the +X ear, Y, Z) before the 0.50 m scale (cycle 4: 6 mm
                                    # lower and 5 mm back for the side view; X kept: the ear tips set the front
                                    # view's width (front w/h +7 %), the back view wants them wider (w/h -8..-13 %):
                                    # drawing conflict; tested X 0.110 front w/h +13 %, 0.118 front overlap -0.04)
EAR_TIP_DY = 0.003                  # the +X ear's tip a little further back than the -X ear's
EAR_F0 = (0.62, -1.0, 0.10)         # bowl facing (X outward for the +X ear, Y forward, Z up): turned out so the
                                    # side view sees the near bowl and the far ear's back
EAR_HW = (0.044, 0.033)             # base half-widths: outer edge, inner edge
EAR_IN_RAMP = [(0.0, "#cdbdb2"), (0.3, "#d6c8bc"), (0.7, "#dacbbf"), (1.0, "#c6b9b4")]   # inner bowl tan, root to tip
EAR_SPIRAL = (0.013, 0.012, 0.005)   # upper curl radius, lower curl radius, band width


def ear_shape(side):
    """Leaf-shaped ear frame for side +1 (+X) or -1: base B, axis a, bowl normal f, width w, length L."""
    j = 0.002 * side
    B = np.array([side * 0.044, -0.155, 0.341])
    # (cycle 2: tips 0.013 higher, 0.006 forward, 0.004 more splay: side drawing ear tip / tail top
    # 0.95, back drawing's ears wider)
    Tp = np.array([side * (EAR_TIP[0] + j), EAR_TIP[1] + EAR_TIP_DY * side, EAR_TIP[2] - abs(j)])   # side: tips ~0.90 of the tail top; front wants taller (views disagree)
    L = float(np.linalg.norm(Tp - B))
    a = (Tp - B) / L
    f0 = np.array([side * EAR_F0[0], EAR_F0[1], EAR_F0[2]])
    f = f0 - (f0 @ a) * a
    f /= np.linalg.norm(f)
    w = np.cross(a, f)
    if w[0] * side < 0:
        w = -w
    return B, a, f, w, L


def ear_hw(u_sign, t):
    """Half-width at fraction t: outer edge (u >= 0) convex, pulled in at the base; inner straighter."""
    t = np.asarray(t, float)
    outer = EAR_HW[0] * (1 - t) ** 0.85 * (1 + 0.95 * t) * (0.6 + 0.4 * np.clip(t / 0.22, 0, 1) ** 0.7)
    inner = EAR_HW[1] * (1 - t) ** 0.9 * (1 + 0.5 * t)
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
        up = spiral((0.010 + j, 0.092), EAR_SPIRAL[0], 1.25, -0.25 * math.pi, 1, 1.15, 0.0, 50, 0.85)
        lo = spiral((0.012 - j, 0.052), EAR_SPIRAL[1], 1.2, 0.75 * math.pi, -1, 1.15, 0.0, 50, 0.85)
        sline = bez2(lo[0], (0.026, 0.062), (0.024, 0.085), up[0], 24)
        stroke = list(reversed(lo)) + sline[1:-1] + up
        bw = EAR_SPIRAL[2]
        widths = np.concatenate([np.linspace(0.0012, bw * 0.95, len(lo)), np.full(len(sline) - 2, bw),
                                 np.linspace(bw * 0.95, 0.0012, len(up))])
        poly_paint(sub[..., 0], X, Y, stroke, widths, 0.0004)
        poly_paint(sub[..., 0], X, Y, bez2((-0.004, 0.02), (0.0, 0.03), (0.006, 0.038), lo[0]), [0.0008, 0.0022, 0.0026, 0.003], 0.0004)
        # indigo zone: upper part of the bowl and a strip along the inner edge, soft
        zone = np.clip((Tg - 0.62) / 0.12, 0, 1)
        zone = np.maximum(zone, np.clip((-Ug - 0.35) / 0.25, 0, 1) * np.clip((Tg - 0.15) / 0.2, 0, 1))
        sub[..., 1] = zone
        img[:, i0:i1] = sub
    return new_image("AF_ears", W, H, img)


EAR_TUFT = (5, 0.0088, 0.0024)   # locks per ear, root half-width, root half-thickness (pre-scale)


def bowl_point(B, a, f, w, L, u, t, lift):
    """A point on the ear's inner bowl surface at (u across -1..1, t along) raised by lift along the bowl
    normal (the same surface build_ear lofts)."""
    t = float(t)
    c = B + a * L * t - f * 0.010 * math.sin(math.pi * t) * 0.7
    D = 0.027 * (1 - t) ** 0.6
    x = u * ear_hw(u, t)
    return c + w * x - f * (D * (1 - u * u)) + f * lift


def build_ear_tufts(side, mat, rng):
    """The ear tuft: a soft fan of cream fur locks growing from the inner base of the bowl (front drawing: a
    fern-like fan rising up and out; side drawing: 4-5 locks fanning up in the bowl). Each lock is a clump of
    hair, full and round at the root, overlapping its neighbours there, bending once and drawn to a soft
    rounded point; the locks lie on the bowl (their path follows its surface), their roots sunk into it.
    Cycle 6 (user: "Smoothen model"): were 5 thin flat blades with needle tips and gaps: a crown of spikes."""
    B, a, f, w, L = ear_shape(side)
    objs = []
    count, W, TH = EAR_TUFT
    n = 20
    tt = np.linspace(0, 1, n)
    for k in range(count):
        q = k / (count - 1)                                   # 0 inner .. 1 outer lock of the fan
        u0 = -0.40 + 0.34 * q + rng.uniform(-0.02, 0.02)      # roots close together: they overlap
        t0 = 0.035 + 0.035 * q + rng.uniform(-0.004, 0.004)
        ln = (0.34 + 0.08 * math.sin(math.pi * q) + rng.uniform(-0.015, 0.015))   # length as a fraction of the ear
        spread = -0.42 + 0.50 * q                             # fan: inner locks lean in toward the skull, outer ones run up the ear
        bend = 0.06 + 0.06 * q
        P = []
        for s_ in tt:
            u = u0 + spread * s_ + bend * s_ * s_
            t = t0 + ln * s_ * (1 - 0.25 * q * s_)
            lift = -0.0012 + 0.0042 * math.sin(math.pi * min(s_ / 0.7, 1.0) * 0.5) + 0.0006 * s_
            P.append(bowl_point(B, a, f, w, L, max(-0.95, min(0.95, u)), t, lift))
        P = np.array(P)
        # full at the root, widest a quarter along, a rounded point (no needle): width ~ (1 - t^2.2)^0.6
        width = W * (0.8 + 0.2 * np.sin(np.clip(tt / 0.25, 0, 1) * math.pi / 2)) * (1 - tt ** 2.2) ** 0.6
        width *= 0.9 + 0.2 * rng.random()
        th = TH * (1 - tt ** 1.8) ** 0.5 + 1e-5
        width[-1] = th[-1] = 0.0
        o, _ = sweep(f"ear_tuft_{side}_{k}", P, th, width, 12, mat, hint=np.tile(f, (n, 1)), uv_rect=(0, 0, 1, 1))
        o["keep_uv"] = True
        o.data.shade_smooth()
        objs.append(o)
    return objs
