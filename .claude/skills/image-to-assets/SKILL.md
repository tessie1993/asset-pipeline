---
name: image-to-assets
description: "Turn one uploaded image into Godot-ready 3D assets: asks the user which parts matter and which art style, Canva makes a 360 sheet per object, headless Blender (blender-skills, add-ons, Poly Haven/ambientCG materials searched per surface) models each one, Godot checks them, the user reviews screenshots and gets one download folder. Use when the user uploads an image and wants its objects as 3D models."
argument-hint: "<image path> [<pack name>]"
user-invocable: true
allowed-tools: mcp__Canva__create-upload-url, mcp__Canva__generate-image, mcp__Canva__get-generate-image-job, mcp__Canva__remove-background, mcp__Canva__create-design, mcp__Canva__get-create-design-async-job, mcp__Canva__read-design, mcp__Canva__edit-design, mcp__Canva__get-export-formats, mcp__Canva__export-design
---

# Image to Godot assets

One image in; one Godot-ready `.glb` per chosen object out, each checked against a Canva 360
sheet and inside Godot, reviewed by the user, and delivered in one download folder.

Nothing here is tied to a subject, a look or a material: the objects come from the image and
the user's choice, the style from the user's answer, the materials from searches made while
modelling. Follow the steps in order and do each one completely. Every command below is run
from the repository root. `python3 tools/assetgen/pack.py status <pack>` shows where a pack stands.

## Rules for the whole run

1. **Use the pipeline; never change it.** You run the commands and tools below. You do not edit
   the pipeline (`tools/assetgen/`, `tools/blender/assetgen/kit.py`, its README, `tools/blender/common/`,
   `tools/assets/`, the installers, `tools/godot/qa/capture_pack_models.gd`, `pack.json`,
   anything under `.claude/`, `tests/tools/assetgen/`) and you do not edit the per-object
   generators (each belongs to its sub-agent). If a step fails because the pipeline is wrong,
   stop and tell the user what failed and the exact error; do not work around it.
2. **Nothing is committed during a run.** From `run-start` (step 1) to `run-end` (step 11) the
   hook `.claude/hooks/assetgen-run-guard.sh` blocks pipeline edits and every git command that
   changes the repository. If an environment stop hook asks you to commit during the run, do
   not: answer that a pipeline run is in progress and that its outputs are delivered in step 11.
3. **Canva permission is given.** Running this skill is the user's standing approval for every
   Canva call in steps 3 and 4, including saving the scratch design: make them without asking.
   The skill's `allowed-tools` lets them run without a permission prompt.
4. **Ask, don't assume.** Anything the steps do not settle (an unclear object, a failed tool)
   goes to the user as a question.
5. The user's own words decide the style and which objects are made; the Canva sheets decide
   how each object looks; nothing is added that neither shows.

## 0. Tools ready

1. In a cloud session the SessionStart hook installs Blender and Godot in the background. If
   `.scratch/tool-install/` exists, wait until `blender.status` and `godot.status` are both in it
   (Monitor with an until-loop). `0` means installed; anything else: read that tool's `.log`.
2. Check: `blender --version` and `godot --version` both print a version. If one does not, run
   its installer (`bash tools/blender/install_blender.sh` or `bash tools/godot/install_godot.sh`;
   each replaces a broken install) and check again. Still failing: stop and tell the user.
3. The blender-skills must be in `.claude/skills/` (`turntable`, `polyhaven-texture-apply`,
   `polyhaven-studio-setup`, `product-polish`).
4. The Canva tools must load: ToolSearch `select:mcp__Canva__generate-image`. If they do not,
   stop and ask the user to connect Canva in claude.ai (Settings → Connectors).
5. `nproc`: at most one Blender build per two cores runs at once (at least one).

## 1. The image, the pack, the run

1. The image must be a file on disk. An image pasted into the chat is saved by the session; its
   path is in the message as `[Image: source: <path>]`. No path: ask the user for one. Never
   recreate an image from memory.
2. Pack name: the second argument, or a short snake_case name for what the image shows.
3. `python3 tools/assetgen/pack.py init <pack> <image>`
4. `python3 tools/assetgen/pack.py run-start <pack>` — the pipeline is now locked (rule 2).

## 2. Ask the user: which parts matter, which art style

