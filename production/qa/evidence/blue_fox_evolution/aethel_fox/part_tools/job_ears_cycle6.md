# Job card: ears (aethel_fox, pack blue_fox_evolution)

## Part
ears: the two ears (build_ear) and the cream ear tufts at the inner base of each ear (build_ear_tufts),
module `aethel_fox_parts/ears.py`.

## What it is
Aethel Fox is a stylised blue fox (anime / painted game art: soft cel shading, clean smooth forms, thin
navy ink outlines). The user approved the model (build 5) and then asked: "Smoothen model. Rough outer
edges caused by low quality reference and too literal copy." This job is that request for the ears.

- The ear: a tall, thin cartilage leaf standing from the skull, furred outside (blue, darker rim), inside
  a shallow bowl (tan with blue spirals painted on, indigo zone with a cyan spiral). In this art style its
  outline is one clean, smooth curve: a straight-ish inner edge, a convex outer edge, a pointed tip, and
  the rim is a soft rounded edge of a thin but solid leaf (never a razor blade, never facets).
- The ear tuft: a soft clump of cream fur growing from the inner base of the bowl. In the drawings it is a
  small fan of 4-5 cream locks (front view: like a fern frond / feather fan rising up and out of the bowl;
  side view: 4 locks fanning up inside the bowl). Each lock is a clump of hair: broad and full at its root,
  overlapping its neighbours there, tapering to a soft rounded point; the fan reads as ONE soft tuft with
  several rounded points, lying in the bowl. It is fur painted smooth, not a crown of needles.

## Comparison
Close-ups (build 5, harness renders, 600 px): `.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/out/b5_clayshot_head_front.png`,
`b5_shot_head_front.png`, `b5_clayshot_full_side.png`, `b5_clayshot_full_34.png`, `b5_clayshot_full_back.png`
(same folder). Reference crops: `.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/r_front_head.png`,
`r_side_head.png`, `r_side_ear.png`.
- Ear tufts, front: build = 5 separate thin flat blades per ear (thickness 1.6 mm at the root -> 0, width
  8.5 mm -> 0 needle tips), spread apart with gaps between them, standing off the bowl: in clay they read as
  a ring of spikes / a crown on the head (head_front clay: the 5 pointed petals at each ear base). Reference:
  a compact soft fan, locks overlapping at their roots, broad rounded-pointed tips, a smooth cream mass.
- Ear tufts, side (full_side, full_34 clay): small spikes poking out at the ear base; reference side: a fan
  of 4 soft locks lying in the near ear's bowl.
- Ear leaf: the outline is smooth in clay; check the rim up close (Nt 30 rings x Nu 15, Subsurf 1): any
  faceting on the outline, a knife-thin rim, a pinched tip or a visible seam at the base must go.

## What needs doing, and why
1. Rebuild build_ear_tufts as a soft fan of 4-5 cream fur locks per ear (why: the thin needle blades
   with gaps read as torn spikes; the drawing paints a soft fan of overlapping locks):
   - each lock a domed clump: section rounded (e.g. an ellipse or a lens with a domed top), root
     thickness ~2.5-3.5 mm and width ~9-12 mm (pre-scale), tapering smoothly; the tip a rounded point
     (width falls to 0 only in the last ~8 % along a smooth curve, no needle);
   - the locks fan from one shared root area at the inner base of the bowl, overlapping their
     neighbours over the lower ~40 % so no gap shows between them; roots buried 1-2 mm into the bowl
     surface; each lock curves gently (one smooth bend, no wobble) up and slightly out, lying close to
     the bowl (lift <= 3-4 mm) so the fan reads as part of the ear;
   - lengths and angles differ a little lock to lock (the middle ones longest), as in the drawing;
   - enough segments along (>= 16) and around (>= 10) for smooth outlines; shade smooth.
2. Ear leaf (build_ear): make every outline and the rim smooth up close: a rounded rim (the front and
   back surfaces meet in a round edge, not a knife edge), a clean tip, a smooth base where it meets the
   skull; raise ring / column counts or the Subsurf level only as far as needed (keep the shape: base B,
   EAR_TIP, EAR_F0, EAR_HW, bowl depth and colours as they are; the user approved them).
3. Materials stay: M_ear_outer, M_ear_inner (spirals, indigo zone), M_ear_tuft cream with its root
   shading; the tufts' UVs must keep the root-to-tip ramp (uvs[0] along the lock in the current shader).

## Reference crops
- front: `.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/r_front_head.png` (ref view 1, both ears' tufts)
- side: `.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/r_side_ear.png`, `r_side_head.png` (ref view 2)
- full views: `production/qa/evidence/blue_fox_evolution/aethel_fox/aethel_fox_ref_view_1.png`, `_2.png`, `_3.png`
- cv boxes for cmp.py (fractions of the object): view 1 `--box 1 0 0 1 0.35`, view 2 `--box 2 0.1 0 0.45 0.35`

## Keep fitting
- Ear base B (+-0.044, -0.155, 0.341), EAR_TIP (0.104, -0.151, 0.452), bowl facing EAR_F0, half-widths
  EAR_HW, all pre-scale (the fox is scaled x1.0403 after the build). Do not move or resize the ears.
- The tufts sit inside the bowl at its inner base: they must not poke through the back of the ear or into
  the skull, and must not float off the bowl.
- Triangles: ears + tufts together <= 19k (now ~16.7k).
- The rest of the head is approved by the user; this job touches only ears.py.

## You may write
- `tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox_parts/ears.py`
- `.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/ears/` (this folder: analysis.md, log.md, renders, test scripts; never job.md)

## Test
From the repository root (renders go to your folder; one Blender job at a time, 1-2 threads; ~2-4 min):
`cd .scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts && timeout 900 blender -b --factory-startup --python harness.py -- --part ears --out e1 --views 1 2 --shots shots_ears2.json --clay --threads 2 --outdir ears/out > ears/out_e1.log 2>&1`
then `PYTHONPATH=.scratch/pydeps python3 .scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/cmp.py e1 --outdir .scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts/ears/out --box 1 0 0 1 0.35 --box 2 0.1 0 0.45 0.35`
(shots_ears2.json in the parts folder: ortho close-ups of the ears and tufts from front, side, three-quarter
and back, lit and clay with --clay). The baseline (build 5) renders are in `parts/out/b5_*`.

## Done when
- In the clay close-ups from front, side, three-quarter and back, each ear tuft reads as one soft fan of
  rounded locks: no needle tips, no gaps between lock roots, no lock standing off the bowl.
- Ear outlines and rims smooth up close in clay (no facets, no knife edge); shape and position unchanged
  (front overlap from cmp.py within 0.01 of the baseline e0/b5 run).
- Lit close-ups: the tufts cream with the root shading, the bowl's spirals unchanged.
- Triangles of ears + tufts <= 19k; no errors in the log.
