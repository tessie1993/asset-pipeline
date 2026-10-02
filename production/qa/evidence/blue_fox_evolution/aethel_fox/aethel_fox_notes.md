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

(Cycle 6 lead: the original Analysis was lost in cycle 4 (recovery note above). These sections are rewritten
from the reference views at full resolution and the Handoff's Understanding; the parts inventory follows.)

### What it is
Aethel Fox, the phase-2 evolution of a stylised blue fox: a slim young fox standing square on long thin legs,
head up, facing -Y, 0.50 m to the top of its tail. Anime / painted game art: soft cel shading, thin navy ink
outlines, clean smooth forms with painted fur strokes. One furred body over a skeleton (skull, neck, ribcage,
pelvis, four legs with paws and toes), very tall ears with painted spiral bowls and cream ear tufts, a
braided leather cord collar with a blue cabochon gem in a silver bezel and silver-white antler branches over
the shoulders, glowing cyan spiral markings, and one huge fur plume tail curling up over the back into a cream
tip. Alive and groomed: nothing worn or dirty.

### Views
Three reference views cut from the sheet (design/asset-packs/blue_fox_evolution/source.jpg, 4096 px):
view 1 front (az 0, el -8; 515 x 1180 px), view 2 three-quarter side (az 62, el 6; 1318 x 1175 px, with a small
back-view fox at its lower right), view 3 back (az 180, el 20; 340 x 695 px). The side view is the main one;
the front decides the face, chest bib and ears; the back the tail's egg shape and the ear splay. Side and
back disagree about the cream tip (side wins), front and back about ear splay.

### Size and proportions
Total height 0.50 m (tail top); body 0.223 x 0.613 x 0.50 m. Pre-scale frame (x1.04 after the build): chest
front Y -0.19, rump Y 0.115, back line Z 0.245, chest bottom Z 0.13, legs ~0.20 m long (radius 0.013-0.018),
head: nose Y -0.24 Z 0.30, eye Z 0.327, crown Z 0.39; ears 0.14 long to tips (0.104, -0.151, 0.452); tail root
(0, 0.110, 0.199), tail top 0.4806. Head about 1/4 of the height to the ear tips; legs as long as the torso is
deep.

### Close observation
Every outline in the drawing is one clean smooth curve with a thin navy line: the body is smooth; fur shows as
a few painted strokes and soft points only where the drawing draws them (two-point cheek ruff, a few fine
strokes at the bib edge and elbow). The cream bib is a painted region: from the jaw down the throat and chest
to a soft V point between the front legs, its edge a smooth curve. The belly is cream underneath, the inner
thighs tan, a tan patch under the tail. The eye is a long almond (tear duct lowest, outer corner high, long
rising wing), iris grey with a dark ring and a white catch light. The tail is a plume of broad flowing locks
painted with cream S-shaped flames ending in curls, glowing cyan swirls and dots on its lower third, a cream
tip curling up at its end; the outline is smooth with a few flame points at the lower back edge and the crown.
User (after approval, cycle 6): the reference is low quality and was copied too literally: build intent, not
pixels.

### Materials and shaders
Fur: painted stylised fur (Principled, roughness 0.74-0.86, fur-stroke noise in colour, roughness and bump),
blue from navy lower legs (#3c4f76) to light head (#a3cfe3), cream #c6bcb3-#dcd2c5, tan #8f8079; glowing cyan
markings (emission #3fb8dc-#a8f0ff). Ears: blue outer with darker rim, inner tan with blue spirals and an
indigo zone with a cyan glow. Eyes: sclera, grey iris, pupil, glossy cornea. Nose dark brown-grey. Cord: brown
braided leather. Silver: bezel, bail, antlers (pale silver-white, polished). Gem: deep blue cabochon with
transmission look. Tail: painted atlas on every lock, root slightly deeper blue, tips lighter.

### Details and nuances
Toes: four per paw with creases. Fur strokes in the shader. Glowing markings differ left and right. Antler
tines each different, rounded polished tips. Tail locks each their own width, length, twist; cream flames each
their own curl. Ear tufts: 5 cream locks per ear, each a little different. No dirt or wear.

### Skills, add-ons and tools
scenario-blender-sculpting (bx_sculpt signed-distance Clay for the body), kit.quad_remesh (Instant Meshes),
kit.mark (cream regions cut on smooth fields), swept tubes (common.sweep) for cord, antlers, ear tufts,
lofted meshes for ears, eye lens and tail locks, painted images (poly_paint) for markings and the tail atlas,
cv.py compare / closeup and the part harness (part_tools/) for checks.

### Build plan
Body clay (torso, neck, head, legs, paws) -> quad remesh -> surface relax (cycle 6) -> cream marking ->
attributes; ears, eyes on the finished mesh (EyeBed), eyelids, nose, mouth; collar (cord, pendant, antlers);
tail (underfur + layered guard-hair locks + painted atlas); scale to 0.50 m. Cycle 6: smoothing pass on every
part (user request), then the kit build, compare, review, Handoff.

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

## Cycle 6
Lead cycle for the user's request after approval: "Smoothen model. Rough outer edges caused by low quality
reference and too literal copy", plus "Remove spikes in belly" and "Don't use masks" (relayed by the
coordinator). No Agent tool in this session (as in cycle 4), so no Sonnet part builders could be spawned: the
lead ran the three part tasks (body, tail, ears + antler tips) itself as parallel background harness jobs and
judged each against full-resolution reference crops (part_tools/r_*.png). The ears job card was written
(part_tools/job_ears_cycle6.md) before the missing Agent tool was found.
Set-up: the notes' Analysis sections (lost in cycle 4) were rewritten so the build gate passes; harness fixed
(it recovered the 0.50 m scale as 1.0 from the brow node, so a rebuilt part was scaled wrongly; now from the
body's pys attribute) and given --outdir; new shot lists shots_smooth.json (front, side, 3/4, back, back 3/4,
low chest, belly side, chest front, head front / side / 3/4, tail side / back / top, legs), shots_tail2.json,
shots_ears2.json.
Root causes found (build 5 clay close-ups, cycle6/ba_*.png left halves):
- Chest, belly, elbows: 14 needle cones in the body clay (5 chest spikes to Z 0.104, 2 x 3 chest-side ruff locks,
  2 x 2 belly fringe locks, 2 elbow tufts; tip radius 1.0-1.2 mm, blend 6 mm): a literal copy of the drawing's
  painted fur flicks; the cream marking covered the spikes, so the bib's lower edge read torn.
- Cheeks: 4 thin cones per side (r 0.010-0.012 -> 0.0012) with jittered tips: a blocky, torn cheek ruff.
- Surfaces: no smoothing after the 16.5k-quad remesh; leg segments unioned with a hard min (crease at every joint).
- Cream boundaries: linear interpolation through knots (a corner at each knot) and hard max/min corners.
- Tail: the path was a 12-knot Catmull-Rom fitted to the side view's silhouette rows (a mask: wobble at Z
  0.32-0.39 and a kink over the curl); 61 narrow locks (10-13 per layer) at rho 0.90 over an underfur at 0.92
  shaded dark (fur_t 0.12, root ramp x0.62, AO to 50 %), lock side edges standing as shelves above the underfur,
  edge locks lifted 0.08-0.22: dark slits, shelves and ragged blades.
- Ear tufts: 5 flat blades 1.6 mm thick with needle tips, spread apart: a crown of spikes.
- Antler tines and pendant drops: radius to 0 at the tip: needles.
Build 6 changes:
- body.py: the 14 spike cones removed; cheek ruff = 2 soft round cones per side (CHEEK_FUR, tips r 4-4.5 mm,
  blend 10 mm); a brisket ellipsoid (0, -0.140, 0.133) r (0.024, 0.021, 0.030) so the chest runs down smoothly
  between the front legs and the cream bib reaches its V low; leg segments blended (LEG_JOINT_BLEND 0.004);
  relax_surface: Taubin smoothing (10 passes, lambda 0.50 / mu -0.53) after the remesh, weighted 0 on the
  approved face (Y < -0.165..-0.185, Z > 0.268..0.282) and on the toes; cream_field rebuilt from smooth
  profiles (Gaussian-smoothed knot curves HEAD_ZB, CHEST_YB, CHEST_WC, BELLY_ZT) with smooth max / min corners
  (CREAM_ROUND 6 mm), no edge noise.
- tail.py: centre line = clamped cubic B-spline with 7 control points (TAIL_CTRL), resampled at even arc
  length; radius profiles smoothed sigma 9 samples (was 4); locks 8/9/8/7/4 per layer (was 12/13/12/10/4),
  0.064-0.104 wide, rho 0.95 + 0.05 t, side edges sunk 0.07 of the radius into the underfur (half at the tip),
  lift 0-0.004, hook halved; underfur at 0.97 and shaded like the locks (fur_t 0.55); root darkening x0.86
  (was 0.62), lock edge darkening 0.94 (0.82), AO darkening to 25 % toward #5a6c98; edge locks 5 with lift
  0.04-0.06 (were 7 with 0.08-0.20). Tail top 0.4803 pre-scale (scale x1.0411, was x1.0403).
- ears.py: ear tufts = a soft fan of 5 domed cream locks per ear (root half-width 8.8 mm, half-thickness 2.4 mm,
  rounded points, 20 x 12 sections), roots close together and overlapping, each path laid on the bowl surface
  (bowl_point) with a 1-4 mm lift, inner locks leaning toward the skull, outer ones up the ear.
- collar.py: antler tines, scroll curls and the two pendant drops end in rounded domes (radius 1.6-2.1 mm), the
  drops 6 mm shorter.
CV build 6: overlap front 0.75 (b5 0.74), side 0.54 (0.55), back 0.76 (0.75); w/h +8 %, -6 %, -12 % (as b5).
CHECK clean (16 degenerate faces, mirror 0.0051). 115,018 tris (b5 118,660). 0.223 x 0.612 x 0.500 m.
Matches (keep), judged in clay and lit, cycle6/ba_<shot>.png (build 5 clay | cycle 6 clay | build 5 lit | cycle 6
lit) and k6_close_<part>.png (reference | build 6):
- Chest and belly (ba_chest_low, ba_belly_side, ba_chest_front, ba_full_34, k6_close_chest_belly): one smooth
  continuous surface from the throat over the brisket to the belly, no spikes; the cream bib edge a clean
  curve ending in a rounded V between the front legs; the belly cream line one smooth curve rising to the
  stifle, as in the side drawing.
- Head (ba_head_front, ba_head_side, ba_head_34, k6_close_head): face identical to build 5 (eyes, wedge snout,
  triangular nose, smiling mouth held by the relax weight); the cheek ruff is a smooth flare with two soft
  points (front drawing: the same two-point flare).
- Ears: tufts read as a soft fan of rounded cream locks in the bowl (side drawing: 4 locks fanning up).
- Tail (ba_tail_side, ba_full_side, k6_close_tail): the clay plume is one smooth, continuous form made of broad
  flowing locks; no dark slits, no shelves; outline smooth with soft flame points.
- Legs and paws: smooth joints, no creases (clay_2).
Differs (measured, with why):
1. Tail cream pattern (k6_close_tail, ba_tail_back): the cream reads as jagged blotches and torn patches across
   the locks (back view: cream area x2.38 of the drawing's, top-centre +0.21 lighter); the drawing paints 5-6
   broad smooth S-bands with curled ends inside blue and a smooth cream cap. Why: the atlas cream crest
   (TAIL_CREAM_W zone) has a deliberately jagged threshold (two sines, 0.14 / 0.06), the flame strokes are
   narrow, and TAIL_LOCK_CREAM turns whole locks cream past 0.62 atlas cream, so cream jumps lock by lock.
2. Tail outline, side (compare overlay view 2): the drawing's plume is an S (narrow root, concave front
   edge low, the widest part high and back); the build is an egg, extra yellow in front of the lower plume and
   magenta behind the top (side overlap 0.54, top-right extra 19 %). Why: radii profiles were fitted to
   mask rows; the path's lower half sits forward.
3. Tail tip end (ba_tail_side): the last cm of the cream tip ends in 3-4 small ragged points (tip locks past
   s 1.0 spread around the centre line); the drawing's tip is one clean curling point.
4. Back view: the cream tip still comes at the camera as a 'beard' (side vs back drawing conflict, cycle 4).
5. Cheek ruff, side clay: a notch between the two points shows as a small step (ba_head_34 clay).
6. Front: head small over a long cream throat; cheek flare extra middle-left 25 % / right 24 % (as b5; the
   user approved the head: change only with a reason).
Needs improving (ranked by how much it hurts what each part is):
1. Tail cream flames: smooth S-bands with curled ends and a smooth cream cap (no jagged crest threshold, no
   lock-by-lock cream jumps): the lit tail still looks ragged though the geometry is smooth.
2. Tail profile toward the drawing's S (narrow root, concave lower front, mass high and back), radii from
   a few knots read off the full-resolution drawing.
3. Tail tip: one clean curling point.
4. Cheek ruff notch: blend the two points a little more (CHEEK_BLEND 0.010 -> 0.013) or shorten the upper one.
5. Back-view cream beard (accept what the side view forces).


## Handoff
State: build 6 is the last kit build (CV, compare, renders in the evidence folder); the generator
(aethel_fox.py + aethel_fox_parts/) is exactly what build 6 built. Builds so far 6 of the standard 8. Cycle 6 in
the notes holds the details of the smoothing pass (root causes and every changed value).

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
  dots on the lower third. In this art style the plume is one smooth form whose locks flow without gaps.
  Built (cycle 6) as tail_underfur (0.97 of the fur radius, shaded like the locks) + 36 broad mesh locks in 5
  layers + 6 edge locks, each lock domed with its side edges sunk into the underfur so neighbours meet
  without slits; centre line a 7-point B-spline (TAIL_CTRL). Cream flames are whole cream locks (fur_cream
  sampled from the atlas) plus atlas strokes. User: "The tail is fur."
- The ear: a tall thin cartilage leaf, furred outside (blue, darker rim), inside an indigo bowl with
  a cyan/cream spiral painted on and cream fur tufts at its base; it stands from the skull and turns
  its bowl forward-outward. The ear tuft (cycle 6) is a soft fan of 5 domed cream locks laid on the bowl
  surface (bowl_point), roots overlapping, rounded points.
- The body surface: one smooth furred skin; fur flicks the drawing paints at the bib edge, elbows and belly
  are strokes on smooth forms, never geometry (cycle 6: the spike cones were removed; Taubin relax after the
  remesh, the face and toes held; cream regions cut on smooth fields).
- Collar (unchanged): braided brown leather cord (three twisted strands), silver bail and bezel,
  deep-blue cabochon gem, silver-white antler branches over both shoulders.

### Part inventory (names by what each thing is)
Code: tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox.py builds and joins; one module per part in
aethel_fox_parts/: common.py (helpers, EYE_X, dark_material), body.py (clay, cheek ruff CHEEK_FUR, brisket,
marking images, fur shaders, brow marking, cream_field from smooth profiles, body_attributes, relax_surface),
face.py (eyes, eyelids, nose, mouth), ears.py (ears, ear tufts, bowl_point), collar.py (cord, pendant, antlers with
rounded tips), tail.py (TAIL_CTRL spline, TAIL_LAYERS, TAIL_EDGE_LOCKS, TAIL_EDGE_SINK, atlas).
body (torso, neck, head, muzzle, stop, legs, paws with toes, cheek ruff, chest with brisket: SDF clay -> quad
remesh 16,500 -> Taubin relax); ears + ear tufts (5 domed locks per ear); eyes; eyelids; brow markings (shader);
nose; mouth; cord (3 strands); bail; bezel + plate; gem; antlers (beam, tines, scroll curls, drops); tail
(tail_underfur + 42 locks). Triangles build 6: 115,018 of 120,000 (tail ~24.7k, was 31.4k: room for detail).

### 2. Comparison (build 6)
CV overlap front 0.75, side 0.54 (kit box holds the small back-view fox), back 0.76; w/h +8 %, -6 %, -12 % (as
build 5). CHECK clean (16 degenerate faces, mirror 0.0051). 115,018 tris. 0.223 x 0.612 x 0.500 m.
Close-ups in evidence cycle6/: ba_<shot>.png = build 5 clay | build 6 clay | build 5 lit | build 6 lit (harness
ortho shots: chest_low, belly_side, chest_front, full_front / side / 34 / back, head_front / side / 34,
tail_side, tail_back), k6_close_<part>.png = reference | build 6 (cv.py closeup), c6_legs_side.png.
- Chest and belly (ba_chest_low = low angle, ba_belly_side = side, ba_full_34 = three-quarter, ba_chest_front):
  smooth and continuous, no spikes; cream bib edge a clean curve with a rounded V low between the front legs;
  belly cream line one smooth curve rising to the stifle.
- Head (ba_head_*): unchanged from the approved build 5 (relax weight 0 on the face); cheek ruff a smooth
  two-point flare; a small notch between its points shows in the side clay (ba_head_34).
- Ears: tufts a soft fan of rounded cream locks (k6_close_head beside the side drawing's 4-lock fan).
- Tail geometry (ba_tail_side, ba_tail_back, aethel_fox_clay_2.png): one smooth plume of broad flowing locks, no
  dark slits or shelves; the tip ends in 3-4 small ragged points.
- Tail colour (k6_close_tail, ba_tail_back lit): cream reads as jagged blotches and torn patches; the drawing
  paints broad smooth S-bands with curled ends and a smooth cream cap. Back view cream area x2.38 of the
  drawing's, top-centre +0.21 lighter (the cream tip 'beard', side vs back drawing conflict).
- Tail outline, side (compare.png overlay): an egg; the drawing an S (narrow root, concave lower front, mass
  high and back): extra in front of the lower plume, missing behind the top.
- Legs and paws (c6_legs_side.png): smooth joints and paws.

### 3. Needs improving (ranked)
1. Tail cream pattern: smooth S-band flames with curled ends inside blue and a smooth cream cap (the lit tail
   still looks ragged though its geometry is smooth).
2. Tail profile toward the drawing's S.
3. Tail tip: one clean curling point.
4. Cheek ruff notch (side clay).
5. Back-view cream beard (accept what the side view forces).

### 4. Next step: part tasks (one lead + part builders; copy each into a job card)
Set-up: R = /home/user/asset-pipeline, P = $R/.scratch/assetgen/work/blue_fox_evolution/aethel_fox/parts: `mkdir -p
$P/out && cp $R/production/qa/evidence/blue_fox_evolution/aethel_fox/part_tools/* $P/ && cd $P && timeout 1200
blender -b --factory-startup --python harness.py -- --base` (40 s; it now recovers the 0.50 m scale correctly),
then `timeout 900 blender -b --factory-startup --python harness.py -- --part tail --out NAME --views 2 3 --shots
shots_tail2.json --clay --threads 1 [--outdir DIR] [--set tail.CONST=value ...]`, `--part ears ... --shots
shots_ears2.json`, `--part full --out NAME --shots shots_smooth.json --clay --threads 4` for body changes;
`PYTHONPATH=.scratch/pydeps python3 $P/cmp.py NAME [--outdir DIR] --box V X0 Y0 X1 Y1` from the repo root. Use
fresh output names. Never kill harness jobs with `pkill -f "harness.py"` from a command line that itself
contains that text (it kills its own shell). If the session has an Agent tool, give TASK A and TASK B to
Sonnet part builders (this session had none; part_tools/job_ears_cycle6.md shows a filled job card).

TASK A. Part: tail colour (tail.py: tail_images, TAIL_CREAM_W, TAIL_ZONE_U0, TAIL_FLAMES, TAIL_LOCK_CREAM).
- What it is: see Understanding (the tail). The cream flames are painted on the fur: in the side drawing
  5-6 broad S-bands rising from the lower plume, each ending in a curl, lying inside blue; the outer side of
  the upper plume and the tip cream with a smooth edge.
- Why: the cream crest threshold has two deliberate sines (0.14, 0.06 amplitude: a jagged 'flame' edge) and
  the flames are narrow strokes; TAIL_LOCK_CREAM turns whole locks cream past 0.62 atlas cream, so the cream
  jumps lock by lock into torn patches (k6_close_tail, ba_tail_back lit): "too literal copy" in colour.
- Do: the crest threshold one smooth curve (drop the sines, or one long low wave); flames 5-6 per side as
  smooth S-curves (few control points, widths 0.020-0.032 m, one curl each), soft edges (soft ~0.002); a lock
  turns cream only where its whole middle line is cream (TAIL_LOCK_CREAM[0] ~0.8, or follow the stroke along
  the lock) so bands run along locks. Back view: a cream cap on the top third.
- Reference crops: part_tools/r_side_tail.png, r_back_tail.png (full-resolution cuts, enlarged; never masks).
- Keep: the lock geometry of build 6, the glow swirls and dots, cream share of the side close-up 0.42-0.47.
- Done when: side and back close-ups show smooth cream bands and cap with clean edges, no torn patches.

TASK B. Part: tail shape (tail.py: TAIL_CTRL, TAIL_RB / TAIL_RF / TAIL_RU, the last layer, the tip).
- Why: the plume is an egg; the side drawing's is an S with a narrow root, a concave lower front edge and the
  mass high and back; the tip ends in 3-4 ragged points (layer-4 locks past s 1.0 spread around the centre).
- Do: read the outline off the full-resolution side drawing (r_side_tail.png, aethel_fox_ref_view_2.png;
  measure points by eye on the image, never from a silhouette or overlap mask) and set the radii with fewer
  knots (6-7), smooth; path control points as needed (7 or fewer). Tip: 2-3 tip locks converging into one
  curling point (no spread past s 1, widths tapering together).
- Keep: tail top 0.4806 pre-scale (scale x1.040-1.042), root (0, 0.110, 0.199), X width, the flush lock build.
- Done when: the side overlay loses the extra in front of the lower plume, the tip is one clean point, the clay
  stays smooth. TASK A and TASK B both write tail.py: one part builder, or B after A.

TASK C (lead). Cheek ruff notch: CHEEK_BLEND 0.010 -> ~0.013 or the upper point 3 mm shorter; judge in the
head_34 and head_side clay shots against r_side_head.png; the face must stay identical (relax weight).
Then the cycle's kit build, compare, review and Handoff. If the review finds nothing worth improving, the next
build is the final one (--final).

### 5. Do not undo
Everything the user approved in build 5: head (wedge snout, triangular nose, smiling mouth, chin), eyes (EyeBed,
EYE_X 0.0278, lens <= 1 mm over the face, eyelid lines, cycle 4 eye shape), brow markings, overall proportions,
stance and leg layout, colours and markings (navy lower legs, cream throat / bib / muzzle, flank glow, tan
patch), braided cord, pendant, antlers, ears (shape, tips, colours). Cycle 6's smoothing: no spike cones in the
body clay (no chest spikes, ruff locks, belly fringe, elbow tufts); the two-point soft cheek ruff; the brisket;
LEG_JOINT_BLEND; relax_surface after the remesh with the face and toes held; cream_field from smooth profiles
with rounded corners and no edge noise; the tail as underfur + broad flush locks with sunk edges (no gaps, no
dark seams, no lifted shelves), the B-spline tail path, radius smoothing 9; the ear tuft fan; rounded antler
and drop tips. The tail stays fur (locks), never a shell. The 120k budget; the part-module split.

### 6. Files
- Reference views: production/qa/evidence/blue_fox_evolution/aethel_fox/aethel_fox_ref_view_{1,2,3}.png; source
  design/asset-packs/blue_fox_evolution/source.jpg (4096 px).
- Latest kit compare (build 6): .../aethel_fox_compare.png; renders aethel_fox_view_*.png, aethel_fox_clay_*.png.
- Cycle 6 close-ups: .../cycle6/ (ba_*.png build 5 vs build 6, clay and lit; k6_close_*.png reference | build 6;
  c6_legs_side.png).
- Part tools: .../part_tools/ (harness.py with --outdir and the scale fix, cmp.py, shots_smooth.json,
  shots_tail2.json, shots_ears2.json, shots*.json, full-resolution reference crops r_*.png and t_*.png,
  job_ears_cycle6.md).
- Generator: tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox.py + aethel_fox_parts/*.py.

### 7. Standing rules
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
- User (after approval): "Smoothen model. Rough outer edges caused by low quality reference and too literal
  copy." The model is a clean, stylized 3D character: every outline and surface is a smooth, continuous curve.
  Never trace the reference's pixel outline or copy its drawing artefacts (stair-steps, anti-aliasing, brush
  wobble, torn edges); fit shapes with smooth splines and a few control points, and read the reference for
  intent (what the form is), not for its exact pixels. Clean up torn or ragged geometry (chest bib edge, cheek
  tufts, tail lock edges and gaps, ear tufts, paws, voxel lumps). Keep the approved head (Cycle 5: wedge snout,
  triangular nose, smiling mouth) and the overall design.
- Lead and part builders (user): the builder that reads this Handoff leads; it runs 2-4 part builders
  on Sonnet 5.5 at once (builder_guide.md section 8).
- User (cycle 6, relayed by the coordinator): "Remove spikes in belly". On build 5 the underside of the chest and
  belly had spiky geometry: the pointed cream tufts and the torn lower edge of the cream patch between the
  front legs. The belly and the lower chest are a smooth, continuous surface, and the edge between cream and
  blue there a clean painted curve, not torn geometry. Check it from the side, three-quarter and a low angle,
  with a close-up in the Handoff.
- User (cycle 6, relayed by the coordinator): "Don't use masks." Never take an outline, shape, proportion,
  colour region or texture from a mask of any kind: a silhouette, a cut-out's alpha, a segmentation, a
  threshold, or the compare's overlap mask. Work from the original reference image itself, looking at it and
  measuring it directly at full resolution. If an outline, a cream region or a lock shape in the generator was
  fitted to a mask, re-derive it by looking at the full-resolution reference and model it as a smooth curve.

