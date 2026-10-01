"""Structure checks the kit runs on every build: what a render can hide.

Per build the kit prints ``CHECK`` lines and records them in ``<id>_build.json``:

- parts: each part's triangles and material; parts that float free of the rest; parts without a
  material; surfaces in one flat colour (a Principled BSDF whose Base Color is a plain value and
  whose material has no texture or procedural node feeding it);
- mesh: non-manifold edges, loose vertices, degenerate faces, and how far the mesh is from
  mirror symmetry across X (for objects the reference shows symmetric).
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

FLOAT_GAP_SHARE = 0.01  # a part further than this share of the asset's size from every other part floats
SAMPLE_VERTICES = 1500
DEGENERATE_AREA = 1e-12
TEXTURE_NODE_TYPES = {"TEX_IMAGE", "TEX_NOISE", "TEX_VORONOI", "TEX_WAVE", "TEX_GRADIENT", "TEX_MAGIC",
                      "TEX_CHECKER", "TEX_BRICK", "TEX_GABOR", "TEX_WHITE_NOISE", "TEX_ENVIRONMENT", "ATTRIBUTE",
                      "VERTEX_COLOR", "AMBIENT_OCCLUSION", "NEW_GEOMETRY", "LAYER_WEIGHT", "FRESNEL", "BEVEL",
                      "OBJECT_INFO", "TEX_SKY", "GROUP"}


def _world_points(obj: bpy.types.Object, limit: int) -> list[Vector]:
    vertices = obj.data.vertices
    step = max(1, len(vertices) // limit)
    return [obj.matrix_world @ vertices[index].co for index in range(0, len(vertices), step)]


def _bvh(obj: bpy.types.Object) -> BVHTree:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def _textured(tree: bpy.types.NodeTree) -> bool:
    return any(node.type in TEXTURE_NODE_TYPES for node in tree.nodes)


def flat_materials(materials) -> list[str]:
    """Materials whose surface is one plain colour: nothing but constants feeds their shaders."""
    flat = []
    for material in materials:
        if material is None or material.get("baked"):
            continue
        if not _textured(material.node_tree):
            flat.append(material.name)
    return sorted(set(flat))


def parts_report(parts: list[bpy.types.Object]) -> dict:
    """Floating parts, parts without a material and flat-colour materials, before the parts are joined."""
    meshes = [part for part in parts if part.type == "MESH" and len(part.data.vertices)]
    bpy.context.view_layer.update()
    corners = [part.matrix_world @ Vector(corner) for part in meshes for corner in part.bound_box]
    size = max((max(c[i] for c in corners) - min(c[i] for c in corners) for i in range(3)), default=0.0)
    gap = max(0.002, FLOAT_GAP_SHARE * size)
    trees = {part.name: _bvh(part) for part in meshes} if len(meshes) > 1 else {}
    floating = []
    for part in meshes if len(meshes) > 1 else []:
        nearest = min(
            (hit[3] for point in _world_points(part, SAMPLE_VERTICES // max(1, len(meshes)) + 50)
             for name, tree in trees.items() if name != part.name
             for hit in [tree.find_nearest(point)] if hit[0] is not None),
            default=float("inf"))
        if nearest > gap:
            floating.append(f"{part.name} ({nearest:.3f} m from the rest)")
    no_material = sorted(part.name for part in meshes if not any(slot.material for slot in part.material_slots))
    materials = {slot.material for part in meshes for slot in part.material_slots if slot.material}
    return {"parts": len(meshes), "floating": floating, "no_material": no_material,
            "flat_colour": flat_materials(materials)}


def mesh_report(obj: bpy.types.Object) -> dict:
    """Topology problems and mirror symmetry of the joined asset."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold and not edge.is_boundary)
    boundary = sum(1 for edge in bm.edges if edge.is_boundary)
    loose = sum(1 for vert in bm.verts if not vert.link_edges)
    degenerate = sum(1 for face in bm.faces if face.calc_area() < DEGENERATE_AREA)
    bm.free()
    points = np.array([vertex.co[:] for vertex in obj.data.vertices], dtype=np.float64)
    symmetry = None
    if len(points) > 3:
        sample = points[:: max(1, len(points) // 4000)]
        tree = KDTree(len(points))
        for index, point in enumerate(points):
            tree.insert(point, index)
        tree.balance()
        mirrored = sample * np.array([-1.0, 1.0, 1.0])
        distances = [tree.find(point)[2] for point in mirrored]
        size = float(np.ptp(points, axis=0).max()) or 1.0
        symmetry = round(float(np.mean(distances)) / size, 4)
    return {"non_manifold_edges": non_manifold, "open_edges": boundary, "loose_vertices": loose,
            "degenerate_faces": degenerate, "mirror_error": symmetry}


def lines(parts: dict, mesh: dict) -> list[str]:
    """The CHECK lines a build prints."""
    out = [f"CHECK parts {parts['parts']}; floating {', '.join(parts['floating']) or 'none'}; "
           f"without material {', '.join(parts['no_material']) or 'none'}; "
           f"flat colour {', '.join(parts['flat_colour']) or 'none'}"]
    out.append(f"CHECK mesh: non-manifold edges {mesh['non_manifold_edges']}, open edges {mesh['open_edges']}, "
               f"loose vertices {mesh['loose_vertices']}, degenerate faces {mesh['degenerate_faces']}, "
               f"mirror error across X {mesh['mirror_error']} of the size (0 = symmetric)")
    return out
