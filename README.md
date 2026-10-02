# asset-pipeline

Image in, assets out. Give Claude Code an image and run `/image-to-assets <image> [<pack name>]
[skip flow]`: you pick which objects in it become 3D models and in which art style, and you get
one detailed, Godot-ready `.glb` per object (mid to high poly, every detail modelled, real
materials and shaders baked into textures), built one render cycle at a time by builders that
compare their own work with the reference, reviewed by you, checked in Godot and delivered as one
zip.

It began as the pipeline of [tessie1993/nokepom](https://github.com/tessie1993/nokepom) as it was
before prep agents were added (commit `4e138ba`, the first commit of nokepom PR 36) and was then
made fully generic: no example pack, no style written into the reference prompts, no fixed sizes or
view angles, and the builder reads its reference directly. It also carries the skills and tools of
nokepom's later pull requests (the `blender-image-to-3d` skill, the Blender 5.2 notes, the Godot
check script, `kit.mark`, cgbookcase textures), without their prep agents. (A separate fresh-context
reviewing agent it once had was replaced by builders that review their own builds every cycle.)

## How it works

1. **You choose.** Claude lists the objects in the image; you say which to make, the art style,
   and optionally triangle budgets (otherwise each builder decides from the object's detail, mid to
   high poly).
2. **Reference per object.** Google Flow's Grid Architect draws each object from every side in
   your style, from your image: the pipeline sets it up (your image uploaded, the exact prompts, one
   shot per side), you look at the set-up and click Generate in Flow yourself (it uses your Flow
   credits) and give the downloaded images back. With `skip flow`, your own image(s) are the
   reference as they are.
3. **Builders per object, in parallel, one render cycle each** (`asset-builder`, the strongest
   model at high effort). Before the first build, the first builder records every view in every
   reference image, measures them, looks at them magnified (`cv.py observe`, `closeup`, `sample`:
   details, imperfections, colour and material variation), reads the Blender skills that fit and
   writes an analysis: every part, every surface's material and its variation, every detail and
   nuance.
4. **Build → compare → review → Handoff, every cycle.** Each builder does one render cycle: the
   next step, one full build (structure checks, every recorded view rendered lit and in clay, the
   CV compare with the reference), then its own comparison part by part and view by view, and its
   review in its notes: what matches, what differs (measured) and why, and a ranked list of what
   needs improving. That list becomes the next step of the **Handoff** it writes for the next
   builder, who gets only the Handoff, the reference views and the latest compare
   (`pack.py brief`). The builders are their own reviewers: a builder ends with `DONE` when its
   review finds nothing worth improving (or the standard 8 cycles are used up).
5. **Lead and part builders.** The builder that reads a Handoff leads the cycle: it splits the
   generator into part modules, makes a test harness, writes one job card per independent part task
   and runs 2 to 4 part builders (`asset-part-builder`) at once, each doing exactly one job and
   reporting; it judges every part against the reference itself, integrates and makes the cycle's
   one full build. Builders run Blender in the background and keep the CPU cores busy. Guides for
   both are in `.claude/skills/image-to-assets/references/`.
6. **Baked for Godot.** The final build bakes every shader into one material (base colour, ORM,
   normal, emission) on one UV atlas, so what renders in Blender is what Godot shows. No flat
   colours, and the reference image is never projected onto a model. Models are mid to high poly:
   sculpted signed-distance clay, quad remeshing, subdivision, bevels, booleans, geometry nodes;
   real materials from Poly Haven, ambientCG, cgbookcase and Blendkit plus procedural, layered
   shaders with masks.
7. **You review**, Godot imports each accepted model and screenshots it from the same views, and
   you get the zip: per object the `.glb`, its baked textures and its renders.
8. **Nothing of the run is left to steer the next one.** `pack.py finish` keeps the models, textures
   and renders and deletes the rest: the builders' notes with their reviews and Handoffs and every
   other .md, the generators with their part modules and helper scripts, the job cards and test
   harnesses, the CV images and the build logs. You choose whether the outputs stay in the
   repository.
