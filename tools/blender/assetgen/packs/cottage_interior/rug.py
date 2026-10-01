"""cottage_interior / rug: round braided rug, from design/asset-packs/cottage_interior/canva/04_rug_360.png.

One thick braided rope coiled in concentric rings, lying flat: a small plain sand disc in the
centre, seven braided rings (rings 3 and 6 darker reddish tan), and a brown bound rim with a thin
brown side band. Every braided ring is a rounded tube with real herringbone (V-shaped plait)
relief and UVs that follow the ring, so the rope texture wraps around the rug instead of being
projected flat. Metres, +Z up, 2.2 m across.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from assetgen import kit  # noqa: E402

DIAMETER = 2.2
RADIUS = DIAMETER / 2
CENTER_R = 0.17            # plain centre disc (the sheet shows ~16 % of the diameter)
RIM_INNER_R = 1.02         # braided rings end here, the bound rim starts
RING_COUNT = 8
DARK_RINGS = (2, 5)        # zero based: at ~40 % and ~72 % of the radius

Z_EDGE = 0.026             # height of the grooves between rings (top of the core)
CROWN = 0.033              # how far a ring crown stands above its groove
ALPHA_MAX = math.radians(68)  # the tube profile is an ellipse arc of +-68 degrees
PITCH = 0.065              # length of one herringbone V along the ring (m)
SPP = 4                    # samples per V along the ring
ARM = 4                    # cross-section segments per arm of the V
AMP = 0.007               # herringbone relief height (m)

# Rope001 is 8 diagonal strands per texture repeat, at 45 degrees in uv space. One grid step of
# the ring mesh (SPP samples per V, ARM steps per V arm) is 1/32 uv unit, so the mesh's ridge
# diagonals fall exactly on the strands; the uv across the ring is mirrored about its centre line,
# which turns the diagonal strands into V shaped herringbone plaits.
UV_STEP = 1.0 / 32.0
STRAND_PHASE = 0.053       # u+v of the strand centres in the texture (mod 1/8), read off the map
NORMAL = 1.6

LIGHT_TINT = "#ffefdc"
DARK_TINT = "#b9967d"
RIM_TINT = "#bb9573"
CENTER_TINT = "#ffffff"


def _tri(bm, uv_layer, corners):
    """Add a triangle from ``[(vert, (u, v)), ...]``."""
    face = bm.faces.new([vert for vert, _ in corners])
    for loop, (_, uv) in zip(face.loops, corners):
        loop[uv_layer].uv = uv
    return face


def braid_ring(name, r_in, r_out, mat, shift):
    """One braided ring: a rounded tube (elliptical arc profile) with a herringbone relief."""
    rc, half = (r_in + r_out) / 2, (r_out - r_in) / 2
    circ = 2 * math.pi * rc
    chevrons = 8 * max(1, round(circ / (8 * PITCH)))   # whole texture repeats round the ring: no seam
    nt = chevrons * SPP
    cross = 2 * ARM
    v0 = STRAND_PHASE + UV_STEP * shift            # strands land on the ridges of this ring
    a = half / math.sin(ALPHA_MAX)                 # half width of the full ellipse
    h = CROWN / (1 - math.cos(ALPHA_MAX))          # its half height

    profile = []
    for j in range(cross + 1):
        u = -1 + 2 * j / cross
        al = u * ALPHA_MAX
        x, z = a * math.sin(al), Z_EDGE + h * (math.cos(al) - math.cos(ALPHA_MAX))
        nx, nz = h * math.sin(al), a * math.cos(al)
        norm = math.hypot(nx, nz)
        profile.append((x, z, nx / norm, nz / norm, 1 - u ** 4))

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    grid = []
    for i in range(nt):
        theta = 2 * math.pi * i / nt
        c, s = math.cos(theta), math.sin(theta)
        column = []
        for j, (x, z, nx, nz, envelope) in enumerate(profile):
            relief = AMP * envelope * math.cos(math.pi / 2 * (i + shift + abs(j - ARM)))
            rho = rc + x + relief * nx
            column.append(bm.verts.new((rho * c, rho * s, z + relief * nz)))
        grid.append(column)

    for i in range(nt):
        i2 = (i + 1) % nt
        u0, u1 = i * UV_STEP, (i + 1) * UV_STEP
        for j in range(cross):
            A, B, C, D = grid[i][j], grid[i2][j], grid[i2][j + 1], grid[i][j + 1]
            vj, vj1 = v0 + abs(j - ARM) * UV_STEP, v0 + abs(j + 1 - ARM) * UV_STEP
            uA, uB, uC, uD = (u0, vj), (u1, vj), (u1, vj1), (u0, vj1)
            if j >= ARM:                           # right arm: ridges run along B-D
                _tri(bm, uv_layer, [(A, uA), (D, uD), (B, uB)])
                _tri(bm, uv_layer, [(D, uD), (C, uC), (B, uB)])
            else:                                  # left arm: ridges run along A-C
                _tri(bm, uv_layer, [(A, uA), (D, uD), (C, uC)])
                _tri(bm, uv_layer, [(A, uA), (C, uC), (B, uB)])
    obj = kit.mesh_object(name, bm, mat)
    obj["keep_uv"] = True
    obj.data.shade_smooth()
    return obj


def build():
    rng = random.Random(7)
    braid = dict(tile=1.0, normal_strength=NORMAL, roughness=0.9)   # uv already in texture units
    lights = kit.material_variants("ambientcg:Rope001", LIGHT_TINT, RING_COUNT, spread=0.05, seed=3, **braid)
    darks = kit.material_variants("ambientcg:Rope001", DARK_TINT, RING_COUNT, spread=0.05, seed=5, **braid)
    rim_mat = kit.material("ambientcg:Rope001", tint=RIM_TINT, tile=6.0, normal_strength=1.0, roughness=0.9)
    center_mat = kit.material("ambientcg:Rope001", tint=CENTER_TINT, tile=12.0, normal_strength=0.6, roughness=0.95)

    parts = []
    width = (RIM_INNER_R - CENTER_R) / RING_COUNT
    for k in range(RING_COUNT):
        mat = darks[k] if k in DARK_RINGS else lights[k]
        parts.append(braid_ring(f"ring_{k}", CENTER_R + k * width, CENTER_R + (k + 1) * width,
                                mat, rng.randrange(SPP)))

    # Core under the rings: fills the grooves, forms the bound rim and the thin brown side band.
    core = kit.lathe("core", [
        (0.0, 0.0), (RADIUS - 0.006, 0.0), (RADIUS, 0.008), (RADIUS, 0.022), (RADIUS - 0.006, 0.031),
        (RADIUS - 0.020, 0.035), (RADIUS - 0.045, 0.034), (RIM_INNER_R - 0.004, Z_EDGE + 0.002),
        (RIM_INNER_R - 0.03, Z_EDGE), (0.0, Z_EDGE),
    ], mat=rim_mat, segments=160)
    kit.smooth(core, 50)
    parts.append(core)

    # Plain sand centre, a gentle pad.
    disc = kit.lathe("centre", [
        (0.0, 0.040), (0.11, 0.0395), (0.158, 0.036), (CENTER_R + 0.006, Z_EDGE - 0.001),
    ], mat=center_mat, segments=64, cap_bottom=False)
    kit.smooth(disc, 50)
    parts.append(disc)
    return parts


if __name__ == "__main__":
    kit.run(build)
