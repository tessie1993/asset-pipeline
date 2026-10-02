"""Aethel Fox (Phase 2 evolution of the blue fox): a slim stylised fox on long thin legs, very tall
pointed ears with tan / indigo spiral bowls, a braided leather cord collar with a round blue gem in a
silver bezel, silver-white antler branches over both shoulders, faintly glowing cyan spiral markings
and one huge plume tail curling up over the back into a cream tip.

Coordinates: metres, +Z up, the fox faces -Y, its left side is +X (the side the main side view sees,
az 65). Every size comes from the notes' Analysis (side view 2262 px/m to a 0.50 m total height,
front view 2270 px/m head-based, back view ~1450 px/m).
"""
import random
import sys
from pathlib import Path

import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit  # noqa: E402
from aethel_fox_parts.common import bvh_of, dark_material, close_holes  # noqa: E402
from aethel_fox_parts.body import (body_clay, mark_images, fur_material, cream_field,  # noqa: E402
                                   body_attributes, brow_frame, BROW_NODES)
from aethel_fox_parts.ears import ear_materials, ear_image, ear_tuft_material, build_ear, build_ear_tufts  # noqa: E402
from aethel_fox_parts.face import eye_material, EyeBed, build_eye, build_eyelids, build_nose, build_mouth  # noqa: E402
from aethel_fox_parts.collar import (silver_material, antler_material, cord_material, gem_material,  # noqa: E402
                                     GEM_C, build_cord, build_pendant, build_antlers)
from aethel_fox_parts.tail import build_tail  # noqa: E402

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
    parts += build_mouth(body_bvh, dark_material("M_mouth", "#3a2f35", 0.5, "#4b3d44"))
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
        mp.inputs["Location"].default_value = loc        # pre-scale: the marking reads the body's
        mp.inputs["Rotation"].default_value = rot        # pre-scale position attributes
        mp.inputs["Scale"].default_value = sc
    return parts


if __name__ == "__main__":
    kit.run(build, texture=4096)