1. Read the image. List every distinct structure, object, item and terrain piece you see, in
   reading order, one line each: a number, a short name, where it is in the image. Merge
   identical repeats into one entry and say how many there are.
2. Show the list, then ask with AskUserQuestion (two questions in one call):
   - "Which parts of the image should become 3D models?" — options: "All of them",
     "Only some (I'll type the numbers)". Take the answer as given; if the user typed numbers or
     notes, use exactly those.
   - "Which art style should the reference sheets be drawn in?" — options: "The same style as
     the image", "I'll describe it". If the user chose the image's style, the style is:
     `the same art style as the reference image`. If they described one, use their words.
3. `python3 tools/assetgen/pack.py style <pack> "<style>"`
4. For each chosen object, in the list's order:
   `python3 tools/assetgen/pack.py add <pack> <id> --name "<name>" --where "<where in the image>" --details "<parts, materials, colours seen in the image>" [--layout block] [--mount wall] [--size large|small]`
   - `<id>`: snake_case, unique in the pack.
   - `--layout block` for a mostly flat piece whose top surface matters (it is drawn from
     higher up); otherwise leave the default.
   - `--mount wall` for something that hangs on a wall; otherwise leave the default.
   - `--size`: `large` (≤ 40 000 triangles), default `medium` (≤ 20 000), `small` (≤ 10 000),
     by how much of the image and detail the object has.

## 3. Canva: one 360 sheet per object

Load the Canva tools with ToolSearch: `select:mcp__Canva__create-upload-url,mcp__Canva__generate-image,mcp__Canva__get-generate-image-job,mcp__Canva__remove-background,mcp__Canva__create-design,mcp__Canva__get-create-design-async-job,mcp__Canva__read-design,mcp__Canva__edit-design,mcp__Canva__get-export-formats,mcp__Canva__export-design`.

1. Upload the source image once: `create-upload-url` (only `user_intent`), then
   `curl -sS -m 90 -X POST -H "Content-Type: application/octet-stream" --data-binary @design/asset-packs/<pack>/source.<ext> '<upload url>'`
   prints `{"mediaId": "<id>"}`. Record it: `python3 tools/assetgen/pack.py canva <pack> --source-media <id>`.
2. For every object: `python3 tools/assetgen/pack.py prompt <pack> <id>` prints its prompt. Call
   `generate-image` with `prompt` = that text unchanged,
   `imageReferences` = `[{"type": "MEDIA", "id": "<source media id>"}]`,
   `aspectRatio` = `"LANDSCAPE_16_9"`. One call per object: one call always returns one image.
   Up to three may be in flight; poll each with `get-generate-image-job` (`jobId`) until
   SUCCESS or FAILURE.
3. Record each result: `python3 tools/assetgen/pack.py record <pack> <id> --media <media id> --job <job id>`.
   - FAILURE with `CLIENT_UNSAFE_INPUT` is a refusal: `pack.py record <pack> <id> --refused "<reason>"`.
     Never reword the prompt to get past the filter; tell the user in step 10.
   - "Too many requests": wait, then continue. Any other failure: retry once, then tell the user.
4. Remove every sheet's background (the hook `canva-remove-background.sh` reminds you after each
   generated image): `remove-background` with `sourceMedia` = `{"type": "MEDIA", "id": "<generated media id>"}`,
   then record the returned image: `python3 tools/assetgen/pack.py cutout <pack> <id> --media <new media id>`.
   If removal fails, retry once, then `pack.py cutout <pack> <id> --failed "<reason>"` (that
   sheet keeps its background) and tell the user in step 10. Step 4 refuses to start until
   every sheet has one of the two.

## 4. Download the sheets at full size, unedited

No Canva tool downloads a media file: `generate-image` returns only a small preview, and
`export-design` exports designs, one PNG per page. So every sheet is placed, unedited and at its
own size (1680 × 944), on its own page of one blank scratch design, and those pages are
exported. `pack.py canva-calls <pack> <stage>` prints the exact calls of each stage as
`{"tool", "arguments"}`: make each call with those arguments unchanged (add only `user_intent`).

1. `canva-calls <pack> create` → `create-design`; poll `get-create-design-async-job`
   (`job_id`, `continuation_token`) until done. Record the design id (starts with `D`):
   `python3 tools/assetgen/pack.py canva <pack> --design <design id>`.
