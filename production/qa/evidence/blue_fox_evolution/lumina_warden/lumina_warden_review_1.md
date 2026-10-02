REFINE blue_fox_evolution lumina_warden

Review round 1 of build 9. Judged on lumina_warden_compare.png, lumina_warden_turnaround.png, the view_N / clay_N / ref_view_N renders, the build and cv JSON, and my own closeups and samples (view 2 boxes 0 0 0.35 0.55 / 0.5 0.25 1 1 / 0.1 0.35 0.62 1, view 1 box 0.15 0.12 0.85 0.62, view 3 box 0 0.6 1 1).
Pixel measurements are given as fractions of the object height H (ground to ear tip) or width W in that view.

## Verdicts

### Checklist per view

| # | expectation | verdict | judged on (view, box) | for a FAIL: the difference as a measurement |
|---|---|---|---|---|
| C1 | View 1 silhouette | FAIL | v1, whole object, overlay | w/h 0.679 vs 0.638 (+6.4 %). Ear tips 0.60 W apart vs 0.68 W, and ear length (tip to outer base) 0.27 H vs 0.31 H, so ears are 13 % short and set too close. Tail lobes are extra at the middle and bottom sides (cv extra: middle-right 0.13, bottom-right 0.14, bottom-left 0.13). Overlap 0.82 |
| C2 | View 1 parts | FAIL | v1, box 0 0.55 1 0.95 | Tails show as two snail-shell discs facing the camera, each with a horn spike on top. The reference shows sweeping banded masses fanning to the full width, and its right tail hooks up in a soft curl. Collar tendrils are straight wires; on the reference they are S-curved antler branches |
| C3 | View 1 form | FAIL | v1 clay, box 0.25 0.25 0.75 0.6 | Clay has no smile crease (the reference has a W mouth about 0.04 W wide under the nose). Collar is a near-horizontal band at z 0.55-0.62, where the reference's two arches meet in a V at the gem (z 0.41) |
| C4 | View 1 details | FAIL | closeup v1 0.15 0.12 0.85 0.62 | One continuous cyan glow line runs cheek to cheek across the nose bridge; the reference has one separate stroke under each eye. Ear tufts are 3-4 thin sticks; the reference has one cream fan that fills the lower third of each bowl. No smile line |
| C5 | View 1 materials | FAIL | v1 box 0.12 0.05 0.25 0.20 (left ear bowl) | Ear bowl glow too weak. Reference: light 5 % #d1fafd, glowing colour #c8f3fb at a 20 % share. Render: light 5 % #819db2, no glowing cluster (lightest cluster #809cb2 at 5 %). Chest cream (#c3bfbb vs #b3acab) and paws (#4c5d79 vs #4d5e82) match |
| C6 | View 1 clean | PASS | build.json checks | - |
| C7 | View 2 silhouette | FAIL | v2 overlay, box 0.55 0.55 1 1 | Overall w/h 1.23 vs 1.241 is fine. The ground lobe is a tangle: the lateral tail loops through the centre tail as a knot (render x 0.60-0.80, z 0.05-0.45; cv extra bottom-centre 0.16). The reference's lobe is one clean coil that sweeps out to a flicked tip at xs 1.18 |
| C8 | View 2 parts | FAIL | closeup v2 0.5 0.25 1 1 | The plume has no flowing lock tips. The reference has 5 or more tapering locks: the top left curl, the top right curl, an inner hook at mid-height, and lower flicks. The render's "top curl tips" are 2 straight horns 0.06-0.09 H tall that stand off the surface. The ground lobe is a knot, not a coil (see C7) |
| C9 | View 2 form | FAIL | closeup v2 0.1 0.35 0.62 1; clay_2 | Hind legs are vertical tubes with no hock angle; the reference's hind cannon slopes back to a hock at z 0.13-0.20. No elbow or carpus bend on the front legs. Paws are smooth blobs with no toe lobes (ref shows 3 toes per paw). Shoulder feathers stand off the body as a wing of flat cards; the reference's locks lie on the shoulder and blend into the body fur |
| C10 | View 2 details | FAIL | closeup v2 0 0 0.35 0.55 | Ears sit 0.06-0.07 H too far back: eye to front of ear bowl is 0.13 H vs 0.06 H. The far-ear notch is missing. Ear tuft is 3 sticks, not a cream fan. No cheek or jaw fur spikes, no smile line along the jaw, no elbow tuft. Belly line is smooth; the reference has a spiky cream fringe |
| C11 | View 2 materials | FAIL | v2 boxes 0.10 0.45 0.20 0.62 and 0.30 0.62 0.50 0.70 | Cream decals with ragged rectangular edges and blue specks inside sit on the side of the shoulder and under the belly; the reference's cream ruff stays at the front of the chest. A grey speckled smear patch is on the tail lobe at v2 box 0.86 0.78 0.90 0.88. On the hind legs the change to navy is a hard horizontal line about 1 cm wide; the reference fades over about 10 cm. Body blue #91b4d1 vs #99c6d8 (0.05 darker, acceptable) |
| C12 | View 2 clean | PASS | build.json | - |
| C13 | View 3 silhouette | PASS | v3 overlay | w/h 0.681 vs 0.709 (-4 %), overlap 0.81. Extra at top-left and top-right is the shoulder-feather / ear spread, within tolerance |
| C14 | View 3 parts | FAIL | closeup v3 0 0.6 1 1 | No centre spiral lobe. The reference's centre lobe is the largest, with a diameter of 0.45 W. On the render the centre tail is a vertical pillar 0.24 W wide that ends in a small knob at the bottom. Wisps are short upward horns at the tops of the lobes; the reference's wisps sweep out sideways beyond the lobes at z 0.28-0.33 |
| C15 | View 3 form | FAIL | v3, box 0.3 0.3 0.7 0.65 | Head is a separate round ball on a narrow neck, 0.29 W wide; the reference's cheek ruff is 0.38 W and merges into the shoulders. Nape spikes are cream horn shapes; on the reference they are blue fur spikes |
| C16 | View 3 details | FAIL | closeup v3 0 0.6 1 1 | Constellation on the centre lobe has 3 stars and 2 line segments vs 5 stars and 4 segments. No cyan streaks along the tails near the root (the reference has 4-6) |
| C17 | View 3 materials | FAIL | v3 box 0.05 0.72 0.15 0.86 and 0.60 0.80 0.66 0.86 | Grey speckled smear patches on the left and right lobes (texture or bake bleed); the reference bands are clean. Bands are 3 equal wide stripes per lobe; the reference has 5-7 per lobe, of varying width, with cyan streaks. Ear backs #88afd8 vs #8ab3d4 match |
| C18 | View 3 clean | PASS | build.json | - |

