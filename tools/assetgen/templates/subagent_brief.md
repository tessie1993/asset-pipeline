You are building ONE 3D game asset in $repo (a Godot project). Everything runs headless in this Linux container; Blender is on PATH as `blender`.

AUTHORIZATION: the user approved this pipeline. You are authorized to create and edit $generator and $notes and to run Blender builds and material searches, without asking. Do not ask "May I write"; nobody can answer you.

YOU MAY CHANGE TWO FILES: $generator and your notes $notes. A pipeline run is in progress: the pipeline itself (the kit, pack.py, the templates, the skill, the README, pack.json, other objects' generators) is locked and a hook refuses edits to it. Do not run git (no add, commit, push, checkout or restore). If the kit cannot do something you need, write the helper inside your own generator and say so in your report.

OBJECT: `$id` — $name.

REFERENCE IMAGES (primary reference; open them with the Read tool — it shows images directly):
1. Canva 360-degree sheet: $sheet — the same object from eight angles (0, 45, 90, 135, 180, 225, 270, 315 degrees) in two rows of four. Your model must be a copy of THIS object, in the same style and with the same detail.
2. Source image: $source — the object is $where.

Then read:
- $description — what the object is, its parts, proportions, surface colours and descriptions, size anchor, triangle budget and the views it is judged on. Where the text and the sheet disagree, the sheet wins.
- $readme — the pipeline rules. Mandatory.
- $kit — the kit API. It already runs the blender-skills' Blender code headless (polyhaven-texture-apply, polyhaven-studio-setup, product-polish, turntable).

RELEVANT SKILLS: the orchestrator found these installed skills relevant to this object. Read each SKILL.md and use its method and Blender code where it applies (run their Blender code headless through your generator, not over a socket):
$relevant_skills
You may also look through $skills for other skills that fit what you are building, and use them the same way.

STEP 1 — UNDERSTAND WHAT YOU ARE BUILDING (before any build). The user's art style for this pack is: "$style". Study the Canva sheet view by view and write your analysis at the top of $notes:
a. What the object is and how it is put together. Knowing what it is tells you which surfaces to look at closely and what each surface is made of.
b. ELEMENTS: every separate element, how many, where each sits and what it connects to.
c. VOLUME of each element: its 3D form, thickness and depth, how far it stands out or sits back, gaps between elements.
d. SHADING: how light falls on it in the sheet (soft or hard edges, bevels catching highlights, dark recesses, ambient occlusion).
e. TEXTURES — an object usually has more than one. From what the object is (a), decide which surfaces carry a texture, then inspect each one up close on the sheet with the zoom tool (run it on the views where that surface faces the camera; `--box` narrows to the surface):
   `cd $repo && blender -b --factory-startup --python tools/blender/assetgen/zoom.py -- $pack $id --view <azimuth> [--box X0 Y0 X1 Y1] [--scale 3]`
   It writes $zoom_example (the Canva view on the left, your render on the right once you have built); open it with the Read tool.
   List every distinct texture as `T1`, `T2`, … and describe each:
   - which elements carry it, and what kind of material it is (metal or not, see-through, glowing);
   - what it looks like on the sheet: the pattern (what repeats), its colour and colour variation (#rrggbb read from the sheet), the size of one repeat in metres (count the repeats across the element and use the size anchor), the pattern's direction on each element, its relief (flat, shallow, deep), gloss, wear;
   - how the user's art style ("$style") shows in it: how the sheet renders this texture in that style — simplified or detailed, painted or photographic, exaggerated or subtle — so the texture you choose and how you set it up (tile, normal_strength, tint, roughness) keep that style;
   - search words: the plain words that describe this texture for a texture library.
f. DETAIL LEVEL: how much surface detail the sheet shows per element, so your model has the same, not more and not less.
These notes are your plan: every decision in the generator follows from them.

TEXTURE SEARCH: there are no preset materials. For each texture T1, T2, … search with its search words:
  `cd $repo && python3 tools/assetgen/pack.py material-search <search words> --previews $previews`
It lists Poly Haven and ambientCG textures (`ref`, name, real-world `size_m` for Poly Haven) and saves each thumbnail. Open the thumbnails with the Read tool and compare each against your description of that texture (pattern, repeat size, direction, relief, colour, style) — not colour alone. Under each texture in $notes record the ref you chose and why it matches, and what differs that `tile`, `normal_strength`, `tint` and `roughness` must correct. Search again with other words whenever nothing matches. Order: a Poly Haven texture first, an ambientCG one when Poly Haven has nothing close, `kit.flat()` for flat colours, see-through and glowing surfaces. Use it as `kit.material("<ref>", tile=<repeats per metre>, tint="#rrggbb", ...)`: `tile` = 1 / the repeat size you measured on the sheet in metres; `tint` multiplies the texture and can only make it darker, so pick a texture at least as light as the colour you need. No procedural shader nodes for the look (they do not reach Godot). Emission ≤ 1.5.

STEP 2 — $cycles CYCLES OF BUILD → RENDER → COMPARE (the standard; see STOPPING for the only way to stop sooner).
Each cycle:
a. BUILD: write or update $generator (it must end with `kit.run(build$run_origin)`), then run (Bash tool `timeout` 600000; builds can take minutes):
   `cd $repo && blender -b --factory-startup --python $generator -- --samples 16 2>&1 | grep -E "BUILT|RENDERED|COMPARE|Error|Traceback|line [0-9]+"`
   The build renders your eight views and the compare sheet $compare (your views on TOP, the Canva sheet BELOW, same angles).
b. COMPARE: open $compare and go view by view, element by element, through ELEMENTS, VOLUME, SHADING, each TEXTURE (T1, T2, …) and DETAIL LEVEL. For every texture also run the zoom tool on a view where it faces the camera and compare pattern, repeat size, direction, relief, colour and style close up. Write in $notes under `## Cycle <n>`:
   - LOOKS RIGHT: what matches, and WHY it matches (which decision made it right — keep those);
   - LOOKS WRONG: what differs, and WHY it differs (the cause in your model: wrong proportion, missing element, flat where the sheet has volume, wrong texture scale, tint too dark, bevel too small, …);
   - FIX: the change for each wrong item, following from its cause.
   Understanding WHY is the point: fix causes, not symptoms, and never undo something that looks right.
c. Apply the fixes; the next cycle's build shows whether they worked.
Rules: judge on $judge_views. Never write image-analysis or measuring scripts and never use Pillow: the compare sheet is your measuring tool. Use the kit's lighting (studio HDRI plus four studio lights); the camera angle and framing come from pack.json — change neither.

STEP 3 — FINAL RENDER: after the last cycle, build once more with the default samples (drop `--samples 16`, keep the 600000 timeout). This is the result you report.

STOPPING
- The standard is all $cycles cycles.
- You may stop sooner only when you are happy with the work: every check in the DEFINITION OF GOOD below passes on the latest compare sheet. Then do the final render and report READY FOR REVIEW: the orchestrator shows your work to the user, who decides whether it is good. If the user wants changes, you will get their words and continue with the next cycle.
- After cycle $cycles: final render and report, whatever the state.

DEFINITION OF GOOD — judged on $judge_views of the latest compare sheet:
- ELEMENTS: the same elements as the sheet, same count, same positions; the silhouette matches; proportions within about 10 % of the sheet.
- VOLUME: every element that stands out, sits back, bulges or has a gap on the sheet does so in the render; nothing is flat that is 3D on the sheet.
- MATERIAL: every surface is the same kind of material as on the sheet, metal where the sheet is metal, similar gloss, see-through where the sheet is see-through; same hue and brightness side by side.
- SHADING: edges the sheet shows soft are bevelled and catch light the same way; recesses are as dark as on the sheet.
- TEXTURES: in the zoom close-ups every texture T1, T2, … matches the sheet: the same pattern, repeat size within about 20 %, direction, relief and colour variation, in the user's art style.
- DETAIL LEVEL: relief and variation between parts as on the sheet — no more, no less.
- BUDGET: the BUILT triangle count is within $budget.
- CLEAN: the build prints BUILT and RENDERED with no error or traceback.

CONSTRAINTS: other builds run in parallel on the same CPUs — keep the default --threads and one Blender run at a time. Triangle budget: $budget.

FINAL MESSAGE: first line `READY FOR REVIEW (cycle <n> of $cycles)` if you stopped early because every check passes, or `CYCLES DONE ($cycles of $cycles)`. Then: a table with one row per check (ELEMENTS, VOLUME, MATERIAL, SHADING, TEXTURES, DETAIL LEVEL, BUDGET, CLEAN) marked pass or fail with one line of evidence each; the last BUILT line; your texture list T1, T2, … with the ref chosen for each and the elements that use it; the skills you used and how; what still looks wrong, view by view, and why; the path of $notes; anything missing from the kit and how you worked around it.
