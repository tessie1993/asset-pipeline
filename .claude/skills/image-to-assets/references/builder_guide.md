# Builder guide: understand, observe, compare, review, hand off (any object, any image)

For the `asset-builder` agents of `/image-to-assets`. Nothing here names a subject: it applies to
anything a reference shows, such as a prop, a building, a plant, a vehicle, a piece of terrain, a
piece of food, a tool, a garment or a character. The look comes only from the reference and the
user's words; the method comes from what each part is.

Paths are relative to the repository root. `cv.py` is `python3 tools/assetgen/cv.py` and
`pack.py` is `python3 tools/assetgen/pack.py`. The tools and add-ons are in
`blender_tools_guide.md`, and the part builders' guide is `part_builder_guide.md`, both in this
folder (`.claude/skills/image-to-assets/references/`).

**The workflow in one paragraph.** Every builder does **one render cycle**: it reads the Handoff
(or, the first time, the brief), does the next step of the build, makes **one full build** (every
recorded view, lit and clay, as the kit renders it), compares it with the reference part by part
and view by view, writes its own **review** (section 6) and the next **Handoff** (section 7), and
ends with `HANDOFF`. A fresh builder continues from that Handoff. A builder ends with `DONE` only
when its own review finds nothing worth improving (or the standard number of cycles is used up),
after the final build and `pack.py done`. There is no separate reviewing agent: you are the one who
compares and notes what needs improving, so be exact and honest about it. The builder that reads a
Handoff is the cycle's **lead**: it gives independent parts to part builders (section 8).

## 1. Understand what you build

Before changing anything, and again whenever something looks wrong, answer these from the
reference, in your own words:

- **What it is and what it is for.** Its purpose or role, how it is used or how it lives, what
  stands or rests on what. A thing that is understood is built with the right logic.
- **How it is made.** Carved, cast, forged, welded, bolted, sewn, woven, knotted, grown, layered,
  poured, baked, stacked, assembled from repeated pieces, painted on. The making explains the
  shapes: where seams fall, why edges are rounded or sharp, why parts repeat and how copies differ.
- **What holds it together.** The load path: which parts carry others, where weight goes down,
  how it stands or mounts, what is rigid and what is soft or flexible.
- **Its scale.** Real-world size of the whole and of its parts; what a detail is next to the whole.
- **Its age and life.** New or used, cared for or neglected; where hands, weather, friction and
  dirt would have acted.

### Think about what you see, then build that

A reference is a picture: marks of colour, value and line on a flat surface. Do not copy the marks;
work out what real thing each mark shows and build that thing. For every part, ask:

- **Solid, or a mass of many small things?** A shape drawn with one outline can be a single hard
  surface, or a mass of many small elements: strands, fibres, threads, bristles, needles, leaves,
  petals, blades of grass, scales, tiles, shingles, feathers, crumbs, foam, smoke, flame or liquid.
  Look for the clues: broken or flicked edges, tips and points along the outline, lines that flow
  in one direction, a change of value from base to tip, see-through gaps, soft shading. A mass of
  many things is built as that mass: its units (single elements, clumps, layers, tips), their
  direction from base to tip, how they overlap and part, how the outline breaks into tips. Never as
  one smooth shell or a flat cut-out with the mass's outline.
- **What does each colour or value change mean?** Form shading, a cast shadow, a highlight, a
  reflection, a glow, a different material, a painted marking, a hole or groove, a thin edge
  catching light. Decide which from the light direction and the other views; build form as form,
  marking as texture, glow as emission.
- **What does each line mean?** An outline, a crease or fold, a seam, the edge between two
  materials, the flow of strands or grain, a painted pattern.
- **How does it behave physically?** Weight and gravity (what hangs, sags, droops, rests), softness
  or stiffness, how soft or loose parts bend and fall, how growth or flow runs, what the material
  does at an edge (thins, frays, curls, chips).
- **What does the art style simplify or exaggerate?** Translate those choices into 3D in the same
  style: keep the stylisation, but give every part the construction of what it is, so it reads as
  that thing from every angle and up close, not only in the drawn view.
- **What is hidden?** Build the unseen sides from the logic of the thing, not by guessing a shape.

