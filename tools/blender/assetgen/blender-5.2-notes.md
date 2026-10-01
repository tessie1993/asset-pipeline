# Blender 5.2 notes for builders

Builders write bpy from memory, and that memory mixes every Blender version. These are the
changes that break generated code on the installed Blender (5.2.2 LTS), and what survives the bake
and the export to Godot. When a name is not listed here, check it on the installed Blender
(`bl_rna`, `hasattr`) instead of recalling it.

Source: nokepom's notes (first collected by jangtrinh/design-os-3d-blender,
`knowledge/00-foundations/blender-version-matrix.md`, MIT), checked on Blender 5.2.2 with
`blender -b --factory-startup` on 2026-09-30, plus what this pipeline's research and smoke builds
found on 2026-10-01.

## API changes that break generated code

| Old name (what memory reaches for) | 5.2 |
|---|---|
| Boolean modifier `solver='FAST'` | `'FLOAT'` (the solvers are `FLOAT`, `EXACT`, `MANIFOLD`) |
| `mesh.use_auto_smooth` | removed: `kit.smooth(obj, angle)` or `bpy.ops.object.shade_auto_smooth()` (Smooth by Angle) |
| Principled `Specular`, `Subsurface`, `Transmission`, `Emission`, `Sheen`, `Clearcoat` | `Specular IOR Level`, `Subsurface Weight`, `Transmission Weight`, `Emission Color` (+ `Emission Strength`), `Sheen Weight`, `Coat Weight` |
| Mix node input `Fac` | `Factor` (Mix Shader keeps `Fac`) |
| `ShaderNodeTexMusgrave` | removed: folded into Noise Texture (its Type and Detail inputs) |
| `material.use_nodes = True` to get a node tree | the tree always exists; `use_nodes` is a deprecated no-op |
| setting `image_settings.file_format` alone | set `image_settings.media_type` first, then `file_format` |
| `action.fcurves` | removed: channelbags (`bpy_extras.anim_utils.action_get_channelbag_for_slot`) |
| `uv.unwrap()` defaults to ANGLE_BASED | it defaults to CONFORMAL: always pass `method=` |
| `BMLoopUV.select` | removed in 5.0 |
| default view transform Filmic | AgX (the kit renders with Standard) |

## Headless traps

- Workbench and EEVEE renders abort without a display (`libEGL`): run them under `xvfb-run -a`.
  The kit renders with Cycles and needs none.
- `sculpt.brush_stroke` and the trim operators fail their poll headless; `sculpt.mesh_filter`
  crashes Blender. Sculpt with signed-distance clay (`bx_sculpt`) or numpy on the vertices.
- QuadriFlow returns CANCELLED ("needs to be manifold") when any edge is shorter than 1e-4, as
  voxel and signed-distance output often is: `kit.clean(obj)` first (`kit.quad_remesh` does).
- Geometry nodes *Grid to Mesh*: its default threshold 0.1 returns an empty mesh from a signed
  distance grid; set it to 0.
- The Bump node's Distance defaults to 0.001 m: set it to the relief's real depth.
- Hair curves are not meshes: they cannot be baked from or exported; convert them (Curve to Mesh,
  hair cards) first.

## What reaches Godot

The final build bakes every material (`bake.py`), so any shader node setup reaches Godot as
textures: base colour (+ alpha), roughness, metallic, ambient occlusion, normal, emission.

| Reaches Godot | Does not (get the look another way) |
|---|---|
| Everything the shaders compute for Base Color, Roughness, Metallic, Alpha and Emission: image textures, procedural textures, colour ramps, masks, input mixes | Subsurface, Transmission, Sheen, Coat (Godot drops these glTF extensions) |
| Relief from Normal Map, Bump and Displacement nodes (baked into the tangent-space normal map) | Relief that should change the outline: model it, or use a Displace modifier |
| Geometry with modifiers applied | Hair curves, constraints, drivers, physics |
| One material per kept surface (`mat["keep"] = True`) as authored | A Mix Shader's exact look: the bake averages its two shaders' inputs; mix inputs instead |

Export: GLB, tangents included, no Draco or meshopt compression (Godot cannot import them).
