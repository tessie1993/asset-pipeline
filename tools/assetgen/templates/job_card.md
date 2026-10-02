# Job card: $part ($id, pack $pack)

<!-- Written by the lead builder after its comparison (builder_guide.md section 8), one card per
part task: fill every field with the specifics of this one job. The part builder reads only this
card and part_builder_guide.md, so the card carries everything: a part builder is only as good as
its job card. Comments like this one do not count as content. -->

## Part
$part

## What it is
<!-- Your understanding of the thing: what it is made of, how it is built, how it behaves, how it
looks in this art style, and the approach that calls for. -->

## Comparison
<!-- What the reference shows and what the current build shows, per view, measured, with the
close-up images (cv.py closeup) by path. -->

## What needs doing, and why
<!-- Each change with the difference from the reference it fixes (measured, the view it shows
in), why the reference looks like that and why the build differs. One large, whole job. -->

## Reference crops
<!-- One crop per view that shows the part (path), and the cv.py closeup boxes
(--view N --box X0 Y0 X1 Y1). -->

## Keep fitting
<!-- Anchors and attach surfaces (from common.py), sizes, the neighbours it meets and how, its
triangle share, the materials it shares. -->

## You may write
<!-- The hooks hold the part builder to exactly these paths (repository-relative, in backticks; a
folder ends with /). Add a module only when this job owns that part too. -->
- `$module`
- `$folder/` (this folder: analysis.md, log.md, renders, test scripts; never job.md)

## Test
`timeout 900 blender -b --factory-startup --python $harness -- --part $part`
<!-- The exact harness command; correct it if your harness takes other arguments. It rebuilds only
this part in place from base.blend and renders it from the reference views and as close-ups. -->

## Done when
<!-- Checks with numbers: outline and proportions per view, colour samples, triangle share, no
gaps or intersections at the anchors. -->
