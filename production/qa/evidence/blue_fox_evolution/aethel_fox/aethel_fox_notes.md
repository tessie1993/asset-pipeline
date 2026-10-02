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

## Handoff
State: build 1 is the last kit build (its CV and compare are in the evidence folder). Since then the
generator holds UNBUILT changes (cycle 2 work, stopped by the user before the kit build): the eyes,
eyelids, brow markings, under-eye strokes and the whole tail were rebuilt; a debug build of them ran
(119,090 triangles, budget 120,000) and close-ups were rendered from it, but no kit build, no CV
compare. The user ended this run to commit. Note: the generator already had un-noted edits after
build 1 (02:10, mostly the eye / face work of the previous builder and the 120k budget); they are
kept and included in the numbers below.

### 1. Understanding
- What it is: Aethel Fox, phase-2 evolution of a stylised blue fox (anime / painted game art: soft
  cel shading, thin navy ink outlines, painted fur strokes). A slim young fox standing square on
  long legs, head up, front -Y, 0.50 m to the tail top. Alive, groomed, nothing worn or dirty;
  variation comes from fur strokes, soft shadows, glowing markings.
- How it is made (as a creature): one furred body over a skeleton (skull, neck, ribcage, pelvis,
  four legs with paws and toes); fur is short and smooth on the body (painted strokes, no locks
  except cheek tufts, chest ruff, elbow tufts, belly fringe); long fur only on the tail.
- The eye (what it is): an eyeball (warm grey-white sclera, big iris with a dark limbal ring and
  radial fibres, a pupil, a glossy cornea whose reflection is the white catch light) in a socket,
  wrapped by upper and lower eyelids; the tear duct sits in the low inner corner. The drawing keeps:
  a large opening (front 60 x 53 px, side 59 x 41 px), long axis rising ~20 deg from the low pointed
  tear duct to the higher outer corner, a thick dark upper eyelid line carried on into a rising
  wing, a thin lower eyelid line, a big grey iris toward the nose (dark slate top under the lid,
  light below with a pale crescent), dark pupil, one white catch light upper-inner. Approach: a domed
  lens (eyeball surface) on a bed measured on the finished body mesh, eyelid lines as flat swept
  lines lying on top, iris painted from the lens UVs.
- The tail (what it is): a fox's brush: a thin tail bone under skin, buried in long fur; dense,
  darker underfur close to the bone; long guard hairs growing from the bone toward the tip, clumping
  into locks that overlap like shingles (locks rooted nearer the base cover the roots of later
  ones), parting where the tail bends; tips lighter, roots darker; the outline is made of lock tips;
  the end is a cream tag. Painted style: broad soft S-flowing locks, cream flame locks curling at
  their ends, pointed tips flicking off the outline, glowing cyan swirls and dots on the lower third.
  Approach: underfur mass + layered mesh guard-hair locks (NOT one smooth shell). The user: "The tail
  is fur."
- Collar (unchanged): braided brown leather cord (three twisted strands), silver bail and bezel,
  deep-blue cabochon gem, silver-white antler branches over both shoulders.

### Part inventory (current, names by what each thing is)
body (torso, neck, head, muzzle, legs, paws with toes, cheek tufts, chest ruff, elbow tufts, belly
fringe: SDF clay -> quad remesh 16,500); ears + ear tufts (5 cream locks per ear); eyes (eye_left /
eye_right); eyelids (eyelid_upper_* / eyelid_lower_*); brow markings (shader, 3D oval per side);
nose; cord (3 strands); bail; bezel + plate; gem; antlers (per side beam + tines, scroll curls,
drop); tail (tail_underfur + tail_fur_lock_00..60: 54 layer locks + 7 edge locks). Full table in the
Analysis, section "Parts inventory" (rows 5, 6, 7, 15, 16 updated this cycle).

