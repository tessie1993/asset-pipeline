---
name: image-to-assets
description: "Turn an image into Godot-ready 3D assets: asks which objects to make and in which art style; Canva draws each object from every side (or, with `skip canva`, the user's own images are used as they are); one builder agent per object analyses its reference with CV tools, builds it in headless Blender and checks every build against the reference; the user reviews, Godot checks, and the user gets one download. Use when the user gives an image and wants its objects as 3D models."
argument-hint: "<image path> [<pack name>] [skip canva]"
user-invocable: true
allowed-tools: mcp__Canva__create-upload-url, mcp__Canva__generate-image, mcp__Canva__get-generate-image-job, mcp__Canva__remove-background, mcp__Canva__create-design, mcp__Canva__get-create-design-async-job, mcp__Canva__read-design, mcp__Canva__edit-design, mcp__Canva__get-export-formats, mcp__Canva__export-design
---

# Image to Godot assets

Image in, assets out: one Godot-ready `.glb` per chosen object, each built by its own builder agent
from its reference image and checked against it, reviewed by the user, checked in Godot and
delivered in one download folder.

Nothing is fixed in advance: the objects and the look come from the image and the user's answers;
each builder finds its object's views, angles, size and triangle budget in its own reference. Run
every command from the repository root. `python3 tools/assetgen/pack.py status <pack>` shows where
each object stands and, in its `next` column, what to do next: after a context compaction or in a
new session, that is all you need to carry on.

## Rules

1. **Use the pipeline; never change it.** From step 1 to step 8 hooks lock it: only the pack's own
   folders change, git is locked, Blender builds wait for the builder's set-up and CV checks, and
   Canva gets only the exact prompts. If a step fails because the pipeline is wrong, stop and tell
   the user the exact error.
2. **Nothing is committed during a run.** If a stop hook asks you to commit, answer that a pipeline
   run is in progress and its outputs are delivered at the end.
3. **Canva permission is given**: running this skill approves every Canva call in step 3.
4. **Ask, don't assume**: whatever the steps do not settle goes to the user.
5. **Keep your context small; the run can be long.** Never open the builders' notes or images
   yourself unless the user asks why; rely on their short final messages and `pack.py status`.
   SendUserFile shows the user an image without loading it into your context. Pipe long output
   through grep or tail.
6. **No bias.** The look comes only from the user's words. Object names, places and details say
   what the object is and its parts, materials and colours (`pack.py add` refuses look words), and
   the Canva prompt is sent exactly as `pack.py prompt` prints it.

## 0. Tools ready

1. In a cloud session the SessionStart hook installs Blender, Godot and the CV libraries in the
   background. If `.scratch/tool-install/` exists, wait until `blender.status`, `godot.status`
   and `cv.status` are all in it (Monitor with an until-loop): `0` means installed; anything else,
   read that tool's `.log`.
2. `blender --version`, `godot --version` and `python3 tools/assetgen/cv.py --help` must work;
   otherwise run `bash tools/blender/install_blender.sh`, `bash tools/godot/install_godot.sh` or
   `bash tools/assetgen/install_cv.sh` and check again. Still failing: stop and tell the user.
3. The Agent tool must list the `asset-builder` type; if it does not, stop and tell the user.
4. Unless the run skips Canva: ToolSearch `select:mcp__Canva__generate-image` must load; if not,
   ask the user to connect Canva in claude.ai (Settings → Connectors).
5. Build slots: `nproc` divided by 2 (at least 1) builders run at once.

## 1. The image, the pack, the run

1. The image must be a file on disk; a pasted image's path is in the message as
   `[Image: source: <path>]`. No path: ask. Never recreate an image from memory. With `skip canva`
   the user may give several images (.png, .jpg, .jpeg, .webp), each a file on disk.
2. Pack name: the second argument, or a short snake_case name for what the image shows.
3. `python3 tools/assetgen/pack.py init <pack> <image>`, with `--skip-canva` when the user said
   `skip canva`.
4. `python3 tools/assetgen/pack.py run-start <pack>`: the run starts; the hooks snapshot and lock
   the pipeline.

## 2. Ask the user

1. Read the image (every image with `skip canva`). List every distinct object, structure, item and
   terrain piece in reading order, one line each: a number, a short name, where it is. Merge
   identical repeats and say how many. With `skip canva`, an image of one object seen from one or
   more sides is one entry.
2. AskUserQuestion, all in one call:
   - "Which of these should become 3D models?" — "All of them", "Only some (I'll type the numbers)".
   - Unless `skip canva`: "Which art style should Canva draw them in?" — "The same style as the
     image", "I'll describe it".
   - "Triangle budgets?" — "Each builder decides from the object's detail (Recommended)",
     "I'll give numbers".
3. `python3 tools/assetgen/pack.py style <pack> "<style>"`: the user's words, or
   `the same art style as the reference image`.
4. Per chosen object: `python3 tools/assetgen/pack.py add <pack> <id> --name "<name>" --where
   "<where in the image>" --details "<its parts, materials and colours>" [--mount wall]
   [--budget <triangles>]`; with `skip canva` add `--reference <image(s) that show it>` (the
   source image itself when the object is in it).

## 3. Canva: each object from every side (not with `skip canva`)

Load the tools with ToolSearch: `select:mcp__Canva__create-upload-url,mcp__Canva__generate-image,mcp__Canva__get-generate-image-job,mcp__Canva__remove-background,mcp__Canva__create-design,mcp__Canva__get-create-design-async-job,mcp__Canva__read-design,mcp__Canva__edit-design,mcp__Canva__get-export-formats,mcp__Canva__export-design`.

