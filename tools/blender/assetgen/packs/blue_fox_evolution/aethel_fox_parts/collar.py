"""The collar: braided cord, pendant (bail, bezel, gem), antler branches."""
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
from aethel_fox_parts.common import NT, bez2, catmull, lin, set_bsdf, spiral, sweep  # noqa: E402

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
    branches.append(("curl", P, 0.0028, 0.0016))
    drop = np.array(bez2((s * 0.009, gc[1] + 0.002, gc[2] - 0.013), (s * 0.010, gc[1] + 0.003, gc[2] - 0.026),
                         (s * 0.006, gc[1] + 0.006, gc[2] - 0.034), (s * 0.002, gc[1] + 0.008, gc[2] - 0.042), 16))
    Sd, Nd = clay.project(drop)
    drop = Sd + Nd * 0.0025
    branches.append(("drop", drop, 0.0026, 0.0016))
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
                # a rounded end (cycle 6, user: "Smoothen model"): the antler tips and the drops end in a
                # small dome like the drawing's polished silver, not a needle point
                T = P[-1] - P[-2]
                T /= np.linalg.norm(T)
                ang = np.radians([30.0, 55.0, 75.0, 90.0])
                P = np.vstack([P, P[-1] + np.outer(np.sin(ang), T) * rr[-1]])
                rr = np.concatenate([rr, rr[-1] * np.cos(ang)])
                rr[-1] = 0.0
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


