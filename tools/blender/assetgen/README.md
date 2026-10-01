# Asset generators (image-to-Godot pipeline)

The whole pipeline, step by step, is the skill `.claude/skills/image-to-assets/SKILL.md`.
This page is the contract for the Blender part: how one generator turns one Canva 360 sheet
into a Godot-ready model. Nothing in the pipeline assumes what an object is, what it is made
of or what style it has: all of that comes from the image, the user's answers and the sheets.

| What | Where |
|---|---|
| Pack manifest: objects, art style, Canva ids, view angle and judged views per object | `design/asset-packs/<pack>/pack.json` |
| Source image | `design/asset-packs/<pack>/source.<ext>` |
| Canva 360 sheets (8 views, two rows of four) | `design/asset-packs/<pack>/canva/NN_<id>_360.png` |
| Object descriptions (reference images embedded) | `design/asset-packs/<pack>/objects/<id>.md` |
| Generators, one per object | `tools/blender/assetgen/packs/<pack>/<id>.py` |
| Models for Godot | `assets/models/<pack>/<id>.glb` |
| Renders, sheet, comparison, Godot shots | `production/qa/evidence/<pack>/<id>/` |
| The user's download (outside the repository) | `<export folder>/<pack>/` and `<pack>.zip` |

## Build one object

```bash
blender -b --factory-startup --python tools/blender/assetgen/packs/<pack>/<id>.py -- \
    [--no-render] [--samples 32] [--threads 2]
```

A build can take several minutes: run it with the Bash tool's `timeout` at 600000.

## How the blender-skills are used

The skills in `.claude/skills/` (from `kevinbadi/blender-skills`) send Blender Python to a GUI
Blender over the blender-mcp socket. Here the same Blender code runs headless inside `kit.py`:

| Skill | In the kit |
|---|---|
| `polyhaven-texture-apply` | `kit.material()`: Poly Haven PBR set via the Poly Haven API, Mapping-node tiling |
| `polyhaven-studio-setup` | render world lit by a neutral Poly Haven studio HDRI |
| `product-polish` | the four "studio" area lights (key, fill, rim, bounce) |
| `turntable` | eight views 45° apart, Cycles, PNG |

`image-to-3d` and `multi-image-to-3d` (Meshy) are not used. `threejs-export` targets the web;
the Godot export is `tools/blender/common/export.py`.

## Materials: searched while building, never preset

There is no material table. Each sub-agent finds the textures for its own object:

```bash
python3 tools/assetgen/pack.py material-search <words describing the surface> --previews <folder>
```

It lists matching textures from Poly Haven (863 texture sets) and ambientCG (about 2,000
materials, loaded through the installed *AmbientCG Material Importer* add-on), each with its
`ref` and a thumbnail saved in `<folder>` to look at before choosing. Order of preference:

1. a **Poly Haven** texture;
2. an **ambientCG** texture, when Poly Haven has nothing close;
3. a **plain Blender material**, `kit.flat("<name>", "#rrggbb", roughness=..., metallic=...,
   emission=..., alpha=...)`, for flat colours, see-through and glowing surfaces.

In a generator: `kit.material("<ref>", tile=<repeats per metre>, tint="#rrggbb", roughness=...,
normal_strength=...)`.
- `tile`: 1 / the texture's real-world size in metres (`size_m` in the search) keeps its true
  scale.
- `tint` multiplies the texture, and glTF carries it as the base colour factor, so Godot shows
  the same colour. It can only darken: choose a texture at least as light as the colour wanted.
- Every distinct combination of settings is its own material.

Only these node set-ups survive the glTF export: image → (tint) → Principled, the
roughness/metal maps, the normal map, a constant colour, emission. Procedural shader nodes do
not reach Godot; never use them for the look.

Glow (`emission`): keep it at 1.5 or below. Godot's default (linear) tone mapping clips stronger
emission to white.

Downloads are cached (`~/.cache/nokepom/`) and locked per texture, so parallel builds can use
the same texture safely.

Installed add-ons (enable with `kit.enable_addon("<id>")`): `sapling_tree_gen`, `modular_tree`,
`easy_tree`, `space_colonization_tree_generator`, `scatter_objects`, `antlandscape`,
`erosion_terrain_extension`, `terrainmixer`, `ambientcg_material_importer`.

## Close-ups: `zoom.py`

```bash
blender -b --factory-startup --python tools/blender/assetgen/zoom.py -- <pack> <id> \
    --view <azimuth> [--box X0 Y0 X1 Y1] [--scale 2]
```

Writes `production/qa/evidence/<pack>/<id>/<id>_zoom_<azimuth>.png`: that view of the Canva
sheet on the left, enlarged, and (once built) the same rendered view on the right. `--box`
crops both to one part (fractions of the view from its top-left). Use it to read textures on
the sheet before building and to compare them after each build.

## Rules for a generator

- One file `tools/blender/assetgen/packs/<pack>/<id>.py`: a module docstring naming the sheet,
  a `build()` that returns the mesh objects, and `kit.run(build)`, or
  `kit.run(build, origin="back")` for wall-mounted objects. The folder names the pack and the
  file name the object. Build with `kit.box`, `kit.cylinder`, `kit.sphere`, `kit.lathe`,
  `kit.add_bevel`, `kit.roughen`, `kit.smooth`, or plain `bmesh`/`bpy`.
