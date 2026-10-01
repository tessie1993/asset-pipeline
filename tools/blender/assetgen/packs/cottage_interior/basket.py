"""basket -- round wicker basket with two twisted-rope handles, heaped with tomatoes, radishes and greens.

Sheet: design/asset-packs/cottage_interior/canva/06_basket_360.png (description: objects/basket.md).

Parts: a lathe shell (dark, seen in the gaps), ten staggered rows of bulging reed segments (real
geometry, one wicker variant per segment), a twisted rope rim, two twisted arch handles at +-X,
and the contents: tomatoes with green calyx stars, radishes with leafy tops, a bunch of large
double-sided leaves with lighter midribs at the back.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from assetgen import kit  # noqa: E402

# ---- dimensions (metres) ------------------------------------------------------------------
BODY_TOP = 0.345          # top of the weave shell
RIM_Z = 0.352             # centre line of the rope rim
RIM_R = 0.2385            # radius of the rim centre line
RIM_TUBE = 0.027
OUTER = [(0.15, 0.0), (0.176, 0.007), (0.191, 0.022), (0.203, 0.05), (0.221, 0.10), (0.236, 0.17),
         (0.245, 0.24), (0.249, 0.30), (0.249, BODY_TOP)]
INNER = [(0.228, BODY_TOP), (0.222, 0.30), (0.21, 0.20), (0.18, 0.08), (0.15, 0.035)]
ROWS = 10
PER_ROW = 20
ROW_Z0, ROW_Z1 = 0.018, BODY_TOP
BULGE = 0.011
WICKER_TILE = 1.8
WICKER_ROUGH = 0.55
WICKER_NORMAL = 2.0


def radius_at(z: float) -> float:
    """Outer shell radius at height z (linear between the profile points)."""
    pts = OUTER
    if z <= pts[0][1]:
        return pts[0][0]
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return pts[-1][0]


# ---- geometry helpers ---------------------------------------------------------------------

def resample(points: list[Vector], spacing: float, closed: bool = False) -> list[Vector]:
    """Points spaced evenly along the polyline (closed: no duplicate end point)."""
    pts = list(points) + ([points[0]] if closed else [])
    lens = [0.0]
    for a, b in zip(pts, pts[1:]):
        lens.append(lens[-1] + (b - a).length)
    total = lens[-1]
    m = max(2, int(round(total / spacing)))
    out = []
    idx = 0
    for k in range(m if closed else m + 1):
        s = total * k / m
        while idx < len(lens) - 2 and lens[idx + 1] < s:
            idx += 1
        seg = lens[idx + 1] - lens[idx]
        f = 0.0 if seg == 0 else (s - lens[idx]) / seg
        out.append(pts[idx].lerp(pts[idx + 1], min(1.0, max(0.0, f))))
    return out


def twisted_tube(name, path, plane_normal, radius, mat, closed=False, ring=12, lobes=3, amp=0.2,
                 pitch=0.05):
    """Rope: a tube along ``path`` whose lobed cross-section turns along the path (diagonal strands)."""
    n = len(path)
    lengths = [0.0]
    for i in range(1, n):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    total = lengths[-1] + ((path[0] - path[-1]).length if closed else 0.0)
    if closed:
        pitch = total / max(1, round(total / pitch))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    rings = []
    for i, p in enumerate(path):
        prev_p = path[(i - 1) % n] if closed else path[max(i - 1, 0)]
        next_p = path[(i + 1) % n] if closed else path[min(i + 1, n - 1)]
        t = (next_p - prev_p).normalized()
        nn = plane_normal.cross(t).normalized()
        bb = t.cross(nn).normalized()
        verts = []
        for k in range(ring):
            phi = 2 * math.pi * k / ring
            rho = radius * (1.0 + amp * math.cos(lobes * phi - 2 * math.pi * lengths[i] / pitch))
            verts.append(bm.verts.new(p + nn * (rho * math.cos(phi)) + bb * (rho * math.sin(phi))))
        rings.append(verts)
    for i in range(n if closed else n - 1):
        i2 = (i + 1) % n
        s0 = lengths[i]
        s1 = lengths[i + 1] if i + 1 < n else total
        for k in range(ring):
            k2 = (k + 1) % ring
            face = bm.faces.new((rings[i][k], rings[i][k2], rings[i2][k2], rings[i2][k]))
            v0, v1 = 2 * math.pi * k / ring * radius, 2 * math.pi * (k + 1) / ring * radius
            for loop, (u, v) in zip(face.loops, ((s0, v0), (s0, v1), (s1, v1), (s1, v0))):
                loop[uv].uv = (u, v)
    if not closed:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = kit.mesh_object(name, bm, mat)
    obj["keep_uv"] = True
    kit.smooth(obj, 60)
    return obj


def add_leaf(bm, bm_vein, base, az, elev, length, width, curl, cup=0.35, nt=9, ns=5):
    """Thin curved leaf blade (single sheet, rendered double-sided) with an optional midrib strip."""
    az_r = math.radians(az)
    heading = Vector((math.cos(az_r), math.sin(az_r), 0.0))
    side = Vector((-math.sin(az_r), math.cos(az_r), 0.0))
    up = Vector((0.0, 0.0, 1.0))
    pos = Vector(base)
    step = length / (nt - 1)
    grid, vein = [], []
    for i in range(nt):
        t = i / (nt - 1)
        e = math.radians(elev - curl * t)
        d = heading * math.cos(e) + up * math.sin(e)
        if i > 0:
            pos = pos + d * step
        n = d.cross(side).normalized()
        u_ = t ** 0.8
        hw = 0.5 * width * max(0.06, math.sqrt(max(0.0, 1.0 - (2.0 * u_ - 1.0) ** 2)))
        row = []
        for j in range(ns):
            sj = -1.0 + 2.0 * j / (ns - 1)
            row.append(bm.verts.new(pos + side * (sj * hw) + n * (cup * hw * sj * sj)))
        grid.append(row)
        if bm_vein is not None:
            vw = 0.0032 * (1.0 - 0.6 * t)
            vein.append((bm_vein.verts.new(pos + n * 0.0022 - side * vw),
                         bm_vein.verts.new(pos + n * 0.0022 + side * vw)))
    for i in range(nt - 1):
        for j in range(ns - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        if bm_vein is not None:
            bm_vein.faces.new((vein[i][0], vein[i + 1][0], vein[i + 1][1], vein[i][1]))


# ---- parts --------------------------------------------------------------------------------

def shell(mat):
    profile = [(0.0, 0.0)] + OUTER + INNER + [(0.0, 0.03)]
    obj = kit.lathe("shell", profile, mat=mat, segments=36, cap_bottom=False)
    kit.smooth(obj, 50)
    return obj


def weave(mats, rng):
    """Ten rows of short, bulging reed segments, each row staggered by half a segment."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    nu, nv = 4, 3
    row_h = (ROW_Z1 - ROW_Z0) / ROWS
    for i in range(ROWS):
        z0 = ROW_Z0 + i * row_h
        stagger = 0.5 * (i % 2)
        for j in range(PER_ROW):
            th0 = 2 * math.pi * (j + stagger) / PER_ROW
            dth = 2 * math.pi / PER_ROW
            bulge = BULGE * (0.85 + 0.3 * rng.random())
            mat_index = rng.randrange(len(mats))
            du, dv = rng.random() * 11.0, rng.random() * 11.0
            grid = []
            for a in range(nu + 1):
                col = []
                th = th0 + dth * (0.03 + 0.94 * a / nu)
                for b in range(nv + 1):
                    z = z0 + row_h * (0.04 + 0.92 * b / nv)
                    shape = (math.sin(math.pi * a / nu) ** 0.5) * (math.sin(math.pi * b / nv) ** 0.5)
                    r = radius_at(z) + bulge * shape - 0.0012
                    vert = bm.verts.new((r * math.cos(th), r * math.sin(th), z))
                    col.append((vert, (th * 0.25 + du, z + dv)))
                grid.append(col)
            for a in range(nu):
                for b in range(nv):
                    corners = (grid[a][b], grid[a + 1][b], grid[a + 1][b + 1], grid[a][b + 1])
                    face = bm.faces.new([c[0] for c in corners])
                    face.material_index = mat_index
                    for loop, c in zip(face.loops, corners):
                        loop[uv].uv = c[1]
    obj = kit.mesh_object("weave", bm, mats[0])
    for m in mats[1:]:
        obj.data.materials.append(m)
    obj["keep_uv"] = True
    kit.smooth(obj, 70)
    return obj