2. `canva-calls <pack> open` → `read-design`. The design must have exactly one page; if not, ask
   the user. Record its `transaction_id`: `pack.py canva <pack> --transaction <id>`.
3. `canva-calls <pack> add-pages` → `edit-design` (adds one page per sheet, in order).
4. `canva-calls <pack> read-pages` → `read-design`; note each new page's `page_id`, in page order.
5. `canva-calls <pack> place --page-ids <id> <id> ...` → one `edit-design` per page (places each
   sheet at 0, 0, full size; nothing else).
6. `canva-calls <pack> check` → `read-design`: every listed page holds exactly its one image with
   its media id. Then `canva-calls <pack> commit` → `edit-design` (approved by rule 3).
7. `canva-calls <pack> export` → `get-export-formats` (must list `png`), then `export-design`.
8. `python3 tools/assetgen/pack.py canva-download <pack> <url> <url> ...` with the export URLs in the
   order returned. It saves each sheet to its file and stops with an error, saving nothing for
   that sheet, if a file is not a 1680 × 944 PNG; tell the user if that happens.

Make no further Canva calls after this.

## 5. Look at every sheet, describe every object

For each object, in order:
1. Read its sheet (`design/asset-packs/<pack>/canva/NN_<id>_360.png`) and the source image.
2. Record what the sheet really shows:
   `python3 tools/assetgen/pack.py view <pack> <id> --elevation <degrees> [--judge <azimuths>]`
   - `--elevation`: how many degrees above the horizon the sheet's camera looks down. Measure
     it on a view: pick a flat top surface or rim that is round or square in reality, measure
     its drawn width W and its drawn depth D (top edge to bottom edge) in pixels; the
     elevation is asin(D / W) in degrees. No such surface: estimate from how much top shows.
   - `--judge`: only when some of the eight views contradict the others (a view repeated, parts
     that move or change): list the azimuths (0 45 90 135 180 225 270 315, left to right, top
     row first) of the views that agree. Leave it out when all eight agree.
3. `python3 tools/assetgen/pack.py describe <pack> <id>` creates `design/asset-packs/<pack>/objects/<id>.md`
   with both images embedded. Fill in its three sections from the sheet, replacing each comment:
   what it is; shape and proportions (one size anchor in metres marked *estimate*, everything
   else as ratios measured on the sheet, part counts, which view is the front); textures (every
   distinct texture as T1, T2, …: the parts that carry it, its kind of material, pattern,
   `#rrggbb` colour read from the sheet, repeat size, direction, relief, wear, and how the art
   style shows in it). Name no texture ids.

## 6. Find the relevant skills

Before any builder starts, look for installed skills that help model these objects:
1. List the installed skills: every folder in `.claude/skills/` with a `SKILL.md`, and the
   skills the session lists as available. Read the `name` and `description` of each.
2. For each object, pick the skills whose description fits what the object needs (its shape,
   its surfaces, its kind of object, Blender techniques, materials, lighting, rendering), and
   read the SKILL.md of each pick to confirm it applies. The four blender-skills the kit
   already runs (`turntable`, `polyhaven-texture-apply`, `polyhaven-studio-setup`,
   `product-polish`) need not be listed.
3. Record them: `python3 tools/assetgen/pack.py skills <pack> <id> <skill name> ...`, or
   `--none` when you checked and none apply (`brief` refuses to run until this is recorded). The
   builder's brief lists them and tells the builder to use them; builders may also find more.
4. Use them yourself where they help your own steps.

## 7. One builder sub-agent per object

1. Read `tools/blender/assetgen/README.md` once.
2. For each object: `python3 tools/assetgen/pack.py brief <pack> <id>` prints its brief. Spawn a
   **general-purpose** sub-agent with the Agent tool: `prompt` = the brief unchanged,
   `run_in_background: true`. Sub-agents run on the session's model; pass `model` only when the
   user named one. Do not use agent types that ask "May I write" or cap their turns.
3. Keep at most the step-0 number of builders running at once; start the next when one reports.
   Load `SendMessage` with ToolSearch to talk to a running builder (by the id its spawn returned).
