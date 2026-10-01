# $id — $name: builder notes

Fill every section of `## Analysis` before the first build (a hook refuses the build until each
has content). After each build write `## Cycle <n>` (n = the build number the kit printed). When
your context budget is reached write `## Handoff`; at the end write `## Report`. These notes are
the only memory a following builder gets: keep them complete and short.

## Analysis

### What it is
<!-- The object as a whole: what it is, how its parts are put together, which side is its front. -->

### Views
<!-- Per recorded view: the side it shows and what only it shows. Sides no view shows, and what
you infer for them. Why this camera (--lens MM or --ortho). -->

### Size and proportions
<!-- Overall size in metres (width x depth x height) and the evidence for it; the ratios from
`cv.py measure` (w/h per view, width : height : depth); the key ratios between parts. -->

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it | modelled or texture | nuances (asymmetry, wear, how copies differ) |
|---|---|---|---|---|---|---|---|

### Textures
<!-- Every distinct surface T1, T2, …: parts that carry it, kind of material, pattern, colour
(#rrggbb), repeat size, direction, relief, gloss, wear, how the art style shows in it; search
words; then the texture chosen with its settings, or kit.flat. -->

### Details and nuances
<!-- Everything small that makes it this object: edges and bevels, seams, gaps, overlaps,
bulges, irregularities, colour variation, markings, small attachments; per item modelled (it
changes the outline or catches light) or texture. -->

### Skills, add-ons and tools
<!-- The installed skills you read and what you use from each; add-ons; kit functions; which CV
check shows each part is right. -->

### Build plan
<!-- Build order (big forms → parts → details → materials → nuances), the technique per part,
and how the triangle budget is split. -->

## Cycles
