# aethel_fox — Aethel Fox (Phase 2): builder notes

Fill every section of `## Analysis` before the first build (a hook refuses the build until each
has content). After each build write `## Cycle <n>` (n = the build number the kit printed). When
your context budget is reached write `## Handoff`; at the end write `## Report`. A critic judges the
final build from the images and this Analysis; following builders read all of it: keep it complete,
exact and in numbers.

## Analysis

### What it is
Aethel Fox, the phase-2 evolution of the stylised blue fox (anime / painted game-art style: soft
cel-like shading, thin dark-navy ink outlines, painted fur strokes, smooth rounded forms). A slim
young fox standing square on four long thin legs, head up and turned a little toward the viewer,
front faces -Y. It reads as THIS creature because of: (1) two very tall pointed ears (tip about as
high above the crown as the head is long) whose inner bowls are tan/cream with blue S-spirals (front
drawing) or indigo with glowing cyan spirals (side drawing), dark blue rims, a fan of 4-5 cream fur
blades at the inner base; (2) a braided brown leather cord collar with a round deep-blue cabochon gem
in a silver bezel hanging on a short bail; (3) silver-white branching antler-like collar pieces that
start beside the pendant, run up over both shoulders and branch outward / backward into curling
tines (like small deer antlers lying on the shoulders), plus scroll curls and a pointed drop below
the gem; (4) one huge plume tail rising from the rump, swelling into a teardrop as tall as the body
and curling over at the top into a cream tip flicked backward, covered in cream flame-swirls on
light blue and with glowing cyan swirls and dots on its lower half; (5) faintly glowing pale-cyan
spiral / flame markings on the haunch, flank, back and forehead. Light blue body with lighter head,
darker navy-blue lower legs and paws, cream muzzle, cheeks, throat, chest (V point between the front
legs) and belly, tan patch under the tail.
Construction: one fused body (torso, neck, head, muzzle, legs, paws, chest ruff / cheek / elbow fur
locks) sculpted as signed-distance clay and quad-remeshed; separate ears (lofted bowls) with cream
fur blades, eyes, lid liners, nose, braided cord (three twisted strands), bail, bezel, gem, antler
branches (swept tubes), one swept tail plume with a curled tip; markings painted into projection /
UV images and mixed on the inputs of one Principled BSDF per surface.

### Views
Reference = top-right panel of source.jpg (4096 px square). Three drawn views, not exact 0/90/180
(the user: "the angles are different"), each drawn at its own scale.
- View 1, front (az 0, el -8, fitted), box 2125 630 2640 1810 (object 2150-2616 x 664-1783): face (eyes, brow
  spots, forehead flame, cream cheeks, nose, W smile), the ear bowls straight on (tan with blue
  S-spirals, cream blade fans), the whole collar (cord loop, bail, round gem in bezel, antler spread
  to +-0.10 m, scroll curls, drop point under the gem), cream chest V, the front legs (nearly
  touching), hind legs just visible outside them, paws with toe lines.
- View 2, side / three-quarter (az 62, el 6 fitted; main focus), box 2652 590 3970 1765: the head profile
  (nose, muzzle, smile, eye with liner, brow spot), the near ear bowl (indigo, cyan spiral, cream
  fan), the far ear's back, the cord crossing the neck, the antler on the near shoulder with its
  tines, gem from the side, flank / haunch / back glowing markings, belly and inner-thigh tan, leg
  joints, the whole tail plume with its swirl pattern, glow and cream curled tip. The box must also
  hold the back view's left half (the back view stands inside the side view's bounding rows, so no
  rectangle holds the side view alone on a plain background): the kit's overlap for view 2 is capped
  (a perfect render scores 0.54); I report a clean overlap with the largest component too.
- View 3, back (az 180, el 20 fitted), box 3625 1130 3965 1825 (object 3639-3948 x 1150-1801): the tail end-on
  as a big egg (cream top = the curled tip, cream swirl flames on blue), the ear backs (plain blue),
  cheek tufts poking out at the sides, hind legs, tan patch under the tail.
Not shown: top, underside, the fox's right (-X) flank. Inferred: right flank mirrors the left with
its markings mirrored and slightly different; underside cream/tan as the side's belly edge.
Camera: perspective --lens 135 (a sheet drawn with mild perspective, as the sibling blue_fox
measured: 135 beat 85/50); azimuth and elevation per view are first estimates from the paw / ear
parallax and are refined by silhouette fits on preview renders.

### Size and proportions
Anchor: "scale 1/6, approx. 50 cm": the overall height (ground to the top of the tail plume) =
0.50 m. Side view: object top 619 px (tail) to ground ~1750 px -> 2262 px/m (vertical 2228 px/m
after el 10). Front view drawn bigger: its head-based scale is 2270 px/m (nose / eye heights match
the side), and its ears are drawn ~10 % taller (front ear tip 0.49 m vs side 0.45 m). Back view
drawn at ~1450 px/m with its tail lower (elevation and drawing). Ground line of the side view:
y = 1732 - 0.12 (x - 2930). Side-view metres: Y = (x - 3150 - X*0.469*2262) / 1997,
Z = (ground(x) - y) / 2228.
cv.py measure: front w/h 0.42 (fill 0.57, symmetry 0.98); side box w/h 1.11 (with the back-view
piece; the fox alone 1159 x 1131 px, w/h 1.025); back w/h 0.47 (fill 0.61, symmetry 0.95).
Overall model target: width (X) 0.20 m (antler tips +-0.10), length (Y) ~0.62 m (nose Y -0.24 to tail
tip +0.37), height 0.50 m.
Landmarks (X from the midline, Y forward negative, Z up, metres):
- Nose tip Y -0.24 Z 0.30; eye centre X +-0.028 Y -0.184 Z 0.318 (eye 0.024 wide, 0.018 tall); brow
  spot Z 0.338; crown Z 0.36 at Y -0.165; back of skull Y -0.10; jaw/chin Z 0.283; cheek tufts X
  +-0.08 Z 0.28-0.30, Y -0.12; head width at the eyes +-0.066.