### Key ratios

| # | expectation | verdict | judged on (view, box) | for a FAIL: the difference as a measurement |
|---|---|---|---|---|
| R1 | length : height 1.24 | PASS | v2 | 1.23 (-0.9 %) |
| R2 | ear length : height 0.27 side / 0.31 front | FAIL | v1, v2 | Side 0.27 (PASS); front 0.27 vs 0.31 (-13 %) |
| R3 | withers : height 0.60 | PASS | v2 | 0.605 |
| R4 | leg length : withers 0.55 | PASS | v2 | 0.57 (+4 %) |
| R5 | head length : height 0.30 | FAIL | v2, box 0 0 0.35 0.55 | Nose to back of skull is 0.35 H (+17 %), because the ears and the cranium sit about 0.06 H too far back |
| R6 | nose height 0.68 | PASS | v2 | 0.68 |
| R7 | tail mass length 0.40 | PASS | v2 | 0.41 |
| R8 | front w/h 0.64; head width : total 0.53 | FAIL | v1 | w/h 0.679 (+6.4 %); head width 0.56 W (+6 %) |
| R9 | back w/h 0.71; centre lobe : width 0.45 | FAIL | v3 | w/h 0.681 (PASS); centre lobe missing (0 vs 0.45 W) |
| R10 | body length : height 0.68 | PASS | v2 | 0.69 |

