# asset-pipeline

Image in, assets out. Give Claude Code an image and run `/image-to-assets <image> [<pack name>]
[skip canva]`: you pick which objects in it become 3D models and in which art style, and you get
one Godot-ready `.glb` per object, reviewed by you, checked in Godot and delivered as one zip.

It began as the pipeline of [tessie1993/nokepom](https://github.com/tessie1993/nokepom) as it was
before prep agents were added (commit `4e138ba`, the first commit of nokepom PR 36) and was then
made fully generic: no example pack, no style written into the Canva prompt, no fixed sizes or
view angles, and the builder reads its reference directly.

## How it works

1. **You choose.** Claude lists the objects in the image; you say which to make, the art style,
   and optionally triangle budgets (otherwise each builder decides from the object's detail).
2. **Reference per object.** Canva draws each object from every side in your style, from your
   image (background removed, downloaded at full size). With `skip canva`, your own image(s) are
   the reference as they are.
3. **One builder agent per object, in parallel** (`asset-builder`). It reads the reference itself
   and sets up before it may build: CV tools find the object's views in the image (any layout, any
   size, a photo or a screenshot), it records each view's angle and the camera, measures the
   reference (proportions, colours, detail, symmetry, width : height : depth), picks the installed
   skills that fit, decides the budget, and writes an analysis with an inventory of every part
   down to the details and nuances.
4. **Build → CV compare → write-up, every cycle.** Each build exports the `.glb`, renders the
   recorded views in seconds and compares them with the reference automatically: outline overlap,
   proportions, the regions missing or extra, colours and brightness, detail density, with one
   compare image and close-up surveys. The next build waits until the builder has written down
   what the compare showed and what it fixes. A final build adds a turnaround.
5. **You review**, Godot imports each accepted model and screenshots it from the same views, and
   you get the zip. The pack's working files are removed from the repository unless you want them
   committed.

## Hooks: how the run is held together

| Hook | When | What it does |
|---|---|---|
| `assetgen-guard.sh pre` | before Bash, Write, Edit, Canva generate-image, during a run | Refuses changes outside the run pack's folders, git changes, a Blender build before the builder's set-up is complete or before the last build's CV compare is written up, a builder's build past its context budget (it hands off), and any Canva prompt that is not exactly `pack.py prompt` with the source image (no bias added) |
| `assetgen-guard.sh post` | after Bash, Write, Edit, during a run | Restores any pipeline file that changed anyway from the run-start snapshot, moves stray files to `.scratch/assetgen/quarantine/`, and after a build points the builder at its CV compare |
| `canva-remove-background.sh` | after Canva image generation | Asks for every generated image's background to be removed |
| `install-tools.sh` | session start (cloud) | Installs Blender 5.2.2, Godot 4.7.2 and the CV libraries in the background |

The guard logic is `tools/assetgen/guard.py`; during a run the hooks run its snapshot copy, so
editing the pipeline cannot switch them off. They do nothing outside a run.

## Tokens, context and speed

- **Builders keep their context small**: `pack.py kit-api` instead of reading the kit, compact CV
  lines, one compare image per build (sized to stay cheap to read), surveys only for views that
  differ, short reports.
- **Context budget per builder**: after 3 builds (`BUILDS_PER_BUILDER`, plus one final build) a
  builder writes a handoff in its notes and a fresh builder continues from the notes, so no context
  fills up with every earlier cycle's images and code.
- **The orchestrator stays lean**: builders fetch their own brief (a one-line spawn prompt), and
  `pack.py status` has a `next` column per object, so a run can resume after a compaction or in a
  new session from the files alone.
- **Fast builds**: cycle builds render only the recorded views at low samples (about 2 s a view),
  `--views N` renders one view, the turnaround only in the final build; builders run in parallel
  (one per two CPU cores); the CV compare runs inside the build.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/image-to-assets/SKILL.md` | The orchestrator's steps |
| `.claude/agents/asset-builder.md` | The builder agent |
| `.claude/hooks/`, `.claude/settings.json` | The hooks above |
| `.claude/skills/` (the other 16) | The blender-skills; builders pick the ones that fit |
| `tools/assetgen/pack.py` | The pack manifest and every bookkeeping step (`pack.py --help`) |
| `tools/assetgen/cv.py` | CV tools: `views`, `grid`, `measure`, `compare`, `closeup` |
| `tools/assetgen/guard.py` | The hooks' logic |
| `tools/assetgen/templates/` | Canva prompt, builder brief, builder notes |
| `tools/assetgen/downloads.py` | Cached, size-checked downloads (textures, HDRIs, thumbnails) |
| `tools/blender/assetgen/kit.py`, `README.md` | The builders' Blender kit and its contract |
| `tools/blender/common/` | glTF export, scene and colour helpers |
| `tools/{blender,godot}/install_*.sh`, `tools/assetgen/install_cv.sh` | Pinned installers |
| `tools/godot/qa/capture_pack_models.gd` | The Godot check |
| `tests/tools/assetgen/` | Unit tests (run in CI) |

A run writes only to `design/asset-packs/<pack>/`, `tools/blender/assetgen/packs/<pack>/`,
`assets/models/<pack>/`, `production/qa/evidence/<pack>/` and `.scratch/`.

## Set up and test

```bash
bash tools/assetgen/install_cv.sh            # OpenCV and NumPy, pinned, into .scratch/pydeps
bash tools/blender/install_blender.sh        # Linux x64
bash tools/godot/install_godot.sh
python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
```

Then `/image-to-assets <image> [<pack name>] [skip canva]` in Claude Code (with the Canva connector
unless you skip Canva).

## Provenance and licences

- The 16 blender-skills in `.claude/skills/` are from kevinbadi/blender-skills, as installed in
  nokepom by its PR 16. nokepom carries no licence notice for them, so none is added here.
- Textures come from Poly Haven and ambientCG (CC0), downloaded while building.
- This repository has no `LICENSE` of its own yet; nokepom's is MIT, © 2026 Donchitos, which may
  not be the holder you want here, so pick one deliberately.
