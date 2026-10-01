"""bucket: wooden bucket of vertical staves, two riveted iron hoops and two wooden spoons.

Sheet: design/asset-packs/cottage_interior/canva/07_bucket_360.png (object text: objects/bucket.md).
Build:
    blender -b --factory-startup --python tools/blender/assetgen/packs/cottage_interior/bucket.py -- \
        [--no-render] [--samples 32]

Metres, +Z up, front toward -Y. Height 0.35 m (scale anchor).

Every stave and both spoons sit on one plank of the `wood_planks` texture (own UVs: grain runs
along the stave / handle); the hoops use the worn `pewter` plate.
"""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from assetgen import kit  # noqa: E402

# ---- dimensions -------------------------------------------------------------------- #
H = 0.35            # bucket height
R_BOT = 0.186       # outer stave radius at the base
R_TOP = 0.205       # outer stave radius at the rim
T = 0.030           # stave thickness (chunky)
N_STAVES = 13
GAP_DEG = 1.5       # groove between two staves
TOP_JITTER = 0.004  # stave tops differ a little in height

HOOP_UPPER = (0.208, 0.318)   # z range of the upper iron hoop (the sheet's hoops are broad)
HOOP_LOWER = (0.045, 0.150)   # z range of the lower iron hoop
HOOP_PROUD = 0.011            # how far the hoop stands out of the staves
HOOP_SINK = 0.004             # how far it sinks into them
RIVETS_PER_HOOP = 12
RIVET_R = 0.017

SPOON_TILT_DEG = 26.0

# textures: `wood_planks` (brown_planks_05) holds 9 planks per repeat, each ~0.111 of the height
PLANK_TILE = 1.1
PLANK_PERIOD = 114.0 / 1024.0
PLANK_FIRST = 84.0 / 1024.0

# colours (the tint multiplies the grey-beige photo texture; the studio lighting brightens it)
STAVE_TINT = "#b58048"
STAVE_INNER_TINT = "#7a4c28"
FLOOR_TINT = "#6a4424"
SPOON_TINT = "#e09a58"
HOOP_TINT = "#c4ccd8"
RIVET_TINT = "#e4eaf4"


def r_out(z: float) -> float:
    """Outer radius of the (almost straight, slightly tapered) staves at height z."""
    return R_BOT + (R_TOP - R_BOT) * z / H