### 2. Comparison (latest evidence)
Kit numbers are still build 1: overlap front 0.73, side 0.53 (clean 0.739), back 0.76; w/h +5 %,
-7 %, -15 %; CHECK all clean; 65,066 tris then (now 119,090 in the debug build).
Eyes, build 1 (user: "Both eyes are bad"), measured against the front/side crops: the eyes read as
narrow slits / round buttons: (a) the eye lens lay on the SDF clay but the remeshed body deviates
from it by 1-2 mm, so body faces cut through the eye edges (torn light-blue shards over the eye);
(b) the opening was 0.0256 x 0.0178 (ref 0.027 x 0.020-0.024), tilt 12 deg (ref ~20 deg); (c) iris
only 1.2 mm toward the nose (ref: iris at the inner side, sclera on the outer side), iris colour too
saturated blue (ref grey #61677b mid, #2a2833 top, #b6b8c4 low; sclera warm #c7c2bd..#dcd7d2);
(d) the eyelid wing floated off the face and the lower eyelid line covered only the outer 60 %;
(e) brow markings doubled (front and side decal projections overlapped on the oblique brow);
(f) glowing arcs under the eyes ("smile" lines): the side-image face strokes and front strokes
landed under the eyes instead of small pale strokes behind / beyond the outer corner.
Eyes after the cycle-2 code (debug close-up c2/b2_0, b2_1, BEFORE the last fixes): opening and iris
now read as anime eyes with eyelid lines all round; remaining then: eyes too big and pushed off the
face (the quadratic bed was raised by the worst penetration: goggle look in the side view), too
much white on the outer side in front view, eyelid colour too grey. Fixed in code after that render
(lens bed = max(fit, face) + 0.4 mm; opening 0.027 x 0.020; iris centre -2.8 mm; dome 1.6 mm;
eye seat in the clay 1.8 mm instead of 3.5; eyelid #1b1d30..#2c2e44 roughness 0.6; brow centre by a
front ray on the body, tilt d=(-0.5,0,1)) -> render c2/b3_* (being written when stopped) not yet
judged.
Tail, build 1: one smooth swept shell with ripples and painted flames ("tails are wrong. It's fur").
Cycle-2 tail (c2/b2_2 side, b2_3 back, first version): reads as fur locks now, but locks were thin
ribbons with gaps, spiky tips like a broom, smooth underfur showing at the root. Fixed in code after
that render (fewer, broader locks 0.03-0.078 wide, thicker 8-12 mm, lift 0.01-0.04, edge locks
0.08-0.2, roots at 0.84 of the radius rising to 0.96, sections 10 around) -> not yet judged.

### 2b. Comparison of the latest code (c2/b3 close-ups; pairs ref | render in work/eyes/p_*.png)
Eyes, front (p_front_eyes.png, same 0.12 m box): now anime eyes with eyelid lines all round, iris
toward the nose, a white catch light, no face shards over the eye, brow markings single ovals.
Still differs: (a) eye centres ~28 % too far apart (render +-135 px vs ref +-105 px in the 420 px
pair; check with cv.py closeup after the kit build before moving them: eye_frame X 0.031 -> ~0.026);
brow markings likewise too far out (+-90 vs +-70 px: brow_frame X 0.0214 -> ~0.018);
(b) a light streak runs across each pupil (the second catch light / fibre noise reads as a scratch):
drop hlm2 to 0.2 or move it below the pupil; (c) nose sits only 0.014 below the eye centre in the
front view vs 0.029 in the front drawing (side drawing: 0.017, model 0.020): a drawing disagreement,
leave the nose; (d) muzzle cream starts higher than the drawing beside the eyes: fine for now.
Eyes, side (p_side_eye.png): too round and facing the camera (render h/w ~0.85, ref 0.69 = 59 x 41
px; ref iris sits in the front corner with the white behind it). Fix: eye normal turned out less
(eye_frame n + side*0.25 -> side*0.10), EYE_BT 0.0112 -> 0.0102, IRIS_C x -0.0028 -> -0.0040, longer
rising wing (last three wing points x1.12/1.26/1.40 -> x1.15/1.38/1.60 of EYE_A, y up to 0.6 EYE_BT),
upper eyelid line thicker over the top (rv peak 0.00145 -> 0.0018). The far eye and its eyelid stick
out beyond the face profile like goggles (ref: only a lash tip shows): EyeBed.lens_h should follow the
face (body_h + 0.4 mm) where the face turns away, not the fitted surface; and lower the dome to 1.2
mm. A cyan side stroke lands on the outer eye corner: move the three side_strokes face strokes 0.008
back (+Y).
Tail, side (p_side_tail.png; note the render box is 0.36 m vs the crop's ~0.30 m, so the render is
drawn ~13 % smaller): reads as fur now (locks overlap, tips break the outline, root dark, tips light).
Differs: (1) the lower plume is a narrow column and the upper part a hood: the drawing's plume swells
into a broad teardrop (widest at ~0.35 of its height, width ~0.6 of the height) then necks into the S
and the curl; raise the underfur to 0.92 of the outline and lock rho to 0.90 -> 1.02, and check the
side CV outline; (2) locks run straight and parallel: give them the drawing's S flow (twist/sway
per layer larger, sway sign following the S: lean forward low, sweep back high); (3) the tip is one
straight spike with a broom end: the drawing's tip is a fat cream curl hooking back, down and up into
a main point plus a second point under the curl: make the tip-tag locks wider (0.04-0.06), fewer (4),
and bend their run-on past s = 1 (TailBody.surface over-run: add a curl up at the end, not only the
-Z droop); (4) cream flames are chopped into stripes by the locks: make cream S-locks (whole locks
cream with curled ends) where the atlas flames are, instead of sampling flames across blue locks.
Tail, back (p_back_tail.png): the drawing's egg is smooth, wide and full with a cream top and blue
sides with cream flame swirls; the render shows cream strands hanging down the middle, gaps and lock
tips poking out at the sides: fewer, broader, better overlapped locks (as above), lock tips lifted less
on the sides (lift 0.01-0.04 -> 0.005-0.02 except the edge locks).

