# aethel_fox — Aethel Fox (Phase 2): builder notes

Fill every section of `## Analysis` before the first build (a hook refuses the build until each
has content). After each build write `## Cycle <n>` (n = the build number the kit printed). When
your context budget is reached write the Handoff section (see the brief).

RECOVERY NOTE (cycle 4 lead): while writing Cycle 4, a scripted rewrite of this file cut it at the first
"## Handoff" string, which was inside the line above, and so dropped the original Analysis (What it is,
Views, Size and proportions, Close observation, Materials and shaders, Details and nuances, Build plan,
Skills) and Cycles 1-3. Builders here may not run git: the full text is in the repository history
(`git show HEAD:production/qa/evidence/blue_fox_evolution/aethel_fox/aethel_fox_notes.md`), to be restored by
the pipeline. What this lead had read and could restore verbatim is below: the parts inventory and Cycle 3.
The Handoff's Understanding section (kept and updated) carries the analysis of what each part is.

## Analysis

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it (technique, skill) | geometry detail (what is modelled: bevels, creases, folds, holes, relief) | nuances (imperfections, asymmetry, how each copy differs) |
|---|---|---|---|---|---|---|---|
| 1 | body (torso, neck, head, muzzle, jaw) | 1 | 0.13 x 0.40 x 0.37 | centred X 0, nose Y -0.24, rump Y 0.11 | SDF clay ellipsoids/cones blended (sculpting bx_sculpt), quad remesh ~16k quads | eye sockets, brow ridge, muzzle bridge, mouth corner crease, tuck-up belly, shoulder blades, rump | head turned 0 (symmetric) but fur locks asymmetric |
| 2 | legs and paws | 4 | leg r 0.018, paw 0.034 x 0.045 x 0.025 | front X +-0.027 Y -0.11; hind X +-0.035 Y 0.095 / 0.05 | SDF tubes through hip/stifle/hock/paw joints, part of the body clay | elbows, hock angle, wrist bump, 4 toe lobes with 3 creases per paw, flat soles | hind stride differs left/right; toe sizes vary |
| 3 | fur locks: cheek tufts, chest ruff spikes, elbow tufts, belly fringe | ~24 | cones r 0.008-0.015, 0.02-0.05 long | cheeks X +-0.07..0.09 Z 0.28; chest Y -0.19 Z 0.10-0.17; elbows; belly | SDF round cones blended into the clay | pointed tips with real relief | every lock its own length/angle (seeded) |
| 4 | ears | 2 | 0.14 long, 0.06 wide at base, 0.012 thick | base X +-0.05 Y -0.13 Z 0.335, tips X +-0.098 Z 0.46, bowls facing forward-out | lofted leaf bowl (rings of front + back surface), Subsurf 1 | bowl depth 0.015, thick rim, tip notch | ear spirals painted per side, left/right differ slightly |
| 5 | ear tufts (cream fur locks at the inner ear base) | 10 | 0.03-0.05 long, 0.01 wide | inner base of each bowl, fanning up | swept flat blades | pointed tips, thickness 2 mm | each blade own angle/length |
| 6 | eyes (eyeball: sclera, iris, pupil, cornea catch light) | 2 | opening 0.027 x 0.020, iris 0.0164 x 0.0194 (cycle 4: opening 0.033 x 0.014, iris 0.0172 x 0.0196) | X +-0.031 Z 0.327 (pre-scale), surface normal turned out 14 deg, long axis tilted 20 deg (cycle 4: 16, inner corner dropped, outer raised) | domed lens (1.6 mm) on a bed fitted to the finished body mesh (EyeBed: ray cast, never cut by the face), UV iris shader | dome, rim tucked 1.2 mm under the eyelid lines | iris toward the nose, catch light upper inner on both eyes |
| 7 | eyelids (upper and lower eyelid lines) | 2 x 2 | upper 0.9-2.9 mm wide, lower 0.5-1.5 mm (cycle 4: lower 0.4-1.2 mm, grey-navy) | upper: tear duct over the top to the outer corner and on into a rising wing; lower: whole lower edge | flat swept lines lying on the higher of eye and face (build_eyelids) | wing tapers to a point, thicker at the tear duct | — |
| 8 | nose | 1 | 0.016 x 0.012 x 0.010 | Y -0.24 Z 0.298 | small SDF clay | nostrils, philtrum line | — |
| 9 | collar cord | 1 | 3 strands r 0.0022 around a ring of 0.05 x 0.06 | ring tilted: front Z 0.19, back Z 0.29 | three helically twisted swept tubes along the neck ring, snapped onto the neck surface | strand bumps, twist | twist phase varies, slight sag at the front |
| 10 | pendant bail | 1 | 0.009 x 0.003 x 0.011 | under the cord front | swept closed loop | rounded | — |
| 11 | gem bezel | 1 | ring r 0.0165, tube 0.0025 | Z 0.173 Y -0.20, facing forward-down | swept torus + back plate | rounded rim, plate behind | — |
| 12 | gem | 1 | 0.024 diameter, 0.010 deep | in the bezel | squashed UV sphere (cabochon dome) | domed | — |
| 13 | antler branches | 2 sides x 6-7 | tubes r 0.004 -> 0.0015, 0.03-0.10 long | from the pendant up over each shoulder | swept tapered tubes along bezier paths, tips hooked | rounded tips, root blended into beam | each tine own length/curl; sides differ |
| 14 | gem scroll curls + drop | 2 + 1 | r 0.003, curl r 0.01 | beside and under the gem | swept spiral tubes | — | mirrored but varied |
| 15 | tail (a fox's brush: underfur round the tail bone + 54 guard-hair locks in 5 layers) | 1 | 0.20 x 0.19 x 0.27 + tip | root Y 0.08 Z 0.23, up and back, tip curls to Y 0.36 Z 0.33 | underfur: swept mass at 0.87 of the outline radius (TailBody path); locks: clumps laid in (arc s, angle, radius) on the fur volume, each rooted under the previous layer, widest a third along, drawn to a point, tips lifting (build_tail_fur_lock) | lock sections domed on top, flat below; tips break the outline; tip-tag locks run on past the end into the curled cream tip | every lock its own width, length, twist, sway, lift; shared painted atlas; root dark, tip light |
| 16 | tail edge locks (guard-hair locks standing out of the outline) | 7 (cycle 4: 8) | 0.03-0.04 wide, 0.25-0.32 of the tail long | 3 on the lower back edge, 3 on the top of the cream crown, 1-2 under the curled tip | same lock builder with a higher tip lift (0.08-0.2) | pointed tips | different lengths and lifts |

## Cycles

## Cycle 3
Build 3 (changes after build 2): tail tip raised (last path points (0.285, 0.370), (0.328, 0.348)), tip
radii fatter, lower plume fuller in front (rf tk 0.06 / 0.14 = 0.047 / 0.071), X widening reverted, tip
locks s1 1.00-1.045, curl 14; cream locks (fur_cream, threshold 0.45..0.75 of the atlas cream); ears tip
Z 0.458, X 0.104, 0.005 forward; eye EYE_BT/BB 0.0108/0.0084 (0.0102 read too narrow/sleepy from the front
in the debug close-up exp/b3c_eyes.png), wing rise flatter (0.13..0.43 EYE_BT), cheek cream +6 mm at
|x| > 0.036..0.056.
CV: overlap front 0.75 (was 0.72), side 0.54 (clean, fox only 0.819; build 2 0.813), back 0.76; w/h +7 %,
-6 % (clean +2.2 %), -13 %. CHECK clean (degenerate faces 16, mirror 0.0051). 117,868 tris. 0.223 x
0.613 x 0.500 m.
Matches (keep): side eye almond with the iris in the front corner and a long wing (closeup view 2 box
0 .12 .25 .38); tail made of locks with whole cream flame locks; front no longer shows the tail beside
the body as much (extra middle 26 / 23 %).
Differs, cause, fix (all go to the Handoff's part tasks):
- Back w/h -13 %: ears upright and narrow from behind (ref ears splay to the egg's width, magenta
  top-left 27 % / top-right 25 %); the cream tip still hangs down the middle of the egg as a 'beard'
  (the tip comes toward the back camera and the tip locks droop).
- Side ear: the near ear shows its thin blue back edge; the drawing shows the inner bowl (indigo with a
  cyan spiral and cream tuft) turned toward the viewer, the ear broad (base ~0.055) and tilted forward.
- Tail side: the lower plume still a column with a cuff where layer 1 starts; tip a straight cream point
  1.2 x the drawing's length, no hook and no second point under the curl.
- Side body: extra (yellow) in front of the chest and front legs, missing (magenta) behind the hind legs
  and over the head / ear: chest 0.006 too far forward, hind legs 0.01 forward, head 0.008 low (cycle 1,
  still open).
- Front: the throat / chest bib is one large cream mass bulging between the collar beams; the drawing's
  cream throat is narrower with blue sides of the neck; top-centre extra 37 % is the tail over the head
  (drawing conflict).
- Front eyes after EYE_BT 0.0108 and the flatter wing: not judged in a close-up yet (kit front render too
  small; use close.py shot [0,-8,0,-0.205,0.345,0.12] on a debug blend).

## Cycle 4
Lead cycle (no Agent tool in this session, so no Sonnet part builders could be spawned: the lead ran the
four part tasks itself as parallel background Blender jobs, 3-4 at a time, judged against the crops).
Set-up done this cycle: generator split into part modules (builder_guide.md section 8 step 1):
tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox_parts/{common,body,ears,face,collar,tail}.py, the
main aethel_fox.py imports them and only builds and joins. Every tuned value is a module constant (face.EYE_*,
LID_*, SCLERA; tail.TAIL_RB/RF/RU, TAIL_FLAMES, TAIL_LOCK_CREAM, TAIL_EXTRA_LOCKS ...; ears.EAR_*; body.THROAT_WC,
CREAM_NOISE) so a harness can try variants with --set. Part harness (copy kept in the evidence folder:
part_tools/harness.py, cmp.py, eyepts.py, shots*.json, reference crops t_*.png): `--base` saves the full build
as parts/base.blend; `--part face|ears|tail|full --out NAME [--views ..] [--shots ..] [--set mod.CONST=value ..]`
rebuilds one part on it, rescales, joins as the kit does and renders the kit views (kit camera, 16 samples)
and ortho close-up shots; cmp.py NAME gives fox-only overlaps (the side box's small back-view fox blanked)
and ref | render | overlay close-ups; eyepts.py measures eye outlines. Baseline check: harness on build 3 gave
front 0.749 / side 0.816 / back 0.765, the kit's own numbers (0.75, clean 0.819, 0.76).
Build 4 changes:
- Eyes (12 variants, e1-e3, f1-f3, g1-g3, h1-h3; sheets cycle4/eyes_cmp1.png, eyes_cmp4.png): EYE_A 0.0135 ->
  0.0165, EYE_BT/BB 0.0108/0.0084 -> 0.0076/0.0066, tilt 20 -> 16, top boost 0.9 -> 0.72, inner corner drop
  0.0026 -> 0.005 (the tear duct is the eye's lowest point in both drawings), outer corner lift 0.0008 -> 0.003,
  iris (-0.0042, 0) r (0.0086, 0.0098), lower eyelid thinner (0.0002 + ...) in its own grey-navy material
  M_eyelid_lower #4b5068, sclera ramp cool grey (side sample #cdc9c8 vs drawing #cac6c7), tear-duct warmth 0.2.
  The clay eye seat follows the longer eye (0.016 x 0.0085).
  Why: the build's eye was a tall round "D" (front 134 x 132 px, side 237 x 190 px vs drawing 166 x 117 and
  315 x 153 in the same 0.12 / 0.075 m boxes) with the inner corner high and the lower lid sagging below it:
  that read "worried". Peaking the top line (EYE_PEAK 0.5) made it worse (apex in the middle); dropping the
  inner corner fixed it. Result (cycle4/p1_eyes.png): front 164 x 111 px (ref 166 x 117), side 301 x 178
  (ref 315 x 153: still 16 % tall), iris in the front corner, long rising wing.
- Brow markings: they had vanished (the shader drew them in Object coordinates, which the kit shifts when it
  sets the origin, pushing the 6 mm-deep oval off the head). Now drawn from the pre-scale position attributes
  (pxf, pys, pzs) and set unscaled: both ovals show again (front and side close-ups).
- Tail (t1-t5; cycle4/b3_close_2_0.45_0.png -> k4_close_2_0.45_0.png): root narrower (rb/rf tk 0.06-0.14), the
  curl's underside fuller (rb tk 0.58-0.95: fills the drawing's lower tip), tip narrower across (ru), one more
  edge lock under the tip (0.80-0.97, a0 1.35), lock lift 0.003-0.010, widths x1.12; atlas cream flames 11
  narrower strokes (0.016-0.026), a lock turns cream only past 0.62 atlas cream. Side cream share (top 3/4 of
  the tail close-up): drawing 0.45, build 3 0.52, t5 (flames 0.013-0.022) 0.37, build 4 0.49.
  Fox-only side overlap 0.816 -> 0.830.
- Ears: tip 6 mm lower and 5 mm back (side ear tips were ~0.02 above the drawing's), bowl turned out (f0 x 0.45
  -> 0.62), base broader (0.044 / 0.033), inner tan lighter, spirals bigger (0.013 / 0.012, band 0.005). Splay
  tested: tip X 0.118 -> back w/h -0.126 -> -0.017 but front overlap -0.04 and front w/h +0.21; X 0.110 -> front
  w/h +0.13. Kept X 0.104: the ear tips set the front view's width (front w/h already +8 %), drawing conflict.
- Body: throat cream half-width 0.06 -> 0.05 (0.034 cut the chest bib too narrow under the collar: reverted
  to 0.044-0.046 there), fine cream-edge noise 0.0012 -> 0.0004 (the cheek line under the eyes was ragged).
CV build 4: overlap front 0.74 (b3 0.75), side 0.55 (fox only 0.830, b3 0.816), back 0.76 (0.76); w/h +8 %,
-6 % (fox only +2.2 %), -12 %. CHECK clean (16 degenerate faces, mirror 0.0051). 116,574 tris. 0.223 x 0.613 x
0.500 m.
Matches (keep): eye shape and size front and side, lower inner corner, thin grey lower lid, cool sclera, brow
ovals; tail outline in the side view (the lower tip filled), more blue in the tail with cream flame locks.
Differs (go to the Handoff): side eye still 16 % tall (top line peaks at the back third, the drawing's is a
smooth rising arc); back-view cream 'beard' (the curled tip comes at the back camera: the side and back drawings
conflict); tail interior reads as many separate white streaks with dark gaps, the drawing as broad smooth
painted locks; far ear edge-on in the side view (drawing: broad); near ear inner tan, the side drawing shows it
indigo with a cyan spiral (front drawing tan with blue spirals: conflict); front: head small and high over a big
cream throat ball, cheek tufts wide (front extra middle-left 26 % / middle-right 24 %), nose a two-lobed blob
(drawing: smooth rounded triangle).

## Cycle 5
Rebuild only, no generator change: build 5 is the committed generator (cycle 4's part modules with the head
passes q1-q4: smiling mouth, tapered jaw, wider wedge snout, triangular nose) run through the kit after the
cluster finish. The user approved the model on the q4 renders ("Model approved").
CV build 5: overlap front 0.74, side 0.55, back 0.75; w/h +8 %, -6 %, -12 %. CHECK clean (16 degenerate
faces, mirror 0.005).

## Handoff
State: build 4 is the last kit build (CV, compare, renders in the evidence folder); the generator
(aethel_fox.py + aethel_fox_parts/) is exactly what build 4 built. Cycles 1-4 in the notes hold the details.

### 1. Understanding
- What it is: Aethel Fox, phase-2 evolution of a stylised blue fox (anime / painted game art: soft
  cel shading, thin navy ink outlines, painted fur strokes). A slim young fox standing square on long
  legs, head up, front -Y, 0.50 m to the tail top. Alive, groomed, nothing worn or dirty; variation
  comes from fur strokes, soft shadows, glowing markings.
- How it is made (as a creature): one furred body over a skeleton (skull, neck, ribcage, pelvis, four
  legs with paws and toes); fur short and smooth on the body (painted strokes; locks only at the cheek
  tufts, chest ruff, elbow tufts, belly fringe); long fur only on the tail.
- The eye: an eyeball (warm grey-white sclera, big grey iris with a dark limbal ring, a pupil, a
  glossy cornea whose reflection is one white catch light) in a socket, wrapped by eyelids; the tear
  duct in the low inner corner. The drawing's eye OPENING faces ~40 deg outward (front 60x53 px, side
  59x41 px: cos(62-phi)/cos(phi) = 1.27 -> phi ~42) while the EYEBALL looks forward (iris round from
  the front, squashed and in the front corner from the side): so the opening is long (intrinsic W/H
  ~2.3 since cycle 4) and its outer half wraps back around the side of the head, the iris painted toward
  the nose. The tear duct (inner corner) is the eye's LOWEST point in both drawings and the outer corner is
  high: an inner corner above the lower lid's sag reads "worried" (cycle 4 finding).
  Built as a domed lens lying on the finished body mesh (EyeBed: ray casts, quadratic fit, never more
  than 1 mm over the face), eyelid lines as flat swept lines on top, iris from the lens UVs.
- The tail: a fox's brush: underfur round a thin bone, long guard hairs clumped into locks that
  overlap like shingles root to tip, tips lighter, outline made of lock tips, cream tag at the end.
  Painted style: broad S-flowing locks, cream flame locks curling at their ends, glowing cyan swirls and
  dots on the lower third. Built as tail_underfur + ~60 mesh locks in 5 layers + 7 edge locks; cream
  flames are whole cream locks (fur_cream sampled from the atlas). User: "The tail is fur."
- The ear: a tall thin cartilage leaf, furred outside (blue, darker rim), inside an indigo bowl with
  a cyan/cream spiral painted on and cream fur tufts at its base; it stands from the skull and turns
  its bowl forward-outward.
- Collar (unchanged): braided brown leather cord (three twisted strands), silver bail and bezel,
  deep-blue cabochon gem, silver-white antler branches over both shoulders.

### Part inventory (names by what each thing is)
Code: tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox.py builds and joins; one module per part in
aethel_fox_parts/: common.py (helpers, EYE_X, dark_material), body.py (clay, marking images, fur shaders, brow
marking, cream_field, body_attributes), face.py (eyes, eyelids, nose), ears.py, collar.py (cord, pendant,
antlers), tail.py.
body (torso, neck, head, muzzle, stop between the eyes, legs, paws with toes, cheek tufts, chest
ruff, elbow tufts, belly fringe: SDF clay -> quad remesh 16,500); ears + ear tufts (5 cream locks per
ear); eyes (eye_left / eye_right); eyelids (eyelid_upper_* / eyelid_lower_*); brow markings (shader,
3D oval per side); nose; cord (3 strands); bail; bezel + plate; gem; antlers (beam, tines, scroll
curls, drop); tail (tail_underfur + tail_fur_lock_00..56). Triangles (build 3, 117,868 of 120,000; build 4 116,574, split about the same):
body 34.8k, ears 14.6k + tufts 2.1k, eyes 2.1k, eyelids 2.0k, nose 2.7k, cord 11.5k, pendant 5.1k,
antlers 11.5k, tail 31.4k. Full table: Analysis, "Parts inventory".


### 2. Comparison (build 4)
CV overlap front 0.74, side 0.55 (kit box holds the small back-view fox; fox only, part_tools/cmp.py: 0.830),
back 0.76; w/h +8 %, -6 % (fox only +2.2 %), -12 %. CHECK clean (16 degenerate faces, mirror 0.0051). 116,574
tris. 0.223 x 0.613 x 0.500 m. Close-ups: evidence cycle4/ (k4_close_<view>_<box>.png = reference | build 4 |
overlay, fox-only normalisation; p1_eyes.png = eye crops beside the eye shots).
- Eyes (cycle4/p1_eyes.png; part_tools/eyepts.py, 600 px frames of the 0.12 m front / 0.075 m side boxes):
  front 164 x 111 px vs drawing 166 x 117, inner corner the lowest point, outer corner high, thin grey-navy
  lower lid, cool grey sclera: reads as the drawing's almond. Side 301 x 178 vs 315 x 153: 16 % tall, the top
  line rises to a peak over the back third and then drops into the wing; the drawing's top line is one smooth
  arc rising from the tear duct into the wing. Front: the whole eye sits ~12 px (2.4 mm) high in the 0.12 m
  frame. The iris could be a little larger in front (drawing ~65 px wide of 600, build ~55).
- Brow ovals: visible again in both views (were missing since the kit's origin shift moved them off the head);
  side: the build's oval sits higher and more upright than the drawing's (drawing: low over the eye's front
  half, tilted with the head's slope).
- Tail, side (k4_close_2_0.45_0.png): outline within a few px all round, lower tip filled; cream share 0.49
  vs 0.45. Still differs: the interior reads as many separate white streaks with dark gaps between locks; the
  drawing's locks are broad, smooth and few, the cream flames broad S-bands with curled ends inside blue; root
  junction with the rump: small extra in front (bottom-left 8 %).
- Tail, back (k4_close_3_0.05_0.1.png): the curled cream tip comes straight at the back camera and shows as a
  cream 'beard' down to the egg's middle (back view: render lighter top-centre +0.18, centre +0.13); the back
  drawing shows a cream cap on the top third only. Geometry says the side drawing's tip (half-way up the plume,
  pointing back) must show there from behind: side vs back drawing conflict; the side view wins.
- Ears: side tips now at the drawing's height (k4_close_2_0_0.png); the far ear is still seen edge-on (thin
  blade, drawing: a broad blue leaf, magenta left of it); the near ear's bowl is tan with dark-blue spirals,
  the side drawing shows it indigo with a cyan spiral (the front drawing shows tan with blue spirals:
  conflict). Back w/h -12 %: the back drawing's ears splay wider, the front drawing's narrower (conflict;
  tests in Cycle 4).
- Front (k4_close_1_0_0.png, k4_close_1_0_0.35.png): the head is small and sits high above a large cream throat
  ball between the collar and the chin (el -8 sees under the jaw); the drawing's head is large, the chin right
  above the collar; cheek tufts flare wide (extra middle-left 26 %, middle-right 24 %); the nose is a two-lobed
  blob (drawing: a smooth rounded inverted triangle with a highlight on top); the top-centre extra 40 % is the
  tail over the head (drawing conflict).
- Side body (k4_close_2_0_0.3.png): neck / chest front a little forward, hind paws a little forward, as cycle 3.

### 3. Next step: part tasks (one lead + part builders; copy each into a job card)
Set-up for the next lead: the split is done. Rebuild the harness first (R = /home/user/asset-pipeline,
P = $R/.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts): `mkdir -p $P && cp
$R/production/qa/evidence/blue_fox_evolution/aethel_fox/part_tools/*.py
$R/production/qa/evidence/blue_fox_evolution/aethel_fox/part_tools/*.json $P/ && cd $P && timeout 1200 blender -b
--factory-startup --python harness.py -- --base` (40 s), then per part: `timeout 900 blender -b --factory-startup --python harness.py --
--part face --out NAME --views --shots shots.json --threads 1 [--set face.EYE_BT=0.007 ...]` (face: shots only,
~3 min at 1 thread), `--part tail --out NAME --views 2 3` (~70 s), `--part ears --out NAME --views 1 2 3 --shots
shots_ears.json`, `--part full --out NAME --shots shots_all.json --clay --threads 4` (body changes: rebuilds
everything); then `PYTHONPATH=.scratch/pydeps python3 <parts>/cmp.py NAME --box V X0 Y0 X1 Y1 ...` from the repo
root (outputs in parts/out/NAME_*). Run 3 jobs at 1 thread side by side. If an Agent tool exists, give each
task below to a Sonnet part builder with a job card; this session had none.

TASK A. Part: eyes (face.py) - finish the side shape, then the nose.
- What it is: see Understanding (the eye; the tear duct is the lowest point).
- Comparison: section 2 "Eyes", "Brow ovals"; Front nose.
- What needs doing, and why: (1) side eye 16 % tall with a peaked top: make the upper eyelid one smooth arc
  that rises from the tear duct into the wing: lower EYE_TOPK 0.72 -> ~0.5 and move its maximum outward
  (replace the (1 - c*c) factor of the boost in eye_opening by a bump centred near c 0.5 that stays > 0 at c 1),
  keep front 164 x 111 (+-10 % of 166 x 117); check with eyepts.py (side target 315 x 153, top y ~230 in the
  600 px frame). (2) Eye 2.4 mm high in front: lower the eye centre Z 0.327 -> ~0.325 (eye_frame and the clay eye
  seat in body.py together) only if the side view agrees (side top 200 vs 230 px says yes). (3) Iris a little
  larger in front (IRIS_R x ~1.08). (4) Nose (build_nose): a smooth rounded inverted triangle, wider at the top
  (front 0.018 wide x 0.010), no visible nostril lobes from the front, dark brown-grey #3a2e30 with a lighter top.
  (5) Brow oval (brow_frame in body.py): lower and tilted with the head's slope in the side view.
- Reference crops: part_tools/t_front_eyes.png (ref_view_1 box 127 291 389 553 = 0.12 m, shot eyes_front),
  part_tools/t_side_eye.png (ref_view_2 box 80 355 243 518 = 0.075 m, shot eye_side).
- Keep fitting: EYE_X 0.0278; eyes on the FINISHED body mesh (EyeBed); lens <= 1 mm over the face; eyelid lines
  on top of the eye's edge; budget eyes + eyelids <= 5k tris.
- Done when: side 315 x 153 +-10 %, front 166 x 117 +-10 %, top line without a peak, nose reads as the drawing.

TASK B. Part: tail (tail.py) - read as the drawing's broad painted locks.
- What it is: see Understanding (the tail). The tail is fur: never a shell.
- Comparison: section 2 "Tail, side / back".
- What needs doing, and why: (1) fewer, broader, flatter guard-hair locks so the surface reads as a few big
  smooth locks (the drawing has ~8-10 visible per side): layer counts 12/13/12/10/4 -> ~8/9/8/7/4, widths x1.4,
  rho closer to the underfur (TAIL_ROOT_RHO 0.90 -> 0.94, tip lift small) so no dark gaps; the underfur's colour
  the same blue as the locks (no dark crevices). (2) Cream flames as broad S-bands with curled ends lying inside
  blue (TAIL_FLAMES count/width; the lock-cream rule turns whole locks cream past 0.62 atlas cream: keep cream
  share 0.42-0.47 measured as in Cycle 4). (3) Back view: reduce the beard with narrower tip locks across X
  (layers 3-4 widths) - accept what the side view's tip forces. (4) Root junction: the small extra in front of
  the root (rf tk 0-0.06).
- Reference crops: part_tools/t_side_tail.png; cmp.py boxes view 2 .45 0 1 .6, view 3 .05 .1 .95 .75.
- Keep fitting: root (0, 0.110, 0.199) pre-scale; tail top 0.4806 pre-scale (keep 0.48-0.485 or the fox
  rescales); X width (TAIL_RU) as build 4; budget 31-33k tris; fox-only side overlap >= 0.83.
- Done when: side close-up reads as broad smooth locks with cream flames (no dark gaps), cream 0.42-0.47, side
  overlap >= 0.83, back cream area smaller than build 4.

TASK C. Part: ears (ears.py).
- What it is: see Understanding (the ear).
- What needs doing, and why: (1) the far ear seen edge-on in the side view: the side drawing shows it as a
  broad leaf; give the ears a slight twist along their length (the bowl normal turning outward toward the tip)
  so from az 62 the far ear's back shows broadly, without changing the front outline. (2) Inner bowl colour:
  front drawing tan with two broad blue spirals and a dark-blue rim, side drawing indigo with a cyan spiral:
  make the indigo zone cover the bowl's outer half and upper third (the part the side view sees) with a cyan
  glow spiral there, the tan + blue spirals on the inner half (the part the front sees); the bowl renders dark
  (#747479 vs drawing #c6b7ae in front box .08 .1 .12 .2): reduce the bowl depth D 0.027 -> ~0.02 or brighten.
- Keep fitting: ear base (+-0.044, -0.155, 0.341), tips EAR_TIP (0.104, -0.151, 0.452) (X: front vs back
  conflict, Cycle 4), ~16.7k tris. Done when: side shows a broad far ear and the near bowl indigo with a spiral;
  front overlap >= 0.74.

TASK D (lead). Part: body - the front view's head and throat.
- What needs doing, and why: in the front view the head is small and high above a big cream throat ball; the
  drawing's head is large with the chin just above the collar: shorten the neck (neck tube in body_clay) /
  lower the head ~0.01 and scale the cranium + cheeks ~1.08 about the head centre; shrink the cheek tufts' X
  reach (cheek list in body_clay: x 0.083 -> ~0.072) (front extra middle-left / right 26 / 24 %). Re-check the
  eye bed (EyeBed follows the finished mesh), the brow oval (brow_frame), the ear base and the collar ring
  (cord_ring follows the clay) after any head move. Side: chest 0.006 back, hind paws 0.01 back (cycle 1).
- Done when: front overlap >= 0.78, fox-only side >= 0.84, no regression in Tasks A-C.

### 4. Do not undo
Overall stance and leg layout; navy lower legs; cream throat / chest V / muzzle; braided cord, pendant (bail,
bezel, gem), antlers over the shoulders; flank glow markings; tan patch; the eye built on the finished body
mesh (EyeBed), lens <= 1 mm over the face, eyelid lines on top of the eye's edge, EYE_X 0.0278, iris toward the
nose, the long rising wing, the stop between the eyes; cycle 4's eye shape (EYE_A 0.0165, BT/BB 0.0076/0.0066,
tilt 16, inner corner drop 0.005, outer lift 0.003, thin grey-navy lower lid, cool sclera); the brow marking
read from the pre-scale position attributes (never Object coordinates: the kit moves the origin); the tail as
underfur + guard-hair locks (not a shell) with whole cream flame locks, cycle 4's tail radii (root narrower,
curl underside fuller); tail X width; the 120k budget split; the part-module split.