- Ears: base centre X +-0.05 Y -0.13 Z 0.335, base width 0.055; tip X +-0.098 Y -0.135 Z 0.46; outer
  edge +-0.10 at Z 0.40; length 0.14.
- Neck: throat Y -0.18 (Z 0.20-0.27); nape Y -0.09 Z 0.30 -> withers Y -0.02 Z 0.245.
- Torso: chest front Y -0.19 at Z 0.18; chest bottom Z 0.13; back line Z 0.245 (Y -0.02 to 0.07);
  belly Z 0.15 (tuck-up behind Y 0.0); rump Y 0.11 Z 0.18; half-width +-0.063 (front, chest).
- Front legs X +-0.027, paws at Y -0.11 (both), leg width 0.036, elbow Z 0.13; paw 0.034 wide,
  0.045 long, 0.025 high.
- Hind legs X +-0.035, paws: near (+X) Y 0.095, far (-X) Y 0.05; stifle Z 0.14, hock Z 0.078 at Y
  +0.10; thigh depth 0.10.
- Tail: root Y 0.08 Z 0.23 (r 0.03), plume centre Y 0.13 Z 0.33 (radius 0.09-0.10), top Z 0.48-0.50
  at Y 0.17, cream tip curling back and down to Y 0.36 Z 0.33.
- Collar cord: front Z 0.19-0.20 at the throat-chest, sides Z 0.26 at X +-0.052, back of neck Z 0.29;
  gem centre Z 0.173 at Y -0.20, gem 0.024 diameter, bezel 0.033; bail 0.009 wide 0.011 tall.
- Antler per side: beam from beside the pendant (X 0.02, Z 0.18) up along the chest side to the
  shoulder (X 0.06, Y -0.15, Z 0.215), branching: top tine to Y -0.09 Z 0.29, rear tine Y -0.07 Z
  0.25, outer tine to X 0.10 Z 0.255 (front), lower tine Y -0.10 Z 0.23; scroll curl beside the gem
  X 0.035 Z 0.15; drop point under the gem to Z 0.125.
KEY RATIOS (side view unless named):
- R1 ear-tip height : total height = 0.90 (side), front ear length : head height = 1.2.
- R2 nose height : total height = 0.60.
- R3 back height : total height = 0.49 (0.245).
- R4 leg length (chest bottom to ground) : back height = 0.53 (0.13 / 0.245).
- R5 head length (nose to back of skull, 0.14) : total height = 0.28.
- R6 tail plume height (root to top, 0.27) : total height = 0.54; plume width 0.19 : height 0.27 = 0.70.
- R7 front: width : height = 0.42; head width at cheeks : total width = 0.35 (0.16 / 0.46 front px).
- R8 front: antler span : body width = 1.6 (0.20 / 0.126).
- R9 back: width : height = 0.47; tail egg width : height = 0.76.
- R10 body length (chest front to rump, 0.30) : total height = 0.60.

### Close observation
cv.py observe sheets 1-3 plus my own magnified crops (head, collar, legs, side head, side collar, side
body, tail, back) in the work folder. Samples (cv.py sample, mean / darkest / lightest):
- Head and forehead blue: front #aad7e9 (#a4d1e5..#b7e1f1, spread 0.014), side head #a0c9de: lightest
  blue on the model; painted soft highlights on the crown and muzzle bridge, fur strokes faint.
- Flank blue: side #83a8bf (#6d8ca7..#95bfd2, spread 0.047): darker than the head; upper leg #7292ae
  (#8aafc8 light, #25354e ink); lower legs and paws navy #435a80 front (#27344d..#4d668d), side #526d92;
  the darkening starts at the elbow / hock and is a soft gradient. Toes: 3 shallow creases per paw,
  paw tops lighter, toe ends rounded.
- Cream: muzzle front #d5c8ba (#b9a799..#e1d9cc), chest #b7aca4 (#c8beb6 lit, #b0a399 shade, fur
  strands visible), belly / inner thigh in shade tan #988a83, tail cream tip #dad0c2, back egg top
  #dedad7, tan patch under the tail #756661 (#74625b, #8d8483). Cream edges are jagged fur-tip edges
  (cheek patch lower edge with 3-4 points, chest V with small spikes, belly edge serrated).
- Ear inner (front): tan #c4b7af with blue spiral strokes #8d9fb2 (two curls, an S shape), outer
  rim dark blue #6c7f9d, cream fan of 4-5 pointed blades #e2dad0 at the inner base. Side: near ear
  bowl indigo #45567b with light cyan spiral #a1c7dd (glowing). The two drawings disagree: I build
  the inner bowl tan with blue spirals in its upper half and an indigo zone deepening toward the
  bottom-inner side, where the spiral glows cyan (both views keep their main read).
- Ear backs: plain blue #94bbd0 (#81a4bf..#96bed2), darker blue rim along the edges; the tip has a
  small notch / tuft (front view ear tips show a little split).
