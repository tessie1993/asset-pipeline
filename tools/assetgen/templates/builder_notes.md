# $id — $name: builder notes

Fill every section of `## Analysis` before the first build (a hook refuses the build until each
has content). Every builder does one render cycle: after its build it writes its own review as
`## Cycle <n>` (n = the build number the kit printed), then the `## Handoff` at the very end of this
file, replacing the previous one. The next builder reads only the Handoff (`pack.py brief` prints
it), so it must stand on its own. At the end, `## Report`. Keep everything complete, exact and in
numbers. The guides are in `.claude/skills/image-to-assets/references/`.

## Analysis

### What it is
<!-- The object as a whole: what it is and what it is for, how its parts are put together, which
side is its front, and its character: what makes it read as this object and not a generic one. -->

### Views
<!-- Per recorded view: the side it shows and what only it shows. Sides no view shows and what
you infer for them, from what. Where the views disagree, how the build settles it. Why this camera
(--lens MM or --ortho). -->

### Size and proportions
<!-- Overall size in metres (width x depth x height) and the evidence for it; the ratios from
`cv.py measure`; the KEY RATIOS between parts (a lid : body height, a roof : wall height, a limb :
body length, a wheel : chassis length, …), each a number a comparison can check. -->

### Close observation
<!-- What `cv.py observe` shows, every view and every tile, plus `cv.py closeup` and `cv.py sample`
wherever a detail needs a closer look. Per region: the small shapes, edges, creases and folds; the
imperfections (dents, chips, scratches, wear, dirt, stains, uneven paint, frayed or clumped
strands); the variation (colour shifts, tone gradients, light and dark patches, irregular
pattern); how one surface meets the next (hard edge, soft blend, seam, gap, overlap). Quote the
`cv.py sample` numbers (mean, darkest, lightest, spread). Nothing is "plain" until you have looked
at it magnified. -->

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it (technique, skill) | geometry detail (what is modelled: bevels, creases, folds, holes, relief) | nuances (imperfections, asymmetry, how each copy differs) |
|---|---|---|---|---|---|---|---|

### Materials and shaders
<!-- Every distinct surface S1, S2, …: the parts that carry it; what it is (wood, painted metal,
stone, cloth, glass, leaves, skin, ceramic, …); its colour range from `cv.py sample` (mean,
darkest, lightest, and where it is lighter or darker and why); roughness and gloss and how they
vary; light passing through or given off; its relief (grain, weave, pores, strands, scratches) and
the relief's scale; pattern scale and direction; wear, dirt, grime, edge highlights; how it blends
into its neighbours (mask, edge softness). Then how you build it: the library material (ref, tile,
tint, mapping) and/or the procedural nodes, the masks that layer it (kit.attribute, kit.mark,
ambient occlusion, pointiness, noise, gradients), and the variation that keeps it from reading
uniform. No surface is one flat colour unless the reference shows one. -->

### Details and nuances
<!-- Everything small that makes it this object, one line each, and how it is made (modelled, or
in the shader). Every imperfection and variation from Close observation is here and gets built. -->

### Skills, add-ons and tools
<!-- The skills you read (blender-image-to-3d for the method and its gates; scenario-blender-*
for sculpting, hard surface, texturing, UVs and baking, retopology, geometry nodes, strands) and
what you use from each; add-ons (blender_tools_guide.md); kit functions; which check shows each
part is right. -->

### Build plan
<!-- Order (big forms → parts → details → materials → nuances), the technique per part, how the
triangle budget is split, the texture size (kit.run(build, texture=2048 or 4096)). -->

## Cycles
<!-- After each build, your own review (builder_guide.md section 6), judged on the images only,
never on what you meant to build. Its format:

## Cycle <n>
### What matches
Per part and per view: what matches the reference (keep it).
### What differs, and why
| part | view | reference | build | difference (measured) | why the reference looks like that | why the build differs |
|---|---|---|---|---|---|---|
### Needs improving
1. Ranked: most visible and most valuable first. Empty when nothing is left worth improving.

Then, at the very end of this file and only after you render, compare, analyse and review, the
Handoff (builder_guide.md section 7). Delete the previous Handoff: only the current one stays.

## Handoff
### Understanding
What each part is, what you know about that thing, and the approach it calls for.
### Part inventory
Every part by the name of what it is: count, position, size, shape, material, connections.
### Comparison
Per view and per part, with measurements, and for each difference why the reference looks like
that and why the build differs.
### Needs improving
The ranked list from your review.
### Next step: part tasks
2 to 4 independent part tasks, each with the job card's fields: the part; what it is; the
comparison (per view, measured, close-up paths); what needs doing and why (generator function or
parameter, from what to what, where, which tool or add-on, how to check it); reference crops
(paths and cv.py closeup boxes); keep fitting (anchors, sizes, neighbours, triangle share); done
when (checks with numbers).
### Do not undo
What is right now and must stay.
### Files to look at
The reference views, the latest compare, the renders and close-ups this Handoff refers to.
### Standing rules
Copied forward unchanged into every Handoff:
- One render cycle per builder: one full build, the comparison and the review (builder_guide.md
  section 6), then the next Handoff (section 7) replacing this one, ending with HANDOFF. DONE only
  after the final build and pack.py done, when the review finds nothing worth improving or the
  cycles are used up.
- Read .claude/skills/image-to-assets/references/builder_guide.md and blender_tools_guide.md
  before working. The builder that reads this Handoff leads: it runs the part tasks with 2 to 4
  part builders at once (builder_guide.md section 8) and judges every part itself.
- Quality: the triangle budget in pack.json, spent where the detail is; every detail; the whole,
  the parts and how they connect; exact shapes, curves, volume and depth, overlap; the amount of
  detail; materials including translucency and glow, texture, gradients, wear and tear; the art
  style.
- Installed Blender add-ons and BlendKit free models (licence check) where they help.
- When the reference's views disagree, say how the build settles it.
- Think about what you see and build that; each part must read as what it is (builder_guide.md
  section 1).
- Understand the thing you are making, conceptually (an eye, wood, a body, a tree root, a roof
  tile, a tyre, a loaf's crust), and let that choose the approach (builder_guide.md section 1).
- For every difference, understand why the reference looks like that and why the build differs;
  the fix follows from the cause (builder_guide.md section 6).
- Compare to the reference often, part by part, after every change, not only at the end of the
  cycle (builder_guide.md section 6).
- Multitask: Blender builds and renders in the background while you keep working; independent
  steps together; keep the 1-minute load near nproc, not far above; never two jobs writing the
  same file (blender_tools_guide.md section 6). The full build always renders every recorded view,
  lit and clay, as the kit renders it.
- The user's wishes for this object, word for word, with when they were given (none yet).
-->
