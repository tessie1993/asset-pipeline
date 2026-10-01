# Asset generators (image-to-assets pipeline)

The whole pipeline, step by step, is the skill `.claude/skills/image-to-assets/SKILL.md`; a builder
gets its task from `python3 tools/assetgen/pack.py brief <pack> <id>`. This page is the contract
for the Blender part: how one generator turns one object's reference into a detailed, Godot-ready
model. Nothing in the pipeline assumes what an object is, what it is made of, how big it is, what
style it has or from which angles it is seen: all of that comes from the image, the user's answers
and the builder's own analysis of the reference.

| What | Where |
|---|---|
| Pack manifest: objects, art style, reference images, recorded views and camera, budget, skills, critic reviews | `design/asset-packs/<pack>/pack.json` |
| Source image; Google Flow images (`flow/NN_<id>_<k>.<ext>`, one per side) or the user's references (`references/`) | `design/asset-packs/<pack>/` |
| Generators, one per object | `tools/blender/assetgen/packs/<pack>/<id>.py` |
| Models for Godot (baked textures inside) | `assets/models/<pack>/<id>.glb` |
| Notes, renders, CV reports, compare sheets, critic reviews, Godot shots | `production/qa/evidence/<pack>/<id>/` |
| Baked texture files (the .glb carries them) | `.scratch/assetgen/bake/<pack>/<id>/` |
| The user's download (outside the repository) | `<export folder>/<pack>/` and `<pack>.zip` |

## Views: recorded from the reference, never fixed

The builder records the views its references show (`pack.py views`), from every reference image:
per view the image, the box around the object in it, the azimuth (0 front, 90 seen from the right,
180 back, 270 from the left) and the elevation (degrees above the horizon), plus one camera for the
object: `--lens MM` for references with perspective (85 by default) or `--ortho` for drawings
without it. `tools/assetgen/cv.py views` proposes the boxes; `cv.py grid` helps read them by eye.
The kit renders exactly those views, each with its box's aspect; the Godot check uses the same angles.

## Looking closely: the CV tools

| Command | What it gives |
|---|---|
| `cv.py measure` | per view: outline w/h, fill, symmetry, main colours, width : height : depth |
| `cv.py observe` | per view a sheet of magnified tiles, each with its colour range, colour spread and texture strength: where the details, imperfections and variation are |
| `cv.py closeup --view N --box …` | one region magnified, reference beside the latest render |
| `cv.py sample --view N --box …` | colour statistics (mean, darkest, lightest, spread, main colours) of the reference and the render in the same box |
| `cv.py compare` (the kit runs it) | per view: outline overlap, w/h change, regions missing or extra, colours, regions lighter or darker, colour zones; `<id>_compare.png` with rows render, clay, reference, overlay |

All observations, no verdicts.

## Build one object

```bash
blender -b --factory-startup --python tools/blender/assetgen/packs/<pack>/<id>.py -- \
    [--views N ...] [--final] [--bake] [--no-render] [--no-clay] [--samples S] [--resolution PX] \
    [--texture PX] [--threads T]
```

- A **cycle build** (no flags) runs the structure checks, exports the `.glb`, renders every
  recorded view at 16 samples and 768 px, lit and in clay (one grey material: the shape alone),
  and runs the CV compare. The renders show the live shaders.
- `--views N` renders one or a few views: the quickest check while shaping one part.
- `--final` **bakes** every shader into textures, then renders the baked model at 32 samples and
  1280 px plus an 8-view turnaround: what you see is what Godot gets. `--bake` bakes in a cycle
  build too. `kit.run(build, texture=4096)` (or `--texture`) for an object seen up close.
- Each rendering build is numbered (`<id>_build.json`, with the checks and the bake); `cv.py
  compare` reports on it and the build gate hook waits for `## Cycle <n>` in the builder's notes
  before the next build.

Renders have a transparent background (the outline is the alpha), a neutral studio (Poly Haven HDRI
plus white key, fill, rim and bounce lights, each aimed at the asset) and an exposure of -1.3, at
which a lit surface's median brightness matches its material colour on average (spheres in 8
colours, L 0.34 to 0.79: mean difference -0.005, at most 0.046; dark colours render a little
lighter, light ones a little darker).