def rim(mat):
    length = 2 * math.pi * RIM_R
    count = int(round(length / 0.06)) * 5
    path = [Vector((RIM_R * math.cos(2 * math.pi * k / count), RIM_R * math.sin(2 * math.pi * k / count), RIM_Z))
            for k in range(count)]
    return twisted_tube("rim", path, Vector((0, 0, 1)), RIM_TUBE, mat, closed=True, ring=10, lobes=2,
                        amp=0.30, pitch=0.06)


def handle(side_sign, mat):
    """Arch handle in the radial plane at +-X: outer leg tucked on the wall, arch, inner leg in the fruit."""
    r_out, a, b, zc, n_exp = 0.272, 0.056, 0.17, RIM_Z, 2.4
    rc = r_out - a
    pts = [(r_out, 0.30), (r_out, 0.326)]
    for k in range(29):
        th = math.pi * k / 28
        c, s = math.cos(th), math.sin(th)
        pts.append((rc + a * math.copysign(abs(c) ** (2 / n_exp), c), zc + b * abs(s) ** (2 / n_exp)))
    pts += [(rc - a, 0.335)]
    path = [Vector((side_sign * r, 0.0, z)) for r, z in pts]
    path = resample(path, 0.05 / 5)
    return twisted_tube("handle_%s" % ("r" if side_sign > 0 else "l"), path, Vector((0, 1, 0)), 0.026, mat,
                        ring=10, lobes=2, amp=0.30, pitch=0.05)