Write in the inventory, per part: what the reference shows, what you conclude it is, and how you
build it so it reads as that. When a part looks wrong in a render, come back here first: a part
built as the wrong kind of thing cannot be fixed by reshaping it.

### Understand the thing you are making; let it choose the approach

Every part is a thing with a nature: an eye, wood, a body, a tree root, a roof tile, a tyre, a
loaf's crust, a blade, cloth, a cable, a rock face. Understand that thing conceptually before you
decide how to build it, because what it is decides the approach. Know:

- **What it is made of and how it is built inside**: its layers and sub-parts, in order, from the
  inside out, and which of them show on the surface.
- **How it came to be**: how it grows, forms, is made, worn or weathered, and what that leaves in
  its shape and surface (rings and grain, taper and branching, folds where it bends, seams where it
  joins, flow lines, growth direction).
- **What it does and how it behaves**: its job, how it moves, bends, holds or bears weight, how it
  sits in, on or around its neighbours.
- **How it looks in life and how this art style draws it**: the features every thing of its kind
  has, and which of them the style keeps, simplifies or exaggerates.
- **How it ages and gets used.**

That understanding chooses the approach: the construction method and tool
(`blender_tools_guide.md` section 1), the sub-parts it needs even where the reference only hints
at them, the topology (where it bends, how edges flow), the materials and how they layer. A mass of
small elements is built as its units (clumps, tufts, layers), not modelled as one solid; a grown
thing is built along its growth, tapering and branching; a layered thing is built in its layers; a
made thing is built the way it is made (cut, joined, stacked, sewn, cast). A part built with an
approach that does not fit what it is cannot be fixed by reshaping it: change the approach. The
reference decides how the thing looks here; the understanding decides how it is put together and
what the reference implies but does not show. Where they seem to disagree, the reference wins on
look and the thing's nature wins on construction.

Write the answers into the Handoff (section *Understanding*) so the next builder starts from them.

## 2. Inventory the parts

List every part the reference shows, large to small.

Name every part by the thing it is (section 1, *Understand the thing you are making*), never by its
shape, look or a number, everywhere: the inventory, the generator's functions, objects and
materials, the part modules, the comparison and the Handoff.

For each part:

- **Name** (what the part is, as above), **count** (and whether the copies are identical, mirrored
  or each a little different), **position** on the whole, **size** relative to the whole and to its
  neighbours.
- **Basic shape** (what primitive or construction it starts from) and **exact shape** (contour,
  curvature, taper, thickness, cross-section, where it starts and ends).
- **Material** (see section 4) and **how much detail** it carries (see section 3).
- **Connection to its neighbours.** Attached, inserted, wrapped around, fused, hinged, layered on
  top, emerging from, hanging from, resting on, threaded through, tied, clamped, glued, growing
  out of. Is the join sharp, blended, gapped, overlapping, covered by another part?
- **Order and overlap.** What is in front of and behind it from each view; what it hides and
  what hides it; what passes over or under it.
- **Relation to the whole.** Symmetric partner, rhythm or spacing in a row, alignment with other
  parts, the direction it points, how it follows or contrasts the main form.

## 3. Detail hierarchy and amount

- **Primary forms**: the big masses that make the silhouette. Get them right first.
- **Secondary forms**: the parts and large features on those masses.
- **Tertiary detail**: the small relief, texture, marks and wear.
- **Amount of detail.** Count what the reference shows: how many grooves, rings, strands, layers,
  plates, rivets, stitches, cracks, stripes, spots, scales, leaves, bricks. Match the count and the
  spacing, not just the idea. Match the density too: where the reference is busy and where it is
  calm. The art style decides how far detail is simplified; follow the reference, not habit.
- **Where the triangles go.** Spend geometry on silhouette curves, on parts seen up close, and on
  relief that changes the outline. Leave flat, calm and hidden areas light. Fine relief that does
  not change the outline goes into the baked normal map.

## 4. Materials, per material

For each material, observe and then build:

- **Base colour** and its **variation**: hue shifts, value changes, saturation, light and dark
  patches, gradients and where they run, colour that changes with depth or wear.
