# asset-pipeline

The `/image-to-assets` pipeline from [tessie1993/nokepom](https://github.com/tessie1993/nokepom),
complete and exactly as it was just before prep agents were added: commit
`4e138ba11c35d2d43e1b1a05877b514949ff95e4` (30 Sep 2026, 19:30), "builders read every texture
from the sheet, not only colour". That is the first of the two commits in
[nokepom PR 36](https://github.com/tessie1993/nokepom/pull/36). Nothing later is in it: no prep
agents (PR 36's second commit) and none of PRs 37–46 (critic, skip canva, outline overlays and
survey, asset agents, OpenCV measuring and the rest).

One image goes in; one Godot-ready `.glb` per chosen object comes out. The whole flow is
`.claude/skills/image-to-assets/SKILL.md`:

1. You pick which objects in the image to model and the art style.
2. Canva draws a 360° sheet per object; the backgrounds are removed and the sheets downloaded at full size.
3. The session itself looks at each sheet and writes the object's description (`pack.py describe`),
   then records the installed skills that help each object (`pack.py skills`).
4. One general-purpose builder sub-agent per object studies its sheet (close-ups with `zoom.py`,
   every texture listed), then runs 5 build → render → compare cycles in headless Blender.
5. You review every build; Godot imports and screenshots each model; you get one download folder.

## Layout

Paths are the same as in nokepom, because the skill, hooks, briefs and READMEs refer to each other by path.

| Path | What it is |
|---|---|
| `.claude/skills/image-to-assets/` | The skill: the steps the session follows |
| `.claude/hooks/assetgen-run-guard.sh` | Locks the pipeline and git while a run is in progress |
| `.claude/hooks/canva-remove-background.sh` | Reminds Claude to remove the background of every generated Canva image |
| `.claude/hooks/install-tools.sh` | SessionStart: installs Blender and Godot in the background (Linux cloud sessions) |
| `.claude/settings.json` | Wires those three hooks |
| `.claude/skills/` (the other 16) | The blender-skills: `turntable`, `polyhaven-texture-apply`, `polyhaven-studio-setup` and `product-polish` run inside the kit; step 6 picks among the rest |
| `tools/assetgen/` | `pack.py` (manifest, prompts, Canva calls, briefs, status, export) and `templates/` |
| `tools/blender/assetgen/` | `kit.py` (the builders' API), `zoom.py` (sheet and render close-ups), the README, `packs/` (per-object generators) |
| `tools/blender/common/` | Shared Blender helpers; `kit.py` uses `cli`, `export`, `scene`, `palette`, `paths` |
| `tools/assets/` | `fetch_cc0_assets.py` (Poly Haven / ambientCG download and cache, used by `kit.py`) and nokepom's other asset scripts |
| `tools/{blender,godot}/install_*.sh` | Pinned Blender 5.2.2 and Godot 4.7.2 installers |
| `tools/godot/qa/capture_pack_models.gd` | Loads each model in Godot and screenshots it |
| `tests/tools/assetgen/` | Unit tests for `pack.py`; `.github/workflows/tests.yml` runs them |

### The example pack: `cottage_interior`

The pack as it stood at that commit: 17 objects with Canva sheets and descriptions, of which
`rug`, `crate`, `basket` and `bucket` are built.

| Path | What it is |
|---|---|
| `design/asset-packs/cottage_interior/` | `pack.json`, `source.jpg`, the 17 Canva sheets, the object descriptions |
| `tools/blender/assetgen/packs/cottage_interior/` | The four generators |
| `assets/models/cottage_interior/` | The four `.glb` models, their textures and Godot `.import` files |
| `production/qa/evidence/cottage_interior/` | Renders, render sheets, compare sheets, Godot screenshots |

`python3 tools/assetgen/pack.py status cottage_interior` shows where it stands.

## Use

```bash
bash tools/blender/install_blender.sh        # Linux x64; the SessionStart hook does both in cloud sessions
bash tools/godot/install_godot.sh
python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
```

Then, in Claude Code with the Canva connector, `/image-to-assets <image> [<pack name>]`.
Packs land in `design/asset-packs/<pack>/`, models in `assets/models/<pack>/`, evidence in
`production/qa/evidence/<pack>/`.

## Hooks and skill

These rows are copied from nokepom's `.claude/docs/hooks-reference.md` and `skills-reference.md` at that commit.

| Hook | Event | Trigger | Action |
| ---- | ----- | ------- | ------ |
| `install-tools.sh` | SessionStart | Session begins (Linux cloud sessions only) | Starts the Blender and Godot installers in the background, logging to `.scratch/tool-install/`; returns at once. Each installer writes its exit code to `.scratch/tool-install/<tool>.status` when it finishes |
| `assetgen-run-guard.sh` | PreToolUse (Bash/Write/Edit) | An `/image-to-assets` run is in progress (`.scratch/assetgen/run.json` exists) | Blocks edits to pipeline files and git commands that change the repository until `pack.py run-end`; the run's outputs and per-object generators stay writable |
| `canva-remove-background.sh` | PostToolUse (Canva image generation) | A Canva image-generation result names a new media id | Tells Claude to run Canva's `remove-background` on it and use the cutout; `pack.py sheets` refuses sheets without a recorded cutout |

| Command | Purpose |
|---------|---------|
| `/image-to-assets` | Turn one image into Godot-ready 3D models — asks which parts matter and which art style, a Canva 360 sheet per object, one headless-Blender sub-agent per object with materials searched per surface, Godot check, screenshot review, one download folder |

## What differs from nokepom at that commit

Every file that came from nokepom is byte-identical to commit `4e138ba`. Written for this repo:

- `.claude/settings.json`: nokepom's hook wiring cut down to the pipeline's three entries (same
  matchers and timeouts). nokepom's other hooks, permissions and status line are the game project's.
- `.github/workflows/tests.yml`: nokepom's workflow with only its `asset-pipeline` job (verbatim)
  and read-only permissions; the other jobs test the game and the creature pipeline.
- `project.godot`: a minimal project so `godot --path . --import` and the capture script work.
  nokepom's own is the game's; this keeps its engine version and renderer settings.
- `.gitignore` and this README.

Left out, because they are the game, not the pipeline:

- The game itself: `src/`, `addons/`, the other `assets/`, `design/levels/` (including the older
  `design/levels/cottage_interior`), the other Blender generators (`tools/blender/{cottage,forest,…}`),
  the rest of `tools/godot/` and `tests/`.
- The rest of nokepom's `.claude/` (its other agents, skills, hooks, docs and rules) and `CLAUDE.md`.
  Step 6 of the skill picks from every installed skill; in nokepom that also included the game
  studio's own skills, here it is the blender-skills.

Some included files were written for the game's levels: `tools/assets/forest_*` and
`stage_meadow_textures.py` read forest and meadow data, and `tools/blender/common/layout.py`,
`validate.py` and `palette.material()` read Sky Village data, none of which is here;
`measure_palette.py` is a general palette tool that was used for the forest. They are kept because
the pipeline's run guard counts all of `tools/assets/` and `tools/blender/common/` as pipeline
files. The pipeline itself does not use them.

## Not verified here

- `kit.py` and `zoom.py` have not been run under Blender in this repo. Their imports resolve to files here and they compile.
- The hooks were pipe-tested and the 26 unit tests pass here.

## Provenance and licences

- The 16 blender-skills in `.claude/skills/` are from kevinbadi/blender-skills, installed in nokepom by its PR 16.
  nokepom carries no licence notice for them, so none is added here.
- The example pack's textures come from Poly Haven and ambientCG (CC0).
- This repo has no `LICENSE` of its own yet. nokepom's is MIT, © 2026 Donchitos, which may not be the holder you want here, so pick one deliberately.