9. **Optionally, one cloud machine per object**: each runs its own builders on its own branch and
   pushes after every Handoff; your session merges and runs your review (see the skill).

## Hooks: how the run is held together

| Hook | When | What it does |
|---|---|---|
| `assetgen-guard.sh pre` | before Bash, Write, Edit and the Google Flow tools, during a run | Refuses changes outside the run pack's folders, git changes, a Blender build before the builder's set-up is complete or before the last build's CV compare and the builder's review are in its notes, a second cycle build by the same builder (one render cycle per builder: it hands off), a part builder writing anything but its job card's files or running Blender on anything but the lead's test harness, any Flow set-up that is not exactly `pack.py flow-call` (no bias added; your image the only reference), and Flow generating on its own (only your click spends credits) |
| `assetgen-guard.sh post` | after Bash, Write, Edit, during a run | Restores any pipeline file that changed anyway from the run-start snapshot, moves stray files to `.scratch/assetgen/quarantine/`, and after a build points the builder at its CV compare and review |
| `builder-tools-context.sh` | when an `asset-builder` or `asset-part-builder` starts | Hands it the guides and the Blender tools table (which tool or add-on for which job), and the method: understand, observe, compare, review, multitask; logs to `.scratch/assetgen/hooks.log` |
| `builder-tools-hint.sh` | after Bash | When a Blender run fails because an operator needs the UI or an add-on is not enabled, points at the headless alternative in the tools guide |
| `install-tools.sh` | session start (cloud) | Installs Blender 5.2.2 with its add-ons, Instant Meshes and xatlas, Godot 4.7.2, the CV libraries and ImageSorcery in the background, then the BlendKit add-on into Blender |

The guard logic is `tools/assetgen/guard.py`; during a run the hooks run its snapshot copy, so
editing the pipeline cannot switch them off. They do nothing outside a run.

## Quality first, then context and speed

- **Quality**: lead builders run on the strongest model at high effort, part builders on a fast
  model, each with one clear job; 8 build cycles per object by default; every cycle's build renders
  every view at 768 px (1280 px final) in lit and clay, never reduced; every builder reviews its own
  build part by part and explains each difference before it fixes it.
- **Context**: one render cycle per builder (`BUILDS_PER_BUILDER`, plus the final build); its
  Handoff is all the next builder reads, so no context fills up with earlier cycles; builders fetch
  their own brief (a one-line spawn prompt) and `pack.py status` has a `next` column per object, so
  a run resumes after a compaction or in a new session.