- **Surface response**: roughness or gloss and how it varies, metallic or not, clearcoat, sheen
  (cloth, velvet, fine fibres), anisotropy (brushed metal, satin, strands).
- **Light passing through**: translucency and subsurface scattering (wax, leaves, thin cloth,
  skin, petals, jade, ice, fruit flesh), transmission and transparency (glass, gems, liquid,
  crystals), how thickness changes it, refraction, tint, cloudiness.
- **Light given off**: emission, its colour, strength, falloff and halo, which parts glow and
  which only look bright.
- **Relief**: bump and normal detail, its scale and direction, how it follows the form.
- **Pattern**: scale, direction, repetition and irregularity, how it wraps around the form and
  across seams, painted pattern against carved pattern.
- **How materials meet**: sharp boundary, soft blend, gradient, an underlayer showing through
  worn spots, a trim or edging between them.

What reaches Godot is what the final build bakes (base colour, roughness, metallic, ambient
occlusion, normal, emission): get the looks of translucency and transmission from those channels.

## 5. Wear, imperfection and life

Worn and rounded edges where things are touched or rubbed; chips, dents, cracks, scratches and
scuffs; dirt, dust, grime and stains collecting in recesses and at the bottom; fading where light
falls; discolouration, rust, patina, moss, water marks; uneven paint; frayed, clumped or tangled
strands; irregular spacing; slight asymmetry. Repeated parts differ from each other. Put
imperfection only where the reference shows it, in the amount it shows.

## 6. The comparison and your review (while you build, after the build, before the Handoff)

### Compare often, part by part, while you build

Do not wait for the end of the cycle to look at the reference again. Compare after every change:

1. **Before you start a part**, crop that part out of every reference view that shows it (same
   framing, enlarged) and keep the crops open as the target.
2. **After every change to the part**, render that part (a close-up from the same angles as those
   reference views, in the background as `blender_tools_guide.md` section 6 describes; the test
   harness of section 8 does this for one part) and put each render next to the same reference
   crop, at the same scale.
3. **Look at the pair** with the checklist below for that part (shape, volume, connection, detail,
   material, and whether it reads as what it is), write one line of what still differs, change it,
   and compare again. Move on to the next part only when the pair matches or you know exactly what
   remains and why.
4. **After the cycle's build**, `cv.py compare <pack> <id>` for the whole, and
   `cv.py closeup <pack> <id> --view N --box X0 Y0 X1 Y1` (reference next to the build, same box)
   for every part you changed and every part next to it, to catch a fix that broke a neighbour.