### Close observation, parts, materials, details (analysis)

| # | expectation | verdict | judged on (view, box) | for a FAIL: the difference as a measurement |
|---|---|---|---|---|
| E1 | face lighter blue than the body, cream muzzle and cheeks | PASS | closeup v1 | - |
| E2 | cream brow spots | PASS | closeup v1 | - |
| E3 | forehead flame mark (3 strokes) | PASS | closeup v1 | - |
| E4 | cyan stroke under and behind each eye | FAIL | closeup v1 | One continuous band across the nose bridge instead of 2 separate strokes |
| E5 | almond eyes, blue iris, thick flicked navy lid line | PASS | closeup v1, v2 | Shape and liner are present; the iris reads slightly darker |
| E6 | smiling mouth line (W) | FAIL | v1 clay, v2 | Absent (no crease, no line) |
| E7 | glossy nose | PASS | v1, v2 | - |
| E8 | cheek fur spikes, 4 per side, uneven | PASS | v1 | Present in front; barely visible in side |
| E9 | ears: indigo bowl, star specks, rim | PASS | v1, v2 | - |
| E10 | ear glowing cyan spiral, left and right differ | FAIL | v1 box 0.12 0.05 0.25 0.20; v2 near ear | Spiral is a thin hairline and reads as a "B" or "3" in the side view; the reference's spiral is a bold glowing curl with 20 % glowing share in the box (render about 5 %, light 0.60 vs 0.95) |
| E11 | ear-base cream tuft, 5 feather blades | FAIL | closeup v2 0 0 0.35 0.55 | 3-4 separate thin sticks, about 0.01 wide; the reference has one fan of 5 blades, about 0.5 of the bowl width, filling the lower third |
| E12 | swirl strokes on the ear backs | PASS | v3 | 1 stroke and a curl vs 2 strokes and a spiral; close enough |
| E13 | notched ear tip | FAIL | v2 far ear | Single point; the reference has a double point |
| E14 | pale ear glow in front | PASS | v1 | An illustration halo, not a surface (the camera / drawing explains it) |
| E15 | chest ruff, V point, spiky locks | PASS | v1 | V at z 0.26 vs 0.30 |
| E16 | collar arched bands meeting at the gem | FAIL | closeup v1 | A near-horizontal band of wires at z 0.55-0.62; the reference's arches dip to a V at the gem |
| E17 | collar scroll curls, 2 per side | PASS | v1 clay | Present, small |
| E18 | collar tendrils, 3-4 per side, antler-like, leaf tips | FAIL | closeup v1, v2 | Straight thin wires with small end hooks; the reference's tendrils are S-curved branches about 2x thicker with curled tips |
| E19 | polished silver | PASS | v1 | - |
| E20 | faceted rhombus gem, bezel, blue glow | PASS | v1 | - |
| E21 | glowing feather marks below the gem | PASS | v1 | - |
| E22 | body blue fur, lighter back, fur strokes | PASS | v2 box 0.40 0.42 0.50 0.52 | #91b4d1 vs #99c6d8 |
| E23 | haunch spiral, back wavy strokes, thigh dots, leg streaks | PASS | v2 | The back strokes are jagged lightning shapes rather than waves (minor) |
| E24 | cream belly fringe, elbow tuft, chest-bottom spikes | FAIL | closeup v2 0.1 0.35 0.62 1 | Belly is a smooth line with a ragged cream decal patch; no elbow tuft; the reference has about 8 belly locks and 1 elbow tuft per leg |
| E25 | shoulder feathers 6-8 per side, iridescent, curled tips | FAIL | v2, clay_2 | Colours match (lavender / mint / blue). About 14 narrow blades (about 0.03 wide) per side fan out from the body like a wing; the reference has 6-8 broad locks (0.05-0.08 wide) lying on the shoulder with up-curled tips |
| E26 | legs: darker navy lower legs and paws, soft gradient | FAIL | v2 hind legs | Colour matches (#4b5d7b vs #4b5f83), but the change is a hard horizontal line instead of a gradient of about 10 cm |
| E27 | leg joints (elbow, carpus, stifle, hock) | FAIL | clay_2 | Hind legs vertical with no hock angle; front legs straight |
| E28 | paws with 3-4 toe lobes and dark creases | FAIL | v1 box 0.40 0.88 0.60 1.0 | No toes. Texture 0.049 vs 0.269, darkest #343f57 vs #1a2143 (no creases) |
| E29 | five tails: centre, 2 lateral, 2 wisps | FAIL | v2, v3 | Centre lobe missing in the back view; the lateral tail is knotted through the centre tail in the side view; the wisps are short horns |
| E30 | tail spiral bands cream / mid-blue / indigo of uneven width | FAIL | closeups v2, v3 | 3 equal broad bands per lobe vs 5-7 bands of 0.02-0.06 m varying width |
| E31 | dark starry zone on the centre tail | PASS | closeup v2 | - |
| E32 | constellation: 6 stars with lines (side) | PASS | closeup v2 | 6 stars and lines; the shape matches |
| E33 | constellation repeat on the centre lobe (back), 4-5 stars | FAIL | closeup v3 | 3 stars vs 5 |
| E34 | glowing cyan streaks along the tails near the root | FAIL | v3 | None visible vs 4-6 |
| E35 | coiled ground lobes, 2 turns, dark eye | FAIL | v2, v3 | Left and right lobes are coiled (PASS). The side-view lobe is a knot and the back centre lobe is missing |
| E36 | top curl tips on the arc | FAIL | v2 | Straight horns standing off the surface vs flowing lock ends that curl with the plume |
| E37 | asymmetry: markings, tails, tendrils not copies | PASS | v1, v3 | mirror error 0.0123; ear spirals differ |

### Missed by the analysis

| # | expectation | verdict | judged on (view, box) | for a FAIL: the difference as a measurement |
|---|---|---|---|---|
| M1 | tail plume edge is made of tapering fur locks, not a smooth tube | FAIL | closeup v2 0.5 0.25 1 1 | The render's outer plume edge is one smooth curve; the reference has 5 or more separate lock tips and an inner hook |
| M2 | ears start directly behind the eye | FAIL | closeup v2 0 0 0.35 0.55 | Eye to ear bowl 0.13 H vs 0.06 H |
| M3 | no texture artefacts | FAIL | v2 0.86 0.78 0.90 0.88; v3 0.05 0.72 0.15 0.86; v2 0.10 0.45 0.20 0.62 | Grey speckled smears on 3 tail areas; cream decal with blue specks on the shoulder side |

Counts: PASS 29, FAIL 39, UNKNOWN 0.

## Fixes

1. **Tail knot and missing centre lobe (C7, C8, C14, E29, E35, R9).** The lateral tail's path crosses through the centre tail's lower coil, so the side view shows a pretzel. The centre tail ends in a knob, so the back view has no centre spiral. Re-route the curves:
   - Centre tail: root at the rump, rising arc to z 0.70, back edge at Y +0.62, down to the ground, then a 2-turn planar coil centred at x 0, Y about +0.45, z 0.16, radius 0.16 (so it is the big centre spiral in the back view). End with the flicked tip running back to xs 1.18 at z 0.05.
   - Lateral tails: keep them outside the centre tail's volume (|x| ≥ 0.16 along their whole path) and coil them at x ±0.24, radius 0.13, axis along ±X.
   - Check the side view for zero self-intersection: no lateral tube may pass between the centre coil and the body.
2. **Tail plume reads as a smooth tube with horns (C8, M1, E36, E30).**
   - Replace the 2 "top curl tips" horns with lock tubes that leave the plume tangentially and follow its flow. Add 5-6 tapering lock tips along the outer and inner plume edges (r 0.02-0.04 tapering to 0, lengths 0.10-0.20), including the inner hook at about xs 0.98 z 0.35 in the side view.
   - Turn the wisps into 0.65 m tubes that leave sideways at z 0.30 to x ±0.36 before curling up (not horns on top of the lobes).
   - Repaint the bands at 2-3x the current frequency (5-7 bands per lobe, widths 0.02-0.06 m drawn from noise) and add 4-6 cyan emission streaks along the tails within 0.25 m of the root.
3. **Texture artefacts (C11, C17, M3).** Speckled grey smears on the lobes (v3 left lobe, v2 lower lobe right edge) look like the starry or emission atlas bleeding into neighbouring UV islands, or rays hitting the wrong tube when baking. Add 8-16 px of padding between islands in the tail atlas and bake with a cage or extrusion small enough not to hit overlapping tails.
   - Shoulder and belly cream decals: the cream projection mask leaks sideways. Limit the chest-ruff mask to faces whose normal has Y < -0.3 (front-facing) and z > 0.22, and drop the blue speck noise inside cream zones.
   - Shift the belly cream to the underside only, with a jagged edge.
4. **Ears and head (C10, R5, M2, E11, E13, E10, R2).**
   - Move the ear bases forward by 0.06 m (base Y about -0.42 instead of -0.36) so the bowl starts 0.06 H behind the eye; scale the cranium's back down so nose to back of skull is 0.30 H.
   - In the front view, rotate the ears 6-8° further outward and lengthen them 10 % (tip spread 0.68 W).
   - Ear tuft: replace the sticks with one fan of 5 blades, each 0.025-0.035 wide at the base and 0.06-0.10 long, overlapping, filling the lower third of the bowl.
   - Add the double point to one ear tip.
   - Ear spiral: widen the stroke to 6-10 mm with emission strength 2-3 so it reads as a bold curl.
5. **Legs and paws (C9, E27, E28, E26).**
   - Rebuild the hind legs with a stifle at z 0.30 (knee forward), a hock at z 0.13-0.18 pushed back by 0.05 m, and a cannon sloping forward to the paw. Add a slight elbow and carpus bend on the front legs.
   - Paws: subtract 3 crease grooves (about 4 mm wide, 6 mm deep) to make 4 toe lobes, with AO darkening to about #1a2143 in the creases.
   - Replace the hard colour step on the legs with a Z ramp from z 0.35 (body blue) to z 0.20 (navy).
6. **Front face and collar (C3, C4, E4, E6, E16, E18).**
   - Break the cheek-to-cheek cyan band into 2 separate tapering strokes under the eyes (mask out |x| < 0.03).
   - Cut a W smile crease (3 mm deep) under the nose that runs back along the jaw in profile.
   - Re-curve the collar's main arcs so they dip from z 0.55 at the sides to meet in a V at the gem (z 0.46).
   - Make the tendrils S-curved swept tubes, r 0.008 tapering to 0.004, with a curled tip (about 1/2 turn), rising up and out to z 0.57-0.62.
7. **Shoulder feathers (E25, C9).** Reduce to 7 locks per side, 0.05-0.08 wide. Lay their roots flat on the shoulder surface (project the root and first third onto the body, normal offset under 5 mm) so they flow back over the shoulder instead of standing out like a wing. Keep the curled tips and the iridescent material.
8. **Small fur detail (E24, C10, C15, E33).**
   - Add 6-8 belly fringe locks (cones 0.03-0.06), one elbow tuft per front leg and blue (not cream) nape and cheek spikes seen from the back.
   - Widen the back-view cheek ruff to 0.38 W.
   - Add 2 stars and their line segments to the back-view constellation on the centre lobe, after fix 1.