## Structure checks, every build

`CHECK` lines (`checks.py`): parts that float free of the rest, parts without a material,
flat-colour materials (nothing but constants feeding the shader), non-manifold and open edges,
loose vertices, degenerate faces, and the mirror error across X (for objects that are symmetric
on the reference).

## Geometry: mid to high poly, every detail modelled

- **Organic forms**: signed-distance clay from the sculpting skill
  (`S = kit.skill("scenario-blender-sculpting", "bx_sculpt")`: `S.Clay`, `sd_ellipsoid`,
  `sd_round_box`, `sd_tube`, smooth blends, plane cuts), meshed by OpenVDB; or geometry nodes'
  *Mesh to SDF Grid* → *SDF Grid Fillet* → *Grid to Mesh* (threshold 0); then
  `kit.quad_remesh(obj, faces)` (Instant Meshes, else QuadriFlow) and a Subdivision modifier.
  `kit.clean(obj)` merges the near-duplicate vertices voxel output leaves.
- **Hard forms**: bevels (`kit.add_bevel`), booleans with the `FLOAT`/`EXACT`/`MANIFOLD` solvers,
  weighted normals: the hard-surface skill (`bx_hardsurface`).
- **Repeated detail that varies**: geometry nodes (`bx_gn`), arrays and scatters from a seeded
  `random.Random`; never an unchanged copy.
- **Relief**: Displace modifiers for relief that changes the outline; bump, normal and displacement
  nodes for the rest (baked into the normal map).
- Primitives and `kit.lathe`, `kit.roughen`, `kit.smooth` remain for parts that need them.

## Materials: real ones, layered, baked

```bash
python3 tools/assetgen/pack.py material-search <words describing the surface> --previews <folder>
```

It searches Poly Haven, ambientCG, cgbookcase and Blendkit (free CC0 materials only: full Blender
node materials, often procedural) and lays the thumbnails out in one `sheet.png`. In a generator:

- `kit.material("<ref>", tile=<repeats per metre>, tint="#rrggbb", roughness=..., normal_strength=...,
  mapping="uv" | "triplanar", relief=<m>)`: a texture set on the part's UVs (world-space box UVs in
  metres unless `obj["keep_uv"]`), or projected from three axes with soft blends (`triplanar`,
  seamless on organic forms; relief from the set's height map).
- `kit.principled("M_name")` returns `(material, tree, bsdf)` for a shader built from nodes:
  noise, Voronoi, wave and gradient textures, colour ramps, ambient occlusion, pointiness, bevel,
  attributes. `kit.uv_node(tree)` maps an image on the kit's UV layer.
- Masks: `kit.mark(obj, field, material)` gives a material to the surface where a field is below
  zero with a clean edge cut into the mesh; `kit.attribute(obj, "name", field)` stores a soft mask
  per vertex, read in a shader with an Attribute node.
- The texturing skill (`kit.skill("scenario-blender-texturing-shading", "bx_materials")`) adds
  edge wear, grunge, curvature masks, stylised skin and eyes and texture painting.
- Blend materials by mixing their **inputs** into one Principled BSDF; a Mix Shader bakes to an
  average of its two shaders (the bake prints a note when it meets one).

**The bake** (`bake.py`, final builds): the joined asset is triangulated and given one square UV
atlas (xatlas, else Smart UV Project); each shader's Base Color, Roughness, Metallic, Alpha and
Emission are baked through emission into the atlas, keeping every mix, mask and texture; the
tangent-space normal (normal maps, bump nodes, the mesh's shading) and ambient occlusion are baked
as they render. The result is one glTF material: base colour (+ alpha), ORM (occlusion, roughness,
metallic), normal and, when something glows, emission. A material marked `mat["keep"] = True` is
left as it is. Subsurface, transmission, sheen and coat do not reach Godot.

Downloads are cached outside the repository (`~/.cache/asset-pipeline`, or `ASSETGEN_CACHE`) and
locked per asset, so parallel builds share them. The reference image is never projected onto a
model, and no surface is one flat colour unless the reference shows one.

## Skills and add-ons

The builders read the skills in `.claude/skills/` that fit their object (`pack.py skills-list`) and
import their scripts with `kit.skill(...)`:

| Skill | For |
|---|---|
| `blender-image-to-3d` | the method: gated phases, silhouettes and ratios measured against the reference, category notes |
| `scenario-blender-expert` | Blender 5.2 API traps, bpy reliability, mesh audit (`bx_audit`) |
| `scenario-blender-sculpting` | organic forms: signed-distance clay, plane cuts, numpy brushes (`bx_sculpt`) |
| `scenario-blender-hard-surface` | bevels, booleans, weighted normals, support loops (`bx_hardsurface`) |
| `scenario-blender-texturing-shading` | layered materials, wear, dirt, colour variation, skin, eyes (`bx_materials`) |
| `scenario-blender-uv-baking` | seams, unwrapping, packing, high-to-low bakes (`bx_uvbake`) |
| `scenario-blender-retopology` | QuadriFlow, voxel remesh, loops, low-poly preparation (`bx_retopo`) |
| `scenario-blender-geometry-nodes` | scattering, arrays, repeated detail (`bx_gn`) |
| `scenario-blender-hair` | fur and hair, hair cards for games (`bx_hair`) |

Scripts that render with Workbench or EEVEE need a display: `xvfb-run -a blender -b ...`. The
other skills in `.claude/skills/` (lighting and render set-ups, camera videos, product shots, AI
image-to-3D, Blender GUI tools) are marked `disable-model-invocation: true`: `pack.py skills-list`
leaves them out and builders never use them, so they cannot change the kit's renders or the model.

Installed add-ons (`kit.enable_addon("<id>")`): `extra_mesh_objects` (rocks, round cubes, gears,
gems), `ivygen`, `looptools`, `mmgpy` (adaptive remeshing), `proceduraltiles` (tile and brick node
groups), `zeeks_auto_uv_unwrap`, `sapling_tree_gen`, `modular_tree`, `easy_tree`,
`space_colonization_tree_generator`, `scatter_objects`, `antlandscape`,
`erosion_terrain_extension`, `terrainmixer`, `ambientcg_material_importer`. Also installed:
Instant Meshes (`instant-meshes`) and xatlas (in Blender's Python).

Read `blender-5.2-notes.md` before writing bpy: the Blender 5.2 names memory gets wrong.

## Rules for a generator

- One file `tools/blender/assetgen/packs/<pack>/<id>.py`: a docstring naming the object, a
  `build()` that returns the mesh objects, and `kit.run(build)` (`kit.run(build, origin="back")`
  for things that hang on a wall). `python3 tools/assetgen/pack.py kit-api` lists the kit's
  functions with their docstrings; plain `bmesh`/`bpy`, the skills' scripts and add-ons are fine too.
- Metres; +Z up; the front faces **-Y** (Godot +Z). The kit applies modifiers and transforms, adds
  world-space UVs (1 UV unit = 1 m; set `obj["keep_uv"] = True` to keep your own), joins
  everything into one mesh named `<id>`, puts the origin at the bottom centre (or the back) and, in
  the final build, bakes.
- Copy the reference: its proportions, every part, every detail, imperfection and variation, every
  surface's material and its variation; model what changes the outline or catches light; copies
  differ as they do in the reference; add nothing the reference does not show.
- The triangle budget is the object's `budget` in `pack.json` (the user's, or the builder's own
  with its reason): mid to high poly; `pack.py done` refuses a model over it.
- Deterministic: seed any randomness (`random.Random(<fixed int>)`).

## Locked during a run

From `pack.py run-start` to `pack.py run-end` the hooks (`.claude/hooks/assetgen-guard.sh`, logic
in `tools/assetgen/guard.py`) allow changes only in the run pack's own folders and `.scratch/`;
any pipeline file changed anyway is restored from the run-start snapshot, stray files are moved to
`.scratch/assetgen/quarantine/`, git is locked, the critic never starts Blender and writes only its
review, Google Flow gets only the exact `pack.py flow-call` set-up and never generates on its own. If the kit cannot do something, the
builder writes the helper inside its own generator; if the pipeline itself is wrong, the builder
reports it and the orchestrator tells the user.