- **Speed**: part builders work on independent parts at the same time, with a harness that
  rebuilds and renders one part; Blender runs in the background while the builders keep working,
  with the load kept near the number of cores; the bake and the turnaround only in the final build;
  objects build in parallel (one per two CPU cores); downloads are cached and shared.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/image-to-assets/SKILL.md` | The orchestrator's steps |
| `.claude/skills/image-to-assets/references/` | The builders' guides: `builder_guide.md` (understand, observe, compare, review, Handoff, lead and part builders), `part_builder_guide.md`, `blender_tools_guide.md` |
| `.claude/agents/asset-builder.md`, `asset-part-builder.md` | The (lead) builder and the part builder |
| `.claude/hooks/`, `.claude/settings.json` | The hooks above |
| `.claude/skills/blender-image-to-3d/`, `.claude/skills/scenario-blender-*/` | The Blender skills builders use (method, sculpting, hard surface, texturing, UVs and baking, retopology, geometry nodes, hair, expert notes) |
| `.claude/skills/` (the other 16) | Skills from nokepom's pipeline (camera videos, product shots, Meshy AI image-to-3D, Blender GUI tools): `disable-model-invocation: true`, so they run only when you call them, and builders never see them |
| `plugins/imagesorcery/` | ImageSorcery MCP, installed apart in its own `.venv` (git-ignored) and registered as `imagesorcery`: image tools (crop, resize, find, detect, ocr) builders may call on copies of the reference views |
| `plugins/blendkit/` | The BlendKit add-on (`install.sh`, into the headless Blender's `user_default` extensions); `login.py`, which logs it in to your BlendKit account (you log in on blendkit.com in your own browser and paste back the address it ends on); `headless.py`, which a `blender -b` script uses to enable it with that login and search, download (as your account, through its BlendKit-Client) and append materials and models. Tokens, downloads and the client stay in `.data/` (git-ignored) |
| `tools/assetgen/pack.py` | The pack manifest and every bookkeeping step (`pack.py --help`) |
| `tools/assetgen/cv.py` | CV tools: `views`, `grid`, `measure`, `observe`, `sample`, `compare`, `closeup` |
| `tools/assetgen/guard.py` | The hooks' logic |
| `tools/assetgen/templates/` | Flow theme and shot prompts, the first-cycle builder brief, the Handoff brief, builder notes (review and Handoff format), the part builders' job card |
| `tools/flow/install_flow_mcp.sh` | Installs the Google Flow MCP server (pinned) and registers it as `google-flow` |
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
bash plugins/imagesorcery/install.sh         # ImageSorcery MCP in plugins/imagesorcery/.venv, registered
bash plugins/blendkit/install.sh             # BlendKit add-on in Blender (after install_blender.sh)
python3 plugins/blendkit/login.py start      # optional: log BlendKit in to your account
python3 -m unittest discover -s tests/tools/assetgen -p "*_test.py"
```

Then `/image-to-assets <image> [<pack name>] [skip flow]` in Claude Code. Unless you skip Flow, the
Google Flow MCP server must be installed on a computer whose Google Chrome is signed in to your
Google account: `bash tools/flow/install_flow_mcp.sh`, then set your account and Chrome profile in
its `config/flow.config.json` and start a new Claude Code session.

## Provenance and licences

- `blender-image-to-3d` is from majidmanzarpour/blender-game-skills and the `scenario-blender-*`
  skills from scenario-labs/skills, both MIT; each folder has its `LICENSE` and a `NOTICE.md`
  saying what was taken and changed. Builders took these up in nokepom's later pull requests too.
- The 16 kevinbadi blender-skills in `.claude/skills/` came with nokepom's pipeline (its PR 16).
  kevinbadi/blender-skills has no licence file, so nothing grants permission to redistribute them;
  decide whether to keep them.
- The Google Flow MCP server is TMSSS05/google-flow-browser-mcp (commit `0c8e80a`), installed
  outside this repository. Its README says MIT but the repository has no licence file. It drives
  your signed-in Chrome profile (it copies the profile's cookies to a temporary folder) with flags
  that hide the automation from Google, which Google's terms may not allow; the pipeline uses only
  its Grid Architect set-up, never its automatic generation. Its image tool's `reference_images`
  option is not implemented (it uploads nothing), which is why Grid Architect is used.
- ImageSorcery MCP is sunriseapps/imagesorcery-mcp 0.12.0 (MIT) from PyPI, with Ultralytics
  YOLOE models (AGPL-3.0) and MobileCLIP; telemetry is switched off. Its detectors were trained
  mostly on photographs: on drawn references they miss and misname things, so the pipeline never
  feeds their output into a build on its own.
- The BlendKit add-on is BlenderKit/Blendkit 3.21.2 (GPL-2.0-or-later), the release
  blendkit.com/get-blendkit serves, with its BlendKit-Client binary. `login.py` repeats the add-on's own
  OAuth login (same client id, PKCE and token requests) because the headless Blender has no browser.
- Textures and materials come from Poly Haven, ambientCG and cgbookcase (CC0) and Blendkit (free
  CC0 materials only), downloaded while building; Instant Meshes (BSD-3) and xatlas (MIT) are
  installed by `install_blender.sh`.
- This repository has no `LICENSE` of its own yet; nokepom's is MIT, © 2026 Donchitos, which may
  not be the holder you want here, so pick one deliberately.