- Metres; Blender +Z up; the object's front faces **-Y** (Godot +Z). The kit applies all
  modifiers and transforms, adds world-space UVs (1 UV unit = 1 m; set `obj["keep_uv"] = True`
  to keep your own), gives every part one UV layer with the same name, joins everything into
  one mesh named `<id>` and puts the origin at the bottom centre (or the back centre for
  `origin="back"`).
- Copy the sheet: its proportions, part count, silhouette, colours and level of detail. Bevel
  edges the sheet shows as soft; keep the irregularity the sheet shows; add no parts or styling
  the sheet does not have.
- Surface detail as rich as the sheet's; a model that reads flat next to its sheet fails:
  - texture visible at the object's size: set `tile` so the texture's pattern is readable at
    the sheet's scale, and raise `normal_strength` where the sheet shows relief;
  - no large area in one flat colour unless the sheet shows one: give each separate part its
    own variant with `kit.material_variants(ref, tint, count, tile=...)`, and make recessed or
    back parts a little darker where the sheet does;
  - real depth: parts that are separate on the sheet are separate in the model, with the same
    gaps, overlaps and layers; bevels big enough to catch a highlight;
  - see-through parts must be see-through (`kit.flat(..., alpha=...)` or open).
- Mid-poly budgets (triangles), set per object in `pack.json` (`size`): large ≤ 40 000,
  medium ≤ 20 000, small ≤ 10 000.
- Deterministic: seed any randomness (`random.Random(<fixed int>)`).
- The camera angle comes from the object's `view_elevation_deg` in `pack.json` (the angle its
  sheet was drawn from) and the framing fits the object; a generator never changes them.

## The pipeline is locked during a run

While a run is in progress (`pack.py run-start` until `pack.py run-end`), the hook
`.claude/hooks/assetgen-run-guard.sh` refuses edits to the pipeline (`kit.py`, this README,
`tools/assetgen/`, `tools/blender/common/`, `tools/assets/`, the installers, the Godot capture
script, `pack.json` files, `.claude/`, the pipeline's tests) and every git command that
changes the repository. A sub-agent changes only its own generator. If the kit cannot do
something, the sub-agent writes the helper inside its own generator and says so in its report;
if the pipeline itself is wrong, the orchestrator reports it to the user.

## Use Blender's materials, textures and lighting

- **Materials**: textures found with `material-search` through `kit.material()` and
  `kit.material_variants()`, and `kit.flat()` for flat colours, see-through and glow.
- **Textures**: make them read like the sheet with `tile` (pattern scale), `normal_strength`
  (relief), `tint` (colour) and `roughness` (gloss).
- **Lighting**: every render is lit by the kit's studio set-up from the blender-skills (a
  Poly Haven studio HDRI plus the four `product-polish` studio lights). Judge the model under
  it; do not remove or replace it in a generator.

## Quality loop (every object): understand, then 5 cycles of build → render → compare

1. **Understand** before building: study the Canva sheet view by view and write, at the top of
   `production/qa/evidence/<pack>/<id>/<id>_notes.md`, what the object is and, per element,
   its count and position, **volume**, **shading** and **detail level**, and a **texture list**
   (T1, T2, …; an object usually has more than one): per texture the elements that carry it,
   the kind of material, the pattern, colour, repeat size, direction, relief and wear read up
   close on the sheet with `zoom.py`, and how the user's art style shows in it. Each texture is
   then searched with its own words and chosen by comparing the thumbnails against that
   description. Every decision in the generator follows from these notes. Read the relevant skills the
   orchestrator listed (and any other installed skill that fits) and use their methods.
2. **Cycle** (the standard is 5):
   - **Build** with `--samples 16`; the build renders the eight views and
     `production/qa/evidence/<pack>/<id>/<id>_compare.png` (the Blender views on top, the Canva
     sheet below, same layout, same angles).
   - **Compare** view by view, element by element, through material, shading, detail level,
     elements and volume, with a `zoom.py` close-up of every texture, and write under `## Cycle <n>` in the notes: what **looks right and
     why**, what **looks wrong and why** (its cause in the model), and the **fix** for each
     wrong item. Fix causes, not symptoms; never undo what looks right.
   - Apply the fixes; the next build shows whether they worked.
   Never write image-measuring scripts: the compare sheet is the measuring tool.
3. **Final render** with the default `--samples 32`.

### Definition of good

Judged on the views in `judge_views` (all eight, unless some views of the Canva sheet
contradict the others and were left out):

| Check | Passes when |
|---|---|
| Elements | same elements as the sheet (count, positions); silhouette matches; proportions within about 10 % |
| Volume | elements stand out, sit back, bulge and have gaps as on the sheet; nothing flat that is 3D on the sheet |
| Material | every surface the same kind of material; metal where metal; similar gloss; see-through where see-through; same hue and brightness |
| Shading | soft edges bevelled and catching light as on the sheet; recesses as dark as on the sheet |
| Textures | in the zoom close-ups every texture matches the sheet: pattern, repeat size within about 20 %, direction, relief, colour variation, in the user's art style |
| Detail level | relief and variation between parts as on the sheet, no more and no less |
| Budget | the `BUILT` triangle count is within the object's budget |
| Clean | the build prints `BUILT` and `RENDERED`, no error or traceback |

Stopping: the standard is all 5 cycles, then the final render, then the report
(`CYCLES DONE`). A builder may stop sooner only when every check passes; it still does the
final render and reports `READY FOR REVIEW`, and the orchestrator shows the work to the user,
who decides. When the user wants changes, the builder continues with the next cycle.