These quick part checks belong to the current cycle. The cycle's build of the whole generator is
always the full kit build (every recorded view, lit and clay, at the kit's render settings): never
a reduced render of the full build, because the comparison needs every view.

### The full comparison

Run `cv.py compare`, then put each reference view next to the same render. Go over the object
first as a whole, then part by part with the inventory, then material by material:

- **The whole**: silhouette and outline from every view, proportions and size ratios,
  orientation and stance, placement and balance of the parts, how the parts meet, connect and
  overlap, the overall art style.
- **Shapes**: exact contours, curves and where curvature changes, straight against curved,
  tapering, thickness, where each part starts and ends, symmetry and asymmetry, edges (sharp,
  soft, bevelled, rounded).
- **Volume and depth**: roundness or flatness, depth front to back, how forms turn away, overlap
  and hide one another, recesses and protrusions, layering, gaps and holes, how the form reads
  from each view.
- **Connections and relations**: every join as the inventory describes it; overlap order; parts
  that float, intersect wrongly or leave gaps; spacing and alignment between parts.
- **Detail**: the amount and density per part against the count in the reference; small shapes,
  ornaments, seams, grooves, ridges, folds, bumps, cracks, dents, chips, holes.
- **Materials**: colour, value, saturation, gradients and transitions, light and dark patches,
  roughness and gloss, metal, translucency and transmission, glow, relief, pattern scale and
  direction.
- **Wear and imperfection**: as in section 5.
- **Art style**: the level of simplification, edge and outline treatment, shading, palette,
  painted or realistic; does the build read as if it came from the same hand?
- **Reads as what it is**: for each part, does it read as the thing section 1 concluded (a soft
  mass as soft, many small elements as many, hard as hard, a marking as a marking), from every
  view and up close? If not, rebuild it as the right kind of thing before tuning its shape.
- **Missing and extra**: anything the reference shows that the build lacks, or the build adds.

Use numbers where they exist (overlap, width/height, colour samples, `cv.py` measurements) and say
what the eye sees where they do not.

### Understand every difference

For every difference you find, while you build and in the full comparison, answer two questions
before you decide what to change:

1. **Why does the reference look like that?** Explain it from what the thing is (section 1): what
   it is made of and how it is built, how it grew or was made, what it does and how it behaves,
   how light meets it, and how the art style draws such a thing. A look you can explain tells you
   what to build; a look you cannot explain yet needs a closer look at the reference.
2. **Why does the build look different?** Find the cause in the build, not only the symptom: the
   wrong kind of construction for that thing, a missing sub-part or layer, a proportion or anchor,
   topology that cannot hold the shape, a material that lacks the property (translucency, glow,
   roughness, gradient), a render or lighting difference.

Write both answers next to the difference. The fix follows from them: when the cause is the
approach, change the approach; when it is a value, change the value. A fix that only pushes the
symptom toward the reference without a reason is a guess.

### Your review: `## Cycle <n>` in your notes

You are your own reviewer. After the full comparison write `## Cycle <n>` (n is the build number
the kit printed) in your notes, judged only on what the images show, never on what you meant to
build:

- **What matches**, per part and per view (keep it).
- **What differs**, per part and per view, as a measurement ("the handle 12 % too long in view 2",
  "the roof 0.04 lighter", "5 chips on the rim in the reference, none in the build", "the trunk
  leans 4° less"), never an adjective, each with the two answers of *Understand every difference*.
- **Needs improving**: a ranked list, most visible and most valuable first, of what still keeps
  the build from the reference. It becomes the Handoff's next step.

The build gate refuses the next build until this section exists. When the list is empty (nothing
left worth improving), or the build count reaches the standard number of cycles, the next build is
the final one (`--final`) instead of a Handoff.

## 7. The Handoff

Before you write it, in this order: **render** (the cycle's full build, every view lit and clay as
the kit renders it), **compare** (`cv.py compare` and close-ups of every part beside the
reference), **analyse** (what the comparison shows, part by part; for each difference why the
reference looks like that and why the build differs, section 6), **review** (`## Cycle <n>`).
The Handoff comes from that analysis, never from memory of earlier renders.

Write it at the end of your notes as `## Handoff`, with the subsections below, and delete the
previous Handoff: the notes hold only the current one. The next builder reads only this section
(`pack.py brief` prints it), so it must stand on its own:

1. **Understanding** (section 1: what each part is, what you know about that thing, the approach
   it calls for) and the **Part inventory** (section 2), kept short and current.
2. **Comparison** (section 6), per view and per part (each part by its name), with measurements.
3. **Needs improving**: the ranked list from your review.
4. **Next step: part tasks.** The most valuable next changes, each with why (the difference from
   the reference it fixes, measured, and the view it shows in; why the reference looks like that
   and why the build differs), each with the approach the thing's nature calls for (section 1),
   precise enough to do without redoing the analysis: which part, which generator function or
   parameter, from what to what, where on that part, which tool or add-on
   (`blender_tools_guide.md`), and how to check it worked. Group it into 2 to 4 **independent part
   tasks** the next lead can give to part builders at the same time (section 8), each with the
   job card's fields: the part, what it is, the comparison with the reference, what needs doing and
   why, its reference crops and what it must keep fitting with its neighbours.
5. **Do not undo**: what is right now and must stay.
6. **Files to look at**: the reference views, the latest compare, the renders and close-ups this
   Handoff refers to.
7. **Standing rules**, copied forward unchanged: the standing rules of the notes template's Handoff
   skeleton, and every wish the user gave for this object, word for word, with when it was given.

Then end with the first line `HANDOFF <pack> <id>`.

When your cycle ends the object instead (your review found nothing worth improving, or the cycles
are used up): make the final build (`-- --final`), review it like any build (`## Cycle <n>`: the
baked renders against the reference), bring the Handoff up to date (its Needs improving list empty
or what remains, its next step "none"), write `## Report`, run `pack.py done <pack> <id>` and end
with `DONE <pack> <id>`. If the user asks for changes later, the next builder starts from that
Handoff and the user's words.

## 8. Lead and part builders (one cycle, several parts at once)

The builder that reads the Handoff is the **lead**. It keeps everything that needs the whole object
in view: the understanding (section 1), the inventory, the judgment of every part against the
reference, the one full build of the cycle, the full comparison and review (section 6) and the
Handoff (section 7). It hands independent parts to **part builders** (agent type
`asset-part-builder`). Each part builder gets **one job** with clear instructions, does it, reports
and ends; any further work on that part is a new job for a new part builder.

1. **Split the generator into part modules** (once; later leads keep it): one file per part in
   `tools/blender/assetgen/packs/<pack>/<id>_parts/<part>.py` (snake_case, named by what the part
   is), each with one build function, and a `common.py` with what the parts share (overall
   dimensions, the anchor points and attach surfaces where parts meet, the shared materials). The
   main generator `<id>.py` imports them, builds them in order and joins them; it still ends with
   `kit.run(build)`. Each part file is owned by one builder at a time.
2. **Pick the part tasks** from the Handoff's next step: 2 to 4 parts that can change without
   each other. Parts that shape each other (a thing and its socket, a surface and what grows out
   of it, a lid and its rim) are one job.
3. **Make the test harness first**: save the current model once as a .blend
   (`.scratch/assetgen/work/<pack>/<id>/parts/base.blend`) and a script
   (`.scratch/assetgen/work/<pack>/<id>/parts/harness.py`) that loads it, rebuilds only one part
   from its module, puts it in place and renders it from the reference views and as close-ups
   beside the reference crops. Run it once yourself so you know it works. Part builders never run
   the full build: the hooks let them run Blender only on scripts in that `parts/` folder.
4. **Compare first, then write one job card per part**: `pack.py job-card <pack> <id> <part>`
   writes `.scratch/assetgen/work/<pack>/<id>/parts/<part>/job.md` from the template; fill every
   field. The card carries the specifics; the part builder guide stays generic.
   - **Part** and **What it is**: your understanding of the thing (what it is made of, how it is
     built, how it behaves, how it looks in this art style).
   - **Comparison**: what the reference shows and what the current build shows, per view,
     measured, with the close-up images (`cv.py closeup`).
   - **What needs doing, and why**: each change with the difference from the reference it fixes.
   - **Reference crops**: paths per view, and the `cv.py closeup` boxes.
   - **Keep fitting**: anchors, sizes, neighbours, triangle share.
   - **You may write**: the module(s) and the card's folder. The hooks hold the part builder to
     exactly the paths listed there.
   - **Test**: the exact harness command.
   - **Done when**: checks with numbers.

   Crop the reference for each part yourself; a part builder is only as good as its job card.
   Give each part builder a large, whole job, not a single small fix.
5. **Spawn the part builders together**, one per job card (Agent tool,
   `subagent_type: "asset-part-builder"`, `run_in_background: true`), each with only this prompt:
   "Repository: <root>. You are a part builder with one job. Read
   .claude/skills/image-to-assets/references/part_builder_guide.md, then your job card
   .scratch/assetgen/work/<pack>/<id>/parts/<part>/job.md, and do that job. Report and stop."
6. **Keep working while they run**: build a part yourself, prepare the integration, crop the
   reference for the next jobs. Keep the machine's load near `nproc`.
7. **Judge every part yourself** against the reference crops and close-ups before it goes in;
   look at the images, not only the report. When a part is not right, write a new job card (what
   is wrong, exactly; the last result's images; what must stay) and spawn a **new** part builder
   for it. Never continue a part builder that has reported.
8. **Integrate**: the one full build of the cycle (all views, lit and clay, as the kit renders
   them), the full comparison with `cv.py compare` and close-ups, your review (section 6), then the
   Handoff (section 7) with the next part tasks.
9. Read the part builders' reports and images, never their transcripts, to keep your context
   small. Part builders build; judging the whole is yours.