1. Upload the source image once: `create-upload-url` (only `user_intent`), then
   `curl -sS -m 90 -X POST -H "Content-Type: application/octet-stream" --data-binary @design/asset-packs/<pack>/source.<ext> '<upload url>'`
   prints `{"mediaId": "<id>"}`; record it: `pack.py canva <pack> --source-media <id>`.
2. Per object, `pack.py prompt <pack> <id>` prints its prompt; call `generate-image` with `prompt`
   = that text unchanged, `imageReferences` = `[{"type": "MEDIA", "id": "<source media id>"}]` and
   `aspectRatio` = `"LANDSCAPE_16_9"` (a hook refuses anything else). Keep up to three in flight
   and poll each with `get-generate-image-job`.
3. On SUCCESS: `pack.py record <pack> <id> --media <media id> --job <job id>`, then
   `remove-background` on that media (the hook reminds you) and
   `pack.py cutout <pack> <id> --media <new id>` (after one failed retry: `--failed "<reason>"`).
   FAILURE with `CLIENT_UNSAFE_INPUT`: `pack.py record <pack> <id> --refused "<reason>"`; never
   reword the prompt to get past it; tell the user in step 7. "Too many requests": wait, then go
   on. Any other failure: retry once, then tell the user.
4. Download the images at full size. `pack.py canva-calls <pack> <stage>` prints the exact calls of
   a stage; make them with those arguments unchanged (add only `user_intent`), in this order:
   `create` (then `pack.py canva <pack> --design <id>`), `open` (the design must have exactly one
   page, else ask the user; then `pack.py canva <pack> --transaction <id>`), `add-pages`,
   `read-pages`, `place --page-ids <the new pages' ids in page order>`, `check`, `commit`,
   `export`. Then `pack.py canva-download <pack> <url> ...` with the export URLs in the order
   returned: each image becomes its object's reference. No further Canva calls.

## 4. One builder per object, in parallel

1. As soon as an object has its reference (`status`: `next` is `build`) and a build slot is free,
   spawn an **asset-builder** (`subagent_type: "asset-builder"`, `run_in_background: true`) whose
   whole prompt is: `Repository: <repository root>. Pack: <pack>. Object: <id>. Build it.` The
   builder fetches its own brief; pass `model` only when the user named one.
2. A builder's final message starts with one of:
   - `DONE <pack> <id>`: go to step 5 for it.
   - `HANDOFF <pack> <id>`: it reached its context budget; at once spawn a fresh asset-builder
     with the same prompt plus `Continue from the Handoff in your notes.`
   - `BLOCKED <pack> <id>: <reason>`: tell the user and act on their answer.
3. Start the next builder whenever a slot frees.

## 5. The user reviews each object

1. SendUserFile (`display: "render"`) with `production/qa/evidence/<pack>/<id>/<id>_compare.png`
   and `<id>_turnaround.png`; in your message, the builder's short report.
2. AskUserQuestion: "Are you happy with <id>?" — "Yes", "No — I'll say what to change".
3. Yes: `pack.py accept <pack> <id>`, then step 6 for it. No: `pack.py reopen <pack> <id>` and
   spawn an asset-builder with the step-4 prompt plus `The user wants: <their words>`.

## 6. Godot check, per accepted object

```bash
godot --headless --path . --import
xvfb-run -a -s "-screen 0 1280x720x24" godot --path . --rendering-driver opengl3 --resolution 1280x720 \
    --script res://tools/godot/qa/capture_pack_models.gd -- --pack <pack> --models <id>
```

Compare its `GODOT_MODEL` line with the build: it loaded; same size (Godot's Y is Blender's Z) and
triangles; every surface has a material; textured surfaces show `albedo_texture: true`. It saves
`<id>_godot_<view>.png` per recorded view. Anything wrong goes back to a builder (step 5.3) with
what failed.

## 7. Export and show everything

1. Folder: the session's scratchpad directory when the system prompt names one, otherwise
   `$HOME/asset-exports`. `pack.py export <pack> <folder>` copies per object the `.glb`, its
   references, the compare sheet, the turnaround and the Godot screenshots into `<folder>/<pack>/`
   and prints the path of `<folder>/<pack>.zip`.
2. In one message, per object (from `pack.py status`: triangles and size in metres, width x depth x
   height): its status, triangles, size and what still differs; and any Canva refusals.
3. AskUserQuestion: "Which assets are good, and what should change on the others?" — "All are
   good", "Some need changes (I'll say which and what)". Changes: step 5.3 for those objects,
   then steps 6 and 7 again.

## 8. End the run

`pack.py run-end` checks that the pipeline is as it was at run-start (it restores anything that
changed), reports what was moved to `.scratch/assetgen/quarantine/`, and ends the lock.

## 9. Deliver and leave the repository clean

1. SendUserFile (`display: "attach"`) with the zip; say where the folder is.
2. AskUserQuestion: "Keep this pack in the repository?" — "No, the download is enough
   (Recommended)": `pack.py discard <pack>` removes its working files, so the repository holds
   only the pipeline again. "Yes, commit it": commit only the pack's folders
   (`design/asset-packs/<pack>/`, `tools/blender/assetgen/packs/<pack>/`,
   `assets/models/<pack>/`, `production/qa/evidence/<pack>/`) as `feat: <pack> asset pack`.