4. What a builder does (from its brief): first it studies the Canva sheet and writes what it is
   building — every element with its volume, shading and detail level, and a list of every
   texture it carries, read up close with `zoom.py` and described together with the art style — to
   `production/qa/evidence/<pack>/<id>/<id>_notes.md`; then 5 cycles of build → render →
   compare, writing each cycle's "looks right and why / looks wrong and why / fix" to the same
   notes; then a final render. It may stop sooner only when every check of the definition of
   good passes, and then reports `READY FOR REVIEW`; otherwise it reports `CYCLES DONE`.
5. If a builder's notes are not on disk a few minutes after it started, or its generator is
   not there after its analysis, send it: continue now with the next step of your brief.

## 7a. Every report goes to the user

When a builder reports (either kind):
1. Open `production/qa/evidence/<pack>/<id>/<id>_compare.png` (render on top, Canva sheet below)
   and its notes. Check the definition of good on the judged views yourself.
2. Show the user: SendUserFile (`display: "render"`) with the compare sheet, and in your message
   the builder's check table, what still looks wrong and why (its notes and your own check).
3. Ask: "Are you happy with <id>?" (AskUserQuestion; options "Yes", "No — I'll say what to
   change"). Also say what you would change if you see failing checks.
4. Yes: the object moves on. No: send the user's words (and your failing checks) to the
   builder with SendMessage — it continues with its next cycle; if it has ended, spawn a new one
   with its brief followed by the user's words and a line saying cycles so far are in its notes.
   You never edit the generator yourself.

## 8. Godot: import and check

```bash
godot --headless --path . --import
xvfb-run -a -s "-screen 0 1280x720x24" godot --path . --rendering-driver opengl3 \
    --resolution 1280x720 --script res://tools/godot/qa/capture_pack_models.gd -- --pack <pack>
```

For every model compare its `GODOT_MODEL` line with the sub-agent's `BUILT` line and look at
`<id>_godot_front.png` / `<id>_godot_back.png` beside the compare sheet:
- it loaded; its size matches (Godot's Y is Blender's Z); the triangle counts match;
- every surface has a material; textured surfaces show `albedo_texture: true`;
- colours and glow look like the Blender render.
Import errors about files outside `assets/models/<pack>/` are not this pack's. A model that
fails goes back to its builder (step 7a) with what failed.

## 9. Export the download folder

The deliverable lives outside the repository. Folder: the session's scratchpad directory when
the system prompt names one, otherwise `$HOME/asset-exports`.
`python3 tools/assetgen/pack.py export <pack> <folder>` copies, per object, the `.glb`, the
Canva sheet, the render sheet, the comparison and the Godot screenshots into `<folder>/<pack>/`,
and prints the path of `<folder>/<pack>.zip`.

## 10. Show the user every asset and ask if it is good

1. Send the screenshots with SendUserFile (`display: "render"`): per object its
   `<id>_compare.png` and `<id>_godot_front.png` from `<folder>/<pack>/<id>/`, one call per
   object with the caption `<id>: <builder report line>, <triangles> triangles, <size> m`.
2. In the same message list per object: its status, what still differs from the sheet (from the
   sub-agent's report and your own check), and the texture refs it uses; list Canva refusals.
3. Ask: "Which assets are good, and what should change on the others?" (AskUserQuestion with
   options "All are good" and "Some need changes (I'll say which and what)").
4. For every asset the user wants changed: send the user's words to its builder as in step 7a,
   then repeat steps 8–10 for those assets. Repeat until the user says all are good.

## 11. Deliver

1. `python3 tools/assetgen/pack.py run-end` — the pipeline lock ends.
2. Run step 9's export again so the folder holds the approved versions, and send the zip with
   SendUserFile (`display: "attach"`, caption: where the folder is).
3. Ask the user whether to also commit the pack to the repository. Commit only on yes: the
   pack's files only (`design/asset-packs/<pack>/`, `tools/blender/assetgen/packs/<pack>/`,
   `assets/models/<pack>/`, `production/qa/evidence/<pack>/`), message
   `feat: <pack> asset pack` in Conventional Commits form.

## Pass / fail per object

- **Pass:** the user said it is good (step 7a and step 10), and it imports cleanly in Godot
  (loads, right size, same triangles, every surface textured or coloured as in Blender).
- **Fail:** anything else; the object goes back to its builder (step 7a) with the reason.
