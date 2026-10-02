# $id — $name: builder notes

Fill every section of `## Analysis` before the first build (a hook refuses the build until each
has content). After each build write `## Cycle <n>` (n = the build number the kit printed). When
your context budget is reached write `## Handoff`; at the end write `## Report`. A critic judges the
final build from the images and this Analysis; following builders read all of it: keep it complete,
exact and in numbers.

## Analysis

### What it is
<!-- The object as a whole: what it is, how its parts are put together, which side is its front,
and its character: what makes it read as this object and not a generic one. -->

### Views
<!-- Per recorded view: the side it shows and what only it shows. Sides no view shows and what
you infer for them, from what. Why this camera (--lens MM or --ortho). -->

### Size and proportions
<!-- Overall size in metres (width x depth x height) and the evidence for it; the ratios from
`cv.py measure`; the KEY RATIOS between parts (head : body height, leg length : body length, …),
each a number the critic can check. -->

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
<!-- Every distinct surface S1, S2, …: the parts that carry it; what it is (fur, skin, wood,
painted metal, cloth, …); its colour range from `cv.py sample` (mean, darkest, lightest, and where
it is lighter or darker and why); roughness and gloss and how they vary; its relief (pores, grain,
weave, strands, scratches) and the relief's scale; pattern scale and direction; wear, dirt, grime,
edge highlights; how it blends into its neighbours (mask, edge softness). Then how you build it:
the library material (ref, tile, tint, mapping) and/or the procedural nodes, the masks that layer
it (kit.attribute, kit.mark, ambient occlusion, pointiness, noise, gradients), and the variation
that keeps it from reading uniform. No surface is one flat colour unless the reference shows one. -->

### Details and nuances
<!-- Everything small that makes it this object, one line each, and how it is made (modelled, or
in the shader). Every imperfection and variation from Close observation is here and gets built. -->

### Skills, add-ons and tools
<!-- The skills you read (blender-image-to-3d for the method and its gates; scenario-blender-*
for sculpting, hard surface, texturing, UVs and baking, retopology, geometry nodes, hair) and what
you use from each; add-ons; kit functions; which check shows each part is right. -->

### Build plan
<!-- Order (big forms → parts → details → materials → nuances), the technique per part, how the
triangle budget is split, the texture size (kit.run(build, texture=2048 or 4096)). -->

## Cycles
