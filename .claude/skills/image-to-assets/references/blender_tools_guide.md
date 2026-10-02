# Blender tools guide for builders (headless Blender 5.2)

What `tools/blender/install_blender.sh` and the plugins install, what each tool is for, and how to
call it from a script that runs in `blender -b`. "Headless: yes" means the tool runs in background
Blender 5.2; "UI only" means it needs a 3D viewport or a pen and does not run headless (use the
named alternative). Pick the tool by the job (section 1), not by habit. Paths are relative to the
repository root.

## 1. Which tool for which job

| Job | First choice | Also |
|---|---|---|
| Big organic or soft forms (rocks, cushions, cloth masses, bodies, dough, terrain lumps) | SDF clay / sculpt procedures from the `scenario-blender-sculpting` skill, then `kit.quad_remesh` | Multires + sculpt moves from the skill; Remesh modifier (voxel) |
| Hard, machined, man-made parts | `scenario-blender-hard-surface` skill: bevels, booleans, weighted normals | Bool Tool auto operators; Edit Mesh Tools (fillet, offset edges, edge roundifier) |
| Turned or round parts (vases, posts, knobs, bottles, wheels) | `kit.lathe(profile)` | Screw modifier |
| Tubes, cords, cables, wires, braids, filigree, vines, rims | Bezier/NURBS curves with bevel depth, taper and tilt, converted to mesh | Geometry Nodes Curve to Mesh with a profile; twisted strands from 2-3 offset curves |
| Repeated parts (rows, rings, scales, studs, planks, tiles, bricks) | Array / Geometry Nodes instancing with per-copy jitter | `scenario-blender-geometry-nodes` skill; Scatter Objects add-on |
| Smooth an uneven loop or surface | LoopTools Relax / Space / Curve | Edit Mesh Tools Relax; CurveFitting |
| Make a loop round, flat or evenly spaced | LoopTools Circle / Flatten / Space | |
| Bridge or loft between loops | LoopTools Bridge / Loft | bmesh `bridge_loops` |
| Masses of many small elements (strands, fibres, bristles, grass, needles, feathers, hair) | `scenario-blender-hair` skill: groom with hair curves + Essentials node groups (Clump, Curl, Frizz, Trim), then hair cards (`add_cards` in `bx_hair`) or mesh strands converted to MESH (the kit keeps only meshes), on a textured base surface | Mesh clumps: tapered curves converted to mesh, layered base to tip with grooves and broken tips; never one smooth shell for a mass of small elements |
| Clean topology from dense shapes | `kit.quad_remesh` (QuadriFlow) or `instant-meshes` | `scenario-blender-retopology` skill; mmgpy remesher |
| Mesh health (non-manifold, degenerate, thin walls, self-intersection) | 3D-Print Toolbox checks | `kit.clean`; the kit's own structure checks |
| UVs | the kit's bake path; `scenario-blender-uv-baking` skill | Zeeks Auto UV Unwrap (auto seams, pack, texel density); xatlas |
| Materials and texture sets | `pack.py material-search` + `kit.material(...)` | BlendKit free materials; Node Wrangler; `scenario-blender-texturing-shading` skill |
| Ready-made sub-parts (a bolt, a gem cut, a chain, a hinge, foliage) | BlendKit free models (licence check), restyled to match the reference | Extra Mesh Objects (gears, gems, pipes, round cubes, twisted torus ...) |
| Lighting and look checks | the kit's renders (`kit.render_views`, every recorded view lit and clay) and `cv.py compare` | `cv.py closeup` and `cv.py sample` on a part |
| Rigging and animation (after the model is accepted) | Rigify, CloudRig | EasyWeight, Corrective Shape Keys, Wiggle Bones, Dynamic Parent, AnimAll, Pose Library |

## 2. Enabling an add-on in a generator