- Eyes: large almond, grey-blue iris dark at the top (#5a6a90) lighter below (#a9b8d0), dark pupil,
  white catch light upper inner, thick dark upper lid liner with a flick at the outer corner, lower
  lid thin; small white corner. Brow spots: cream ovals 0.012 x 0.007.
- Forehead: pale-cyan flame mark (3 thin strokes, centre teardrop) between the ears; faint light
  streaks on the cheek under the eye (side view: 2 small pale strokes behind the eye).
- Nose: small dark brown-black (#3a2e32) rounded triangle with a highlight on top; mouth a dark W.
- Cord: braided brown leather, 3 strands twisted, #865d4b lit / #53433f shade, highlights on each
  strand bump, about 0.006 m thick; visible all around the neck in the front view; in the side view
  it passes under the antler and behind the neck fur.
- Gem: deep saturated blue cabochon (#1d4fb0..#5a9cf0) with a white specular spot upper left and a
  lighter lower rim (internal glow); bezel silver grey #cacacb with darker inner edge; bail a
  rounded rectangle loop.
- Antlers: silver-white with blue tint (#c8dcec lit, #8fb0d0 shade, dark outline), glossy (sharp
  highlights along the top of each branch), smooth organic branches tapering to rounded tips that
  hook; each branch differs in length and curl; a little textured streak where the beam crosses the
  cord on the shoulder (side view).
- Glowing markings: pale cyan #a7e6f5 cores with a soft lighter halo, on the haunch (spiral + 3-4
  flame strokes + dots), along the back (2 long strokes from the shoulder to the tail root), on the
  shoulder and front leg (thin streaks), forehead flame. Tail: blue #7893bf with glowing cyan swirls
  #92ddec and dots in the lower third, cream #d7cfc4 flame-swirls (6-8, each different) on the
  middle and upper parts, light blue lighter streaks #9ad2ea near the left edge; tip cream with
  pale-blue glowing dots where blue meets cream.
- Imperfections / variation: fur strokes in the blue (thin lighter streaks along the body), soft
  shadows under the belly and inside the legs, darker blue toward the legs' backs, chest ruff spikes
  uneven (5-7 points of different length), cheek tuft points uneven, the far ear slightly smaller
  in the side view, the near hind leg longer stride than the far one, antler tines different on the
  two sides (front view: the fox's right side has 4 tips, the left 4 with different curls).

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it (technique, skill) | geometry detail (what is modelled: bevels, creases, folds, holes, relief) | nuances (imperfections, asymmetry, how each copy differs) |
|---|---|---|---|---|---|---|---|
| 1 | body (torso, neck, head, muzzle, jaw) | 1 | 0.13 x 0.40 x 0.37 | centred X 0, nose Y -0.24, rump Y 0.11 | SDF clay ellipsoids/cones blended (sculpting bx_sculpt), quad remesh ~16k quads | eye sockets, brow ridge, muzzle bridge, mouth corner crease, tuck-up belly, shoulder blades, rump | head turned 0 (symmetric) but fur locks asymmetric |
| 2 | legs and paws | 4 | leg r 0.018, paw 0.034 x 0.045 x 0.025 | front X +-0.027 Y -0.11; hind X +-0.035 Y 0.095 / 0.05 | SDF tubes through hip/stifle/hock/paw joints, part of the body clay | elbows, hock angle, wrist bump, 4 toe lobes with 3 creases per paw, flat soles | hind stride differs left/right; toe sizes vary |
| 3 | fur locks: cheek tufts, chest ruff spikes, elbow tufts, belly fringe | ~24 | cones r 0.008-0.015, 0.02-0.05 long | cheeks X +-0.07..0.09 Z 0.28; chest Y -0.19 Z 0.10-0.17; elbows; belly | SDF round cones blended into the clay | pointed tips with real relief | every lock its own length/angle (seeded) |
| 4 | ears | 2 | 0.14 long, 0.06 wide at base, 0.012 thick | base X +-0.05 Y -0.13 Z 0.335, tips X +-0.098 Z 0.46, bowls facing forward-out | lofted leaf bowl (rings of front + back surface), Subsurf 1 | bowl depth 0.015, thick rim, tip notch | ear spirals painted per side, left/right differ slightly |
| 5 | ear tufts (cream fur locks at the inner ear base) | 10 | 0.03-0.05 long, 0.01 wide | inner base of each bowl, fanning up | swept flat blades | pointed tips, thickness 2 mm | each blade own angle/length |
| 6 | eyes (eyeball: sclera, iris, pupil, cornea catch light) | 2 | opening 0.027 x 0.020, iris 0.0164 x 0.0194 | X +-0.031 Z 0.327 (pre-scale), surface normal turned out 14 deg, long axis tilted 20 deg (outer corner up) | domed lens (1.6 mm) on a bed fitted to the finished body mesh (EyeBed: ray cast, never cut by the face), UV iris shader | dome, rim tucked 1.2 mm under the eyelid lines | iris toward the nose, catch light upper inner on both eyes |
| 7 | eyelids (upper and lower eyelid lines) | 2 x 2 | upper 0.9-2.9 mm wide, lower 0.5-1.5 mm | upper: tear duct over the top to the outer corner and on into a rising wing; lower: whole lower edge | flat swept lines lying on the higher of eye and face (build_eyelids) | wing tapers to a point, thicker at the tear duct | — |
| 8 | nose | 1 | 0.016 x 0.012 x 0.010 | Y -0.24 Z 0.298 | small SDF clay | nostrils, philtrum line | — |
| 9 | collar cord | 1 | 3 strands r 0.0022 around a ring of 0.05 x 0.06 | ring tilted: front Z 0.19, back Z 0.29 | three helically twisted swept tubes along the neck ring, snapped onto the neck surface | strand bumps, twist | twist phase varies, slight sag at the front |
| 10 | pendant bail | 1 | 0.009 x 0.003 x 0.011 | under the cord front | swept closed loop | rounded | — |
| 11 | gem bezel | 1 | ring r 0.0165, tube 0.0025 | Z 0.173 Y -0.20, facing forward-down | swept torus + back plate | rounded rim, plate behind | — |
| 12 | gem | 1 | 0.024 diameter, 0.010 deep | in the bezel | squashed UV sphere (cabochon dome) | domed | — |
| 13 | antler branches | 2 sides x 6-7 | tubes r 0.004 -> 0.0015, 0.03-0.10 long | from the pendant up over each shoulder | swept tapered tubes along bezier paths, tips hooked | rounded tips, root blended into beam | each tine own length/curl; sides differ |
| 14 | gem scroll curls + drop | 2 + 1 | r 0.003, curl r 0.01 | beside and under the gem | swept spiral tubes | — | mirrored but varied |
| 15 | tail (a fox's brush: underfur round the tail bone + 54 guard-hair locks in 5 layers) | 1 | 0.20 x 0.19 x 0.27 + tip | root Y 0.08 Z 0.23, up and back, tip curls to Y 0.36 Z 0.33 | underfur: swept mass at 0.87 of the outline radius (TailBody path); locks: clumps laid in (arc s, angle, radius) on the fur volume, each rooted under the previous layer, widest a third along, drawn to a point, tips lifting (build_tail_fur_lock) | lock sections domed on top, flat below; tips break the outline; tip-tag locks run on past the end into the curled cream tip | every lock its own width, length, twist, sway, lift; shared painted atlas; root dark, tip light |
| 16 | tail edge locks (guard-hair locks standing out of the outline) | 7 | 0.03-0.04 wide, 0.25-0.32 of the tail long | 3 on the lower back edge, 3 on the top of the cream crown, 1 under the curled tip | same lock builder with a higher tip lift (0.08-0.2) | pointed tips | different lengths and lifts |

### Materials and shaders
- S1 body fur (blue): parts 1-3. Painted stylised fur. Colour by height: lower legs #435a80..#526d92
  (Z < 0.06), upper legs #7292ae, flank #83a8bf (mean, #6d8ca7..#95bfd2), head #a0c9de..#aad7e9
  (lightest). Fur strokes: stretched noise along the body / down the legs (L +-0.04), soft blotches
  (+-0.03); roughness 0.72-0.86 with the strokes; bump from the strokes 1.5 mm. AO darkening in
  creases (toes, joints, under locks). Glowing markings from a side projection image (object-space
  normal weighted: both flanks, mirrored and varied) and a front image (forehead flame, chest),
  colour #b6ecf8 core, emission cyan 0.8. Built: kit.principled + attributes zh/legs/face + painted
  numpy images (no library fur fits a painted style: material-search showed only realistic pelts in
  the sibling run).
- S2 cream fur: muzzle, cheeks, throat, chest, belly, inner thighs, tail-base patch. #d5c8ba muzzle,
  #c8beb6..#b0a399 chest, #988a83 belly shade, #756661 patch under the tail. Same strokes and bump,
  colour ramp by height and a belly/patch tan mask. Edge with blue: kit.mark with a noisy field for
  the jagged fur-tip edge.
- S3 ear back: blue #94bbd0 with darker rim #6c7f9d along the edges (UV distance to the rim),
  strokes. S4 ear inner: tan #c4b7af..#cebcaf upper, indigo #45567b toward the inner-lower bowl,
  blue spiral strokes #6d86ad painted in the ear UVs, glowing cyan spiral cores where the indigo is.
  Roughness 0.65-0.8.
- S5 cream blades: #e2dad0 tips, #b9b0a8 at the root, strand noise.
- S6 eye: UV-driven iris (dark top #4e5c85 -> light bottom #b9c6dc), pupil #1a1f35, catch light
  (emission), rim dark; roughness 0.12. S7 liner/nose: dark #1f2238 / #352a2e, roughness 0.3-0.45,
  noise variation and nose highlight from roughness.
- S8 cord leather: brown #865d4b lit, #53433f in the grooves between strands (AO + strand-angle
  ramp), fine grain noise bump 0.4 mm, roughness 0.55-0.75 (worn strand tops shinier).
- S9 silver (bezel, bail): metallic 1, #cfd2d8..#9aa0ad, roughness 0.18-0.35 with noise, AO tarnish
  in crevices.
- S10 antler: pale silver-white with a blue tint, not fully metal: base #d4e4f0 tops -> #8fb0d0
  undersides (normal-Z ramp in object space), metallic 0.35, roughness 0.2-0.3, faint streak noise
  along the branch, AO darkening at forks.
- S11 gem: deep blue #1d4fb0 core -> #5a9cf0 lower rim (UV radial), white spec spot, emission blue
  0.6 (it glows faintly), roughness 0.05.
- S12 tail: UV atlas painted in numpy along the sweep: base light blue #8fb8d8 -> deeper #7893bf at
  the lower inner side; cream flame swirls #d7cfc4 (8 strokes along the tail, spirals at the ends);
  tip region cream (last 30 % of the path) with a jagged boundary; glowing cyan swirls / dots in the
  lower third (emission atlas); light streaks #a8daf0. Strand noise in colour, roughness, bump.

### Details and nuances
- Forehead flame mark (3 strokes) - front projection image, glow.
- Brow spots (cream ovals) above each eye - decal image.
- Cheek pale strokes behind the eye (side) - side projection.
- W smile line and mouth corner - decal (dark line) + slight crease.
- Haunch spiral, 3-4 flame strokes and 3 dots on each flank (mirrored, varied) - side projection.
- Two long glowing strokes along the back from the shoulder to the tail root - side projection.
- Thin glow streaks on the shoulder and front leg - side projection.
- Cream jagged edges: cheek patch lower edge, chest V spikes, belly serration - kit.mark noise field
  + modelled ruff spikes.
- Elbow white tuft at the back of each front leg - clay cone + cream mark.
- Toe creases 3 per paw - clay subtract cones.
- Ear rim darker blue - ear shader UV rim mask.
- Ear tip notch - geometry (tip split).
- Ear inner spirals: two curls (S), indigo zone and cyan glow - ear UV image.
- Cream blade fans in the ears, 5 per ear with different lengths - geometry.
- Eye catch light, liner flick - shader + geometry.
- Nose highlight - roughness variation.
- Cord: three twisted strands, groove shading, slight sag - geometry + shader.
- Gem highlight spot and lighter lower rim - gem shader.
- Bail and bezel - geometry.
- Antler tines hook at the tips, sides differ, glossy highlights - geometry + shader.
- Tail swirls: cream flames, glowing cyan swirls and dots in the lower third, light streaks, cream
  curled tip with jagged lobes, small glowing dots at the cream/blue boundary near the tip - UV atlas
  + geometry (tip lobes, flutes).
- Tan patch under the tail base - cream mark with tan ramp.
- Fur strokes everywhere, soft AO in creases, lower legs darker - shader.

### Build plan
1. Body clay (one SDF, voxel 2.1 mm) -> quad remesh 11k quads (~22k tris) -> cream zones by kit.mark
   (noisy field) -> attributes (zh, face, legs, tan, patch, projection coordinates).
2. Ears (lofted bowls, 2 materials, Subsurf 1, ~4k tris each) with 5 cream blades each; eyes, lid
   liners, nose (fine clay 1 mm).
3. Collar: braided cord (3 twisted strands snapped to the neck), bail, bezel ring + back plate, gem
   dome; antlers: per side a beam snapped over the shoulder + 5 tines, scroll curl, drop (~7k tris).
4. Tail plume: swept tube with fluted section (44 x 110), 5 pointed flicks; numpy-painted colour /
   emission atlas (cream flames with curls, cream tip, glowing swirls and dots).
5. Materials: fur blue / cream (painted strokes, projection glow images, AO), ear outer / inner,
   blades, cord, silver, antler, gem, eye, nose / liner, tail.
Budget split (60k): body 23k, cord 8.6k, tail 10.7k, ears 8k, antlers 6.7k, small parts 7k.
Cameras: the drawings disagree on the tail height (side: plume top above the ear tips; front: no
tail visible between the ears; back: egg top below the ear tips). The side view (main focus) sets
the tail; the per-view angles were fitted on silhouette previews: front el -8 (camera a little
below: the tail drops behind the head), side az 62 el 6, back el 20 (lens 135). Preview fits:
front 0.75-0.77, side 0.745 (clean), back 0.74 before detail work.
Order: silhouette per view, then forms (head, legs), then markings / materials, then details.

### Skills, add-ons and tools
- blender-image-to-3d: method (silhouette, ratios, measured gates).
- scenario-blender-sculpting: bx_sculpt Clay SDF body, nose; Clay.project to snap the cord, antlers,
  eyes onto the surface.
- scenario-blender-retopology: kit.quad_remesh of the voxel body (static asset: auto remesh).
- scenario-blender-texturing-shading: masks into one Principled BSDF's inputs, AO crevices, bump at
  real depth, emission for glow, eye from UVs.
- scenario-blender-expert: 5.2 names, headless rules.
- Helpers: preview script (build() without kit.run, silhouette renders with the kit camera) and a
  clean-overlap script in the work folder.
- Material search: braided leather rope (only flat leather / wicker weaves: not a twisted cord at
  this scale), polished silver (rusty / brushed tiles): none fits the painted style -> procedural.

## Cycles

## Cycle 1
CV (kit): overlap front 0.73, side 0.53 (clean, fox only: 0.739), back 0.76; w/h +5 %, -7 % (clean +1 %),
-15 %. CHECK: floating none, no material none, flat colour none, non-manifold 0, open 0, mirror 0.0038.
65,066 tris (budget 60,000: trim needed). Dimensions 0.212 x 0.639 x 0.527 m.
Matches (keep): overall layout and stance, long legs with navy lower legs, cream throat/chest V and
muzzle, braided cord, pendant with bail / bezel / blue gem, antler beams over the shoulders with tines,
flank haunch spiral and back strokes glowing, tail plume with flicks and cream tip, tan patch.
Differs, cause, fix:
- Height 0.527: the tail top rose above plan (flute ripple + radius); side wants plume top = 1.11 x ear
  tip (0.51 with ears 0.46). Lower the upper centre line 0.015-0.02, ripple 0.035 -> 0.025.
- Front top-centre extra 56 %: the tail shows between the ears (front drawing hides it; the drawings
  disagree, side wins). Lowering the tail reduces it; documented as a drawing conflict.
- Side: ears 0.01-0.015 too low and too far back (magenta above / ahead of the near ear); head and
  back line ~0.008 low; chest 0.006 too far forward (yellow in front of the chest); hind legs and rump
  ~0.01 forward of the drawing. Fix: ear base Y -0.152, tip Z 0.475 and X +-0.108 (more splay, also for
  the back view), torso and head +0.008, chest back 0.006, hind paws +0.01.
- Back w/h -15 %: ears too upright and the egg narrow: splay the ears, widen the plume across X.
- Tail pattern: the side drawing's plume is ~40 % cream (long flames into spirals, cream on the
  outer/top edge of the curl), the back egg has a cream top; mine is mostly plain blue with small
  flames and a cream stripe in the back. Add a cream zone on the outward/upper side of the upper half
  (normal-driven, jagged edge) and bigger flames.
- Clay row: a horizontal shading line across the tail mid-height: check the flute ripple / frames.
- Head front: face reads flat, eyes small; later cycle (forms after the silhouette).

## Cycle 2
Build 2 (this run's first kit build) = the cycle-2 code of the previous builder plus this run's fixes.
Eye study before the build (exp_eye.py on dbg2.blend: eye variants rebuilt on the finished body, front and
side close-ups next to the target crops; exp/e1_*, e2_*):
- Spacing measured on the crops (dark eyelid components, 0.12 m box): ref eye x 0.0174..0.0518, render
  0.0214..0.0556 -> 3.5 mm too far out (not 28 %). EYE_X 0.031 -> 0.0278 (constant; the clay eye seat
  follows it). Brow ovals measured ref +-0.0216 vs render +-0.0228: left as they are.
- EYE_TURN (0.10 / 0.25 / 0.55 / 0.9) changes almost nothing: the lens follows the face. The face at the
  eye already faces az ~33-39 deg. The drawing's eye: the opening faces ~40 deg outward (front 60x53 px,
  side 59x41 px give cos(62-phi)/cos(phi) = 1.27 -> phi ~ 42 deg) while the eyeball looks forward (iris
  round from the front, squashed from the side). So the opening is intrinsically long: W/H ~1.5 ->
  EYE_BT/BB 0.0112/0.0088 -> 0.0102/0.0082; iris painted toward the nose IRIS_C x -0.0028 -> -0.0036.
- Opening shape: pointed tear duct (corner sharpness exponent 0.75 inner, 0.35 outer); the upper
  eyelid's top carried long and high toward the outer corner (front drawing: steep rise at the duct, a
  long nearly straight top line into the wing; ours was a round dome sloping down outward = worried look).
- Wing longer (to 1.60 EYE_A, 0.70 EYE_BT), upper eyelid line thicker (peak 1.8 mm).
- Lens bed: face + clip(fit - face, 0, 0.6 mm) + 0.4 mm (never more than 1 mm over the face: no goggle
  rim), dome 1.6 -> 1.2 mm. Cornea roughness 0.08 -> 0.24 and the second catch light 0.45 -> 0.15 (the
  light streak across the pupil was the sun's reflection on a mirror cornea).
- Stop / bridge between the eyes added to the clay (ellipsoid (0, -0.199, 0.326), r 0.012 x 0.011 x
  0.017): the far eye showed fully over the muzzle in the side view; the drawing hides it but its lashes.
- Cheek cream raised to just under the eyes (cream_field zb +4..6 mm at y -0.225..-0.165); the blue
  bridge V down to the nose stays.
- Side-view face strokes moved 0.008 back (+Y), off the outer eye corner.
Tail study (exp_tail.py: tail rebuilt on dbg2.blend, rendered with the kit camera; tail_cmp.py: same
normalisation as cv compare): with broader locks (root rho 0.90, underfur 0.92), S flow per lock
(s_flow 0.18-0.32 x sin 2 pi t), lift 0.005-0.02, tip locks 4 x 0.045-0.06 m: side overlap (fox only)
0.782 (build 1: 0.739), back 0.757, back w/h -10 %; the tip was a long thin spike, and from the back it
ran down the middle as a cream streak. Then: tip radii fatter (rb/rf/ru at tk 0.78-0.95), plume ru +8-10 %
(tk 0.06-0.58), tip locks s1 1.00-1.045, tip curl up 14 x over^2.
Build 2 result: CV overlap front 0.72, side 0.57 (clean, fox only: 0.813, build 1 0.739), back 0.75;
w/h +11 %, -5 % (clean +3.6 %), -8 %. CHECK: floating none, no material none, flat colour none,
non-manifold 0, open 0, degenerate faces 16 (lock tips / eye rim, harmless), mirror 0.005. 117,870 tris
(budget 120,000). 0.223 x 0.619 x 0.500 m, scale x1.039.
Matches (keep): side eye (cv closeup view 2 box 0 .12 .25 .38) now an almond with the iris at the front,
dark upper eyelid running into a long rising wing, thin lower line, catch light; the far eye no longer
shows over the bridge. Tail reads as fur (overlapping locks, tips in the outline); side outline close.
Differs, cause, fix:
- Front: tail shows beside and over the body (extra middle-left 30 %, middle-right 28 %, top-centre
  44 %): the X widening (+10 %) of the plume. Reverted ru; the top-centre is the drawing conflict (tail).
- Tail tip: a long thin cream spike reaching past the drawing's tip (extra top-right 15 % in the side)
  and, from the back, a cream 'beard' down the middle of the egg (the tip hangs toward the back camera).
  Fix: the last two path points raised 0.01 / 0.02, the tip locks shorter, curl up.
- Tail side: the lower plume is a column with a vertical front edge and a cuff where layer 1 starts;
  the drawing's plume bulges forward at mid-height. Fix: rf at tk 0.06 / 0.14 0.039/0.061 -> 0.047/0.071.
- Tail pattern: cream flames are stripes chopped across locks. Fix: cream locks (fur_cream attribute:
  where a lock's middle line meets cream in the atlas it is cream from there to its tip).
- Side: ear tip too low (ref ear tip / tail top 0.95, mine 0.925) and back: ears too upright. Fix: ear tip
  Z 0.445 -> 0.458, X 0.100 -> 0.104, base / tip 0.005 forward.
- cv.py closeup of view 1 is unusable (the front render's box includes the tail top, so the face sits
  lower): use close.py shots for the front eyes.

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

## Handoff
State: build 3 is the last kit build (CV, compare, renders in the evidence folder); the generator is
exactly what build 3 built (copy: .scratch/assetgen/work/blue_fox_evolution/aethel_fox/snap_gen.py;
debug blend of it: work/dbg2.blend, built by work/dbg2.py). Cycles 2 and 3 in the notes hold the details.
The generator is still one file (not yet split into part modules: builder_guide.md section 8 step 1 is
the next lead's first job).

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
  ~1.5) and its outer half wraps back around the side of the head, the iris painted toward the nose.
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
body (torso, neck, head, muzzle, stop between the eyes, legs, paws with toes, cheek tufts, chest
ruff, elbow tufts, belly fringe: SDF clay -> quad remesh 16,500); ears + ear tufts (5 cream locks per
ear); eyes (eye_left / eye_right); eyelids (eyelid_upper_* / eyelid_lower_*); brow markings (shader,
3D oval per side); nose; cord (3 strands); bail; bezel + plate; gem; antlers (beam, tines, scroll
curls, drop); tail (tail_underfur + tail_fur_lock_00..56). Triangles (build 3, 117,868 of 120,000):
body 34.8k, ears 14.6k + tufts 2.1k, eyes 2.1k, eyelids 2.0k, nose 2.7k, cord 11.5k, pendant 5.1k,
antlers 11.5k, tail 31.4k. Full table: Analysis, "Parts inventory".

### 2. Comparison (build 3)
CV overlap front 0.75, side 0.54 (the kit box holds the small back-view fox too; fox only, work
clean_cmp.py: 0.819), back 0.76; w/h +7 %, -6 % (clean +2.2 %), -13 %. CHECK clean (16 degenerate
faces, mirror 0.0051). 0.223 x 0.613 x 0.500 m.
- Eyes, side (cv.py closeup view 2 box 0 .12 .25 .38; work/exp/b4c_eyes.png bottom row): an almond
  with the iris in the front corner, white behind, thick upper line into a rising wing: reads right.
  Still: the drawing's eye is longer and lower (in the same 0.075 m box: ref ~185 x 85 px incl. wing,
  build ~140 x 120 px); the sclera is peach (#e2cdbd-ish) vs the drawing's light grey #dcd7d2..#c7c2bd.
- Eyes, front (b4c_eyes.png top row, 0.12 m box): spacing right (centres +-0.035 both); eyes read
  smaller and "worried": the upper lid peaks over the inner half and slopes down outward, then the
  wing ticks up; the drawing's top line is high and long toward the outer corner. The lower line is a
  bold full dark line; the drawing's is thin, grey-navy, fading under the iris. Iris covered more at
  the top than in the drawing.
- Face: cream under the eyes rises to the outer cheeks now; the drawing's front muzzle cream is a
  heart / V with the blue bridge down to the nose: close. Nose sits higher under the eyes in the front
  drawing than in the side drawing: drawing conflict, leave.
- Tail, side (closeup view 2 box .45 0 1 .6; exp/b3_close_2_0.45.png): locks, cream flame locks,
  glowing swirls: reads as fur. Differs: lower plume a column with a vertical front edge and a cuff
  where layer 1 starts (the drawing's egg bulges forward at mid height, widest at ~0.35 of its
  height); the tip is one straight cream point ~1.2 x the drawing's length, no hook up at its end and
  no second point under the curl.
- Tail, back (closeup view 3 box .05 .1 .95 .75; exp/b3_close_3_0.05.png): egg width about right; a
  cream 'beard' of tip locks hangs down the middle to the egg's centre (the drawing: cream cap on the
  top third, blue sides with big cream swirls).
- Ears: back w/h -13 %: the drawing's ears splay wider (magenta top-left 27 %, top-right 25 %); side:
  the near ear shows its thin blue back edge, the drawing shows its indigo inner bowl with the spiral
  turned toward the viewer, ear broader and tipped forward.
- Body, side overlay: extra in front of the chest and front legs, missing behind the hind legs and over
  the head: chest ~0.006 too far forward, hind legs ~0.01 forward, head ~0.008 low. Front: the throat /
  chest cream is one large bulging bib between the antler beams; the drawing's cream throat is narrower
  with blue neck sides. Front top-centre extra 37 % = the tail over the head (drawing conflict).

### 3. Next step: part tasks (one lead + part builders; copy each into a job card)
The lead first splits the generator into part modules (builder_guide.md section 8 step 1): suggested
modules: common.py (NT, sweep, smoothstep, bvh_of, set_attr, materials helpers, scale handling), body.py
(body_clay, cream_field, body_attributes, fur_material, mark images), face.py (EYE_* constants,
eye_frame, eye_opening, EyeBed, build_eye, build_eyelids, eye_material, brow_frame / brow_marking,
build_nose, front/side face strokes), ears.py, collar.py (cord, pendant, antlers), tail.py (tail_path,
TailBody, specs, locks, tail_images, tail_material). Harnesses exist for two of them: work/exp_eye.py
(rebuilds the eyes on dbg2.blend with constants as JSON variants, renders front + side close-ups) and
work/exp_tail.py + work/tail_cmp.py (rebuilds the tail on a debug blend, renders kit views 2 and 3 with
the kit camera, overlap and overlay like cv compare).

TASK A. Part: eyes and eyelids (with the brow markings and the face cream around them).
- What it is: see Understanding (the eye). Opening faces ~40 deg out, eyeball looks forward.
- Comparison: as section 2 "Eyes, side / front" and "Face" (b4c_eyes.png; closeup view 2 box 0 .12
  .25 .38).
- What needs doing, and why: (1) longer opening wrapping back around the head: EYE_A 0.0135 -> ~0.016
  with the outer half following the face (the bed already does) so the side eye gets ~1.3 x longer
  while the front stays (front width is foreshortened); keep EYE_BT/BB 0.0108/0.0084 or lower BB to
  0.0078 if the side stays too tall (side h/w target 0.5 incl. wing, front 0.75-0.88). (2) Upper eyelid
  top high and long toward the outer corner (eye_opening's top boost 0.9 -> ~1.3, or move the arch
  peak outward), wing as a continuation of the top line (front: short, slightly rising; side: long). (3)
  Lower eyelid thinner (rv2 0.00028+.. -> ~0.0002) and grey-navy (#4b5068), thicker only at the tear
  duct. (4) Sclera cooler: ramp toward #dcd7d2..#c7c2bd, less duct warmth; check the lid shadow does
  not tint it. (5) Iris: less covered at the top in front (IRIS_C y +0.0006 or BT up).
- Reference crops: work/eyes/t_front_eyes.png (ref_view_1 box 127 291 389 553 = 0.12 m, pairs with
  close.py shot [0,-8,0,-0.205,0.345,0.12]), work/eyes/t_side_eye.png (ref_view_2 80 355 243 518 =
  0.075 m, pairs with [62,6,0.01,-0.21,0.345,0.075]), magnified: eyes/ref1_eyes.png, ref2_eye.png;
  cv.py closeup view 2 box 0 .12 .25 .38 (view 1 closeups are framed differently: use close.py).
- Keep fitting: eye centre X EYE_X 0.0278 (pre-scale; build scales x1.040), Z ~0.327; eyes on the
  FINISHED body mesh (EyeBed), never on the clay; the clay eye seat follows EYE_X; the stop between the
  eyes (clay ellipsoid (0, -0.199, 0.326)); brow ovals +-0.0214; budget eyes + eyelids <= 5k tris.
- Done when: side close-up eye (incl. wing) within 10 % of the crop's length and height, iris in the
  front corner; front close-up eye height and width within 10 % of the crop, top line high toward the
  outer corner (no worried slope), thin lower line, sclera within 0.05 brightness of #d2cdc8; no face
  faces through the eye; the far eye shows only its lash tip beyond the profile in the side view.

TASK B. Part: tail (underfur, guard-hair locks, painted atlas, cream locks, tip).
- What it is: see Understanding (the tail). The tail is fur: never a shell.
- Comparison: section 2 "Tail, side / back" (exp/b3_close_2_0.45.png, exp/b3_close_3_0.05.png; fox-only
  side overlap 0.819 is held mostly by the tail outline; tail test alone exp/t2_cmp.png: 0.825).
- What needs doing, and why: (1) lower plume: bulge forward at mid height and lose the cuff: raise rf
  further at tk 0.14-0.25, spread layer-1 roots (s0 0.13-0.22 -> 0.08-0.24) and give layer 0 longer
  locks reaching past layer 1's roots. (2) Tip: shorter (path end or tip-lock s1), fatter, hooking up at
  its end (TailBody.surface over-run TAIL_TIP_CURL) with a second smaller point under the curl (one or
  two short edge locks at s 0.85-0.95 on the +B side). (3) Back view: no cream beard: the tip locks
  must not hang toward the back camera (raise / shorten them, or curl them up), the cream cap only on
  the top third; blue sides keep big cream swirl locks. (4) Cream share: side drawing ~40 % cream; check
  with cv.py sample on the tail box.
- Reference crops: work/eyes/t_side_tail.png (ref_view_2 560 10 1200 690), work/eyes/ref2_tailgrid.png
  (pixel grid), ref_view_3 egg; cv.py closeup view 2 box .45 0 1 .6, view 3 box .05 .1 .95 .75.
- Keep fitting: root on the rump at path start (0, 0.110, 0.199) pre-scale; tail top 0.4806 pre-scale
  sets the 0.50 m scale (keep within 0.48-0.485 or the whole fox rescales); tail not wider in X (ru)
  than build 3 (wider shows beside the body in the front view); budget 31-33k tris.
- Done when: tail-only kit-camera test (exp_tail.py + tail_cmp.py): side overlap >= 0.83, back >= 0.76
  with no cream below the egg's top third in the middle; tip length within 10 % of the drawing; side
  plume's widest point at 0.3-0.4 of its height; reads as locks of fur up close.

TASK C. Part: ears and ear tufts.
- What it is: see Understanding (the ear).
- Comparison: section 2 "Ears" (back w/h -13 %; side near ear seen edge-on).
- What needs doing, and why: splay the ears outward (tip X 0.104 -> ~0.115-0.12) for the back view's
  width; turn the bowl normal f0 = (side*0.45, -1, 0.1) more outward/forward so the side view (az 62)
  sees the indigo bowl and spiral; broaden the base (~0.055) as the side drawing; keep the front view's
  ear outline (front overlap must not drop).
- Reference crops: ref_view_1 top 30 % (ears), ref_view_2 box 0 0 .35 .35 (cv.py closeup view 2 box 0
  0 .3 .35), ref_view_3 top 35 % (cv.py closeup view 3 box 0 0 1 .35).
- Keep fitting: ear base on the skull at (+-0.044, -0.155, 0.341) pre-scale, tufts follow ear_shape;
  ear tip Z ~0.458 (ear tip / tail top 0.95 in the side drawing); ~16.7k tris.
- Done when: back w/h within 5 % of 0.475 with the ears; side close-up shows the inner bowl and spiral
  as the crop; front overlap >= 0.75.

TASK D (lead or a 4th builder). Part: body silhouette and the throat cream.
- What needs doing, and why: side overlay: chest 0.006 back, hind legs / paws 0.01 back, head and back
  line 0.008 up (cycle 1 measurements, still open); front: narrower cream throat bib (cream_field
  chest wc 0.046-0.06 -> ~0.035-0.045) with blue neck sides. Re-check the eye bed after any head move.
- Reference crops: ref_view_2 whole (side), ref_view_1 box .2 .35 .8 .7 (throat / chest).
- Done when: fox-only side overlap >= 0.85, front >= 0.78, no regression in Tasks A-C.

### 4. Do not undo
Overall stance and leg layout; navy lower legs; cream throat / chest V / muzzle; braided cord,
pendant (bail, bezel, gem), antlers over the shoulders; flank glow markings; tan patch; the eye built
on the finished body mesh (EyeBed), lens <= 1 mm over the face, eyelid lines on top of the eye's edge,
EYE_X 0.0278, iris toward the nose, the long rising wing, the stop between the eyes; the tail as
underfur + guard-hair locks (not a shell) with whole cream flame locks; tail X width as build 3; the
120k budget split.

### 5. Files
- Reference views: production/qa/evidence/blue_fox_evolution/aethel_fox/aethel_fox_ref_view_{1,2,3}.png
- Latest kit compare (build 3): .../aethel_fox_compare.png; renders aethel_fox_view_*.png, clay_*.png
- Work folder (.scratch/assetgen/work/blue_fox_evolution/aethel_fox/): snap_gen.py (= generator),
  dbg2.py -> dbg2.blend (debug build of snap_gen.py), close.py (close-up shots), exp_eye.py (eye
  variants), exp_tail.py + tail_cmp.py (tail in kit views), clean_cmp.py (fox-only overlap),
  eyes/ (target crops t_*.png, magnified ref crops, pair.py, gridcrop.py), exp/ (this run's renders:
  b4c_eyes.png, b3_close_*.png, t2_cmp.png, e1/e2 eye variants). PYTHONPATH=.scratch/pydeps for cv2.

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
- Lead and part builders (user): the builder that reads this Handoff leads; it runs 2-4 part builders
  on Sonnet 5.5 at once (builder_guide.md section 8).