### 5. Files
- Reference views: production/qa/evidence/blue_fox_evolution/aethel_fox/aethel_fox_ref_view_{1,2,3}.png
- Latest kit compare (build 4): .../aethel_fox_compare.png; renders aethel_fox_view_*.png, clay_*.png
- Cycle 4 close-ups: .../cycle4/ (k4_close_*.png ref | build 4 | overlay; p1_eyes.png; eyes_cmp1/4.png eye
  variant sheets; b3_close_2_0.45_0.png = build 3 tail for comparison)
- Part tools (persist; the work folder is deleted after a run): .../part_tools/ harness.py, cmp.py, eyepts.py,
  shots.json (eyes), shots_ears.json, shots_all.json, reference crops t_front_eyes.png, t_side_eye.png,
  t_side_tail.png. PYTHONPATH=.scratch/pydeps for cv2.
- Generator: tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox.py + aethel_fox_parts/*.py

### 6. Standing rules
- builder_guide.md (/tmp/claude-0/-home-user-asset-pipeline/2396fed5-5999-5364-b5d1-d9749bebc958/scratchpad/builder_guide.md)
  and blender_tools_guide.md (same folder) are the method; read both first.
- User's wishes: "Both eyes are bad. Fix the eyes." (first priority until they match the drawings).
- The tail is fur.
- Think about what you see and build that (builder_guide.md section 1).
- Understand the thing you are making, conceptually (an eye, wood, a body, a tree root), and let
  that choose the approach (builder_guide.md section 1).
- Name every part by what it is, never by its shape or look (builder_guide.md section 2).
- Multitask: Blender builds and renders in the background while you keep working; independent steps
  together (blender_tools_guide.md section 6).
- Use all the cores (user): while the 1-minute load in /proc/loadavg is below nproc, start another
  background Blender job instead of waiting: one process per view or close-up angle, parameter variants
  side by side, the next part's test while the full build runs; timeout on every run, do not push the
  load far above nproc, never let two jobs write the same file (blender_tools_guide.md section 6).
- Builds render as the kit renders them (user): all views, lit and clay, the kit's own samples and
  resolution, the bake where planned; look at the full compare (cv.py compare) after every build.
- Compare to the reference often, part by part, after every change, not only at the end of the
  cycle (builder_guide.md section 6).
- The user doubled the triangle budget to 120,000: spend it on details (body and paws with toes,
  tail locks, ears, antler scrolls, braided cord, eyes, gem).
- Work in one render cycle per run when the user asks; end with a Handoff as builder_guide.md
  section 7 describes.
- User (cycle 4): "Focus on the mouth and head and jaw shape". The head, jaw and mouth are the priority:
  judge them from the front, side and three-quarter views against the reference crops, with close-ups of
  each in the Handoff.
- User (cycle 4): "Improve the cv. Instead of only looking at the shape, let conceptual understanding lead
  you more." Let conceptual understanding lead every comparison, not the silhouette numbers: (1) start from
  what each part is: for every inventory part ask first whether it reads as that thing, the way it looks in
  life and in this art style, from every view and up close; (2) then check the features its nature implies:
  its inner structure (one surface, or many elements, and how they flow, clump and end), how it attaches,
  what its material does with light (gloss, wetness, translucency, glow), how it ages; (3) measure those
  features in the reference and the build (crops, cv.py sample and closeup); (4) treat the overlap and aspect
  numbers of cv.py compare as a coarse check of the outline only, never the target: a change that raises
  overlap but makes a part read less as what it is goes the wrong way; (5) in the review and the Handoff,
  rank what needs improving by how much it hurts what each part is, not by pixel area.
- User (cycle 4): "Snout too narrow. Make more fox shaped snout". A fox snout is a wedge: broad where it
  meets the cheeks and the eyes, tapering evenly to a small, pointed, triangular nose; in profile the bridge
  runs fairly straight from just below the eyes to the nose tip; the muzzle is deep at its base with the lower
  jaw and chin following under it; from the front the cream muzzle area is wide and blends into the cheeks.
  It must never look like a thin tube stuck onto a round head. Keep the smiling mouth line and the chin.
  Check front, three-quarter and profile against the reference crops; close-ups in the Handoff.
- User (sister object, cycle 4): "remove edge mistake due to using downscaled image". Check every colour
  boundary close up for pixel stair-steps (blue to cream on the face, muzzle, cheeks, chest and legs; the ear
  markings; the forehead and brow marks; the body and tail swirls; the glowing lines). Build colour
  boundaries from the full-resolution source image, or from smooth vector curves and masks, never from a
  downscaled crop.
- User (cycle 4): references stay at original image quality. Build outlines, colour boundaries and
  textures only from the source image or its native-resolution cut-outs (a cut-out is fine, a resized one
  isn't). Never use a mask, compare sheet or downscaled image made for the quick check. Check whether the
  tail path (fitted to outline rows in the kit camera's normalised frame) and any other outline, mask or
  colour boundary came from such an image; if so, rebuild it from the source.
- The tail stays fur (the rule above). The smooth-plume tail tests of cycle 4 (pl1, pl2, plume_cmp*.png)
  came from an orchestrator's own reading of the drawing, not from the user: do not continue them.
- Lead and part builders (user): the builder that reads this Handoff leads; it runs 2-4 part builders
  on Sonnet 5.5 at once (builder_guide.md section 8).