### Exactly what changed in the generator (unbuilt; build and check it)
tools/blender/assetgen/packs/blue_fox_evolution/aethel_fox.py:
- EYES section rewritten: EYE_A/BT/BB = 0.0135/0.0112/0.0088, EYE_TILT 20, IRIS_C (-0.0028,
  0.0004), IRIS_R (0.0082, 0.0097); eye_frame (tilt param); eye_opening() (was almond); class
  EyeBed (ray casts on the finished body mesh, quadratic fit, lens_h = max(fit, face) + 0.4 mm);
  build_eye(bed, mat) -> objects eye_left / eye_right (dome 1.6 mm, rim 1.2 mm under);
  build_eyelids(bed, mat) (was build_liner) -> eyelid_upper_*/eyelid_lower_*; build() makes
  body_bvh = bvh_of(body) after the cream mark and an EyeBed per side.
- eye_material rewritten (grey iris ellipse, crescent, fibres, limbal ring, pupil, lid shadow,
  tear duct, two catch lights; no Coat: it does not reach Godot). M_liner renamed M_eyelid.
- Clay eye seat depth 0.0035 -> 0.0018.
- Brow markings: decal brow ovals removed; brow_frame(clay, body_bvh) + brow_marking(nt) (Mapping
  node in object space, X mirrored); BROW_NODES set to the final scale at the end of build().
- front_strokes: the under-eye arcs replaced by 3 short pale strokes beyond each outer eye corner;
  side_strokes: the 2 long cheek strokes replaced by 3 short strokes behind the outer corner.
- TAIL: tail_flicks removed; class TailBody (path, frames, radii, surface(s, angle, rho), past-tip
  run-on); tail_fur_lock_specs(rng) (5 layers 12/13/12/11/6 + 7 edge locks); build_tail_fur_lock
  (n 22 x 10 section, attributes fur_t / fur_w / fur_id, UVs on the tail atlas, REPEAT); build_tail
  = tail_underfur (0.87 radius, 40 around, every 2nd path sample, fur_t 0.12) + locks;
  tail_material rewritten (root dark / tip light ramp, strand grooves, lock-edge darkening, per-lock
  tone, AO, bump).
- Renames: ear_blades -> build_ear_tufts (ear_tuft_*), M_cream_blade -> M_ear_tuft.
- Budget trims: body quad remesh 18000 -> 16500, cord 300 -> 240 rings.
Backup of the generator as of the first cycle-2 debug build:
.scratch/assetgen/work/blue_fox_evolution/aethel_fox/eyes/gen_c2_backup.py (before the last fixes);
the current generator = snap_gen.py in the work folder.