Use the kit: `kit.enable_addon("bl_ext.blender_org.<id>", with_preferences=True)` (or for the
pipeline's own extensions `bl_ext.user_default.<id>`). `with_preferences=True` is needed by add-ons
that read their preferences on register (rigify, cloudrig, bool_tool, EdgeFlow); it does not save
the user's preferences (the kit runs `--factory-startup`). Plain bpy equivalent:
`addon_utils.enable("<module>", default_set=True)`.

Operators run on the active object and the current selection: set the mode
(`bpy.ops.object.mode_set(mode="EDIT")`), select with bmesh (`bmesh.from_edit_mesh`, set
`.select`, `bm.select_flush(True)`, `bmesh.update_edit_mesh`), call the operator, check its
return value is `{'FINISHED'}`, and measure that the mesh changed as intended. When an operator
needs a 3D viewport (poll fails with "context is incorrect"), it is UI only: use the alternative.
Prefer bmesh, modifiers and Geometry Nodes for anything that must be exact and repeatable.

## 3. Installed add-ons

### Modeling (headless: yes unless marked)

- **LoopTools** (`bl_ext.user_default.looptools`, edit mode, select a loop or region):
  `mesh.looptools_relax` (smooth a loop keeping its shape), `looptools_space` (even spacing),
  `looptools_circle` (make round), `looptools_flatten` (best-fit plane), `looptools_curve` (smooth
  curve through a loop), `looptools_bridge` (bridge/loft loops). `looptools_gstretch` needs strokes.
- **Edit Mesh Tools** (`bl_ext.blender_org.edit_mesh_tools`): `mesh.relax` (shape-keeping relax),
  `mesh.offset_edges` (offset an edge loop on the surface: insets, trims, grooves),
  `mesh.edge_roundifier` (arcs on edges), `mesh.face_inset_fillet` (rounded insets),
  `mesh.fillet_plus`, `mesh.vertex_chamfer`, `mesh.split_solidify`, `mesh.random_vertices`
  (irregularity), `object.mextrude` (multi-extrude with rotation, scale and randomness: spikes,
  branches, horns, prongs, tendrils), `edgetools_*` (extend, project, slice, spline between edges,
  shaft), `object.mesh_edge_length_set`.
- **CurveFitting** (`bl_ext.blender_org.CurveFitting`): `mesh.curve_fitting` smooths uneven vertex
  runs into a fair curve.
- **Bool Tool** (`bl_ext.blender_org.bool_tool`, object mode, active = canvas, selected =
  cutters): `object.boolean_auto_difference / _union / _intersect / _slice` (applied at once),
  `object.boolean_brush_*` (live, non-destructive cutters), `boolean_apply_all`. Carve tools
  (`carve_box`, `carve_circle`, `carve_polyline`) are UI only.
- **3D-Print Toolbox** (`bl_ext.blender_org.print3d_toolbox`): `mesh.print3d_check_all` and the
  single checks (solid, intersect, degenerate, thickness, sharp, overhang, shells),
  `mesh.print3d_clean_non_manifold`, `mesh.print3d_info_volume / _area`, `mesh.print3d_hollow`.
  Use the checks as an extra health pass before the final build.
- **Extra Mesh Objects** (`bl_ext.user_default.extra_mesh_objects`): parametric primitives such as
  gears, gems, pipe joints, round cubes, twisted torus, star, wedge, honeycomb, beam, pyramids.
- **Align Tools** (`bl_ext.blender_org.align_tools`): align selected objects to the active one.
- **Copy Attributes Menu**: copy modifiers, constraints, transforms and materials between objects.
- **Node Wrangler** (core): node helpers for material building.
- **Bsurfaces** (`bl_ext.blender_org.bsurfaces_gpl_edition`): `mesh.surfsk_add_surface` builds a
  surface from curves or loose edges; its stroke tools are UI only.
- **mmgpy** (`bl_ext.user_default.mmgpy`): adaptive remeshing.
- **UI only**: EdgeFlow (`set_edge_flow`, `set_edge_curve`, `set_edge_linear`; use LoopTools Curve
  / Relax and CurveFitting instead), Auto Mirror (use a Mirror modifier with bisect), F2, Snap
  Line Tool, PolyQuilt (retopology by hand; use `kit.quad_remesh` or `instant-meshes`).

### UV and baking

- **Zeeks Auto UV Unwrap** (`bl_ext.user_default.zeeks_auto_uv_unwrap`): `uv_fixer.auto_seams_unwrap`
  (seams from sharp edges, unwrap, pack), `uv_fixer.pack_scale` (even texel density),
  `uv_fixer.unwrap_marked_seams`, `uv_fixer.quick_triplanar_fix`. The interactive seam picker is UI only.
- **xatlas** (Python module in Blender's Python): automatic charting and packing.

### Materials and assets

- **BlendKit** (`plugins/blendkit/headless.py`; it needs a BlendKit login, made once with
  `python3 plugins/blendkit/login.py start`, and says so when there is none): `headless.enable()`,
  `headless.search("asset_type:model is_free:true <words>")` or `asset_type:material`,
  `headless.append(asset)`. Check `asset["license"]`. Restyle anything appended (shape, scale,
  colour, wear, art style) until it matches the reference. Without a login, use the libraries below.
- **ambientCG Material Importer**, Poly Haven and cgbookcase through `pack.py material-search`.

### Nature and terrain (pipeline's own)

ANT Landscape, Erosion Terrain, TerrainMixer, Procedural Tiles, Scatter Objects, Sapling Tree
Gen, Modular Tree, Easy Tree, Space Colonization Tree, Ivy Gen.

### Rigging and animation (after the model is accepted)

Rigify (core; metarigs and rig generation), CloudRig (rig generation and rigging tools),
EasyWeight (weight painting helpers), Corrective Shape Keys, Wiggle Bones (secondary motion on
bones), Dynamic Parent (animated parent switching), AnimAll (animate mesh data), Pose Library
(core). Not part of building a static model.

## 4. Command-line tools

- `instant-meshes` (/usr/local/bin): field-aligned quad remeshing of a dense mesh.
- `python3 tools/assetgen/cv.py` (views, grid, measure, compare, closeup, observe, sample): the
  reference measurements and the compare. `cv.py closeup <pack> <id> --view N --box X0 Y0 X1 Y1
  [--scale S]` puts a box of reference view N next to the same box of the latest build (box as
  fractions of the object, from its top-left): use it per part after every build.
- `python3 tools/assetgen/pack.py kit-api`: the kit's functions (box, cylinder, sphere, lathe,
  add_bevel, roughen, smooth, clean, quad_remesh, material, material_variants, mark, attribute,
  render_views, run, enable_addon, skill).
- ImageSorcery MCP (crop, resize, find, detect, ocr), when the session has its tools
  (`mcp__imagesorcery__*`); during a run it works on copies of the reference views in the pack's
  evidence folder and in `.scratch/`.

## 5. Skills (read the SKILL.md before using one; `pack.py skills-list` lists them)

`scenario-blender-expert` (Blender 5.x API and how a 3D artist judges a result),
`scenario-blender-sculpting`, `scenario-blender-hard-surface`, `scenario-blender-geometry-nodes`,
`scenario-blender-hair`, `scenario-blender-retopology`, `scenario-blender-uv-baking`,
`scenario-blender-texturing-shading`, `blender-image-to-3d` (the gated build method).
`kit.skill(skill_name, module)` imports a skill's script. Skills that `pack.py skills-list` leaves
out (lighting and render set-ups, camera videos, product shots and the like) are not for builders:
they would change the kit's renders or the model.

## 6. Work in parallel (multitask)

- **Let Blender run while you work.** Start a build, render or close-up as a background command
  (Bash with `run_in_background: true` and `timeout` in front of `blender`) and keep working while
  it runs: study the next part in the reference, think through what that thing is and how to build
  it, write its code, crop and measure the reference. You are notified when the command ends; then
  read the tail of its log and its images. Do not wait with `sleep` and do not poll.
- **Do independent steps together.** Send independent tool calls in one turn: several file reads,
  reference crops, `cv.py` measurements, renders of different parts or views.
- **Use all the cores.** The machine has `nproc` cores, shared by every running builder and part
  builder. Keep them busy: check `cat /proc/loadavg` when you start a job, and while the 1-minute
  load is below `nproc`, start another background Blender job instead of waiting. Split work into
  parallel jobs: one process per view or close-up angle, parameter variants of a part side by side,
  a texture bake in one process while previews render in another, the next part's test while the
  full build runs. Use `timeout` on every Blender run, and do not push the load far above `nproc`
  (that only slows every job down).
- **Keep parallel work from colliding.** Never run two jobs that write the same file at once. Do
  not edit a script while a background Blender run is loading it: give the run its own copy, or
  edit after it has loaded.
- **Never shrink the full build.** Quick renders are for a single part (the test harness, a
  close-up). The cycle's build of the whole generator always renders every recorded view, lit and
  clay, as the kit renders it, because the comparison needs all of them.
