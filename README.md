# asset-pipeline

Image in, assets out. Give Claude Code an image and run `/image-to-assets <image> [<pack name>]
[skip canva]`: you pick which objects in it become 3D models and in which art style, and you get
one detailed, Godot-ready `.glb` per object (mid to high poly, every detail modelled, real
materials and shaders baked into textures), reviewed by a critic and by you, checked in Godot and
delivered as one zip.

It began as the pipeline of [tessie1993/nokepom](https://github.com/tessie1993/nokepom) as it was
before prep agents were added (commit `4e138ba`, the first commit of nokepom PR 36) and was then
made fully generic: no example pack, no style written into the Canva prompt, no fixed sizes or
view angles, and the builder reads its reference directly. It also carries the skills and tools of
nokepom's later pull requests (the `blender-image-to-3d` skill, the fresh-context critic, the Blender
5.2 notes, the Godot check script, `kit.mark`, cgbookcase textures), without their prep agents.

## How it works

1. **You choose.** Claude lists the objects in the image; you say which to make, the art style,
   and optionally triangle budgets (otherwise each builder decides from the object's detail, mid to
   high poly).
2. **Reference per object.** Canva draws each object from every side in your style, from your
   image (background removed, downloaded at full size). With `skip canva`, your own image(s) are
   the reference as they are.
3. **One builder agent per object, in parallel** (`asset-builder`, the strongest model at high
   effort). Before it may build it records every view in every reference image, measures them, looks
   at them magnified (`cv.py observe`, `closeup`, `sample`: details, imperfections, colour and
   material variation), reads the Blender skills that fit and writes an analysis: every part,
   every surface's material and its variation, every detail and nuance.
4. **Build → compare → write-up, every cycle.** Mid-to-high-poly models: sculpted signed-distance
   clay, quad remeshing, subdivision, bevels, booleans, geometry nodes; real materials from Poly
   Haven, ambientCG, cgbookcase and Blendkit plus procedural, layered shaders with masks. Each
   build runs structure checks, renders every recorded view lit and in clay and compares them with
   the reference (outline, proportions, colours, colour zones). The next build waits until the
   builder has written down what the compare showed and what it fixes.
5. **Baked for Godot.** The final build bakes every shader into one material (base colour, ORM,
   normal, emission) on one UV atlas, so what renders in Blender is what Godot shows. No flat
   colours, and the reference image is never projected onto a model.
6. **A critic reviews** each finished object with fresh eyes (`asset-critic`): every expectation
   PASS/FAIL from a named view, fixes as measurements; up to 3 rounds of fixes.
7. **You review**, Godot imports each accepted model and screenshots it from the same views, and
   you get the zip. The pack's working files are removed from the repository unless you want them
   committed.

## Hooks: how the run is held together

| Hook | When | What it does |
|---|---|---|
| `assetgen-guard.sh pre` | before Bash, Write, Edit, Canva generate-image, during a run | Refuses changes outside the run pack's folders, git changes, a Blender build before the builder's set-up is complete or before the last build's CV compare is written up, a builder's build past its context budget (it hands off), a critic starting Blender or writing anything but its review, and any Canva prompt that is not exactly `pack.py prompt` with the source image (no bias added) |
| `assetgen-guard.sh post` | after Bash, Write, Edit, during a run | Restores any pipeline file that changed anyway from the run-start snapshot, moves stray files to `.scratch/assetgen/quarantine/`, and after a build points the builder at its CV compare |
| `canva-remove-background.sh` | after Canva image generation | Asks for every generated image's background to be removed |
| `install-tools.sh` | session start (cloud) | Installs Blender 5.2.2 with its add-ons, Instant Meshes and xatlas, Godot 4.7.2 and the CV libraries in the background |

The guard logic is `tools/assetgen/guard.py`; during a run the hooks run its snapshot copy, so
editing the pipeline cannot switch them off. They do nothing outside a run.

## Quality first, then context and speed

- **Quality**: builders and critics run on the strongest model at high effort; 8 build cycles per
  object by default; up to 3 critic rounds; renders at 768 px (1280 px final) in lit and clay.
