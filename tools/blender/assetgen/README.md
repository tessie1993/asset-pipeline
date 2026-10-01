# Asset generators (image-to-assets pipeline)

The whole pipeline, step by step, is the skill `.claude/skills/image-to-assets/SKILL.md`; a builder
gets its task from `python3 tools/assetgen/pack.py brief <pack> <id>`. This page is the contract
for the Blender part: how one generator turns one object's reference into a Godot-ready model.
Nothing in the pipeline assumes what an object is, what it is made of, how big it is, what style it
has or from which angles it is seen: all of that comes from the image, the user's answers and the
builder's own analysis of the reference.

| What | Where |
|---|---|
| Pack manifest: objects, art style, reference images, recorded views and camera, budget, skills | `design/asset-packs/<pack>/pack.json` |
| Source image; Canva images (`canva/NN_<id>.png`) or the user's references (`references/`) | `design/asset-packs/<pack>/` |
| Generators, one per object | `tools/blender/assetgen/packs/<pack>/<id>.py` |
| Models for Godot | `assets/models/<pack>/<id>.glb` |
| Notes, renders, CV reports, compare sheets, Godot shots | `production/qa/evidence/<pack>/<id>/` |
| The user's download (outside the repository) | `<export folder>/<pack>/` and `<pack>.zip` |

## Views: recorded from the reference, never fixed

The builder records the views its reference shows (`pack.py views`): per view the reference image,
the box around the object in it, the azimuth (0 front, 90 seen from the right, 180 back, 270 from
the left) and the elevation (degrees above the horizon), plus one camera for the object: `--lens MM`
for references with perspective (85 by default) or `--ortho` for drawings without it.
`tools/assetgen/cv.py views` proposes the boxes; `cv.py grid` helps read them by eye. The kit
renders exactly those views, each with its box's aspect; the Godot check uses the same angles.

## Build one object

```bash
blender -b --factory-startup --python tools/blender/assetgen/packs/<pack>/<id>.py -- \
    [--views N ...] [--final] [--no-render] [--samples S] [--resolution PX] [--threads T]
```

- A **cycle build** (no flags) exports the `.glb`, renders every recorded view at 12 samples and
  512 px (about 2 s a view on two threads, measured here) and runs the CV compare.
- `--views N` renders one or a few views: the quickest check while shaping one part.
- `--final` renders the views at 32 samples and 768 px and adds an 8-view turnaround for review.
- Each rendering build is numbered (`<id>_build.json`); `cv.py compare` reports on it and the build
  gate hook waits for `## Cycle <n>` in the builder's notes before the next build.

Renders have a transparent background (the outline is the alpha), the studio lighting below and an
exposure of -1.5, at which a lit surface's median brightness matches its material colour (measured
on spheres and boxes, colours L 0.34 to 0.79, mostly within about 0.04): give a part the reference's
colour and the render shows that colour, and so does Godot.

## The CV compare after every build

`tools/assetgen/cv.py compare` (run by the kit) normalises both outlines to the same height and
prints one line per view: outline overlap, the width/height change, the regions (of a 3 x 3 grid)
missing or extra in the render, mean and main colours with brightness, the regions rendered lighter
or darker, and edge density (detail). It writes `<id>_compare.png` (rows: render, reference,
overlay with magenta missing and yellow extra) and per view `<id>_cv_survey_<n>.png` (3 x 3 close-up
tiles, reference beside render). `cv.py closeup` zooms on one region. All observations, no verdicts.

## How the blender-skills are used

The skills in `.claude/skills/` (from `kevinbadi/blender-skills`) send Blender Python to a GUI
Blender over the blender-mcp socket. Here the same Blender code runs headless inside `kit.py`:

| Skill | In the kit |
|---|---|
| `polyhaven-texture-apply` | `kit.material()`: Poly Haven PBR set via the Poly Haven API, Mapping-node tiling |
| `polyhaven-studio-setup` | render world lit by a neutral Poly Haven studio HDRI |
| `product-polish` | the four "studio" area lights (key, fill, rim, bounce) |
| `turntable` | the final build's turnaround |

Builders read the other skills (`pack.py skills-list`) and run their Blender code inside their own
generator when it helps; skills that need an external service or a GUI give their method only.

## Materials: searched while building, never preset

```bash
python3 tools/assetgen/pack.py material-search <words describing the surface> --previews <folder>
```

It lists matching textures from Poly Haven and ambientCG (loaded through the installed *AmbientCG
Material Importer* add-on), each with its `ref` and a thumbnail to look at before choosing. In a
generator: `kit.material("<ref>", tile=<repeats per metre>, tint="#rrggbb", roughness=...,
normal_strength=...)`; `kit.flat("<name>", "#rrggbb", ...)` for flat colours, see-through and glow.
`tint` multiplies the texture and can only darken it. Only image → (tint) → Principled set-ups,
roughness/metal maps, normal maps, constant colours and emission reach Godot: no procedural
shader nodes for the look. Keep emission at 1.5 or below.

Downloads are cached outside the repository (`~/.cache/asset-pipeline`, or `ASSETGEN_CACHE`) and
locked per texture, so parallel builds can share them.

Installed add-ons (`kit.enable_addon("<id>")`): `sapling_tree_gen`, `modular_tree`, `easy_tree`,
`space_colonization_tree_generator`, `scatter_objects`, `antlandscape`,
`erosion_terrain_extension`, `terrainmixer`, `ambientcg_material_importer`.

## Rules for a generator

- One file `tools/blender/assetgen/packs/<pack>/<id>.py`: a docstring naming the object, a
  `build()` that returns the mesh objects, and `kit.run(build)` (`kit.run(build, origin="back")`
  for things that hang on a wall). `python3 tools/assetgen/pack.py kit-api` lists the kit's
  functions (`box`, `cylinder`, `sphere`, `lathe`, `add_bevel`, `roughen`, `smooth`, materials) with
  their docstrings; plain `bmesh`/`bpy` and add-ons are fine too.
- Metres; +Z up; the front faces **-Y** (Godot +Z). The kit applies modifiers and transforms, adds
  world-space UVs (1 UV unit = 1 m; set `obj["keep_uv"] = True` to keep your own), joins
  everything into one mesh named `<id>` and puts the origin at the bottom centre (or the back).
- Copy the reference: its proportions, every part, the details and nuances, the colours and the
  level of detail; model what changes the outline or catches light, texture what is flat; copies
  differ as they do in the reference; add nothing the reference does not show.
- The triangle budget is the object's `budget` in `pack.json` (the user's, or the builder's own
  with its reason); `pack.py done` refuses a model over it.
- Deterministic: seed any randomness (`random.Random(<fixed int>)`).

## Locked during a run

From `pack.py run-start` to `pack.py run-end` the hooks (`.claude/hooks/assetgen-guard.sh`, logic
in `tools/assetgen/guard.py`) allow changes only in the run pack's own folders and `.scratch/`;
any pipeline file changed anyway is restored from the run-start snapshot, stray files are moved to
`.scratch/assetgen/quarantine/`, git is locked, and Canva gets only the exact `pack.py prompt`.
If the kit cannot do something, the builder writes the helper inside its own generator; if the
pipeline itself is wrong, the builder reports it and the orchestrator tells the user.
