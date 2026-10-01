"""crate: open wooden crate with braces (Canva sheet design/asset-packs/cottage_interior/canva/05_crate_360.png).

Square open-topped crate, 0.6 m wide, ~0.95 x width tall. A chunky frame (mitred top rim and
base band, four corner posts) stands proud of vertical plank walls; braces sit on top of the
planks: front (-Y) one diagonal, +X an X, back (+Y) one diagonal, -X plain planks. Small dark
nail heads sit at the ends of the frame battens. Inside: plain plank walls and a plank floor.

Every part is a beam built with its length along local X, so the kit's UVs are replaced by
local ones (u along the grain) and each plank shows another part of the wood texture.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from assetgen import kit  # noqa: E402

# ----------------------------------------------------------------------------- #
# Dimensions (metres). The -Y face is modelled; the other faces are it rotated about Z.
# ----------------------------------------------------------------------------- #
HEIGHT = 0.57
HALF = 0.29            # posts and plank frame; the base band is proud of it (outer 0.30)
BAND_D = 0.06          # depth of the rim / base battens (outer face at HALF)
POST_W = 0.075         # square corner posts
BASE_H = 0.07          # base band height
RIM_H = 0.11           # top rim height
PLANK_IN = HALF - 0.055    # planks: inner face (a hair behind the band's inner face)
PLANK_OUT = HALF - 0.036   # planks: outer face (recessed behind the frame)
RIM_GROW, BASE_GROW = 0.006, 0.010   # bands stand proud of the posts
PLANK_COUNT = 5
BRACE_W = 0.07
BRACE_IN = PLANK_OUT - 0.002
BRACE_OUT = HALF - 0.002
FACES = (0, 90, 180, 270)   # rotation about Z of the -Y face: -Y, +X, +Y, -X
BRACES = {0: ("/",), 90: ("/", "\\"), 180: ("/",), 270: ()}

TINT_PLANK = "#9e6832"
TINT_FRAME = "#9d6d31"
TINT_NAIL = "#34302d"
# brown_planks_05: 9 boards per texture tile; board centres sit at v = 0.0292 + k / 9.
BOARD_V0, BOARD_PITCH = 0.0292, 1.0 / 9.0


def _rz(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def _local_uvs(bm, offset, origin=(0.0, 0.0, 0.0)):
    """Planar UVs in the part's own frame (metres): u runs along local X, i.e. along the grain."""
    layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        normal = face.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        for loop in face.loops:
            x, y, z = (c - o for c, o in zip(loop.vert.co, origin))
            u, v = {0: (y, z), 1: (x, z), 2: (x, y)}[axis]
            loop[layer].uv = (u + offset[0], v + offset[1])


def board_offset(rng, tile):
    """UV offset that centres one board of the plank texture on a part (u random along the grain)."""
    return (rng.uniform(0.0, 1.0), (BOARD_V0 + BOARD_PITCH * rng.randrange(9)) / tile)