- **Context**: after 5 builds (`BUILDS_PER_BUILDER`, plus one final build) a builder writes a
  handoff in its notes and a fresh builder continues from them, so no context fills up with every
  earlier cycle; builders fetch their own brief (a one-line spawn prompt) and `pack.py status` has
  a `next` column per object, so a run resumes after a compaction or in a new session.
- **Speed**: a cycle build takes seconds to a minute (quick `--views N` checks in between); the
  bake and the turnaround only in the final build; builders run in parallel (one per two CPU
  cores); downloads are cached and shared.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/image-to-assets/SKILL.md` | The orchestrator's steps |
| `.claude/agents/asset-builder.md`, `asset-critic.md` | The builder and the critic |
| `.claude/hooks/`, `.claude/settings.json` | The hooks above |
| `.claude/skills/blender-image-to-3d/`, `.claude/skills/scenario-blender-*/` | The Blender skills builders use (method, sculpting, hard surface, texturing, UVs and baking, retopology, geometry nodes, hair, expert notes) |
| `.claude/skills/` (the 16 kevinbadi ones) | Blender skills from nokepom's pipeline; MCP-based, their method only carries over headless |
| `tools/assetgen/pack.py` | The pack manifest and every bookkeeping step (`pack.py --help`) |
| `tools/assetgen/cv.py` | CV tools: `views`, `grid`, `measure`, `observe`, `sample`, `compare`, `closeup` |
| `tools/assetgen/guard.py` | The hooks' logic |
| `tools/assetgen/templates/` | Canva prompt, builder brief, builder notes, critic brief |
| `tools/assetgen/downloads.py` | Cached, size-checked downloads (textures, HDRIs, thumbnails, Blendkit) |
| `tools/blender/assetgen/kit.py`, `README.md` | The builders' Blender kit and its contract |
| `tools/blender/assetgen/bake.py`, `checks.py` | The bake into glTF textures; the structure checks |
| `tools/blender/assetgen/blender-5.2-notes.md` | The Blender 5.2 names memory gets wrong, and what reaches Godot |
| `tools/blender/common/` | glTF export, scene and colour helpers |
| `tools/{blender,godot}/install_*.sh`, `tools/assetgen/install_cv.sh` | Pinned installers |
| `tools/godot/qa/check_pack_model.sh`, `capture_pack_models.gd` | The Godot check |
| `tests/tools/assetgen/` | Unit tests (run in CI) |

A run writes only to `design/asset-packs/<pack>/`, `tools/blender/assetgen/packs/<pack>/`,
`assets/models/<pack>/`, `production/qa/evidence/<pack>/` and `.scratch/`.

## Set up and test

```bash
bash tools/assetgen/install_cv.sh            # OpenCV and NumPy, pinned, into .scratch/pydeps
bash tools/blender/install_blender.sh        # Linux x64: Blender, add-ons, Instant Meshes, xatlas
bash tools/godot/install_godot.sh
python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
```

Then `/image-to-assets <image> [<pack name>] [skip canva]` in Claude Code (with the Canva connector
unless you skip Canva).

## Provenance and licences

- `blender-image-to-3d` is from majidmanzarpour/blender-game-skills and the `scenario-blender-*`
  skills from scenario-labs/skills, both MIT; each folder has its `LICENSE` and a `NOTICE.md`
  saying what was taken and changed. Builders took these up in nokepom's later pull requests too.
- The 16 kevinbadi blender-skills in `.claude/skills/` came with nokepom's pipeline (its PR 16).
  kevinbadi/blender-skills has no licence file, so nothing grants permission to redistribute them;
  decide whether to keep them.
- Textures and materials come from Poly Haven, ambientCG and cgbookcase (CC0) and Blendkit (free
  CC0 materials only), downloaded while building; Instant Meshes (BSD-3) and xatlas (MIT) are
  installed by `install_blender.sh`.
- This repository has no `LICENSE` of its own yet; nokepom's is MIT, © 2026 Donchitos, which may
  not be the holder you want here, so pick one deliberately.