### 3. Next step
1. Making the eye (first priority): apply the eye fixes listed in 2b (spacing, side-view shape and
   facing, iris further forward, wing, goggle edge, pupil streak, side stroke), then build (kit) the
   current generator in the background; open the compare and new close-ups;
   pair each with the target crops (eyes/pair.py) and judge the eyes first (user's priority):
   the eye: opening 0.027 x 0.020 at front view 60 x 53 px ref; iris toward the nose with white only
   as a crescent on the outer side; eyelid lines continuous with the wing attached to the face; no
   face shards over the eye; eye surface level with the eyelids (side view: no goggle rim). If the
   eye is still too large in the front view, lower EYE_A first (0.0135 -> 0.0125), then EYE_BT.
2. The tail is fur (user): check in the side and back close-ups that the locks read as soft broad
   clumps flowing root to tip, overlapping, outline broken into tips, cream tip curling into 2-3
   points (ref tail: main hook at the end, a second point under the curl, flicks on the crown top
   edge and the lower right edge). If locks still look like thin ribbons, raise widths again and
   lower the count; if the underfur shows between locks, raise layer counts or the root rho (0.84).
   Check the side CV outline: locks may grow the silhouette 3-6 %: scale the underfur / rho.
   Then the cream pattern: cream flames should be whole cream locks (consider giving locks whose
   tips sample cream in the atlas a cream body, making cream S-locks with curled ends).
3. Then the cycle-1 outline items still open: lower the tail top 0.015-0.02 (height 0.527 -> 0.50
   before the scale), ears 0.01-0.015 higher and further forward, splay ears more for the back view,
   widen the tail across X (back w/h -15 %).

### 4. Do not undo
Overall stance and leg layout; navy lower legs; cream throat / chest V / muzzle; braided cord,
pendant (bail, bezel, gem), antlers over the shoulders; flank glow markings; tan patch; the eye
built on the finished body mesh (EyeBed), never on the clay; eyelid lines on top of the eye's edge;
the tail as underfur + guard-hair locks (not a shell); the 120k budget split.

### 5. Files
- Reference views: production/qa/evidence/blue_fox_evolution/aethel_fox/aethel_fox_ref_view_{1,2,3}.png
- Latest kit compare (build 1): .../aethel_fox_compare.png; renders aethel_fox_view_*.png, clay_*.png
- Target crops: .scratch/assetgen/work/blue_fox_evolution/aethel_fox/eyes/t_front_eyes.png
  (ref_view_1 box 127 291 389 553 = 0.12 m square at eye height, pairs with close.py shot
  [0,-8,0,-0.205,0.345,0.12]), t_side_eye.png (ref_view_2 80 355 243 518 = 0.075 m, pairs with
  [62,6,0.01,-0.21,0.345,0.075]), t_side_tail.png (ref_view_2 560 10 1200 690), ref1_eyes.png,
  ref2_eye.png (magnified with pixel grid), ref2_tailgrid.png
- Close-ups: .../work/.../c2/cur_*.png (before this cycle), b2_*.png (first cycle-2 code), b3_*.png
  (latest code, if the render finished)
- Scripts: work/dbg2.py (builds snap_gen.py into dbg2.blend, prints TRIS per part; copy the
  generator to snap_gen.py first), work/close.py (blender -b <blend> --python close.py -- '[[az,el,
  cx,cy,cz,size],...]' out), eyes/gridcrop.py (pixel-grid crop), eyes/pair.py (ref crop | render),
  both run with PYTHONPATH=.scratch/pydeps.

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
- Compare to the reference often, part by part, after every change, not only at the end of the
  cycle (builder_guide.md section 6).
- The user doubled the triangle budget to 120,000: spend it on details (body and paws with toes,
  tail locks, ears, antler scrolls, braided cord, eyes, gem).
- Work in one render cycle per run when the user asks; end with a Handoff as builder_guide.md
  section 7 describes.