def contents(rng):
    objs = []
    tomato_mats = [kit.flat("tomato_a", "#b83a24", 0.35), kit.flat("tomato_b", "#c4472a", 0.35),
                   kit.flat("tomato_c", "#a93424", 0.35), kit.flat("tomato_d", "#c9563a", 0.35)]
    radish_mats = [kit.flat("radish_a", "#9e2f54", 0.45), kit.flat("radish_b", "#b03d5f", 0.45),
                   kit.flat("radish_c", "#c04c6a", 0.45)]
    leaf_mats = [kit.flat("leaf_a", "#3f8a2a", 0.6), kit.flat("leaf_b", "#387a25", 0.6),
                 kit.flat("leaf_c", "#4a9832", 0.6)]
    vein_mat = kit.flat("leaf_vein", "#78b84a", 0.6)
    calyx_mat = kit.flat("calyx", "#2f6a1d", 0.6)
    fill_mat = kit.flat("veg_fill", "#3a1c18", 0.6)

    fill = kit.sphere("veg_fill", 0.215, (0, 0, 0.30), fill_mat, scale=(1.0, 1.0, 0.45), segments=20, rings=8)
    kit.smooth(fill)
    objs.append(fill)

    leaf_bms = [bmesh.new() for _ in leaf_mats]
    vein_bm = bmesh.new()
    calyx_bm = bmesh.new()

    def tomato(pos, mat, r=0.06):
        obj = kit.sphere("tomato", r, pos, mat,
                         scale=(rng.uniform(0.94, 1.06), rng.uniform(0.94, 1.06), 0.86), segments=16, rings=9)
        for v in obj.data.vertices:  # heirloom ribs and a dimple around the stem
            x, y, z = v.co
            rho = math.hypot(x, y)
            rib = 1.0 + 0.05 * math.cos(5 * math.atan2(y, x)) * min(1.0, rho / (0.6 * r))
            dimple = 0.16 * r * math.exp(-(rho / (0.3 * r)) ** 2) * (1.0 if z > 0 else 0.0)
            v.co = (x * rib, y * rib, z - dimple)
        kit.smooth(obj)
        objs.append(obj)
        top = Vector(pos) + Vector((0, 0, r * 0.86 * 0.85))
        start = rng.uniform(0, 72)
        for k in range(5):
            add_calyx(top, start + 72 * k)

    def add_calyx(top, az):
        add_leaf(calyx_bm, None, top, az, 14, 0.04, 0.018, 55, cup=0.2, nt=4, ns=3)

    def radish(pos, mat, az_out, tilt):
        k = 1.25
        profile = [(0.006 * k, -0.052 * k), (0.02 * k, -0.041 * k), (0.036 * k, -0.016 * k),
                   (0.042 * k, 0.008 * k), (0.036 * k, 0.03 * k), (0.02 * k, 0.043 * k),
                   (0.006 * k, 0.048 * k), (0.0, 0.05 * k)]
        obj = kit.lathe("radish", profile, pos, mat, segments=14)
        u = Vector((math.cos(math.radians(az_out)), math.sin(math.radians(az_out)), 0.0))
        axis = Vector((0, 0, 1)).cross(u)
        rot = Matrix.Rotation(math.radians(tilt), 3, axis)
        obj.rotation_euler = rot.to_euler()
        kit.smooth(obj)
        objs.append(obj)
        crown = Vector(pos) + rot @ Vector((0, 0, 0.055))
        for j in range(3):
            az = az_out + 120 * j + rng.uniform(-20, 20)
            add_leaf(leaf_bms[rng.randrange(3)], vein_bm, crown, az, rng.uniform(50, 66), 0.10, 0.05,
                     rng.uniform(20, 35), cup=0.3, nt=7, ns=4)

    # outer ring (front is -Y, i.e. angle 270), inner ring and crown
    outer = [(270, "t", 0), (321, "t", 1), (13, "r", 1), (64, "t", 2), (116, "r", 0), (167, "r", 2),
             (219, "t", 3)]
    for ang, kind, m in outer:
        a = math.radians(ang)
        rad = 0.14 + rng.uniform(-0.006, 0.006)
        pos = (rad * math.cos(a), rad * math.sin(a), 0.375 + rng.uniform(-0.004, 0.004))
        if kind == "t":
            tomato(pos, tomato_mats[m])
        else:
            radish(pos, radish_mats[m % 3], ang, 30)
    inner = [(300, "t", 2), (60, "r", 0), (180, "t", 3), (250, "t", 0), (350, "r", 2)]
    for ang, kind, m in inner:
        a = math.radians(ang)
        pos = (0.085 * math.cos(a), 0.085 * math.sin(a), 0.41 + rng.uniform(-0.004, 0.004))
        if kind == "t":
            tomato(pos, tomato_mats[m], 0.056)
        else:
            radish(pos, radish_mats[m % 3], ang, 20)
    tomato((0.0, 0.0, 0.432), tomato_mats[1], 0.054)

    # the large green leaves standing up at the back
    big = [((0.05, 0.11), 80, 70, 0.24, 0.14, 30, 0), ((-0.02, 0.12), 110, 64, 0.22, 0.13, 35, 1),
           ((0.11, 0.08), 40, 60, 0.20, 0.12, 40, 2), ((0.02, 0.09), 90, 80, 0.25, 0.14, 25, 0),
           ((-0.07, 0.10), 140, 57, 0.19, 0.12, 40, 1), ((0.08, 0.13), 65, 74, 0.25, 0.14, 22, 2),
           ((0.0, 0.05), 100, 68, 0.19, 0.11, 30, 2)]
    for (x, y), az, el, ln, wd, cv, m in big:
        add_leaf(leaf_bms[m], vein_bm, (x, y, 0.39), az, el, ln, wd, cv, cup=0.3, nt=10, ns=5)

    for bm, mat in zip(leaf_bms, leaf_mats):
        obj = kit.mesh_object("leaves", bm, mat)
        kit.smooth(obj, 80)
        objs.append(obj)
    objs.append(kit.mesh_object("veins", vein_bm, vein_mat))
    calyx = kit.mesh_object("calyx", calyx_bm, calyx_mat)
    kit.smooth(calyx, 80)
    objs.append(calyx)
    return objs


def build() -> list[bpy.types.Object]:
    rng = random.Random(11)
    opts = dict(tile=WICKER_TILE, normal_strength=WICKER_NORMAL, roughness=WICKER_ROUGH)
    shell_mat = kit.material("ambientcg:Wicker007A", tint="#b88452", **opts)
    reeds = kit.material_variants("ambientcg:Wicker007A", "#f2f2f2", 6, spread=0.08, seed=3, **opts)
    rope_mat = kit.material("ambientcg:Wicker007A", tint="#fbf3ea", **opts)
    objs = [shell(shell_mat), weave(reeds, rng), rim(rope_mat), handle(1, rope_mat), handle(-1, rope_mat)]
    objs += contents(rng)
    return objs


kit.run(build)