def wrap(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def plank_v(k: int, tile: float) -> float:
    """UV v (metres) of the middle of plank k of the wood_planks texture."""
    return (1.0 - (PLANK_FIRST + PLANK_PERIOD * (k % 9))) / tile


# ---- helpers ------------------------------------------------------------------------ #

def bevel_and_smooth(obj, width: float, segments: int = 3, angle: float = 45.0) -> None:
    """Apply a bevel now (so the smoothing sees the bevelled mesh), then smooth by angle."""
    kit.add_bevel(obj, width, segments)
    kit._bake(obj)
    kit.smooth(obj, angle)


def set_uv(bm: bmesh.types.BMesh, fn) -> None:
    """Own UVs: fn(co, normal) -> (u, v) in metres."""
    layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        for loop in face.loops:
            loop[layer].uv = fn(loop.vert.co, face.normal)


# ---- bucket ------------------------------------------------------------------------- #

def make_stave(i: int, top_z: float, rng: random.Random, plank: int, outer_mat, inner_mat):
    pitch = 2 * math.pi / N_STAVES
    half_gap = math.radians(GAP_DEG) / 2
    a0, a1 = i * pitch + half_gap, (i + 1) * pitch - half_gap
    mid = (a0 + a1) / 2
    bm = bmesh.new()

    def vert(a, r, z):
        return bm.verts.new((r * math.cos(a), r * math.sin(a), z))

    ro_b, ro_t = r_out(0.0), r_out(top_z)
    ob = (vert(a0, ro_b, 0.0), vert(a1, ro_b, 0.0))
    ot = (vert(a0, ro_t, top_z), vert(a1, ro_t, top_z))
    ib = (vert(a0, ro_b - T, 0.0), vert(a1, ro_b - T, 0.0))
    it = (vert(a0, ro_t - T, top_z), vert(a1, ro_t - T, top_z))
    obm = vert(mid, ro_b + 0.003, 0.0)     # the outer face bulges a little: chunky, catches a highlight
    otm = vert(mid, ro_t + 0.003, top_z)
    bm.faces.new((ob[0], obm, otm, ot[0]))
    bm.faces.new((obm, ob[1], ot[1], otm))
    inner = bm.faces.new((ib[1], ib[0], it[0], it[1]))
    bm.faces.new((ob[0], ot[0], it[0], ib[0]))
    bm.faces.new((ob[1], ib[1], it[1], ot[1]))
    bm.faces.new((ot[0], ot[1], it[1], it[0]))
    bm.faces.new((ob[0], ib[0], ib[1], ob[1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    inner.material_index = 1

    offset_u = rng.uniform(0, 1)
    v_c = plank_v(plank, PLANK_TILE)
    radial = Vector((math.cos(mid), math.sin(mid), 0.0))

    def uv(co, normal):
        rad = math.hypot(co.x, co.y)
        d = wrap(math.atan2(co.y, co.x) - mid) * rad
        if abs(normal.z) > 0.7:                          # top / bottom faces
            return (rad + offset_u, v_c + d)
        if abs(normal.dot(radial)) > 0.7:                # outer / inner faces: grain runs up the stave
            return (co.z + offset_u, v_c + d)
        return (co.z + offset_u, v_c + (rad - R_TOP))

    set_uv(bm, uv)
    obj = kit.mesh_object(f"stave_{i}", bm, outer_mat)
    obj.data.materials.append(inner_mat)
    obj["keep_uv"] = True
    bevel_and_smooth(obj, 0.007, 3, 45.0)
    return obj


def make_hoop(name: str, z0: float, z1: float, mat, segments: int = 72):
    """Iron band: a revolved rounded-rectangle section that follows the stave taper."""
    b = 0.0045
    section = [(-HOOP_SINK, z0), (HOOP_PROUD - b, z0), (HOOP_PROUD, z0 + b),
               (HOOP_PROUD, z1 - b), (HOOP_PROUD - b, z1), (-HOOP_SINK, z1)]
    bm = bmesh.new()
    rows = []
    for dr, z in section:
        r = r_out(z) + dr
        rows.append([bm.verts.new((r * math.cos(2 * math.pi * k / segments),
                                   r * math.sin(2 * math.pi * k / segments), z))
                     for k in range(segments)])
    for a, b_row in zip(rows, rows[1:] + rows[:1]):
        for k in range(segments):
            k2 = (k + 1) % segments
            bm.faces.new((a[k], a[k2], b_row[k2], b_row[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = kit.mesh_object(name, bm, mat)
    kit.smooth(obj, 40.0)
    return obj


def make_rivets(tag: str, z: float, phase_deg: float, mat) -> list:
    rivets = []
    radius = r_out(z) + HOOP_PROUD
    for k in range(RIVETS_PER_HOOP):
        a = math.radians(phase_deg + 360.0 * k / RIVETS_PER_HOOP)
        obj = kit.sphere(f"rivet_{tag}_{k}", RIVET_R,
                         (radius * math.cos(a), radius * math.sin(a), z), mat,
                         scale=(0.5, 1.0, 1.0), segments=12, rings=6)
        obj.rotation_euler = (0.0, 0.0, a)
        kit.smooth(obj, 60.0)
        rivets.append(obj)
    return rivets


# ---- spoons ------------------------------------------------------------------------- #

def loft(name: str, rings, mat, v_c: float, segments: int = 16):
    """Round rod through rings (z, radius, x offset, y offset); radius 0 closes an end."""
    bm = bmesh.new()
    grid = []
    for z, r, ox, oy in rings:
        if r <= 1e-6:
            grid.append(bm.verts.new((ox, oy, z)))
        else:
            grid.append([bm.verts.new((ox + r * math.cos(2 * math.pi * k / segments),
                                       oy + r * math.sin(2 * math.pi * k / segments), z))
                         for k in range(segments)])
    for lower, upper in zip(grid, grid[1:]):
        for k in range(segments):
            k2 = (k + 1) % segments
            if isinstance(upper, bmesh.types.BMVert):
                bm.faces.new((lower[k], lower[k2], upper))
            else:
                bm.faces.new((lower[k], lower[k2], upper[k2], upper[k]))
    if not isinstance(grid[0], bmesh.types.BMVert):
        bm.faces.new(list(reversed(grid[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    def uv(co, normal):  # grain along the handle; mirrored round the rod so it stays in one plank
        return (co.z, v_c + (abs(math.atan2(co.y - rings[0][3], co.x) / math.pi) - 0.5) * 0.05)

    set_uv(bm, uv)
    obj = kit.mesh_object(name, bm, mat)
    obj["keep_uv"] = True
    kit.smooth(obj, 45.0)
    return obj


def dish(name: str, a: float, b: float, zc: float, depth: float, thick: float, mat, v_c: float,
         segments: int = 20):
    """Spoon bowl: a thin dished oval (half width a along X, half length b along Z) opening toward -Y."""
    rhos = (1.0, 0.78, 0.55, 0.3, 0.0)
    bm = bmesh.new()

    def surface(extra):
        rows = []
        for rho in rhos:
            y = depth * (1.0 - rho * rho) + extra
            if rho == 0.0:
                rows.append(bm.verts.new((0.0, y, zc)))
            else:
                rows.append([bm.verts.new((a * rho * math.cos(2 * math.pi * k / segments), y,
                                           zc + b * rho * math.sin(2 * math.pi * k / segments)))
                             for k in range(segments)])
        return rows

    inner, outer = surface(0.0), surface(thick)
    for rows in (inner, outer):
        for lo, up in zip(rows, rows[1:]):
            for k in range(segments):
                k2 = (k + 1) % segments
                if isinstance(up, bmesh.types.BMVert):
                    bm.faces.new((lo[k], lo[k2], up))
                else:
                    bm.faces.new((lo[k], lo[k2], up[k2], up[k]))
    for k in range(segments):
        k2 = (k + 1) % segments
        bm.faces.new((inner[0][k], inner[0][k2], outer[0][k2], outer[0][k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    set_uv(bm, lambda co, n: (co.z, v_c + co.x * 0.6))
    obj = kit.mesh_object(name, bm, mat)
    obj["keep_uv"] = True
    kit.smooth(obj, 60.0)
    return obj


def make_spoon(tag: str, tip, lean_dir, face_dir, mat, plank: int) -> list:
    """Wooden spoon: bowl at the low end, thick round handle rising, leaning toward lean_dir (XY)."""
    v_c = plank_v(plank, 1.6)
    y0 = 0.012
    handle_rings = [
        (0.080, 0.0150, 0.0, y0), (0.110, 0.0190, 0.0, y0), (0.150, 0.0250, 0.0, y0),
        (0.200, 0.0310, 0.0, y0), (0.260, 0.0330, 0.0, y0), (0.272, 0.0330, 0.0, y0),
        (0.282, 0.0300, 0.0, y0), (0.289, 0.0240, 0.0, y0), (0.294, 0.0140, 0.0, y0),
        (0.2965, 0.0, 0.0, y0),
    ]
    parts = [loft(f"spoon_{tag}_handle", handle_rings, mat, v_c),
             dish(f"spoon_{tag}_bowl", 0.038, 0.056, 0.056, 0.022, 0.008, mat, v_c)]
    lean = Vector(lean_dir).normalized()
    psi = math.atan2(lean.x, -lean.y)
    base = Matrix.Rotation(psi, 4, "Z") @ Matrix.Rotation(math.radians(SPOON_TILT_DEG), 4, "X")
    target = Vector((face_dir[0], face_dir[1], 0.25)).normalized()
    best, best_score = 0.0, -2.0
    for chi in range(0, 360, 5):
        rot = base @ Matrix.Rotation(math.radians(chi), 4, "Z")
        score = (rot.to_3x3() @ Vector((0.0, -1.0, 0.0))).dot(target)
        if score > best_score:
            best, best_score = chi, score
    matrix = Matrix.Translation(Vector(tip)) @ base @ Matrix.Rotation(math.radians(best), 4, "Z")
    for part in parts:
        part.matrix_world = matrix
    return parts


# ---- build -------------------------------------------------------------------------- #

def build():
    rng = random.Random(7)
    stave_mats = kit.material_variants("polyhaven:brown_planks_05", STAVE_TINT, N_STAVES, spread=0.12, seed=3,
                                       tile=PLANK_TILE, normal_strength=3.0)
    inner_mats = kit.material_variants("polyhaven:brown_planks_05", STAVE_INNER_TINT, N_STAVES, spread=0.08, seed=5,
                                       tile=PLANK_TILE, normal_strength=2.0)
    floor_mat = kit.material("polyhaven:brown_planks_05", tint=FLOOR_TINT, tile=PLANK_TILE, normal_strength=1.5)
    hoop_mat = kit.material("polyhaven:metal_plate_02", tint=HOOP_TINT, tile=1.2, roughness=0.45, normal_strength=1.5)
    rivet_mat = kit.material("polyhaven:metal_plate_02", tint=RIVET_TINT, tile=6.0, roughness=0.35, normal_strength=1.0)
    for m in (hoop_mat, rivet_mat):  # worn iron, not a mirror: constant metallic instead of the map's
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for link in list(bsdf.inputs["Metallic"].links):
            m.node_tree.links.remove(link)
        bsdf.inputs["Metallic"].default_value = 0.55
    spoon_mat = kit.material("polyhaven:brown_planks_05", tint=SPOON_TINT, tile=1.6, normal_strength=1.5)

    planks = list(range(9))
    rng.shuffle(planks)
    parts = []
    for i in range(N_STAVES):
        top = H + rng.uniform(-TOP_JITTER, TOP_JITTER)
        parts.append(make_stave(i, top, rng, planks[i % 9], stave_mats[i], inner_mats[i]))

    # wooden floor inside the bucket (dark: it sits in the shadow of the walls)
    parts.append(kit.cylinder("floor", R_BOT - T + 0.004, 0.030, (0, 0, 0.035), floor_mat, segments=30))

    parts.append(make_hoop("hoop_upper", *HOOP_UPPER, hoop_mat))
    parts.append(make_hoop("hoop_lower", *HOOP_LOWER, hoop_mat))
    parts += make_rivets("upper", sum(HOOP_UPPER) / 2, 6.0, rivet_mat)
    parts += make_rivets("lower", sum(HOOP_LOWER) / 2, 21.0, rivet_mat)

    parts += make_spoon("a", (-0.055, 0.030, 0.255), (-0.90, 0.45), (0.0, -1.0), spoon_mat, 3)
    parts += make_spoon("b", (0.055, 0.000, 0.255), (0.90, -0.25), (0.0, -1.0), spoon_mat, 5)
    return parts


if __name__ == "__main__":
    kit.run(build)
