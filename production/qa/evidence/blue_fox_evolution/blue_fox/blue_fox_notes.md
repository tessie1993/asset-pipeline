# blue_fox — Blue Fox Creature (Phase 1): builder notes

Fill every section of `## Analysis

### What it is
A small stylised (cel-shaded, soft painted, anime/Pokemon-like) four-legged fox creature standing square on
all four legs, ~0.30 m to the ear tips. One fused furry body: big rounded head with a short pointed muzzle, two
very large pointed leaf-shaped ears (about 1/3 of the total height), slim neck, compact barrel body, four slim
straight legs with small round paws, and one huge bushy leaf-shaped plume tail that rises up-back at ~28 deg
and is as thick (~0.10 m) as the body is tall. Front faces -Y. Colour scheme: light sky-blue fur, cream
muzzle/cheeks/throat/chest/belly, tan inner ears with cream fur tufts, darker blue lower legs and paws, dark
blue spirals on the ears, a cream flame + spiral pattern and cream-white tip on the tail, a cream-tan patch
under the tail. Accessories: a two-strand braided brown leather cord collar with a silver-set round deep-blue
cabochon pendant hanging on the chest. Character read: huge ears + big glossy eyes with white highlights +
gentle closed-mouth smile ("w" mouth) + oversized plume tail + gem pendant. Art style: the reference's own:
smooth stylised volumes, soft painted gradients, subtle painted fur streaks, crisp graphic markings, dark
contour lines (contour ink cannot be modelled; not built, noted).

### Views
Reference = the user's sheet `source.jpg`, top-left panel only (the user: "treat this image as the
reference sheet; the angles are different" -> the three panels are NOT exact orthographic 0/90/180 views:
angles estimated per view, perspective camera).
- View 1, box 190 1105 545 1825, az 0, el 2 (fitted, see Cycles 2-3): front. Only it shows the face
  frontally (both eyes, brow dots, nose, "w" mouth), the collar V and pendant centred, chest cream width,
  leg spacing, ear splay, and the tail tip peeking above the head between the ears + tail sides behind
  the shoulders (tail is wider than the body).
- View 2, box 606 598 1892 1668, az 59, el 13 (derived from the paw/ear parallax in Cycle 1, refined by
  silhouette fit in Cycle 2): the "main focus" view is a 3/4 view from the front-left (+X side, head
  to image left), not a profile: near/far front paws 102 px apart with the far one 35 px higher, near/far
  hind paws 138/32 px, ear tips 253 px apart -> a symmetric fox at az 55-60, el 13 reproduces all of it
  with no head turn and no leg stagger. Only it shows body length, back line, belly line, leg joints
  (elbow, hock), tail curve/thickness and the tail pattern, collar drape, ear inner side with fur tuft.
  CAVEAT: the rectangular box also contains the top of the back-view fox (ears + tail top, x>=1552,
  y>=1232); cv.py keeps every component, so the kit's view-2 overlap is capped (~0.66 when the fox
  itself overlaps 0.75): I measure a clean overlap with the largest component only (clean_cmp.py in the
  work folder) and report both.
- View 3, box 1552 1222 1865 1830, az 180, el -1 (fitted): back. Only it shows the ear backs (dark blue
  patch with light spiral), the tail from behind (egg shape covering the whole body: the tail's
  underside and end, cream end + central blaze + two cream curls), the cream-tan patch under the tail,
  hind leg spacing, cheek tufts from behind.
- Not shown: underside (inferred: cream-tan belly continues between the legs), top of the back (inferred
  smooth light blue), the fox's right side (mirror of the left; tail pattern mirrored with small changes).
- Camera: perspective --lens 135 (silhouette fits: 135/200 beat 85 and 50 in every view; the sheet is
  drawn with little perspective). The three drawings disagree in places (tail height from behind vs
  from the side, head size front vs side): recorded as per-view ceilings, not chased in both.

### Size and proportions
Size anchor: "Approx. 30 cm" = height to the ear tips 0.30 m (side view 1045 px -> 0.287 mm/px; front view
697 px -> 0.43 mm/px; back view 590 px -> 0.51 mm/px). Overall (built target): width 0.145 m (ear tip to
ear tip; tail 0.11) x length 0.385 m (nose to tail tip) x height 0.30 m.
cv.py measure: front w/h 0.48, fill 0.62, symmetry 0.97; side w/h 1.19 (incl. back-fox intrusion; clean
1264x1059 -> 1.19), fill 0.45; back w/h 0.50, fill 0.61, symmetry 0.94. width:height:depth 0.48:1:1.19.
Side-view landmarks (px -> m, Y = (x-1100)*0.305 mm incl. az correction, Z from a ground line tilted by the
camera g(x) = 1642 - 0.118 (x-900)): nose tip Y -0.146 Z 0.181; eye centre Y -0.095 Z 0.192; skull top
Z 0.232; chin Z 0.162; ear tips Z 0.29 (Y -0.066, X +-0.066); chest front Y -0.085 Z 0.10; sternum Z 0.064;
withers Y -0.012 Z 0.139; back Z 0.138; croup Y 0.067 Z 0.134; tail base Y 0.076 Z 0.133; buttock Y 0.09
Z 0.082; belly low point Z 0.065; front paws Y -0.05/-0.06; hind paws Y 0.062/0.048; hock Y 0.079 Z 0.03;
tail mid-line (Y,Z,half-thickness): (0.092,0.139,0.025) (0.107,0.144,0.035) (0.122,0.151,0.044)
(0.153,0.163,0.049) (0.183,0.179,0.041) (0.214,0.197,0.020) tip (0.238,0.20,0).
KEY RATIOS (side view unless named; checked on renders):
- R1 ear length (base to tip) : total height = 0.085/0.30 = 0.28 (front 200/697 = 0.29)
- R2 back height : total height = 0.139/0.30 = 0.46
- R3 belly clearance (ground to belly) : total height = 0.065/0.30 = 0.22
- R4 body length (chest front to buttock) : total height = 0.175/0.30 = 0.58
- R5 tail length (base to tip, straight) : total length = 0.17/0.385 = 0.44
- R6 tail max thickness : back height = 0.098/0.139 = 0.71
- R7 head length (nose to back of skull) : head height = 0.105/0.072 = 1.46
- R8 front: head width over cheek tufts : total width = 290/334 = 0.87 (perspective-inflated)
- R9 front: eye spacing : head width = 105/290 = 0.36
- R10 back: tail width : total width = 210/305 = 0.69

### Close observation
cv.py observe (3 sheets) + magnified crops (face, collar, ear, tail, legs, front face) + samples:
- Fur body (side r2c2, r3c2): smooth soft volumes, subtle painted fur streaks along the flow (back to
  rump, down the legs); top lighter #9bc3d7 (L0.77), flank #89b1c7 (L0.70, dark #6f94ae, light #9cc5d9,
  spread 0.08), head top lightest #a4cbdd (L0.80). Belly/shadow side darker. Small jagged fur tufts where
  cream meets blue on the chest edge (pointed flame tongues), an elbow tuft behind the near front leg
  (Y -0.02 Z 0.07), small fur nicks on the outline of the rump/neck.
- Lower legs & paws (r3c1, r3c2): darker, slightly greyer blue #6d90ad (L0.58) on the shins, paws
  #6787a9 (L0.55); gradient from body blue above the elbow/hock to this; paws round, 2 short toe grooves on
  the top front of each paw (3 toes), no pads visible; far legs darker (shadow).
- Head: muzzle top blue down to the nose; cream lower face #c5b3a1 (muzzle) to #d0c0ae (cheek, light
  #e6d6c6, L0.73-0.82, spread 0.07); cream/blue border runs from just above the nose, under the eyes, to
  the cheek ruff whose rear edge has 2 pointed tufts each side (seen from front and back as side spikes).
  Brow dots: two cream ovals #dad4cc above the eyes (0.009 x 0.0045 m). Nose: small dark rounded triangle
  #3b3535-#5a4f50 with a soft light top highlight. Mouth: thin dark "w" smile line under the nose, upturned
  ends.
- Eyes (front crop): big, round-oval; cream sclera visible on the outer side (#e0d6cc); iris grey-brown
  #6d6a70 graded darker at top; large dark pupil #3a3941; white round highlight upper-inner + small
  lower-outer reflection; thick dark upper lid line extending outward into a small wing; thin lower line.
- Ears (ear crop): big pointed leaves, thin (~3-4 mm rim), cupped, opening forward-outward; inner face
  tan #b69c8d (dark #8f7060 deep in the cup, L0.36-0.86, spread 0.12) with a cream fur tuft #dacbb6 of 3
  pointed spikes rising from the inner base; light blue rim band around the inner face; upper third of
  the inner face blue with a dark blue (#2b3d63-#505c79) spiral (1.5 turns) + curved tail stroke; tip
  darker blue (#4a6a9a). Ear backs light blue #92b8d1 with a dark blue patch #4a6695-#6d8db1 holding a light
  blue spiral (back view), plus a dark curved stroke on the far ear back in the side view.
- Tail (tail crop, back view r1c2-r2c3): leaf-shaped plume, light blue #92bad2 (L0.73) with long painted
  streaks along its length, underside and base darker #5b7a98 (back view lower half #496687, L0.42);
  cream pattern #c9c0b9-#d9d1cd: a flame band along the top edge from mid-tail to tip with 3-4 tongues
  pointing back toward the base, one big spiral curl (r ~0.015) in the distal half, a cream swoosh along
  the lower edge; the tip all cream-white #d9d1cd (L0.84, grey shading #908282 in folds) with 3 pointed
  tufts (main tip up-back, one spike on top, one hook below). From behind: cream blaze down the centre with
  tongues + two cream curls left and right.
- Undertail patch (back r3c2): round cream-tan #826d5f-#9d8b81 patch (0.04 m wide) below the tail base,
  above the hind legs. Belly patch (side r3c2): tan #9f8b7d between the legs, soft edge.
- Collar (collar crop): 2-strand twisted rope, each twist a lozenge with highlight #c08a64 on top, mid
  #9a6a4c, dark grooves #5e3e2c between twists, ~0.0055 m thick, ~8 twists per 0.03 m; drapes from the
  nape down to the chest front, slightly loose.
- Pendant: silver bezel ring #c8c8d0 (dark #707078 inner edge, bright rim highlight), deep blue cabochon
  #20378b (dark #111f6a at the rim, lighter blue centre, crisp white highlight upper-left); small silver
  bail ring joins it to the cord.
- Imperfections / variation: fur streak strokes irregular; cream edges jagged and not symmetric; the two
  tail-side curls differ in size; ear spirals left/right mirrored but not identical; slight tone patches
  on the flank; darker crease at the elbows/armpit and where the legs meet the belly; paws slightly
  different sizes in view.

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it (technique, skill) | geometry detail (what is modelled: bevels, creases, folds, holes, relief) | nuances (imperfections, asymmetry, how each copy differs) |
|---|---|---|---|---|---|---|---|
| 1 | head (cranium + muzzle + jaw) | 1 | 0.072 h x 0.105 l x 0.07 w | centre (0,-0.085,0.198); nose tip (0,-0.146,0.181) | SDF clay (bx_sculpt Clay): cranium ellipsoid, muzzle round-cone, lower jaw cone, smooth blends | brow ridge over the eyes, eye sockets, stop between muzzle and forehead, mouth crease (shader line + shallow groove) | slight jaw asymmetry none (front symmetric); blue/cream border jagged |
| 2 | cheek ruff tufts | 2 sides x 2 spikes | spikes 0.012-0.018 long | sides of head behind the mouth, Z 0.17-0.18, pointing out-back | SDF round cones blended into cheek ellipsoids | pointed tuft tips, groove between spikes | upper spike longer than lower; left/right spikes rotated differently (seeded) |
| 3 | ears | 2 | 0.088 long, 0.048 wide, 3-5 mm thick | base (+-0.045,-0.06,0.212), tips (+-0.066,-0.066,0.292), opening facing forward-outward 25 deg | custom SDF gothic-arch leaf, cupped (bent), hollowed bowl on the inner face, blended into the skull | rim thickness, inner bowl depth ~4 mm, rounded tip | ears splayed 14 deg, mirror copies with seeded 2 deg tilt difference |
| 4 | ear fur tufts | 2 x 3 spikes | 0.012-0.022 long | inner base of each ear, rising up-out | SDF cones inside the bowl (fused) | pointed tips | spike lengths differ per ear (seeded) |
| 5 | eyes | 2 | 0.022 x 0.020 lens | (+-0.023,-0.104,0.193), facing forward-out 18 deg | separate flattened sphere set into a socket, painted texture (sclera/iris/pupil/highlights/lid line) | socket in the head clay, upper lid ridge | gaze aimed slightly differently per eye (highlight mirrored, offset) |
| 6 | nose | 1 | 0.013 w x 0.008 h | tip of muzzle (0,-0.148,0.183) | separate rounded-triangle ellipsoid blob | nostril dimples (shader) | - |
| 7 | neck | 1 | r 0.03 | from head base to chest | SDF round cone | throat curve | - |
| 8 | torso: chest, ribcage, loin, hips | 1 | 0.175 long x 0.07 wide x 0.078 deep | Y -0.09..0.09, Z 0.064..0.143 | SDF ellipsoids smoothly blended | waist tuck before the hips, chest keel, rump | belly line rises toward the hind legs |
| 9 | chest fur tufts | 3-4 | 0.008-0.015 | front-lower chest edge and elbow backs | SDF small cones | pointed | different lengths (seeded) |
| 10 | front legs | 2 | 0.13 tall, 0.022 -> 0.014 thick | X +-0.024, near (+X) Y -0.050, far (-X) Y -0.060 | SDF tubes shoulder-elbow-wrist | elbow bump, slim wrist | far leg 1 cm forward (stance) |
| 11 | hind legs | 2 | thigh 0.04, shin 0.015 thick | X +-0.031, paws Y 0.062 (+X) / 0.048 (-X) | SDF thigh ellipsoid + tubes hip-stifle-hock-paw | stifle forward, hock back angle | stance differs per side |
| 12 | paws | 4 | 0.028 l x 0.02 w x 0.014 h | under each leg, flat sole at Z 0 | SDF ellipsoid clipped flat at the ground | 2 toe grooves each (3 toes) | sizes differ 3 % (seeded) |
| 13 | tail | 1 | 0.17 long, up to 0.098 thick, 0.11 wide | from croup (0,0.076,0.133) up-back to tip (0,0.238,0.20) | SDF chain of 14 oriented ellipsoids smoothly blended along a curve | leaf profile, belly of the plume, tip tufts | - |
| 14 | tail tip tufts | 3 | 0.015-0.03 | tip, top spike, lower hook | SDF cones | pointed, curved | each different |
| 15 | collar cord | 1 (2 strands) | strand r 0.0016, cord 0.0055 thick, loop ~0.2 long | around the neck: nape (0,-0.03,0.158) to chest front (0,-0.095,0.118) | two helices twisted along a closed path projected 2.8 mm outside the clay surface, bmesh tube sweep | twist lozenges, grooves | twist pitch jittered 5 % |
| 16 | pendant bezel + back plate | 1 | outer r 0.0105, 0.004 thick | hanging under the cord at the chest front (0,-0.104,0.104), facing forward-down | lathe profile (kit.lathe) | raised rim, inner lip | - |
| 17 | gem cabochon | 1 | r 0.0082, dome 0.004 | in the bezel | lathe dome | smooth dome | - |
| 18 | bail ring | 1 | r 0.0025, wire 0.0011 | top of the bezel, linking the cord | torus | - | - |

### Materials and shaders
All body markings are painted into the body's own UV texture from python fields evaluated at every texel's
3D position (bx_materials TexelMap; procedural fields, never the reference image): crisp, jagged-noise edges
at texture resolution. The shader then adds fur streak variation and bump; the final build bakes.
- S1 blue fur (body, head, legs top, tail, ear backs): stylised soft fur, roughness 0.75-0.9 (matte, no
  gloss). Colours: top #a2c9dc, flank #8fb7cc, underside #7ea4bd, head top #a8cde0 (sample means L0.70-0.80,
  spread 0.08). Relief: fine fur streaks 0.3-1 mm, along the flow (body along Y, legs along Z, tail along its
  axis): anisotropic noise from a flow-aligned attribute frame -> colour +-6 % and bump 0.0004 m. Patchy
  light/dark tone noise (scale 0.03 m, +-4 %).
- S2 dark leg blue (lower legs, paws): #6d90ad -> paws #6787a9, soft gradient over 0.03 m into S1; darker
  in toe grooves (AO-like), same fur streaks vertical.
- S3 cream fur (muzzle, cheeks, throat, chest, belly, brow dots, tail pattern): #d4c4b2 (cheek) to #c8b6a4
  (chest), belly darker tan #b09a88 (sample #9f8b7d under shadow), brow dots #ddd6cc; jagged flame edge
  (noise 2-4 mm) on the chest/cheek borders, crisp edge elsewhere; roughness 0.85.
- S4 tail cream/white: #ddd6d1 tip with grey folds #b8b0ac in the tip tufts, pattern #cfc6bf; streaks.
- S5 ear inner skin/fur: tan #b69c8d, darker #94786a deep in the bowl, lighter #c9b19f toward the rim; ear
  tuft cream #dacbb6; roughness 0.8.
- S6 dark blue markings (ear spirals, ear tip, ear back patch): #3c5383 stroke, tip gradient #557ba6; ear
  back patch #4f6c9a with light spiral #93b9d3; crisp edges.
- S7 undertail patch: cream-tan #a8927f centre to #8c7767 rim, soft edge 3 mm.
- S8 eyes: sclera #e2d8cd, iris grey #77737a -> #5a565e top, pupil #2e2c33, highlight white #ffffff
  (also emission-free), lid line #262028; roughness 0.08 on the eye (wet gloss), 0.5 on lid line.
- S9 nose: #3e3436 with lighter top #6a5b5d, roughness 0.35 (slightly moist sheen).
- S10 braided leather cord: procedural principled: brown #9a6a4c, per-strand twist gradient (lighter crest
  #c08a64, darker grooves #5a3b2a from a per-vertex 'twist' attribute), leather grain noise bump 0.0002 m,
  roughness 0.5-0.65 varied.
- S11 silver (bezel, bail): metallic 1, #cfd0d6 base with slight blue tint, roughness 0.22-0.35 noise,
  micro-scratch bump (stretched noise 0.00005 m), darker in the inner lip.
- S12 gem: deep blue #1c3590 -> rim #0f1f66, lighter centre #3a5ec8 (radial gradient from attribute),
  roughness 0.04, small internal speckle variation; reads glossy under the studio lights (Godot gets base
  colour + low roughness).

### Details and nuances
- Brow dots: two cream ovals above the eyes (painted S3).
- Eye highlights: big white dot upper-inner + small one lower-outer (painted in eye texture).
- Upper eyelid dark line with small outer wing; lower lid thin line (painted, lid ridge modelled).
- "w" smile mouth line under the nose with upturned corners: shallow groove in clay + dark painted line.
- Nose highlight on top (painted gradient).
- Cheek ruff tufts: 2 pointed spikes per side (modelled).
- Ear: cream fur tuft spikes inside (modelled), tan bowl darker deep inside (painted gradient), blue rim
  band (painted), dark blue tip gradient (painted), spiral + stroke on inner upper third (painted), dark
  patch with light spiral on the back (painted); left/right spirals mirrored, centre offset 1 mm (variation).
- Chest/cheek cream edges jagged like fur (noise in the field), tufts on the chest edge (modelled).
- Elbow tufts behind the front legs (modelled).
- Lower legs darker blue gradient; toe grooves (modelled + darker paint).
- Tail: flame band with tongues, big spiral curl, small hooks, lower swoosh (painted); cream-white tip with
  3 tufts (modelled) and grey shading in folds (painted); underside darker (painted gradient); right side
  pattern a variation of the left (offset 4 mm, different curl size).
- Undertail cream-tan patch (painted, soft edge).
- Belly tan between the legs (painted).
- Fur streaks everywhere along the flow (shader noise + bump), patchy tone variation (noise).
- Collar: 2 strands twisted, highlight per twist, dark grooves (modelled twist + attribute shading).
- Pendant: bezel rim + inner lip (modelled), gem dome (modelled), gem gradient + highlight (shader +
  gloss), bail ring (modelled).
- Not built: the reference's dark ink contour lines (a drawing convention, not a surface).

### Skills, add-ons and tools
- blender-image-to-3d: the gated method (silhouette and ratios before detail; measured mismatches;
  inferred sides listed), creature notes (ribcage/pelvis masses, hock vs stifle, tail as a tube).
- scenario-blender-sculpting (bx_sculpt): signed-distance `Clay` for the whole fused body (ellipsoids,
  round cones, tubes, smooth blends, custom gothic-arch ear SDF, sockets and grooves with `sub`, mouth
  groove with `Clay.stroke`, flat soles with `intersect`), meshed by OpenVDB (voxel 1 mm).
- scenario-blender-retopology: static asset -> automatic reduction is acceptable; Decimate (collapse) to
  31k triangles keeps the thin ears and tufts that a uniform quad remesh at this budget would tear.
- scenario-blender-texturing-shading (bx_materials): `TexelMap` + numpy fields paint colour,
  roughness and height into the body's own UVs (procedural, seam-proof, crisp edges at texture
  resolution); masks drive colour, roughness and height together; principled-input mixing only (no Mix
  Shader); data maps Non-Color.
- scenario-blender-expert: Blender 5.2 API traps (Mix node sockets by index, Specular IOR Level,
  headless operators), audit habits.
- Kit: kit.principled, kit.uv_node, kit.attribute (nose, gem, cord lobes), kit.lathe (pendant), kit.clean,
  kit.mesh_object; CV tools measure/observe/sample/closeup/compare; own helpers in the generator
  (value-noise fbm, polyline/spiral stroke masks, tube sweep, collar ray-projection).
- Library materials: searched leather (polyhaven:brown_leather, ambientcg:Leather037/038) and silver
  (cgbookcase:BatteredMetal01, blendkit brushed aluminium); the reference's cord and setting are
  smooth stylised surfaces, so both are procedural principled materials (grain/scratch noise bump,
  roughness variation) rather than scanned sets whose pattern scale does not match a 5 mm cord.

### Build plan
1. Build 1: full first pass (clay body, eyes, nose, collar, pendant, painted markings) -> read outline
   overlap per view, w/h, missing/extra regions; fix proportions first (head size, tail size/angle, leg
   lengths, ear size), check the camera angles (az/el per view, lens).
2. Build 2-3: proportions and silhouette to overlap >= 0.90 (view 2 judged on the clean largest-component
   overlap), key ratios within 5 %.
3. Build 4-5: markings and materials against `cv.py sample` (cream borders, tail pattern, ear spirals,
   leg darkening, brightness within 0.05), details (toe grooves, tufts, mouth, eye highlights).
4. Handoff after 5 builds if not done; then final `--final` bake build and report.

## Cycle 1
Build 1: 41,424 tris; CHECK clean (no floating, no flat colour, 0 non-manifold, mirror 0.0026).
CV overlap: view 1 0.77, view 2 0.56 (clean, largest component only: 0.647), view 3 0.84; w/h +6 %, +6.4 %,
-6.1 %.
What matches (keep): fused clay body reads as the fox; ears cupped with tan bowl, cream tufts, spirals;
eyes (iris, pupil, highlights, lid line); nose; cream face/throat/chest from the front; braided cord +
silver/gem pendant; dark lower legs; undertail patch.
What differs, measured on the clean overlay/column profiles:
- View 2 camera was wrong. Re-derived from the reference itself: near/far front paws are 102 px apart and
  the far paw 35 px higher, near/far hind paws 138 px / 32 px, near/far ear tips 253 px apart. A
  symmetric fox reproduces all of these with az 55, el 13 (lateral factor cos55 = 0.57: 0.047 m leg
  spacing -> 94 px; depth 0.82 x 0.047 x sin13 -> 30 px; ear tips +-0.067 -> 0.077 m apart) and no head
  turn or leg stagger. Silhouette camera fit on the build-1 mesh agrees (az 65-70 el 18-25 beat az 75 el
  10). So: view 2 -> az 55, el 13; all side-view landmarks recomputed with
  u = 0.819 Y + 0.574 X, v = 0.974 Z - 0.184 X + 0.129 Y (s = 0.287 mm/px).
- Consequences (new design numbers): body 14 % longer (chest Y -0.086 to buttock 0.115), head higher
  and bigger (skull top Z 0.241, nose Y -0.156 Z 0.191, eye centre (+-0.0235, -0.113, 0.207), chin Z
  0.171), ear tips (+-0.067, -0.064, 0.30), front paws Y -0.05/-0.053, hind paws Y 0.066-0.071 (no
  stagger), hock (0.082, 0.031).
- Tail too low and too small: at 75 %/85 % of the side width the reference tail edges sit 0.10-0.12 of
  the height higher (top 0.862/0.891 vs 0.755/0.776). Recomputed tail line (base Y 0.096 Z 0.133 -> tip
  Y 0.285 Z 0.193, max half-thickness 0.047-0.052) and raised 8 deg about its base as a compromise with
  the back view, where the tail egg top reaches 0.886 of the height (needs a lower camera: back view
  el -6). Tail lateral radius 1.15 x vertical (back view width 0.107 m).
- View 1: extra top-centre 25 % = the tail dome showing above the head (reference shows only a small
  tip); missing middle-left/right 15-17 % = the tail sides behind the shoulders + wider cheek tufts.
  Front elevation lowered 12 -> 7 (tail tip at 0.846 of the height needs ~7 deg), tail wider.
- View 3: render narrower (w/h -6 %), tail egg too low (render top 0.79-0.81 vs 0.85-0.87 at the centre).
- Materials: tail curls/flame not readable in view 2 (only the cream tip and noise blotches): the pattern
  chart (phi x r, s x L) put the curls at phi 72 deg, mostly beyond the visible side at az 75; re-check
  after the tail change. Render 0.03-0.05 lighter than the reference overall (ref L0.60/0.62/0.56 vs
  0.63/0.66/0.61): darken fur colours ~5 %.
Fixes for build 2: view 2 az 55 el 13, view 1 el 7, view 3 el -6; torso/head/legs/tail/collar to the
recomputed numbers; fur colours -5 %.

## Cycle 2
Build 2 (az 55 el 13 side, front el 7, back el -6; lens 85): 41,424 tris, CHECK clean, mirror 0.0012.
Overlap view 1 0.80, view 2 0.58 (clean 0.655), view 3 0.80; w/h +1 %, -2 %, -4 %.
What improved (keep): front w/h now +1 %; tail top edge follows the reference in view 2; body length and
paw spacing consistent with the az 55 geometry; tail curl now reads.
What differs:
- View 2: the far ear rendered as a thin needle above the head (it was seen edge-on: its opening faced
  (-0.42,-0.90), almost in the plane of the az-55 camera). The reference shows the far ear's BACK and the
  near ear's full inside -> ear opening normal turned to (+-0.80, -0.60).
- Camera fit on the build-2 mesh (silhouette renders, clean overlap): side az 60 el 13 lens 135 0.761 vs
  az 55 el 13 lens 85 0.677; lens 135/200 beat 85 and 50 in all views (front el 0-4 0.80-0.83 vs el 7 0.79;
  back el 0 0.838, -3 0.827, -6 0.797). The reference is drawn with little perspective -> lens 135;
  view 1 el 2, view 2 az 59 el 13, view 3 el -1.
- Overlay at the fitted camera (ovl2.png): reference ears wider and their front edge further forward
  (~0.006 m); skull top ~4 mm higher; throat/chest front ~6 mm further forward; back line ~4 mm higher and
  belly higher (yellow under the belly); rump/buttock ~15 mm too far back (yellow behind the thigh and
  under the tail root); front paws ~4 mm too far back, hind paws ~6 mm too far forward.
- View 3: render narrower (w/h -4..-7 %): tail lateral radius 1.15 -> 1.25 x; view 3's top-centre
  rendered 0.24 darker: from behind the reference shows the tail's UNDERSIDE carrying a cream blaze from
  the tip down to the middle with a curl each side -> added an underside blaze + two underside curls to
  the tail pattern (the side view's lower swoosh moved to phi 110-120 deg where it belongs).
- Materials: front L0.60 = reference; side 0.65 vs 0.62 (tail top lighter); back 0.53 vs 0.56.
Fixes for build 3: ears (normal, half width 0.027 -> 0.030, base 6 mm forward), cranium +4 mm, chest
forward 4 mm, torso +4 mm, belly keel +4 mm, hips/thigh 8/6 mm forward, paws (front -0.060, hind 0.066),
tail wider; views 1 el 2, 2 az 59 el 13, 3 el -1, lens 135.

## Cycle 3
Build 3 (lens 135; view 1 el 2, view 2 az 59 el 13, view 3 el -1): 41,423 tris. Overlap view 1 0.82,
view 2 0.66 (clean 0.751), view 3 0.84; w/h +1.8 %, -1.2 %, -1.3 % (all within 3 %).
CHECK: non-manifold edges 3, open edges 6 (new: decimation at the thin, wider ears) -> repair pass after
decimation (delete verts on >2-face edges, fill holes).
What matches (keep): proportions (w/h within 2 % in every view), far ear now shows its back in view 2,
body/legs/head placement, tail line and size in view 2, egg-shaped tail from behind.
What differs:
- View 1: ears too narrow from the front (opening normal (0.80,-0.60) shows the inner face at 53 deg;
  reference front ear width ~110 px = 0.047 m at mid-height vs ~0.036 rendered) -> normal (0.68,-0.73),
  more cup (9 -> 13) so the far ear in view 2 still reads broad from its curled rim.
- View 1 colour zones: cream (#cdbdaf, 25 % of the reference) rendered at x0.28 of its area: the cheeks
  under the eyes and the chest V are cream on the reference (chest ~0.065 m wide); rendered cheeks blue,
  chest strip narrow -> head cream boundary at the eye bottom on the cheeks (Z 0.195), chest width
  0.028-0.036 m.
- View 2 tail (closeup_2): reference distal ~35 % of the tail cream (tip + flame band along the top with
  hooks pointing back), big curl ~0.045 m across; rendered tip cream from s 0.80 only, curl 0.032 m, top
  band hidden on the top -> tip from s 0.70, top blaze widened toward phi 60 deg, curl radius 0.024 with a
  0.002-0.005 m stroke.
- View 3 (closeup_3): reference egg = cream upper part with a central tongue down and two curls left/right
  at mid height, darker lower part; rendered a large cream underside diamond and blue top -> underside
  blaze reduced (s >= 0.62, narrower), top blaze from s 0.30 so the egg top reads cream, underside curls
  at phi +-110 deg / s 0.50, swoosh at phi +-135 deg / s 0.45-0.88; fur streak contrast on the tail lowered
  (ripple lines when looking down the tail axis).
- Brightness: view 1 0.58 vs 0.60, view 2 0.64 vs 0.62, view 3 0.57 vs 0.56 (within 0.05).

## Cycle 4
Build 4: 41,424 tris; CHECK clean again (non-manifold 0, open 0 after the repair pass), mirror 0.0011.
Overlap view 1 0.80 (clean 0.804), view 2 0.66 (clean 0.751), view 3 0.84 (clean 0.841); w/h +6.9 %,
-1.2 %, +2.1 %.
What improved (keep): tail pattern now reads in view 2 (top flame band from s 0.35, curl on the side,
cream tip) after making the tail chart continuous (nearest point on the centre-line segments, not the
nearest of 64 samples: that quantised s into 3.7 mm steps = the blocky edges and the ring stripes seen
from behind); cream face/chest wider; ears broad from the front; manifold mesh.
What differs:
- View 1 w/h +6.9 %: ear tips too far out (X 0.073; reference ear tips over the outer cheek line) and the
  ears too short relative to the height (reference ear tips higher) -> tips X 0.068, Z 0.312.
- View 1 cream zone still x0.35 of the reference's area: the reference's lower head is cream across the
  whole cheek width and the chest V reaches the shoulders -> cheek cream back to Y -0.058 above Z 0.175,
  chest width 0.030/0.036/0.040 m at Z 0.10/0.12/0.14, boundary further back.
- View 2: hindquarters still bulge behind the thigh (yellow, ~10 mm) -> hips/thigh 8 mm forward; the
  reference neck/withers line is higher behind the head (magenta between ear and back) -> nape/withers
  mass added; ears slightly small -> longer.
- View 3: the egg seen from behind is the tail's UNDERSIDE and its end (a rising tail's top faces away),
  so the reference's cream upper egg = the cream end region and the central blaze = an underside blaze
  -> tip cream from s 0.62 all round, underside blaze from s 0.45 (au < 1.3) with tongues toward the base;
  side curl moved to s 0.50, r 0.021 so the tip does not swallow it. Undertail patch rendered small and
  dark brown -> radius 0.021, lighter cream-tan.
- Brightness within 0.03 in all views (0.58/0.60, 0.65/0.62, 0.57/0.56).

## Cycle 5
Build 5: 41,424 tris (budget 45,000), CHECK clean (0 floating, 0 without material, 0 flat colour, 0
non-manifold, 0 open), mirror 0.0011. Overlap view 1 0.83 (clean 0.827), view 2 0.66 (clean 0.749),
view 3 0.85 (clean 0.847); w/h +2.6 %, -1.8 %, -0.8 % (all within 3 %).
Brightness: view 1 0.58 vs 0.60, view 2 0.65 vs 0.62, view 3 0.58 vs 0.56 (within 0.05).
What matches (keep): proportions and w/h in all views; ear shape/size/splay; cream face, cheeks and chest;
dark lower legs; undertail patch now a visible cream-tan disc; tail flame band + curl + cream end in
view 2; collar now a darker brown (#45291b/#8a5a3d/#b27a55 ramp).
What still differs (measured):
- View 2 (clean 0.749): reference head/near ear larger and further forward (magenta around the near
  ear's front edge and the skull top, ~6-8 mm); hindquarters/thigh back edge still ~6 mm behind the
  reference (yellow); tail lower edge near the root lower than the reference; front legs ~4 mm behind.
- View 1 (0.83): missing middle-left/right 11-13 % = the tail's sides that the reference shows beside the
  shoulders (our tail is hidden behind the body from the front at el 2: the reference draws the tail
  ~0.12 m wide at neck height there), ear tops (top-left/right 12-13 %); cream zone area x0.39 of the
  reference (cheeks/chest still narrower than drawn).
- View 3 (0.85): reference ear tips higher and wider (top-left/right 12-13 %); the egg's top reads blue
  in the render where the reference is cream (top-centre darker by 0.10): the tail's distal top would
  have to face backward (curl the tip up/forward) to show from behind.
- Not yet done: the final --final bake build, the Report, `pack.py done`.

## Cycle 6
(New builder, continuing from the Handoff.) Build 6: 43,728 tris (budget 45,000; collar strands now ring 8),
CHECK clean (0 floating, 0 without material, 0 flat colour, 0 non-manifold, 0 open), mirror 0.0012.
Kit overlap view 1 0.92, view 2 0.69 (clean, fox only: 0.79), view 3 0.89; w/h +2 %, -0 %, -1 % (all within 3 %).
Brightness: view 1 0.58 vs 0.60, view 2 0.65 vs 0.62 (tail too cream), view 3 0.58 vs 0.56.
Before building I compared the cycle-5 renders with the reference side by side, cropped to the same height
(sbs.py), plus outline profiles per column/row (prof.py) and silhouette fits of debug builds (fit3.sh: dbg
build + camfit + camscore + ovl, no kit build). Changes and why:
- Head 14 % wider, 12 % taller, 5 % longer (scaled about the back of the skull: h()/hr() with HEAD_PIV,
  HS = 1.14/1.05/1.12): the reference head spans 0.87 of the front width and its head is ~20 % taller in
  view 2. Brow mass 4 mm forward, thicker muzzle and jaw (view 2 forehead/chin 8-9 mm behind the
  reference). Eyes 0.0118 -> 0.0128 radius, socket and lid ridge scaled.
- Ears: half width 0.030 -> 0.034, bases closer to the centre (X 0.032) and 5 mm forward, tips
  (+-0.071, -0.071, 0.315); opening normal (0.60,-0.80): the front view's ears are wide with their inner
  edges 0.02 m apart over the skull; the outer edges were 5 mm too far out at mid height.
- Cheek ruff: three fat tufts per side (base r 0.009-0.012) instead of two needles; tips at |X| <= 0.046
  (they were the widest thing in the back view).
- Chest: extra full chest mass 9 mm forward (view 2 chest front 9 mm behind), neck thicker, back 3-4 mm
  higher, belly 2 mm lower, hips/thighs 4-8 mm forward, hind paws Y 0.056-0.057, front paws -0.067/-0.068.
- Legs 12-15 % thicker (reference legs ~20 % thicker in front and back); paws X 0.020 (front) and 0.0265
  (hind) with the upper legs kept wider: both front and back views draw the paws closer than the shoulders.
- Tail: taper plume instead of a balloon: centre line rising more at the end, radius per point
  (TAIL_RZ) re-fitted from the view-2 column profiles (mid thicker, distal end thinner underneath, tip
  lower), lateral factor per point TAIL_W 1.0-1.25 (it was 1.35 everywhere: the back-view egg was
  wider than the reference and the far side of the wide tail stuck up above the root in view 2).
- Collar braid thicker (strand r 0.0019, offset 0.0015, ring 8) so the lozenges read.
- Camera: lens 135 -> 200 re-recorded for all views (silhouette fits on the new shape: view 1 0.922 vs
  0.915, view 3 0.895 vs 0.888 with w/h -1.5 % instead of -3.9 %, view 2 0.791 vs 0.798). The front/back
  w/h disagreement at 135 (+2.7 % / -3.9 % with the same ears) was perspective: the ears are near the
  camera in the front view and far in the back view.
What matches (keep): outline in views 1 and 3 (0.92 / 0.89), proportions, head size, ears, legs, chest.
What differs (measured):
- View 2 ears: the reference shows the NEAR ear tip 0.025 of the height above the far one; a symmetric fox
  at az 59 el 13 (el confirmed by the paw parallax) always puts the far ear 0.024 m higher (X spread x
  sin el). The drawing tilts the head toward the viewer; a 13 deg head roll would break the symmetric
  front view (symmetry 0.97), so this stays a recorded ceiling of view 2 (also the kit number includes the
  back-view fox inside view 2's box: kit 0.69 = clean 0.79).
- Tail pattern: the render's distal 40 % was all cream (tip from s 0.62): the reference tail is blue with a
  cream flame band along the top, a big cream spiral in the middle of the distal half, a cream swoosh
  along the lower side and only the last ~18 % cream. View 2 top-right 0.13 lighter. From behind the
  reference egg is blue with a central cream blaze and two curls at mid height; render was mostly cream.
- Belly tan ran down the inner hind legs (back view tan stripes): belly mask now needs a downward normal
  and Y < 0.05.
- Inner ear: tan reached 85 % of the ear; the reference has tan on the lower ~half, the upper part mid
  blue with a big dark spiral, and a wide blue rim.
Fixes for build 7: tail pattern redone (tip from s 0.80, flame band s 0.40-0.95 over |phi| < 1.35,
spiral r 0.019 at phi 1.42 s 0.60, swoosh at phi ~1.95 from s 0.36, underside blaze au < 0.8 from s 0.50,
underside curls at s 0.66); on_tail mask covers the tip end; undertail patch lower and larger (r 0.023);
tail root thicker (r 0.024) with a softer join (blend 0.018) so it is no "balloon on a stalk"; belly mask;
inner ear tan to v 0.047 + mid-blue upper part, spiral r 0.0095, rim 4.2 mm.

## Cycle 7
Build 7: 43,728 tris, CHECK clean (0 floating/without material/flat colour/non-manifold/open), mirror 0.0011.
Kit overlap view 1 0.89, view 2 0.70 (clean 0.78), view 3 0.91; w/h +2 %, -0 %, -1 %.
Brightness: view 1 0.58 vs 0.60, view 2 0.64 vs 0.62, view 3 0.56 vs 0.56 (view 2's tail no longer too light).
What matches (keep): tail is now a plume (thick root flowing out of the rump, widest in the middle,
tapering to an upturned cream tip), blue with a cream flame band on top, a cream spiral in the distal
half, a lower swoosh, cream tip; back view egg blue with a central cream blaze and two curls (as the
reference); undertail cream-tan disc visible; belly tan no longer runs down the inner hind legs.
What differs (measured with cv.py sample and close previews, prev2.py):
- View 1 outline 0.89: the reference draws the tail beside the shoulders (missing middle-left/right 9-13 %);
  the tail root lateral factor 1.0 hid it -> TAIL_W middle 1.30-1.35 (fit: view 1 0.916, view 2 0.799,
  view 3 0.902).
- Colours (sample, front): inner ear render #837771 vs reference #b09d92, chest #8d807b vs #a89d9c, cheek
  #938d85 vs #b2aca6: cream/tan 0.10-0.17 too dark -> cream #dccbb9/#e6d8c8/#c3af9b, ear tan
  #d0b8a6/#dcc6b3/#a68a7b, ear tuft #e8d9c6. Paws render #657f97 vs #557396 (reference darker, more
  saturated) -> leg #5f83aa, paw #4f6f9a. Back view tail underside render #5c7487 vs #425b7d -> tail
  underside #4d6c94 at 0.70, body underside #6689ad. Head in view 2 render #b7dceb vs #92afc0 -> head
  lightening 0.7 -> 0.3. Fur roughness 0.80 -> 0.86 (render had #bce8fc specular glints the reference
  does not have).
- Face (close previews next to the reference): eyes were round goggles 0.20 of the head width with a
  sclera ring and too far apart; the reference eye is 0.16 of the head width, 1.16 x wider than tall, the
  iris fills its height, eyes closer (spacing 0.32 of the face width) -> eye radius 0.0110 x 0.0095,
  aim (0.31,-0.95), start X 0.010 Z 0.203; iris radius 0.82, pupil 0.50, lid line hugs the top edge;
  socket an ellipsoid matching the eye, lid ridge thinner. Nose 60 % too big -> half widths 0.0052 x
  0.0035. Mouth was invisible from the front (the painted line was the unprojected design line, ~1 mm
  off the scaled head) -> paint now follows the surface points returned by the carved stroke; added a
  philtrum groove; "w" mouth 20 % narrower. Ear tufts were thin needles -> fat spikes (base r 0.005-0.007).
- Tail flame band widened toward the tip (s_b 0.70 at |phi| 1.2, to |phi| 1.5) so the back view's
  upper egg reads cream like the reference.
- Still a view-2 ceiling: far ear above the near ear (Cycle 6), forehead/chest 5-8 mm behind the
  reference's in the bbox-normalised overlay.

## Cycle 8
Build 8: 43,728 tris, CHECK clean (0 floating/without material/flat colour/non-manifold/open), mirror 0.0012.
Kit overlap view 1 0.92, view 2 0.70 (clean 0.80), view 3 0.90; w/h +2 %, -0 %, -1 %.
Brightness: view 1 0.59 vs 0.60, view 2 0.64 vs 0.62, view 3 0.53 vs 0.56 (all within 0.05).
What matches (keep): outlines in views 1 and 3 >= 0.90; face (almond eyes filling with iris, lid line,
brow dots, small nose, "w" mouth with philtrum, cream lower face and cheek tufts); plume tail with the
flame band/spiral/swoosh/cream tip; back-view blaze and curls; dark saturated paws (sample render
#567190 vs reference #557396); tail underside from behind #4b5e77 vs #425b7d.
What differs (cv.py sample):
- Back view upper egg render #929ea5 vs reference #bfb4af (blue showing at the top of the egg): the
  flame band now widens to |phi| 1.8 near the tip (s_b 0.62/0.74/0.86 at |phi| 1.2/1.5/1.8), the spiral
  moved to phi 1.55 s 0.57 so it stays on blue in view 2, and the tip tufts with their fillets are cream
  (blue "V" under the tip seen end-on came from the fillets lying outside the tail mask).
- Inner ear render #92867f vs #b09d93, chest #948782 vs #a89d9c: still ~0.07-0.10 darker under the kit
  lights -> ear tan #dcc6b4/#e6d3c2/#b89c8b, cream #e6d6c4/#eee2d3/#cdb9a5.
- Recorded ceilings (not chased further): view 2 far ear above the near ear (the drawing tilts the head
  toward the viewer, Cycle 6); view 2 kit overlap includes the back-view fox inside its box (clean 0.80);
  the front view draws the tail lower beside the shoulders than the side view allows.
8 builds reached: next is the --final bake build.

## Report
Final build 9 (--final, baked at 4096 px), lens 200, views 1 az 0 el 2 / 2 az 59 el 13 / 3 az 180 el -1.
- OUTLINE: view 1 overlap 0.92, w/h +2 % (pass); view 3 0.90, w/h -2 % (pass); view 2 kit 0.69, w/h -0 %
  (FAIL on overlap). View 2's box also holds the back-view fox (bottom-right 51 % "missing" is that
  drawing). With the fox alone the overlap is 0.80 (clean_cmp/camscore). What is left after that is the
  drawing's head roll: the near ear tip is drawn above the far one, which a symmetric fox at el 13 cannot
  show without breaking the symmetric front view. Key ratios: proportions checked on the per-column/row
  profiles each cycle. Ear length / height, back height, belly clearance and body length are within the
  w/h tolerance in every view. Tail thickness follows the view-2 profile to within about 0.02 of the
  height in the middle.
- PARTS: all 18 inventory rows built (fused clay head/muzzle/jaw, 3 cheek tufts per side, cupped ears
  with 3 fat inner tufts, painted eyes in sockets with lid ridges, nose, neck, torso, chest mass and tufts,
  4 legs with toe grooves, plume tail with 3 tip tufts, 2-strand twisted cord, lathed bezel, gem, bail).
  Copies differ: seeded tuft lengths and cheek tuft jitter per side, mirrored ear spirals with offsets,
  tail curls left/right of different size, paws placed per side.
- DETAILS: brow dots, almond eyes with full iris, pupil, 2 highlights, lid line and wing; nose with
  highlight ramp; carved "w" mouth plus philtrum (painted on the carved surface line); jagged cream
  borders; ear tan bowl, blue rim, mid-blue upper ear with a dark spiral, dark tip, dark ear-back cap
  with a light spiral; tail flame band with tongues, spiral, hook, lower swoosh, cream tip with tufts,
  underside blaze and curls (back view); undertail disc; belly tan; darker lower legs and paws; fur
  streaks and tone patches. All are visible in the renders and the turnaround.
- MATERIALS: (cv.py sample, build 8 to 9) paws #567190 vs reference #557396; tail underside from behind
  #4b5e77 vs #425b7d; body side in view 2 #a0c9de vs #96bed3. Mean brightness per view 0.61/0.65/0.53 vs
  0.60/0.62/0.56 (within 0.05). The cream and tan in the front view were brightened for the final
  (the earlier render was 0.07 to 0.10 darker under the kit lights). CHECK flat colour: none. In view 2
  the top-right is 0.10 lighter: the cream tail tip and flame band read lighter than the drawing's
  shaded cream.
- FORM: the clay renders show the volumes: skull, muzzle, cheek ruff, chest, waist, thigh, hock, toe
  grooves, cupped ears, and the plume tail swelling from a thick root to an upturned tip.
- CLEAN: CHECK parts 9; floating none; without material none; flat colour none; non-manifold 0, open 0,
  loose 0, degenerate 0; mirror 0.0012. 43,728 triangles (budget 45,000).
- Last lines: BUILT blue_fox {"triangles": 43728, "dimensions_m": [0.153, 0.452, 0.312], "materials":
  ["M_blue_fox"], "glb_bytes": 39627680}. BAKE blue_fox: base_color, normal, orm at 4096 px in 241.6 s
  (no Mix Shader note; every material mixes its principled inputs). The baked renders and turnaround
  match the cycle-8 renders.
- Materials: procedural texel-painted fur, cream, tan, markings and eyes (bx_materials TexelMap at
  2048/4096: colour, roughness, height), a ramp-attribute nose, procedural leather cord (twist-lobe
  attribute), silver (metallic, scratch bump) and gem (radial gradient, gloss). Skills:
  blender-image-to-3d, scenario-blender-sculpting (Clay SDF, strokes), -texturing-shading,
  -retopology (decimate + manifold repair), -expert, and the kit's CV tools.
- Still differs and why: view 2's far ear sticks up as a thin edge above the near ear (drawing
  inconsistency, see above). The front view draws the tail lower beside the shoulders than the side
  view allows (middle-right 6 % missing). The reference's ink contour lines are a drawing convention
  and are not built. From exactly 90 deg the ears read thin because their openings face out-forward.

## Cycle 9
Build 9 is the --final bake (43,728 tris, budget now 90,000). Kit overlap view 1 0.92, view 2 0.69 (fox only
0.80), view 3 0.90; w/h +2 / -0 / -1 %; CHECK clean. Critic review 1: REFINE (blue_fox_review_1.md, 64 checks).
User: "Both eyes are bad. Fix the eyes." and "In all 3 the tails are wrong. It's fur in the tail."
What I measured this cycle (full-resolution crops of source.jpg with a pixel grid, work folder; front view
0.433 mm/px, side 0.287 mm/px):
- Eyes, front (eyes_front.png): opening 24 x 20 mm (right eye x 282-338, y 1336-1383; left x 400-459),
  centres 120 px apart = X +-0.026 about the midline (x 370); outer corner pointed and 3.5 mm higher than the
  round inner corner; the lash line is 1.5-2 mm thick, thicker toward the outer corner, and runs on ~3 mm out
  and up as a wing; thin (~0.6 mm) grey-brown lower line; iris ~19 mm across (fills the opening height),
  centre 3.5 mm toward the nose, dark top #4d4852 to light grey-brown bottom #a59c9a, dark limbal ring; pupil
  a vertical oval ~11 x 13.5 mm #2e2c34; white catch light r 2.2 mm, 3.5 mm above the iris centre; a faint
  second reflection lower-inner (r ~1.2 mm); cream sclera shows only on the outer side.
- Eye, side (eye_side.png): almond 24 x 18 mm, iris at the front (nose side), big cream sclera behind it,
  lash wing at the back corner, brownish lower line toward the front.
- Render vs reference (blue_fox_cv_closeup_1.png, box 0.22 0.28 0.78 0.46): the render's eyes are round
  balls standing out of the face with a full dark ring all round: 25 % too small, 17 % too close (review #5,
  #7, #54). Relative to the brow dots the eyes are at the right height, but the render's nose and mouth sit
  ~5-7 mm higher than the reference's (closeup rows: ref eye 75 / nose 140 / mouth 180 px, render 72 / 120 /
  155). Cause: the eye was a painted sphere pushed out of a socket, with no eyelids; the muzzle is short in
  the front view.
- Nose and mouth (nose_front.png): nose 12.6 x 8.2 mm (render 30 % narrower: it is buried in the muzzle),
  rounded inverted triangle, grey highlight band on its upper half; mouth a 35 mm smile, a slight rise in the
  middle (y 1424) between two dips (y 1428) 8.7 mm each side, corners up at y 1420; nose bottom to mouth
  centre 6 mm; no philtrum (render has one).
- Tail (tail_side.png, tail_end.png, tail_tip.png, tail_back.png): it is fur. Locks flow from the root to the
  end, their tips pointing to the tail end; the outline breaks into lifted lock tips: a small one on the top
  edge (1740,722, about s 0.78), one on the lower edge (1830,912, about s 0.9), the end itself (1878,830)
  pointing back-down along the last tangent; a grey crease runs between two end locks (1770-1830, 820-870).
  Blue locks rooted on the first half lie over the cream end fur like shingles: their pointed tips reach
  into the cream (side view, top of the distal half: blue tongues pointing to the end), and the cream left
  between them reads as tongues pointing back to the root (the "flame band"). Lower distal side blue with
  one cream spiral (painted marking, r ~0.016 m). From behind (the tail's underside): the end's lock tips are
  crumpled cream with grey shading in the middle; a cream blaze down the middle ending in lock-tip tongues
  pointing down (to the root) at ~0.46 H; two cream curls at its lower ends.
  Render: one smooth shell (SDF plume) with the pattern painted on and two bead knobs on top: the wrong kind
  of thing (review #24-26, #33-36; user). Fix: rebuild the tail as fur, not reshape the shell.
What matches (keep): outline views 1 and 3; proportions, key ratios R1-R5, R8; legs, paws and toe grooves;
body blue; chest cream; brow dots; collar twist geometry; silver; clean mesh.
Other differences: as listed in review 1 Fixes 3, 5, 7, 8, 9, 11 (ears, pendant and collar, hind shins,
belly/undertail/lower legs, tufts, fur grain); answered under Review 1.

## Review 1
Status of each Fix after this cycle (nothing below is built yet; this cycle ended before its build):
1. Tail pattern: approach changed. The pattern comes from the fur locks (blue locks over cream end fur, see
   the Handoff), plus painted curls; underside blaze start s 0.50 -> 0.58, curls at its lower ends (s 0.60,
   phi +-2.5, r 0.012 / 0.011), lower swoosh removed, cream #cfc8c2 / tip #d8d3cf. NOT written yet.
2. Tail shape: TAIL_RZ (max 0.049, distal 0.026 / 0.012) and TAIL_W (widest low, 1.37 at Z 0.145, 0.98-1.0
   from Z 0.19) WRITTEN; the tip tufts (TAIL_TUFTS) and the two bead knobs are removed; end locks replace them
   (Handoff step 2). Not built.
3. Ears (cup, flat 3-lobe tuft, rim band, tip, spiral sizes, back patch 60 %): not started.
4. Eyes: eyeball + socket + eyelids + lash-line ridge WRITTEN in body_clay (carve_eyes); eyeball mesh, its
   paint and the face's lash-line paint still to do (Handoff step 1). Not built.
5. Pendant and collar: not started; numbers in Handoff step 4.
6. Nose and mouth: philtrum removed (clay stroke and paint), mouth line widened to 33 mm with the shallow
   central rise WRITTEN; nose not yet (Handoff step 3).
7. Hind shins: not started.
8. Belly, undertail, lower legs: not started; numbers in Handoff step 5.
9. Elbow, chest and cheek tufts: not started.
10. Front-view tail sides: through TAIL_W (written); check after the tail is built.
11. Fur grain: not started; numbers in Handoff step 5.

## Cycle 10
Build 10 (cycle build, no bake): 80,088 tris (budget 90,000); CHECK clean (10 parts, no floating, no flat colour,
0 non-manifold). Overlap view 1 0.89 (w/h +1 %), view 2 0.70 (w/h -1 %; the box holds the back-view fox too),
view 3 0.90 (w/h -2 %). Changes this cycle (from the Handoff steps 1-5, 7, Fix 7 and part of Fix 3):
- Eyes, rebuilt twice. (a) The Handoff's ball-in-socket (ellipsoid eyeball 17 x 14.5 x 11.5 mm + socket +
  eyelid shell) rendered as marbles at the bottom of round holes: the face around the eye stands 3-15 mm in front
  of any ball that fits (probe: face Y at X 11 mm runs -153 -> -138 mm across the eye height: the nose bridge),
  and a sloped "bowl" cut to reach the lids dug 9 mm trenches down the nose bridge. (b) Now: the eye opening is
  the traced reference outline (eye_parts / eye_opening_field: U(a), L(a) tables, pointed outer corner 2 mm up,
  near-vertical inner side; 23 x 19.2 mm) and the eyeball is its visible front built from the face height
  map (eye_front_y: 0.1 mm under the face at the centre, 0.7 mm at the lid edge = the lid margin, diving
  under the lids 1.6 mm beyond, 0.4 mm corneal bulge over the iris), a closed thin shell (eyeball_mesh,
  3,328 tris each), painted in front-view coordinates (iris r 8.3 mm centred 3.9 mm toward the nose, pupil
  9.4 x 12.2 mm, catch light r 2.1 mm up-inner, limbal ring, radial fibres, dark strip under the lids). The
  clay only cuts the skin in front of it (sd_eye_opening) and keeps the lash ridge; lash/lower-lid paint on the
  face from eyelid_marks. Front close-up (blue_fox_cv_closeup_1.png, e4_eyes_front_cmp.png): reads as the
  reference's eyes (almond, wing corner, iris toward the nose, white catch light, no ring).
- Tail rebuilt as fur: its own object `tail` (fine clay 0.7 mm): underfur (0.88 of the outer radius) + 94
  guard-hair locks (8 rings + 4 end locks), flat bent shingles that rise from the root (sunk 2.4 mm) to the
  tip, painted per lock (blue/cream by the flame zones), curls painted on top. Close-up
  (blue_fox_cv_closeup_2.png, t5_cmp.png, t6_cmp.png): NOT right yet: the shingle relief is too strong and
  thin flat fins/discs stand out of the surface on the distal top and sides (also after clamping the lock
  bending to the local radius, t6), the end is a needle hook, the colour is a mosaic of lock-shaped patches
  instead of the reference's soft flame tongues, the side spiral too small. See the Handoff task Tail.
- Nose 12.6 x 8.2 mm (step 3); collar V-drape, 9 mm twist, strand r 2.0 mm, new cord ramp, bezel rim, upright
  bail 4.2 x 2.6 mm, gem ramp (step 4); C_LEG/C_PAW, belly band, one undertail oval, fur grain (step 5);
  hind shin hock Y +0.015 -> +0.0105 (Fix 7); ear tuft = one flat 3-lobe tuft (Fix 3 part); body voxel
  1.0 -> 0.8 mm, BODY_TRIS 36,000; parts named by what they are (step 7).

## Cycle 11
Build 11 = build 10 + the lock-bending clamp (exact sagitta, w <= 1.3 R): 80,088 tris, CHECK clean, overlap
0.89 / 0.70 / 0.90 (unchanged); the tail fins remain (cause not yet found, see task Tail).

## Cycle 12
Lead: no Agent tool in this session, so no part builders could be spawned (builder_guide s.8); the lead ran the four
part tasks itself with a part test harness (work folder parts/: harness.py rebuilds one part into a saved .blend, or
the whole model, and renders the recorded views with the kit's own studio and cameras; cmp.py puts a reference box
beside any render, as cv.py closeup does; probe_pat.py prints the tail pattern masks on an (s, phi) grid; --diag paints
the tail's (s, phi) grid to map the reference onto tail coordinates). The generator stays one file (the hooks allow
only blue_fox.py; part modules in a new folder were not risked).

Changes, each checked in harness renders beside the reference crops before the build:
- TAIL (task A). Fins: CAUSE FOUND: lock_seg_sd gave every segment a cap as long as the lock's half width (up to
  17 mm) beyond each end, along the segment's tangent; where the lock bends round the tapering envelope these straight
  caps stood out of the fur as thin fins. Cap now min(w, 0.6 ln + th): fins gone (tA clay). Relief: lock half
  thickness 0.25 -> 0.12 w (max 2.2 mm), root sink 2.4 -> 0.6 mm, blend 0.9 -> 2.5 mm (variant B, chosen over A
  0.15 / 1.0 / 1.5 mm: softer streaks, as the style draws). End locks min half width 2 mm. End radii TAIL_RZ
  0.026/0.012/0.007/0.004 -> 0.034/0.020/0.009/0.004 (0.036/0.025/0.014 made a club). Root flares: TAIL_W
  1.08/1.19/1.33/1.37 -> 1.60/1.70/1.70/1.60 (front view shows the tail beside the shoulders to |X| 0.064).
  Colour: the flame zones lead (75 %), locks only bend the zone edge (25 %); lock shading 0.94-1.0 -> 0.975-1.0,
  crease 0.06 -> 0.025; height grooves 0.18 -> 0.07; underside weight 0.70 -> 0.60; lit top cream dulled.
  Pattern re-placed from the (s, phi) grid render: top cream from s 0.40 with flame tongues, blue tongue at phi
  0.65-1.2 to s 0.82-0.86, spiral centre s 0.50 phi 1.25 r 25 mm winding out to its underside, its outer arm a broad
  band (6-15 mm) sweeping to the tip through (phi 1.47, s 0.60) (1.18, 0.71) (0.85, 0.80); lower band from under the
  spiral back to s 0.34; wave hook at (0.62, 0.45).
- EARS (task C). EAR_CUP 13 u^2 -> 0.42 u^2 / hw(v) (a rolled half-cone; SDF divided by sqrt(1 + slope^2)),
  EAR_OPEN (0.60, -0.80) -> (0.85, -0.52): after orthogonalising to the outward-tilted ear axis the old frame faced
  view 2's far ear 11 deg past edge-on (blade). EAR_HALF_W 0.034 -> 0.037. Tuft: 4 lobes, 2.4 mm thick, tips lifted
  1.8 mm (shadow lines). Tan inner skin: teardrop (ear outline at 72 % length, 3 mm rim). Dark spiral stroke 3 mm,
  back patch from v 0.031 (60 %), tip #4a6a9a from v 0.062.
- FACE (task B). Cream border 5 mm lower (front close-up: cream touched the eye's lower edge; reference shows the
  lower lid line and a blue band under the eye). Brow dots measured at +-25 mm (were +-18) and 2 mm higher, 12 x 5.4
  mm (this overrides the Handoff's "do not undo brow dots": the side-by-side shows them 7 mm too close to the centre).
  Lash ridge stroke n 60 -> 120, radii +0.1 mm; no fur streak colour or bump inside the lid-line masks. Cheek tufts
  reach |X| 0.063 (were 0.052).
- COLLAR (task D). The cord hung as a U following the neck; the reference V: the pendant's weight pulls it straight
  from the neck sides under the cheek tufts (|X| 0.037, Z 0.154) to the bail (Z 0.131). Loop centre 6 mm higher,
  front points blended to that V. Leather ramp darker (#3a2016 / #5f3726 / #94603f); silver roughness 0.18-0.36 ->
  0.30-0.46 (read dark); gem ramp brighter (#8fb0f0 centre -> #1d38a8 rim).

Build 12: 80,061 tris (budget 90,000); CHECK 10 parts, no floating, no flat colour, 0 non-manifold, but 7 OPEN edges
(make_manifold filled holes only up to 16 sides: now 200). Overlap view 1 0.88 (w/h +1 %), view 2 0.70 (-1 %),
view 3 0.87 (-2 %): views 1/3 lose 1-3 % at the ears (missing top-left/right 12-14 %: the outward opening makes the
ears narrower from the front and back) and gain extra top-centre 6-12 % (the distal tail as a dome above the head).
Judged by what each part is (new user rule, below), part by part against the reference crops:
- Tail: no fins (cause fixed); relief now soft streaks; the composition reads (top cream with flame tongues, the
  blue tongue, the spiral and its arm sweeping into the cream end, the central tongue and two curls from behind).
  Still wrong: the end reads as a club with a nib, not as guard hairs converging to a soft point with two notches;
  the distal part sits too high (dome above the head in views 1/3, yellow along the distal top in view 2) and ends
  too soon (the reference tip reaches further back); strand streaks fainter than the reference's.
- Ears: read as cupped fennec ears; the far ear in view 2 now shows its back with the patch and spiral (~50 px vs
  the reference's ~60; it was an edge-on blade); tuft reads as layered fur lobes. From the front they read ~15 %
  narrower than the reference (the cost of the outward opening; accepted: the far ear reading as an ear matters
  more than 1-2 % overlap).
- Eyes: shape and size of the opening match in clay (22 x 19 mm); the paint still differs: the cream border met the
  eye's lower edge under its outer half (border now 8 mm lower than build 11 in total), the iris was cool grey and
  77 % of the eye width (reference warm grey-brown, ~65 %): R_IRIS 8.3 -> 7.5 mm, iris/sclera warmer, second catch
  light on. Brow dots now at the reference's spacing.
- Collar: the V drape and height now match the crop; the cord reads as two twisted leather strands (darker since).
  The gem read flat navy with no catch light (reference: bright domed cabochon, big white highlight): dome 4.2 ->
  5.3 mm, rim #142a80; silver satin.
After build 12, written for build 13: tail end locks (main top lock carries the point; a top-notch tuft s 0.60-0.86
phi 0.30 flick 1.3 and a lower tongue s 0.64-0.94 phi pi-0.15 flick 1.4, neither converging; side locks converge),
TAIL_PTS distal 4-8 mm lower and the end 12 mm further back, tail streak colour 0.06 -> 0.10 and height 0.25 -> 0.32,
the eye paint and gem changes above, hole fill 200 sides.

New user rule (coordinator, this cycle): conceptual understanding leads every comparison, not the silhouette
numbers; overlap/aspect are a coarse outline check only; rank what needs improving by how much it hurts what each
part is. (Copied into the Handoff's Standing rules.)

## Cycle 13
Build 13 = build 12 + the tail end/streak changes, the eye paint, the gem dome, hole fill 200 (see Cycle 12's last
paragraph) + s_b at phi 0.2-0.65 later (blue tongue back). 80,063 tris; CHECK 10 parts, no floating, no flat colour,
0 open edges but 1 non-manifold edge (left for the next build to find: make_manifold's 200-side fill may close a
hole across a pinched rim). Overlap 0.88 (w/h +3 %) / 0.70 (+0 %) / 0.87 (-0 %); view 3 centre 0.09 darker.
Part by part (what it reads as, then measures):
- Tail: reads as a soft fur plume; it now reaches the reference's tip in view 2 (overlay matches the end) and
  converges to a point; streaks show. Wrong: from behind a HORN stands on the top of the egg (the top-notch tuft's
  7.8 mm lift) and a RING crease runs round the end (the five end-lock roots all at s 0.60-0.70); the two notches
  still do not read in view 2's outline; the cream edges were frayed by the fbm jag (reference: smooth brush curves).
- Eyes (front close-up b13_eyes_v1): blue band and lower lid under the eye, warm iris at ~65 % of the eye width,
  brow dots at the reference spacing: reads close to the reference. Remaining: the reference's upper lid arc is
  ~15 % higher (rounder eye).
- Collar: V drape correct; the gem still shows no catch light (the studio key does not reach the camera off the
  dome): this style paints it, so it is painted now (gem_hl).
- Stair-step check (new standing rule): face cream border (6x) and tail cream border (5x) show no texel stair-steps:
  every marking is a smooth procedural 3D field painted per texel (2048 px, ~0.2-0.3 mm per texel), nothing comes
  from an image or a downscaled crop.
Written for build 14: end-lock roots staggered s 0.55-0.70 and sunk 3x TAIL_SINK, top tuft lift 0.9 (was 2.6), lower
tongue 2.0; tail pattern jag 0.035 fbm(90) + 0.015 fbm(300) -> 0.014 fbm(60) + 0.003 fbm(200); gem catch light
(attribute gem_hl, white #f4f8ff mixed into the base colour inputs, not a Mix Shader).

## Cycle 14
Lead: no Agent tool in this session either, so no part builders: the lead ran the part tasks itself (said so in the
final message). User priority this cycle: "Look at the snout closer from all angles and fix the snout, make it more fox
like." Snout first, then the build-14 steps already written into the generator by the last lead (tail end-lock roots
staggered and sunk, top tuft lift 0.9, lower tongue 2.0, tail pattern jag softened, gem catch light gem_hl) and the e1
eye test (upper lid arc x1.06-1.12, rounder eye) went into this build untested on their own.

New lead tools (work folder parts/): headtest.py builds ONLY the head (the body clay box cut to the head, so ~2 min
instead of ~5), the eyeballs and the nose from a generator copy, paints them with the generator's own paint, and
renders snout close-ups at the REFERENCE'S PIXEL DENSITY (fox height: view 1 696 px -> 2231 px/m = 0.448 mm/px; view 2
1049 px -> 3253 px/m = 0.307 mm/px; --scale 2 renders at 2x) from front (az 0 el 2), view 2 (az 59 el 13), side (az 90),
q30 (az 30 el 6), top (az 20 el 62) and below (az 25 el -45), lit and clay, and prints ANCHOR pixels of the near eye's
inner corner (X 0.015 Z 0.201 on the face) and the nose tip. snoutcmp.py puts the native reference view next to a
render aligned on that eye corner (reference | before | after | clay | outline overlay red ref / cyan render);
beforeafter.py stacks before/after lit and clay for the angles the reference does not show. snout_cam.py renders any
.glb/.blend the same way (an imported .glb shows the clay only: its base-colour alpha cuts the lit render).

### Snout: what makes the reference read as a fox (native crops ref_v2_head.png, ref_v1_head.png in parts/snout)
- A fox snout is the long narrow rostrum of the skull under short fur: a STRAIGHT bridge (nasal bones) from a shallow
  stop between the eyes' inner corners down to the nose; the sides (maxillae) slope out to the upper lips, so a section
  is a rounded trapezoid, narrow on top, widest at the lip line; the upper lips hang a little over a NARROW lower jaw
  whose small chin sits behind and below the nose; the nose leather caps the very tip and its top continues the bridge.
- Reference, measured on view 2 against the near eye's inner corner (Y -0.1405, Z 0.201): nose front 35.7 mm ahead
  (Y -0.176) and its top-front corner 9.6 mm lower (Z 0.1915); bridge Z 0.2025 (stop, Y -0.151) -> 0.1977 (-0.158) ->
  0.1956 (-0.165) -> 0.193 (-0.171), a straight line falling ~25 deg; nose bottom Y -0.171 Z 0.184; mouth starts under
  the nose Y -0.167 Z 0.178, lowest 10 mm out (Z 0.1775), corners X +-0.0177 Y -0.144 Z 0.180 (below the eye's inner
  corner; front view: 34 mm wide, corners up 2.7 mm, only a slight central rise); chin Y -0.164 Z 0.175, jaw underside
  0.171 (-0.157) -> 0.167 (-0.145); nose (front) 13.4 x 7.7 mm rounded triangle, #4e3b3e with a #6c5f60 top highlight;
  muzzle cream #dccbb8 climbs the snout's sides to just under the bridge (Z ~0.196 halfway, the nose's top at the tip):
  only the bridge's top band is blue.
- Build 13 (before, parts/snout/s0 and the evidence sheets): the muzzle was a ROUND CONE (r 23 -> 12 mm, 39 mm long)
  blended into a forehead dome with a round lower-jaw cone under it: from every angle a short bulbous puppy/cat muzzle,
  convex bridge, nose a sausage on the front, mouth 17 mm long, cream only below Z 0.1835. Measured: nose 9.6 mm too far
  back (view 2: eye->nose (-97.9, +29.8) native px vs the reference's (-124.8, +33)), nose and mouth ~5 mm too high
  (front: nose centre 5.4 mm above the reference's), top view a wide round cylinder.
- Cause: wrong construction (a cone has a round section and a convex top; it cannot give a straight bridge, a tapering
  wedge from above or a lip line), not wrong numbers. Rebuilt with the method that fits:
  sd_muzzle() = rounded-trapezoid sections (exact 2D trapezoid SDF, sides bulging 1.5 mm, rounded 7.5 mm max) lofted
  along Y from tables SN_Y/SN_ZT (bridge)/SN_ZB (lip line)/SN_WT/SN_WB, its root as wide as the eyes' inner corners (the
  face there carries the eyes: a narrow root moved them 8.5 mm back, first try), its front by height (SN_TIP_Z/Y: inside
  the nose leather, then the philtrum leaning back to the mouth); sd_jaw() = a narrow rounded wedge (JAW_*) tucked 3.5 mm
  under the lips, chin at Y -0.166, blended into throat and cheeks (blend 12 mm); build_nose() = the nose leather as its
  own SDF mesh (0.2 mm voxels, 1,600 tris): front-view rounded triangle 16 x 8.6 mm before rounding (reads 13 x 7.7),
  top domed across and following the bridge, front domed and leaning back 3 mm toward the bottom, its back diving under
  the bridge fur after 7 mm; MOUTH re-traced (world coordinates); a cream field zc(Y) on the snout (body_color).
- Iterations (all in parts/snout, sheets cmp_sN_v2/front.png and ba_sN.png): s1 narrow root (eyes moved back, jaw a hard
  plate), s2 wide root + softer sections + jaw into the throat (outline matches, nose a slab), s3 receding philtrum +
  bigger nose (a brick standing above a round ridge), s4 short domed pad (too small), s5 = built: 16 mm pad, gentler mouth.
- After (s5 = build 14): view 2 eye->nose (-123.6, +38.5) native px vs reference (-124.8, +33): length within 1 %, nose
  1.7 mm low; the 50/50 blend of reference and render (judged by eye) shows forehead, stop, bridge, nose, philtrum,
  chin and jaw lines on top of each other, the smile ~1 mm lower and curving up less at the back than the reference's;
  front: nose 13 x 8 mm rounded triangle at the reference's place (0.7 mm high); top view a tapering wedge, below view a
  narrow jaw under the lips. Reads as a fox's snout from every angle. Evidence: blue_fox_snout_v2_before_after.png,
  blue_fox_snout_front_before_after.png (reference | build 13 | build 14 | clay | 50/50 blend of reference and build 14), blue_fox_snout_angles_
  before_after.png (side, q30, top, below: before / after / before clay / after clay).
- Still differs: front-view mouth a "w" with a pointed centre (the stroke dips into the midline notch between the lip
  halves; reference: a soft wave); chin seen from the front shows vertical edges where the jaw meets the cheeks (reference
  a soft rounded chin); cheek tufts in view 2 read as spikes (reference: soft cream ruff with one gentle point).

- New user rule mid-cycle, "Don't use masks": the sheets above were first made with thresholded outline overlays
  (red reference / cyan render) and a body-alignment test (bodyalign.py, now retired, its result discarded: it never
  steered the build). The reference pixel densities were first read from a threshold of the fox's height; re-measured
  directly on the native reference at 6x/3x zoom with a 5 px grid: view 1 ear tip y 13 -> paw outline y 707 (694 px),
  view 2 near ear tip y 11 -> paw y 1059 (1048 px): the densities stand. snoutcmp.py now shows a plain 50/50 image
  blend of reference and render (no masks, no thresholded outlines); every snout measurement above was read by eye on
  the native reference (zoomed crops, hand-read pixels), not from a mask.

### Build 14 (full)
80,698 tris (budget 90,000); CHECK 10 parts, no floating, no flat colour, mirror 0.0014; 3 non-manifold + 1 open edge
(were 1 / 0: to find; probably make_manifold over the new jaw/neck seam). Overlap 0.88 (w/h +3 %) / 0.70 (+3 %) / 0.87
(-0 %); view 3 centre 0.10 darker. Part by part (what it reads as):
- Snout: as above; in the full view 2 the head now reads as a fox's.
- Tail (build-14 steps): from behind still a cream DOME with a small horn and two white dots on top and a ring crease
  (reference: soft cream mass ending in a few wispy flame tips); from the side the cream top band is thin and the spiral
  stands upright in the middle (reference: wide cream top with flame tongues, big spiral, cream tip). Not fixed.
- Gem: still reads dull navy with a dark halo (the silver bezel renders dark); reference: bright domed blue cabochon with
  a white highlight in a bright silver ring.
- Eyes (e1 rounder upper lid): no visible harm; the reference's eyes still read rounder/larger.

## Handoff (current: after build 14)

### 1. Understanding
- Whole: small stylised fox (~0.31 m to ear tips), soft painted anime 3D style; light-blue fur, cream face/chest/
  belly, big cupped ears, huge plume tail, braided leather cord with a silver-set blue cabochon. Young, no wear.
- Body: one soft mass under short fur: SDF clay (voxel 0.8 mm), fur only in paint + normal map.
- Snout (Cycle 14): the rostrum = rounded-trapezoid sections lofted along Y (sd_muzzle: straight bridge, wedge from
  above, sides sloping to the lip line), the lower jaw a narrow wedge under the lips with a small chin (sd_jaw), the nose
  leather its own SDF mesh capping the tip (build_nose). Keep this construction; never go back to a cone.
- Eye: what shows is the eyeball's front framed by the lids, built from the face's own height map (eye_front_y); lids =
  margin cut + lash ridge + paint. The face at the eyes' inner corners comes from the snout root: changing the root's
  width moves the eyes (Cycle 14: a narrow root moved them 8.5 mm back).
- Tail: a mass of fur: dense underfur round the bone, guard-hair locks rooted toward the base, tapering to points,
  shingled; LOW relief in this style (soft streaks), colour = painted flame tongues and a spiral.
- Ears: thin cupped cartilage leaves with fur (rolled half-cone), tan inner skin, cream tuft, blue rim, dark tip, spirals.
- Collar: two leather strands twisted, hanging in a V; pendant = silver bezel cup + blue cabochon + bail.

### 2. Part inventory (generator names)
body (body_clay: head, sd_muzzle, sd_jaw, cheeks + cheek ruff cones, neck, torso, legs, paws, ears + sd_ear_tuft, tail
root stub; carve_eyes; mouth stroke MOUTH), eyeball_left/right (eyeball_mesh), nose (build_nose / sd_nose), tail
(tail_clay: underfur + tail_locks; tail_color), collar_cord_strand_0/1, pendant_bezel, pendant_gem, pendant_bail.
Materials M_body_fur, M_tail_fur, M_eyeball_*, M_nose, M_collar_leather, M_pendant_silver, M_pendant_gem.
Triangles 80,698 / 90,000: body 36,000, tail 26,000, eyes 2 x 3,328, nose ~1,600, collar 9,216, rest.

### 3. Comparison (build 14: blue_fox_compare.png; snout sheets blue_fox_snout_*_before_after.png; closeups
blue_fox_cv_closeup_1/2/3.png = pendant view 1, tail view 2, tail view 3)
- View 1 (0.88, w/h +3 %): snout and nose in place (front sheet); mouth a pointed "w" (reference a soft wave); chin with
  vertical side edges; missing top-left/right 12-13 % = ears (narrow from the front since the outward opening); pendant
  gem dull navy, bezel dark (reference bright silver ring, bright blue gem, white highlight).
- View 2 (0.70 kit; its box includes the back-view fox, so the kit number stays low): head reads as a fox's; snout
  outline within ~1 mm of the reference on the eye-aligned overlay; cheek tufts read as spikes; tail: thin cream top band,
  upright spiral, end a club with a nib (reference wide cream top with flame tongues, big spiral, soft point, 2 notches).
- View 3 (0.87): tail from behind a cream dome with a horn + two white dots + ring crease; centre 0.10 darker.

### 4. Next steps: part tasks (each independent; run with headtest.py / harness.py, then one full build)

TASK A. Part: face finishing (MOUTH + mouth stroke in body_clay, sd_jaw, cheeks + cheek ruff cones in body_clay).
- What: the smile is a painted + carved crease where the upper lip overhangs the jaw; the chin a small soft bulge; the
  cheek ruff soft cream fur with one gentle point per side.
- Do: (1) mouth: no carve within |X| < 2.5 mm (or a shallower stroke there) so the centre is a soft wave, not a point;
  check front close-up vs ref_v1_head.png (corners up 2.7 mm, centre rise ~0.3 mm). (2) chin: widen JAW_W at the front
  (0.0052 -> 0.0065) and raise the jaw blend or add a soft chin ellipsoid so the front shows no vertical edges.
  (3) cheek ruff: the three cones per side read as spikes in view 2: fewer/softer (2 tufts, r0 x1.3, tips rounded,
  blend 0.009) keeping |X| 0.06 in the front outline. Check: headtest.py front/v2/q30 + snoutcmp.py.
- Keep: SN_*/JAW_* tables (snout outline matches), the eye-corner face (Y -0.1405 at X 0.015).

TASK B. Part: tail (tail_env, TAIL_RINGS/TAIL_END_LOCKS, tail_locks, tail_clay, tail_color/tail_pattern).
- From behind: no horn/dots/ring: the end is guard hairs converging to a soft point (locks of different lengths ending
  at different s, no shared root ring, the top tuft not lifted); from the side: cream top band from s 0.40 as wide as
  the reference's (top third of the tail depth) with flame tongues, the spiral big (r 20-25 mm) and lying along the tail,
  cream tip. Crops: parts/crops tail_side.png, tail_back.png; closeup boxes view 2 0.55 0 1 0.6, view 3 0.1 0.05 0.9 0.65.
  Test: harness.py --base <full .blend> --part tail (save a base .blend from the current generator first).

TASK C. Part: pendant (collar(): pendant_bezel/gem/bail, silver_material, gem_material).
- Gem reads dull navy with a dark halo; reference: bright #3f63cc-#8fb0f0 domed cabochon, big white highlight, bright
  silver bezel ring ~1/5 of the radius wide. Brighten the silver (base #c8ccd4, roughness 0.25, metallic 1 reads dark in
  the studio: give it a lighter base and lower metallic or a painted highlight band), gem centre lighter, gem_hl bigger.
  Closeup view 1 box 0.3 0.5 0.7 0.68 --scale 3.

TASK D. Mesh health: 3 non-manifold + 1 open edge appeared in build 14 (make_manifold over the new jaw/neck seam?):
  find them (kit CHECK lists counts only: select non-manifold in a saved .blend and print their positions) and fix.

### 5. Do not undo
Views/cameras; body proportions, legs, paws; the Cycle 14 snout (sd_muzzle/sd_jaw/build_nose, SN_*/JAW_*/NOSE_*, MOUTH
positions, snout cream field zc); brow dots (Cycle 12 spacing); eye construction (Cycle 10) and eye positions; tail as
its own fur object; manifold repair; texel painting (no Mix Shader).

### 6. Files
Reference views blue_fox_ref_view_1..3.png (native cut-outs); compare blue_fox_compare.png; snout sheets
blue_fox_snout_v2_before_after.png, blue_fox_snout_front_before_after.png, blue_fox_snout_angles_before_after.png;
work folder .scratch/assetgen/work/blue_fox_evolution/blue_fox/parts: headtest.py (head-only build + snout close-ups at
reference density, ANCHOR lines), snoutcmp.py (no masks: plain image blend), beforeafter.py, ev.sh (anchor from a log), snout_cam.py,
harness.py (whole model or one part into a saved .blend), cmp.py, gen_s0..s5.py (s0 = build 13 generator, s5 = build
14), snout/s0..s5 renders and logs, build14.log.

### 7. Standing rules
- builder_guide.md and blender_tools_guide.md (scratchpad copies named in the task) are the method: read both
  first; the Handoff follows builder_guide.md section 7.
- The user's wishes: "Both eyes are bad. Fix the eyes." (done in Cycles 10-13; keep); "Look at the snout closer from all
  angles and fix the snout, make it more fox like." (Cycle 14: rebuilt; finish with Task A); the critic's review 1 Fixes.
- The tail is fur.
- Think about what you see and build that (builder_guide.md section 1).
- Understand the thing you are making, conceptually, and let that choose the approach (builder_guide.md section 1).
- Understand every difference: why the reference looks like that and why the build differs (cause, not symptom)
  (builder_guide.md section 6).
- Name every part by what it is, never by its shape or look (builder_guide.md section 2).
- Multitask: Blender builds and renders in the background while you keep working; independent steps together
  (blender_tools_guide.md section 6).
- Use all the cores: while the 1-minute load in /proc/loadavg is below nproc, start another background Blender job
  instead of waiting (one process per view or close-up, parameter variants side by side); timeout on every run;
  never let two jobs write the same file (blender_tools_guide.md section 6).
- Cycle builds render all views lit and clay at the kit's samples and resolution; look at the full compare after
  every build.
- Lead and part builders (user): the builder that reads this Handoff leads; it runs 2-4 part builders on Sonnet 5.5
  at once (builder_guide.md section 8); without an Agent tool the lead runs the part tasks itself and says so.
- Compare to the reference often, part by part, after every change (builder_guide.md section 6).
- Refresh the Handoff after every full build (user), so a stop at any point leaves a current Handoff.
- One render cycle per builder when the task says so, ending with a Handoff; never ask "May I"; no git.
- User rule: Let conceptual understanding lead every comparison, not the silhouette numbers.
  1. Start from what each part is. For every part in the inventory, ask first whether it reads as that thing, the way
     it looks in life and in this art style, from every view and up close.
  2. Then check the features its nature implies: its inner structure (one surface, or many elements, and how they
     flow, clump and end); how it attaches; what its material does with light (gloss, wetness, translucency, glow);
     how it ages.
  3. Measure those features in the reference and the build: crops, cv.py sample and closeup.
  4. Treat the overlap and aspect numbers of cv.py compare as a coarse check of the outline only, never the target. A
     change that raises overlap but makes a part read less as what it is goes the wrong way.
  5. In the review and the Handoff, rank what needs improving by how much it hurts what each part is, not by pixel area.
- User rule: no pixel stair-steps along colour boundaries. Check every colour boundary close up; build colour
  boundaries from the full-resolution source image or smooth vector curves and masks, never from a downscaled crop.
- User rule: "Don't use masks." Never take an outline, shape, proportion, colour region or texture from a mask of any
  kind: a silhouette, cut-out alpha, segmentation, threshold, or the compare's overlap mask. Work from the original
  reference image itself, looking at it and measuring it directly at full resolution.
- User rule: References stay at original image quality. Build outlines, colour boundaries and textures only from the
  source image or its native-resolution cut-outs (a cut-out is fine, a resized one isn't). Never use a mask, compare
  sheet or downscaled image made for the quick check. Judge small details on their own close-up renders at the
  reference's pixel density, not on enlarged crops of full-body renders.