def wood_set(key, tint, count, tile, tag, spread, seed, roughness=0.5, normal_strength=2.0):
    """``count`` lightness variants of one wood at one tile, named by ``tag`` (tiles differ per part)."""
    rng = random.Random(seed)
    base = [int(tint.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    mats = []
    for n in range(count):
        scale = 1.0 + rng.uniform(-spread, spread)
        color = "#%02x%02x%02x" % tuple(max(0, min(255, round(c * scale))) for c in base)
        mats.append(kit.material(key, tint=color, tile=tile, roughness=roughness,
                                 normal_strength=normal_strength, name=f"M_{tag}_{n}"))
    return mats


def _finish(obj, bevel, segments=2, angle=35.0):
    obj["keep_uv"] = True
    kit.smooth(obj, angle)
    if bevel > 0.0:
        kit.add_bevel(obj, bevel, segments)
    return obj


def beam(name, size, loc, rot, mat, face_rot, bevel, offset=(0.0, 0.0), segments=2):
    """Box of ``size`` (length along local X, then Y, Z) at ``loc``, tilted by ``rot`` and turned
    about Z with the face it belongs to."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.normal_update()
    _local_uvs(bm, offset)
    obj = kit.mesh_object(name, bm, mat, _rz(loc, face_rot), (rot[0], rot[1], rot[2] + face_rot))
    return _finish(obj, bevel, segments)


def mitre(name, z0, z1, mat, face_rot, bevel, offset, segments=2, grow=0.0):
    """One side of a square frame, cut at 45 degrees at both ends."""
    o, i = HALF + grow, HALF - BAND_D
    bm = bmesh.new()
    pts = [(-o, -o, z0), (o, -o, z0), (o, -o, z1), (-o, -o, z1),
           (-i, -i, z0), (i, -i, z0), (i, -i, z1), (-i, -i, z1)]
    v = [bm.verts.new(p) for p in pts]
    for idx in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 1, 5, 4), (3, 7, 6, 2), (0, 3, 7, 4), (1, 5, 6, 2)):
        bm.faces.new([v[k] for k in idx])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    _local_uvs(bm, offset, origin=(0.0, -(o + i) / 2, (z0 + z1) / 2))
    obj = kit.mesh_object(name, bm, mat, (0, 0, 0), (0, 0, face_rot))
    return _finish(obj, bevel, segments)


def nail(name, loc, rot, mat, face_rot=0):
    obj = kit.cylinder(name, 0.007, 0.008, _rz(loc, face_rot), mat,
                       (rot[0], rot[1], rot[2] + face_rot), segments=10)
    obj.data.shade_smooth()
    return obj


def build():
    rng = random.Random(11)
    inner = HALF - POST_W
    pw = 2 * inner / PLANK_COUNT                     # plank pitch (0.075)
    dz = HEIGHT - RIM_H - BASE_H                     # clear height between base band and rim
    tile_plank = BOARD_PITCH / pw                    # one texture board per plank
    # Frame parts use the same boards but show only the middle of one (no dark groove lines).
    tile_post, tile_rim = 0.085 / POST_W, 0.085 / RIM_H
    tile_base, tile_brace = 0.085 / BASE_H, 0.085 / BRACE_W
    planks = wood_set("polyhaven:brown_planks_05", TINT_PLANK, 6, tile_plank, "plank", 0.13, 3)
    posts = wood_set("polyhaven:brown_planks_05", TINT_FRAME, 4, tile_post, "post", 0.05, 5, normal_strength=1.4)
    rims = wood_set("polyhaven:brown_planks_05", TINT_FRAME, 4, tile_rim, "rim", 0.05, 6, normal_strength=1.4)
    bases = wood_set("polyhaven:brown_planks_05", TINT_FRAME, 4, tile_base, "base", 0.05, 7, normal_strength=1.4)
    braces = wood_set("polyhaven:brown_planks_05", TINT_FRAME, 4, tile_brace, "brace", 0.05, 8, normal_strength=1.4)
    iron = kit.material("polyhaven:metal_plate", tint=TINT_NAIL, tile=4.0, roughness=0.5)

    parts = []
    rim_z0 = HEIGHT - RIM_H
    # Mitred rim and base rings.
    for z0, z1, tag, mats, tile, grow in ((0.0, BASE_H, "base", bases, tile_base, BASE_GROW),
                                          (rim_z0, HEIGHT, "rim", rims, tile_rim, RIM_GROW)):
        for k, rot in enumerate(FACES):
            parts.append(mitre(f"{tag}_{rot}", z0, z1, mats[k % len(mats)], rot, 0.014,
                               board_offset(rng, tile), segments=3, grow=grow))

    # Corner posts between the base band and the rim.
    post_len = dz + 0.01
    post_c = HALF - 0.0005 - POST_W / 2
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        parts.append(beam("post", (post_len, POST_W, POST_W), (sx * post_c, sy * post_c, (BASE_H + rim_z0) / 2),
                          (0, -90, 0), posts[k % len(posts)], 0, 0.014, board_offset(rng, tile_post), 3))

    # Plank walls: six planks per face, each a hair different in depth and colour.
    z0, z1 = BASE_H - 0.01, rim_z0 + 0.01
    for rot in FACES:
        for i in range(PLANK_COUNT):
            x = -inner + pw * (i + 0.5)
            y_out = PLANK_OUT + rng.uniform(-0.002, 0.002)
            parts.append(beam("plank", (z1 - z0, y_out - PLANK_IN, pw),
                              (x, -(PLANK_IN + y_out) / 2, (z0 + z1) / 2), (0, -90, 0),
                              planks[(i + rot // 90) % len(planks)], rot, 0.007, board_offset(rng, tile_plank), 3))

    # Braces: applied battens whose ends disappear into the posts and bands.
    angle = math.degrees(math.atan2(dz, 2 * inner))
    length = math.hypot(dz, 2 * inner) + 0.03
    cz = (BASE_H + rim_z0) / 2
    for rot in FACES:
        for n, kind in enumerate(BRACES[rot]):
            out = BRACE_OUT + 0.002 * n
            tilt = -angle if kind == "/" else angle
            parts.append(beam("brace", (length, out - BRACE_IN, BRACE_W), (0, -(BRACE_IN + out) / 2, cz),
                              (0, tilt, 0), braces[(rot // 90 + n) % len(braces)], rot, 0.009,
                              board_offset(rng, tile_brace), 3))

    # Nail heads at the ends of the rim and base battens, and on the rim's corners.
    for rot in FACES:
        for z, grow in ((HEIGHT - RIM_H / 2, RIM_GROW), (BASE_H / 2, BASE_GROW)):
            for sx in (-1, 1):
                parts.append(nail("nail", (sx * (HALF - 0.03), -HALF - grow - 0.001, z), (90, 0, 0), iron, rot))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(nail("nail_top", (sx * (HALF - BAND_D / 2), sy * (HALF - BAND_D / 2), HEIGHT - 0.001),
                              (0, 0, 0), iron))

    # Plank floor inside.
    fw = 2 * (HALF - BAND_D) / 5
    for i in range(5):
        y = -(HALF - BAND_D) + fw * (i + 0.5)
        parts.append(beam("floor", (2 * (HALF - BAND_D) - 0.004, fw - 0.002, 0.02), (0, y, 0.06), (0, 0, 0),
                          planks[i % len(planks)], 0, 0.003, board_offset(rng, tile_plank)))
    return parts


if __name__ == "__main__":
    kit.run(build)
