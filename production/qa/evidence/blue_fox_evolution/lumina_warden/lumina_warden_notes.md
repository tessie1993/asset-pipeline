# lumina_warden — Lumina Warden (Phase 3): builder notes

Fill every section of `## Analysis

### What it is
Lumina Warden, the phase-3 evolution of a stylised blue fox (anime / painted game-art style, soft
cel-like shading with dark navy ink outlines and painted fur strokes). A slender fox standing square on
all four legs, head up and turned forward (front faces -Y). It reads as THIS creature because of:
(1) two huge pointed ears (about a third of the total height) with dark indigo, star-speckled
inner bowls carrying glowing cyan spirals and cream fur tufts at the base; (2) a thick cream chest
ruff under a silver filigree collar holding a diamond-shaped glowing blue crystal; (3) iridescent
lavender / cyan / mint feather-like fur tufts sweeping up and back off both shoulders; (4) a huge
mass of several curling tails behind it that coil into spiral lobes on the ground, banded blue and
cream, with dark indigo star-speckled areas and a white star constellation joined by thin glowing
lines; (5) glowing cyan swirl markings on forehead, cheeks, flanks, haunch and legs. Body blue
fur, lower legs and paws darker navy-blue, cream muzzle, cheeks, chest, belly.
Construction: one fused body (torso, neck, head, muzzle, legs, paws, fur tufts) sculpted as
signed-distance clay; separate ears, eyes, nose, collar, gem, shoulder feathers and five tails
that overlap the body like the drawing's layers.

### Views
Reference = bottom row of source.jpg (4096 px square). Three drawn views, orthographic (no
perspective convergence; a turnaround sheet), each drawn at a slightly different scale and, as the
user says, the angles differ between them (the front view's ears are drawn larger and its tails
are spread wider; the back view shows three ground lobes the side view cannot).
- View 1, front (az 0, el 5), box 160 2090 1150 3636: face, eye shape, forehead/cheek markings,
  ear insides (indigo, stars, cyan spiral, cream tuft), collar filigree and gem straight on, chest
  ruff V point, front legs and paws with toes, tails fanning out left and right on the ground (the
  fox's right lobe curls up into a hook). The ear glow halo is part of its outline (pale cyan, about
  15 px).
- View 2, side (az 90 = head to the left, we see the fox's +X / left side; main focus), box 1290 2280
  2990 3655: profile of head, muzzle and nose, ear stance, back line, belly line, leg joints (elbow,
  carpus, stifle, hock), shoulder feathers, collar seen edge-on with the gem projecting at the chest,
  the big arcing tail with the constellation and the coiled ground lobe with a flicked tip.
- View 3, back (az 180), box 3018 2235 4016 3638: back of the ears (blue, with cyan spirals on their
  backs), the nape, shoulder feathers sticking out sideways, the tails' roots fanning from the rump
  and the three spiral ground lobes (left, centre, right) plus two thin wisp tails curling out to the
  sides; one hind paw shows under the centre lobe.
Not shown: top and underside. Inferred: top of the back is the side view's smooth back line with the
back view's width; underside belly is cream (side view shows the cream belly edge); the fox's right
(-X) side mirrors the left except that the constellation is on the visible (+X) side and the tails
differ.
Camera: --ortho (a drawn turnaround, no perspective), elevation 5 for all (a little of the paws' tops
and the back shows).

### Size and proportions
Size anchor: sheet says scale 1/4, approx. 100 cm: taken as the total height (ground to ear tip) =
1.00 m. Side view: 1353 px = 1.00 m (ppm 1353); front view drawn at 1500 px/m (ears larger); back
1382 px/m.
cv.py measure: front w/h 0.64 (fill 0.58, symmetry 0.95), side w/h 1.24 (fill 0.49), back w/h 0.71
(fill 0.53, symmetry 0.97); width : height : depth = 0.64 : 1 : 1.24.
Overall model: width (X) 0.66 m (tail lobes, wisps to 0.70) x length (Y) 1.24 m x height 1.00 m.
Side-view landmarks (xs = metres from the nose tip backwards, z above ground):
nose tip xs 0 z 0.68; eye xs 0.12 z 0.72; forehead top z 0.80; ears base z 0.74-0.80 at xs 0.18-0.36,
tips z 1.00 at xs 0.22 (far) and 0.34 (near); jaw/throat z 0.62; chest front xs 0.10 (ruff) with the gem
at xs 0.08-0.14 z 0.40-0.50; withers z 0.60 at xs 0.40; back flat z 0.60-0.62 to the rump xs 0.75;
chest bottom z 0.33 (xs 0.22-0.40); belly z 0.37-0.40 (xs 0.45-0.62); front paws xs 0.17-0.30 and
0.27-0.38; hind paws xs 0.55-0.65 (far) and 0.70-0.80 (near); hock z 0.13; stifle z 0.30; tail root
xs 0.74 z 0.56; upper tail arc top z 0.73 at xs 0.95-1.10; tail back edge xs 1.24 at z 0.45; ground
lobe xs 0.72-1.18 z 0-0.30, flicked tip to xs 1.18 z 0.05.
Front view (x from the centre line): ear tips x +-0.21 z 0.99, outer ear edge +-0.24; head width +-0.12,
cheek tufts +-0.17 at z 0.60; eyes x +-0.055 z 0.665; nose z 0.595; collar z 0.40-0.55, span +-0.16;
gem 0.06 wide x 0.11 tall, centre z 0.41; front legs centred x +-0.075, 0.07 wide; tail lobes to
x -0.31 / +0.31, z 0.03-0.33, right hook to z 0.39.
Back view: ear tips x +-0.17, outer +-0.21; shoulder feathers to x +-0.17 z 0.45-0.62; body +-0.13;
lobes: left centre x -0.25 z 0.13 r 0.13, centre x 0 z 0.12 r 0.16, right x +0.24 z 0.13 r 0.13; wisps to
x +-0.36 at z 0.28-0.33.
KEY RATIOS (side view unless named):
- R1 length : height = 1.24 (side w/h).
- R2 ear length (base to tip) : height = 0.27 (side), 0.31 (front).
- R3 withers height : height = 0.60.
- R4 leg length (chest bottom to ground) : withers height = 0.55 (0.33 / 0.60).
- R5 head length (nose to back of skull, xs 0-0.30) : height = 0.30.
- R6 nose height : height = 0.68.
- R7 tail mass length (xs 0.74-1.24) : total length = 0.40.
- R8 front: width : height = 0.64; head width (cheek tufts) : total width = 0.53.
- R9 back: width : height = 0.71; centre lobe diameter : width = 0.45.
- R10 body length (chest front to rump, xs 0.10-0.78) : height = 0.68.

### Close observation
cv.py observe (3 sheets, 9 tiles each) plus my own 1:1 crops (front head, side head, chest, side
body, side tail). Sample numbers are cv-style stats of 20-40 px boxes (mean, darkest 5 %, lightest 5 %).
Head (front r1c2, side r1c1): smooth blue fur lighter than the body (face #9ecde1 L0.77, very
even, sd 0.007); cream muzzle #d8cfc6 L0.82 (dark #cfc3ba, light #e1d8cf) that runs from the nose
back under the eye to jagged cheek tufts; cream brow spots above each eye (#cad9de-#ebe8e3, L0.84);
glowing cyan flame mark on the forehead (three strokes, the centre a teardrop) and a cyan stroke
under/behind each eye; almond eyes slanted up-out, bright blue iris (#4f6d9e mean, light catch
#d8f2ff) with a thick navy upper lid line (#203767) that flicks out; small black-brown nose
(#282736 dark, glossy highlight #d6d3de); a subtle smiling mouth line (W-shape under the nose in
front). Fur edges on the cheeks are drawn as 3-5 sharp spikes each side, uneven lengths.
Ears (front r1c1/r1c3, side r1c1, back r1c1-r1c3): long leaf shapes, outer back face blue
(#769abf L0.59, darker toward the rim #6586b0), inner bowl deep indigo-violet (#5c68a1-#565a93,
L0.37-0.42) speckled with tiny white/cyan star dots of uneven size and a glowing cyan spiral (one
curl, tail running down to the base, light #a2e2fd L0.84); a thin blue rim around the bowl; cream
fur tuft (#d9d3d0) of 4-5 feather-like blades at the inner base, tips spiky; the backs of the ears
carry 2 cyan swirl strokes each (back view). Ear tips are slightly notched/split (side view far ear
tip has a small double point). Pale cyan glow around the ears in the front view only.
Chest and collar (front r2c2, side r2c1, my chest crop): cream chest ruff (#c9cfce-#e0dbd3)
falling to a V point at z 0.22 between the legs, its edge cut into spiky fur locks; a bluish tint
in the ruff below the gem with cyan glowing feather marks (light #a6f3fe) radiating from under the
gem (blue glow halo, dark #104883 at the gem rim). Collar: polished silver (mean #aaadb7, dark
#33384b in the grooves, highlight #e8e8ea) round wires about 8-10 mm thick: two main arched bands
around the neck front meeting at the gem; on each side 2 scroll curls (C and S curls) and 3-4
antler-like tendrils rising up and out at x +-0.13..0.17 with small leaf-tipped ends; the two sides
are near mirror copies but the tendril ends differ in length. Gem: elongated rhombus, faceted (a
vertical and a horizontal ridge, 4 facets each lit differently: #1d46ad dark to #bee5ff light),
set in a silver bezel frame about 8 mm wide; glows blue (emission). In side view it projects forward
from the chest as a flat rhombus 0.03 thick.
Body (side r2c2, back r2c2): blue fur #83a6c0 L0.63 (dark #7495b2, light #8eb4cd) with lighter back
and haunch top (#95c1d5 L0.73) and softly darker belly side; long soft fur strokes visible as faint
lighter streaks following the body direction (texture 0.06-0.11). Glowing cyan swirl markings
(#bef4ff L0.92 core, #9bc6dc soft edge): on the haunch a spiral curl with two flame strokes above,
three wavy strokes along the back from the withers, a few dots and a short stroke on the thigh,
streaks on the upper front leg. Cream belly fringe (#887f83 in shadow) with spiky locks; a spiky
fur tuft at the back of each elbow and at the chest bottom.
Shoulder feathers (side r2c1, back r2c1/r2c3): 6-8 long curved blade-like locks per side, fanning
up and back from the shoulder, tips sharp and curling up; colour shifts along each blade: base blue
(#82b5c8), mint/cyan streaks (#95d2da-#9ff0d0) in the middle, lavender (#b4a6e6) at the tips and
edges, a few white speckles; blades differ in length (0.12-0.25 m) and curl.
Legs and paws (front r3c2, side r3c1/r3c2): upper legs body blue grading to darker navy-blue lower
legs (#50698b L0.40, dark #445b80) and paws (#465a80 L0.35, dark #38486f); paws rounded with 3-4 toe
lobes separated by dark creases; slight lighter rim light on the front of the legs.
Tails (side r2c3/r3c3, back r3c1-r3c3, front r3c1/r3c3): five tails from the rump. Thick (up to 0.15 m
radius) with tapering, curled, pointed tips. Painted in spiral bands following each tail's coil:
cream bands (#ddd5c5 L0.84, shadow #bfbdb9) alternate with mid-blue (#88b0c8 L0.66) and dark indigo
(#465a8c L0.35) bands; band widths vary (0.02-0.06 m), not regular. The big upper tail in side view has
a dark indigo inner area (#5d7ca6 mean, dark #465a8c) with faint star specks and the constellation:
6 white-cyan glowing star dots (radius 8-15 mm, uneven) joined by thin glowing lines (2-3 mm). The back
view centre lobe repeats 4-5 stars of the constellation on its left half. Ground lobes are coiled
spirals (2 turns) with a dark eye at the centre. Cyan glowing streaks run along the tails near the root
(back view). Wisp tails: thinner (r 0.03-0.05), curl up at their tips.
Imperfections / variation: none of the markings are symmetric copies (left ear spiral vs right
spiral differ in size; tails all different); fur edges are ragged; star dots differ in size and
brightness; tail band widths vary; the collar tendrils are uneven.

### Parts inventory
| # | part | count | size (m) | position and orientation | shape and how to model it (technique, skill) | geometry detail (what is modelled: bevels, creases, folds, holes, relief) | nuances (imperfections, asymmetry, how each copy differs) |
|---|---|---|---|---|---|---|---|
| 1 | torso (chest, ribcage, belly, haunches) | 1 | 0.68 long x 0.24 wide x 0.30 tall | Y -0.52..+0.16, z 0.32-0.62, level back | SDF clay ellipsoids (chest, ribcage, pelvis) smooth-blended, sculpting skill, quad remesh | chest deeper than belly (tuck-up), haunch bulge, shoulder blade bulge | belly fringe locks of different lengths |
| 2 | neck | 1 | r 0.09, 0.2 long | from chest (Y -0.40 z 0.52) up to head (Y -0.42 z 0.70) | SDF tube blended into chest and head | fur mane spikes at the nape (back view) | spikes uneven |
| 3 | head (cranium + muzzle + cheeks) | 1 | 0.30 long, 0.24 wide, 0.17 tall | cranium centre Y -0.42 z 0.73; nose tip Y -0.62 z 0.68 | SDF ellipsoid cranium, tapered muzzle cone, jaw, brow mound | eye sockets, brow ridge, mouth crease (smile), chin | cheek tufts differ per side |
| 4 | cheek fur tufts | 2 sides x 4 spikes | spikes 0.03-0.07 long | x +-0.12..0.17 z 0.57-0.66 pointing out-down | SDF cones blended in | sharp tips | each spike its own length and angle |
| 5 | chest ruff locks | 1 ruff, ~9 spikes | ruff 0.24 wide, 0.33 tall; spikes 0.04-0.08 | front of chest z 0.22-0.60, V point at z 0.22 | SDF ellipsoid mound + downward cones | layered spiky locks at bottom and sides | uneven spike lengths |
| 6 | front legs | 2 | 0.33 long, r 0.035-0.045 | x +-0.075, Y -0.38 (+X) / -0.30 (-X) | SDF tapered tubes, elbow and carpus joints | elbow tuft spike, carpal bend | staggered as in side view |
| 7 | hind legs | 2 | 0.42 long, thigh r 0.08 | x +-0.08, thigh Y 0.07, paws Y 0.13 (+X) and -0.02 (-X) | SDF thigh ellipsoid + tubes stifle-hock-paw | hock angle, thigh bulge | far leg angled forward |
| 8 | paws with toes | 4 | 0.09 long x 0.07 wide x 0.045 tall | under each leg | SDF ellipsoid + 4 toe spheres, crease subtracted between toes | toe lobes and creases | toe sizes vary |
| 9 | ears | 2 | 0.30 long, 0.13 wide at base, 0.025 thick | base x +-0.09 Y -0.36 z 0.77, tip x +-0.19 Y -0.33 z 1.00, inner bowl faces forward-out | bmesh lofted leaf with a curved bowl, solidified, subdivided | bowl depth 0.03, rounded rim, notched tip | left/right tilt and spiral differ |
| 10 | ear inner tufts | 2 ears x 5 blades | 0.05-0.10 long | inner base of each ear, rising out of the bowl | bent tapered blades (bmesh) | thickness 4 mm, sharp tips | each blade its own length/curve |
| 11 | eyes | 2 | 0.05 x 0.022 almond | x +-0.055 z 0.67 Y -0.53, slanted up-out 15 deg | flattened ellipsoids set into the head, shader iris | embedded in sockets | catch-light placement per eye |
| 12 | upper lid liners | 2 | 0.055 long, r 3 mm | over each eye, flicking out | swept tube | raised ridge | flick differs |
| 13 | nose | 1 | 0.03 wide x 0.02 tall | Y -0.62 z 0.68 | SDF/ellipsoid rounded triangle, separate glossy object | nostril dents | - |
| 14 | collar main bands | 2 | wire r 0.008, arcs 0.25 long | around neck front z 0.42-0.55 meeting at the gem | swept tube along 3D curves | round wire | slightly different arcs |
| 15 | collar scroll curls | 2 per side | spiral r 0.03 | x +-0.06..0.12 z 0.42-0.50 on the chest | swept tube along a planar spiral | tapering end | left/right differ in turns |
| 16 | collar tendrils | 4 per side | 0.08-0.14 long, r 0.005 | rising out from the sides x +-0.12..0.17 z 0.47-0.57 | swept tapering tubes with leaf tips | leaf-tip bulbs | lengths differ |
| 17 | gem bezel | 1 | 0.075 x 0.13, wire 0.008 | around the gem, Y -0.52 z 0.41 | swept rhombus tube | bevelled frame | - |
| 18 | crystal gem | 1 | 0.06 x 0.11 x 0.035 | Y -0.535 z 0.41, facing forward | faceted bipyramid (bmesh), flat shaded | facets and ridges | - |
| 19 | shoulder feather locks | 2 sides x 7 | 0.12-0.26 long, 0.03-0.05 wide | from shoulders Y -0.35..-0.20 z 0.48-0.60, sweeping up/back/out | bent tapered blades with thickness (bmesh) | thickness 6 mm, curled tips | every lock its own length, curl, yaw |
| 20 | centre tail (constellation) | 1 | 0.95 long path, r up to 0.15 | root Y 0.12 z 0.55, arcs up to z 0.73, back to Y 0.62, down and coils on the ground at Y 0.35 | swept tube along a 3D curve with radius profile, coiled end | coil spiral lobe, pointed tip | dark starry zone + constellation only here |
| 21 | lateral tails | 2 | 0.8 path, r up to 0.13 | root at rump, out and down to coiled lobes x +-0.22 Y 0.30 z 0.13 | swept tubes, coiled ends | 2-turn spiral lobe | left one curls up into a hook (front view), right lies flat |
| 22 | wisp tails | 2 | 0.65 path, r up to 0.05 | from rump out sideways to x +-0.34 z 0.30, tips curling up | swept tapering tubes | curled tip | different curls |
| 23 | top curl tips | 2 | 0.15 long r 0.02 | on top of centre tail arc (xs 0.80, 1.20 z 0.70) | swept tubes curling | hooked tip | different sizes |
| 24 | constellation stars | 9 | r 0.006-0.013 | on the centre tail's +X side (6) and back of its lobe (3-4) | small domes (spheres) half sunk, emissive | raised dots | sizes and brightness differ |
| 25 | glowing markings | many | strokes 3-10 mm wide | forehead, under eyes, ear spirals, back, haunch, legs, chest, tails | shader: emission from distance-to-stroke attributes | - | each stroke its own shape |

### Materials and shaders
S1 body fur (parts 1-8 body clay): stylised painted fur. Base #83a6c0 (L0.63; range #7495b2-#8eb4cd),
lighter on the back and the face (#95c1d5-#9ecde1, L0.73-0.77, gradient on Z and an attribute for
the face), darker toward the lower legs and paws (#50698b L0.40 at z 0.15 to #465a80 L0.35 at the
paw; gradient on Z for the legs). Cream zones (muzzle, cheeks, brow spots, chest ruff, belly
underside, inner thigh) #d8cfc6-#e0dbd3 (L0.82-0.86), bluish cream in shadow #c9cfce, edges jagged
(noise-broken attribute mask, narrow ramp). Roughness 0.75-0.9 (fur is matte), varied by noise.
Relief: fine fur strokes as a bump from a stretched noise/wave texture (strokes about 1-2 cm long,
running back along the body and down the legs), 1 mm deep. Colour variation: low-frequency noise
+-0.03 L and the stroke texture +-0.02. Glowing cyan markings (#bef4ff core, emission 2-4) from
distance-to-stroke attributes; soft glow edge #9bc6dc. Built with kit.principled + attributes.
S2 ear outer (ears back + rim): blue #769abf (L0.59), darker at the rim (#6586b0), roughness 0.8, fur
strokes along the ear length; cyan swirl strokes on the back (emission).
S3 ear inner (bowl): indigo-violet #5c68a1 -> #565a93 (L0.37-0.42), darker toward the base, roughness
0.7, star specks (voronoi points thresholded, white/cyan, sizes vary, emission), glowing cyan spiral
from an attribute; hard edge to S2 via kit.mark.
S4 cream fur tufts (ear tufts): #d9d3d0 with blue-grey shadow strands (#b3adaf), roughness 0.85,
stroke texture along the blade.
S5 eye: iris blue #4f6d9e with a lighter lower half (#7fb4e0), dark pupil and outer ring #203767, a white
catch light (#d8f2ff) top-out; roughness 0.15 (wet); built procedurally from object-space coordinates.
S6 lid liner / nose: navy-black #282736 / #1c2240, roughness 0.3 (nose glossy), slight noise.
S7 polished silver (collar, bezel): metallic 1, base #c8ccd6, roughness 0.22-0.4 by noise, darker tarnish
#5a5f70 in crevices (AO mask), a slight blue reflection from the environment.
S8 crystal gem: deep blue #1d46ad-#4d81d7 with facet variation, emission blue #3d8bff strength 3,
roughness 0.05, flat shaded facets; lighter inner sparkle.
S9 shoulder feathers: iridescent gradient along each blade (attribute t along blade, plus an attribute
across): base blue #82b5c8 -> mint #9ff0d0 / cyan #95d2da streaks -> lavender #b4a6e6 at the tips and
edges; streak noise along the blade; white specks; slight emission on the cyan streaks (0.4);
roughness 0.5.
S10 tail fur: spiral bands from an attribute (band coordinate along each tail's coil, broken by noise):
cream #ddd5c5 (shadow #bfbdb9), mid blue #88b0c8, dark indigo #465a8c; band widths vary; roughness 0.8;
fur stroke bump along the tail; dark indigo starry zone on the centre tail (attribute), star specks;
constellation lines and glowing streaks near the root as emission from attributes.
S11 constellation stars: white-cyan #e6fbff emission 6, roughness 0.3.
Mixes are done on the inputs of one Principled BSDF per surface (no Mix Shader).

### Details and nuances
- Forehead flame mark (three cyan strokes, middle teardrop): shader attribute strokes, emission.
- Cyan stroke under and behind each eye: shader.
- Cream brow spot above each eye (oval): shader attribute.
- Almond eyes slanted up-out with a thick dark lid line flicking outward: modelled liner tube + eye object.
- Smiling mouth line (W under the nose): crease cut in the clay.
- Nose glossy with two nostril dents: modelled.
- Cheek fur spikes, 4 per side, uneven: modelled cones.
- Ear inner indigo with star specks of uneven size: shader (voronoi specks).
- Ear inner cyan spiral, left and right differ: shader attribute.
- Cream ear-base tufts, 5 blades per ear, each different: modelled blades.
- Cyan swirl strokes on the ear backs (back view): shader.
- Notched ear tip: modelled (small second point).
- Nape mane spikes (back view): modelled cones.
- Collar wires polished silver with dark grooves: modelled tubes + AO tarnish in shader.
- Collar tendrils with leaf tips, uneven: modelled.
- Rhombus gem with facets and blue glow: modelled bipyramid + emission.
- Glowing feather marks on the chest below the gem: shader emission.
- Shoulder feather locks, iridescent lavender/cyan/mint, white specks, uneven lengths: modelled blades + shader.
- Three wavy cyan strokes on the back, spiral curl on the haunch, dots on the thigh: shader.
- Elbow fur tuft and chest-bottom spikes and belly fringe locks: modelled cones.
- Lower legs and paws darker navy: shader gradient.
- Toe lobes with dark creases: modelled + AO.
- Fur strokes over all fur: bump + colour noise (shader).
- Tail bands cream / blue / indigo of uneven widths following the coils: shader attribute.
- Coiled spiral ground lobes with a dark centre: modelled coil + shader.
- Dark indigo starry area with the constellation (6 stars + lines) on the side tail: modelled star dots + shader lines.
- Constellation repeated on the centre lobe in back view (4 stars): modelled dots + lines.
- Glowing cyan streaks along the tails near the root: shader.
- Wisp tails curling up at the tips, hooked curl tips on top of the tail arc: modelled.

### Skills, add-ons and tools
- blender-image-to-3d: the method (measure, silhouette first, then forms, details, materials), the
  creature notes (ribcage/pelvis masses, hock and stifle placement, tails as tubes) and the gate habit
  of writing every mismatch as a number.
- scenario-blender-sculpting (bx_sculpt): signed-distance `Clay` with smooth blends for the whole
  body (ellipsoids, round cones, tapered tubes, half-space clip for the ground), `sd_cone` fur locks,
  `Clay.project` to snap collar wires, feather roots and eye frames onto the sculpted surface,
  `bezier` for guide curves; meshed by OpenVDB.
- scenario-blender-retopology: `kit.quad_remesh` (Instant Meshes) of the voxel body to ~18k quads:
  static asset, auto-remesh is the documented route.
- scenario-blender-texturing-shading: masks into the inputs of one Principled BSDF (no Mix Shader),
  noise with contrast ramps, bump distance at the real relief (1-1.5 mm), AO-driven tarnish in the
  silver, eye built from its own UVs; emission for the glow (reaches Godot).
- scenario-blender-expert: Blender 5.2 names (Emission Color/Strength, Mix node indices), headless rules.
- Kit: kit.principled, kit.mark (hard cream edges cut into the mesh), kit.quad_remesh, kit.mesh_object,
  kit.UV_LAYER, kit.run(texture=4096). Own helpers in the generator: swept tubes with elliptic
  sections and UVs (tails, collar, feathers, tufts, liners), numpy painters for the projection masks
  and the tail / ear textures, bilinear tube sampling to paint world-space constellation lines.
- Material search: fur (only realistic brown pelts, wrong style) and polished silver (rusty / brushed
  plates): none fits a painted stylised fox, so every surface is procedural + painted masks.
- Checks: CV compare per view (outline, colours), clay row for the forms, cv.py closeup/sample for the
  head, collar, tails; CHECK lines for floating parts and manifold.

### Build plan
1. Body clay (one SDF, voxel 4.2 mm) -> quad remesh 18k quads (~36k tris) -> cream zones by kit.mark
   -> attributes (height, face, leg mask, projection coordinates).
2. Ears (lofted bowl leaves, 2 materials, Subsurf 1, ~5k tris each) with 5 cream tufts each; eyes,
   lid liners, nose (fine clay 1.1 mm).
3. Collar: neck rings, arcs, scroll curls, tendrils with leaf buds, gem bezel (swept wires, ~10k
   tris); faceted gem on the chest surface.
4. Shoulder feathers: 7 blades per side from projected shoulder roots (~5k tris).
5. Tails: centre coil tail (40 sides x 122 rings), two lateral coiled lobes, two wisps, six curl tips
   (~30k tris); constellation stars raycast onto them; painted band / starry textures in a shared UV
   atlas (2048 x 2304) plus an emission atlas.
6. Materials: fur (blue + cream variants) with projected glow and decals, ear outer/inner, tuft,
   feather, silver, gem, eye, nose/liner, star, tail.
Budget split (100k): body 36k, tails 30k, ears + tufts 12k, collar 10k, feathers 5k, small parts 4k.
Texture: kit.run(build, texture=4096) (fine glowing lines and stars).
Order of cycles: silhouette per view first (tail mass and ears), then forms (head, legs), then
markings / materials, then details.

## Cycles

## Cycle 1
(Before it: one `--no-render` test run, and helper previews in my work folder that showed generated
images rendering black: the colourspace was set after the pixels, which regenerates a generated
image. Fixed in new_image().)
CV: overlap front 0.76, side 0.76, back 0.77; w/h front 0.72 vs 0.64 (+13 %), side 1.22 vs 1.24 (-2 %),
back 0.68 vs 0.71 (-4 %). CHECK: no floating parts, 2 non-manifold edges + 2 degenerate faces, 100,192
tris (budget 100k).
Matches (keep): overall layout (head left, five tails, lobes on the ground in front and back views),
tail bands cream/blue/indigo following the coils, dark starry zone with the constellation on the
side tail, three ground lobes in the back view, collar + glowing gem, cream chest and muzzle, navy
lower legs, ear bowls indigo with stars and cyan spiral.
Differs, cause, fix:
- Front w/h +13 %: wisps reach x +-0.34 and lobes +-0.33; the reference front is +-0.31 (back +-0.36).
  The views disagree (front 0.64, back 0.71): aim at width 0.67 (front +5 %, back -5 %). Wisp tips to
  +-0.31, lobe centres +-0.19.
- Side top-left missing 19 %: head too low and small; reference crown z 0.83 (mine 0.805), visible
  ear only from z 0.80 to 1.00. Raise cranium to centre z 0.745, rz 0.078; ear base to z 0.735.
- Ear tips span 0.46 of the height; front wants 0.42, back 0.34: tips to x +-0.195, bowl normal
  less outward (0.32 instead of 0.45) so the front sees the full bowl width.
- Back top-left/right lighter by 0.14-0.19 and extra 16 %: ear backs carry two large bright cyan
  strokes; make them thinner (x0.6) and the outer ear emission 0.8.
- Front middle-left/right darker by 0.11-0.14: tail lobes too dark; reference lobes are cream-heavy
  (#9fa8b9 mean, L0.66). Cream band share 0.30 -> 0.36, dark band narrower.
- Side chest: cream with blue islands (field noise 7 mm + blue between): reference chest side is clean
  cream back to Y -0.36 at z 0.5. Cream boundary further back (yb +0.03), noise halved.
- Side feathers small and grass-green; reference locks reach z 0.72 at Y -0.14, lavender/cyan. Lengths
  0.20-0.32, widths 0.03-0.045, ramp more lavender.
- Collar reads as a chain (two parallel rings): keep one thin ring (r 5.5 mm), lower at the front.
- Paws small (reference 0.09 x 0.05): paw ellipsoid 0.040 x 0.055 x 0.03, toes r 0.016.
- Legs: lower leg dark zone too short (reference navy up to z 0.30): ramp stops moved up 0.03-0.05.
- Bottom-right of the side: the flick curl hidden inside tail A: start it at Y 0.42 and run it to
  Y 0.60 with r 0.05.
- 2 non-manifold edges: from kit.mark cuts or the gem poke; check after the changes.

## Cycle 2
CV: overlap front 0.80 (+0.04), side 0.75, back 0.81 (+0.04); w/h front 0.68 vs 0.64 (+6 %), side 1.24 (0 %),
back 0.64 vs 0.71 (-9 %). CHECK: floating none, non-manifold 0, open edges 22, 98,154 tris.
Row-by-row extents (my helper rows.py: reference vs render, both normalised to height 1, side Y):
- z 0.04: reference tail ground contact Y 0.13-0.43 + flick 0.53-0.57; mine 0.29-0.58: the lower loop
  of tail A sits 0.15 too far back. z 0.4: reference has a gap between rump and tail (Y 0.12-0.26);
  mine is filled by the lateral tails coming down at Y 0.19-0.33 and tail A's inner loop.
- z 0.12: far hind leg reference Y -0.09..0.00, mine -0.03..0.04 (0.06 too far back). z 0.2: the two
  front legs are separate in the reference (-0.38..-0.32, -0.30..-0.24), merged in mine (legs too thick).
- z 0.8-0.9: reference ears span Y -0.45..-0.28 (far ear forward, ears seen at ~45 deg); mine -0.37..-0.29.
- Front z 0.4: reference +-0.15, mine +-0.23: wisps and lateral tails pass beside the chest. Front z
  0.7-0.9: reference ears +-0.20..0.245, mine +-0.15..0.22 (ears drawn bigger in front). Back z 0.9:
  reference +-0.18, mine +-0.21: the two views disagree on ear spread; keep mine between.
- Back z 0.2-0.3: reference lobes/wisps +-0.35, mine +-0.29-0.30; front z 0.2 reference +-0.31, mine
  +-0.335: the views disagree on the lobe width too (kept between).
Fixes: tail A re-routed (arc lower and broader, rv 0.165, back side at Y 0.455, bottom sweeping
forward to Y 0.15 then curling up into a spiral at (0.31, 0.25)); lateral tails go back behind tail A
before dropping (Y >= 0.30 below z 0.45); wisps lower (start z 0.44, out at z 0.28-0.34); legs slimmer
(radii 0.05/0.036/0.026, blend 0.015), far hind paw to Y -0.05, near hind hock/paw +0.02; ears wider
(outer 0.10), bowl turned out 0.45, far ear tip Y -0.42; find the 22 open edges.

## Cycle 3
CV: overlap front 0.82, side 0.78, back 0.81; w/h front 0.66 vs 0.64 (+3 %), side 1.22 vs 1.24 (-2 %),
back 0.66 vs 0.71 (-7 %, the views disagree, see Cycle 2). CHECK: all clean (0 non-manifold, 0 open,
floating none) after close_holes() fills the remesh holes. 98,578 tris.
(Back view elevation re-recorded as 0: at 5 deg the tails nearest the camera drop 0.05 m in the
projection and the back w/h fell to 0.62; the drawn back view shows no top-down tilt. A trial of the
front at 10 deg cut its overlap 0.83 -> 0.77, so the front stays at 5.)
Matches: outline in all three views within 0.18-0.22 of the reference; the side legs, back line,
tail arc top and back edge (rows.py: z 0.5 -0.53..0.61 vs -0.54..0.61; z 0.62 -0.49..-0.12 /
0.14..0.55 vs -0.49..-0.15 / 0.14..0.52); collar, gem, star dots, tail bands.
Differs, cause, fix (from rows.py and cv closeup of the front head):
- Side z 0.3-0.4: reference gap between thigh and tail at Y 0.12-0.26 with a broad hanging curl at
  Y 0.26-0.38; mine filled by lateral tails and wisps dropping at Y 0.2-0.4 and a thin curl. Route the
  lateral tails and wisps down behind tail A (Y 0.42-0.45), CurlHang broader (r 0.034, Y 0.26-0.36).
- Side z 0.7: tail arc top below 0.70 (reference 0.285..0.426 at z 0.7): rv ramped up too late along
  the path; rv now 0.11 at 5 %, 0.16 at 12 %, 0.18 at 25 %.
- Side z 0.04: lower lobe sat 0.15 too far back: bottom loop moved forward (to Y 0.17) and tightened
  (rv 0.08 at the front turn) so the gap above it stays open.
- Front head (closeup): head narrow (+-0.15 vs +-0.17-0.20 at z 0.6-0.7), eyes small and half
  closed, forehead had five bright stripes (side forehead stroke projected onto the brow), cream
  covered the whole lower face, neck and cheeks as one block. Fixes: cranium rx 0.106, brow rx 0.08,
  cheeks 0.075/0.062; eyes 0.056 x 0.027 with a thinner liner and a larger iris; forehead flame only
  (teardrop + 2 thin side strokes); face cream lower (z 0.684 under the eye) with a blue nose bridge
  narrowing to the nose; neck cream bib +-0.075..0.105 so the neck sides stay blue; glow emission 0.8
  and halos 0.15; ear spirals thinner, ear emission 0.9; cheek tufts thicker (r 0.03) and longer.
- Ears in the side view 0.04 too far back at z 0.8-0.9: ear bases and tips moved forward 0.024-0.03.

## Cycle 4
CV: overlap front 0.83, side 0.79, back 0.79 (mean 0.81); w/h front 0.66 vs 0.64 (+3 %), side 1.22 vs 1.24
(-2 %), back 0.66 vs 0.71 (-7 %). CHECK: floating none, no material none, flat colour none, non-manifold 0,
open 0, mirror 0.0128. 98,952 tris (budget 100,000). Dimensions 0.653 x 1.242 x 0.994 m.
Matches (keep): front silhouette (lobes, legs, chest V, collar width +-0.17 at z 0.5); side back line,
legs and paws (rows z 0.12: front legs -0.374..-0.322 / -0.293..-0.241 vs ref -0.384..-0.332 /
-0.303..-0.249; far hind -0.066..-0.009 vs -0.087..-0.004), tail arc top now at z 0.70 (0.225..0.434 vs
0.223..0.426), tail back edge, lower lobe ground contact 0.074..0.467 (+ flick 0.473..0.569) vs ref
0.10..0.43 + 0.53..0.57; back lobes +-0.31..0.33 at z 0.1-0.3 (ref +-0.33..0.35). Face now reads: blue
head with forehead flame, open blue eyes with liner, cream muzzle sides, nose; collar/gem; glowing
constellation with 6+5 stars and lines; tail bands.
Still differs (cause -> fix):
1. Side z 0.3-0.4 (CV "extra bottom-centre 17 %, centre 9 %"): the reference gap between rump and tail is
   Y 0.12..0.26 at z 0.4; mine only 0.168..0.184. Cause: tail A's root is thick (rv 0.11 at 5 % of the
   path, its underside reaches z 0.43 at Y 0.2) plus CurlHang. Fix: rv profile [0:0.05, 0.05:0.075,
   0.1:0.12, 0.18:0.17, 0.25:0.18, ...]; CurlHang start at Y 0.33 (keep r 0.034).
2. Side top-left missing 13 %: reference ears sit further forward and are seen wider (z 0.9 ref
   -0.449..-0.28, mine -0.418..-0.298); the far (-X) ear tip to Y -0.44, near ear -0.31, and turn the
   bowls a little more toward the camera side (f0 x 0.5) if the front allows.
3. Back top-left/right extra 17-20 % and lighter by 0.14: ears too wide for the back view (z 0.9 ref
   +-0.18, mine +-0.23; z 0.7 ref +-0.10, mine +-0.21 from the outer base flare). The front view wants
   +-0.245 at z 0.9: the drawings disagree. Keep a middle (+-0.21) by dropping the base flare
   (0.02*(1-t)^4 term) and darkening the ear backs (ramp #6585b0 -> #587aa6) with the cyan strokes at
   0.6 emission.
4. Back w/h -7 % and front +3 %: same width seen front/back; the reference views disagree (0.64 vs
   0.71). Leave it, document in the Report.
5. Front top-left/right missing 10-11 %: the reference front ears are drawn bigger (and the glow halo
   adds ~15 px): unreachable without breaking the back view; leave.
6. Materials: CV front "middle-left darker by 0.09" (tail lobes in front): add more cream at the lobes'
   outer coil (cream band share 0.36 -> 0.40); side "middle-right lighter by 0.10": the dark starry zone
   is smaller than the reference's (ref interior #5d7ca6, dark #465a8c): widen the zone ellipse to
   (0.17, 0.19) around (0.37, 0.42).
7. Detail still to check in close-ups (not yet looked at closely): paws/toes creases, feather colours
   (reference lavender tips + mint streaks), ear tufts (now wide blades), collar tendrils/leaf tips.

## Cycle 5
(Builder 2. Helper previews in the work folder before the build, as the Handoff describes.)
CV: overlap front 0.83, side 0.79, back 0.81 (mean 0.81); w/h front 0.68 vs 0.64 (+7 %), side 1.22 vs 1.24
(-2 %), back 0.68 vs 0.71 (-4 %). CHECK: floating none, no material none, flat colour none, non-manifold 0,
open 0, mirror 0.0112. 98,456 tris. Dimensions 0.679 x 1.247 x 0.993 m.
Found and fixed (biggest error of builds 1-4): the kit renders every view by turning a "Turntable" parent
(kit.render_views), so the fur shader's WORLD normal (Geometry > Normal) changed with the view: in the side
view the front projection (chest feathers, leg streaks) was painted on the flank and the side strokes were
missing; in the back view the forehead flame and brow spots were painted on the back of the head. Now the
fur (and gem facets) use Texture Coordinate > Normal (object space): the flank haunch spiral, back strokes and
thigh dots show in the side view; the back of the head is plain blue. The bake is unaffected either way.
Other changes in this build (from Cycle 4 items and my look at the renders):
- Inner legs were cream down to the paws (belly mask |x| < 0.075 with no lower limit; the legs sit at |x|
  0.075): far legs read pale grey in the side view. Belly cream now z 0.30-0.392, |x| < 0.068.
- Ears 17 % wider (EAR_K) and turned 40 deg outward (f0 x 0.80): side view now sees each ear 0.08-0.10 wide
  (was 0.04); near ear tip 0.025 forward. Eyes larger (0.062 x 0.031), iris fills the almond, pale-blue
  corners instead of white, turned 0.3 outward so the side view sees the almond; thicker lid liner.
- Head: crown/brow larger and forward, muzzle and nose 0.014 longer, cheek tufts 10 % longer; chest mound and
  front legs 0.01-0.018 forward (side overlay had magenta all along the front).
- Tail A: root raised and thinner in plane (rv 0.075 at 5 %, 0.10 at 10 %); lower loop wider across X (ru
  0.15) for the back view's centre lobe; root and arc blue-dominant (cream band 0.18 instead of 0.40 for
  u < 0.25) with 6 glow streaks; lateral tails start higher (z 0.535) and their lobes sit at x +-0.19, r 0.075;
  tail cream share 0.40 (front lobes were darker by 0.09); starry zone ellipse 0.165 x 0.185.
Matches (keep): side flank markings now as the reference (spiral on the haunch, flame strokes, back
strokes); dark navy far legs; side chest cream; constellation; back lobes width at z 0.1-0.2.
Still differs (measured on cv closeups 1 and 2, overlay):
1. Front: ears read as flat trapezoids with a horizontal base edge floating beside the head at x +-0.2,
   z 0.735; the reference ear's outer edge runs down into the cheek at z 0.66. Fix: taper the outer
   half-width at the base (x0.55 at t 0, full at t 0.25) and lower the ear base 0.015.
2. Front face: head narrower than the reference (eye level +-0.12 vs +-0.15), eyes dark and sleepy. Fix:
   cranium rx 0.125, cheeks x 0.085 r 0.068; iris ramp brighter (#bfe8ff..#2b4590), pupil smaller.
3. Side: crown ~0.015 low; raise cranium to z 0.755, rz 0.088.
4. Back: tail A's arc rises as a column to z 0.72 behind the head (the back drawing shows the nape there; the
   side drawing needs the arc: the drawings disagree). Fix: flatter ribbon at the arc (ru 0.045-0.05 for
   t < 0.4) so the column is thinner from behind.
5. Front w/h +7 % / back -4 %: lobe width is a compromise between the two drawings (front +-0.31, back
   +-0.35): leave.

## Cycle 6
CV: overlap front 0.80, side 0.80, back 0.77 (mean 0.79); w/h front 0.68 (+6 %), side 1.23 vs 1.24 (-1 %), back
0.68 vs 0.71 (-4 %). CHECK: all clean (floating none, no material none, flat colour none, non-manifold 0,
open 0), mirror 0.0125. 98,696 tris (body remesh 14,500 quads, lateral tails 28 sides to stay in budget).
Changes in this build: ear outer edge pulled in at the base (x0.55 at t 0) and base lowered to z 0.722 (no
flat bottom edge floating beside the head); cranium rx 0.123 / crown z 0.84, cheeks wider; brighter iris
and smaller pupil; tail A a flat ribbon across X along the arc (ru 0.05) and moved to x +0.03; the
lateral tails' roots now run down INSIDE tail A's ribbon (catmull along tail A's path) and leave it below
the starry zone; the constellation stars are cast onto tail A only (before, the lateral tail in front
caught half of them); toe creases cut between the toe lobes; AO darkening in the fur shader (creases,
joints, under locks); shoulder locks rewritten: 9 per side in two layers, S-curved, twisted, each its own
length/width/curl; cream edge noise reduced (blue islands on the neck).
Matches (keep): side view now clean as drawn: the tail A ribbon with the dark starry interior and the full
6+1 star constellation with its lines, the gap under the tail root, the lobe below; side head with a
visible almond eye; flank markings; front ears no longer floating plates.
Differs, cause, fix:
1. Front middle-left/right extra 21-25 % and back middle-left/right extra 18 %: the wisp tails now leave
   the rump at z 0.585 and run out as raised arms at z 0.4-0.58 (front reference has nothing outside
   +-0.18 above z 0.38). Fix: wisp path (0.01, 0.12, 0.50) -> (0.03, 0.30, 0.42) -> (0.20, 0.33, 0.32) ->
   (0.305, 0.25, 0.275): out at z <= 0.35 where they pass beside the body.
2. Front and back: a dark hole in the middle of each lateral lobe spiral (clay row too): the spiral's
   centre drifts in Y (0.03 sin(phi/2)) and the tube tapers, leaving a tunnel between the last turns.
   Fix: a squashed plug (r 0.04, tail material, UV in the strip's coil-centre band) at each coil centre.
3. Back: ears +-0.22 vs reference +-0.18 at z 0.9 (front reference +-0.245): drawings disagree, kept.
4. Front w/h +6 %: the lobes (back wants +-0.35, front +-0.31): kept between.

## Cycle 7
CV: overlap front 0.81, side 0.80, back 0.82 (mean 0.81); w/h front 0.68 (+6 %), side 1.23 vs 1.24 (-1 %), back
0.68 vs 0.71 (-4 %). CHECK: all clean, mirror 0.0122. 99,272 tris (budget 100,000). Dimensions 0.675 x 1.247 x 0.993 m.
Changes: wisps leave the rump at z 0.50 and pass the body at z 0.32-0.42; plugs at the lateral coil
centres (the dark tunnels are gone in the front and back renders and the clay row); brow spots moved up to
z 0.764 and made smaller (they sat on the upper lid).
cv.py sample, side view (reference / render): flank 0.40-0.48 box #9dcfdf / #a5cae5 (L within 0.02);
tail starry zone 0.72-0.78 x 0.40-0.50 #697ea1 / #697fa1 (same mean, same dark #3b4c7b / #43527a, spread
0.181 / 0.182); muzzle/forehead box 0.06-0.10 x 0.20-0.25 #a2d0e1 / #c1dce2 (render takes in more cream
muzzle: box falls on the cream edge, which sits ~0.01 higher than drawn).
Matches (keep): everything listed in Cycle 6; the back view overlap rose 0.77 -> 0.82 with the lower wisps.
Differs, cause, fix:
1. Front middle-left/right extra 16 %: wisps still pass beside the chest at z 0.35-0.42 (front reference
   is +-0.15 at z 0.4 and has its side tails at z <= 0.35). Fix: wisp control points (0.01, 0.12, 0.48) ->
   (0.03, 0.30, 0.38) -> (0.20, 0.33, 0.28) -> (0.305, 0.25, 0.26), tip curling up to z 0.31.
2. Front top-left/right missing 11-12 % (ears drawn ~10 % bigger in the front view than in the side and
   back views) and back top extra 15-19 % (ears drawn smaller there): the drawings disagree; ears kept
   between. Front w/h +6 % / back -4 % (lobe width): kept between the two drawings.
Next: build 8 with fix 1, then the --final bake.

## Cycle 8
CV: overlap front 0.82, side 0.79, back 0.81 (mean 0.81); w/h front 0.68 (+6 %), side 1.23 vs 1.24 (-1 %), back
0.68 vs 0.71 (-4 %). CHECK: all clean (floating none, no material none, flat colour none, non-manifold 0,
open 0), mirror 0.0123. 99,272 tris. Dimensions 0.675 x 1.247 x 0.993 m.
Change: wisps lowered (pass the body at z 0.28-0.38): front overlap 0.81 -> 0.82, front middle extra 16 %
-> 9-12 %.
Matches (keep): all of Cycles 6-7.
Remaining differences, all from the drawings disagreeing with each other (not fixable without breaking
another view): front ears drawn ~10 % bigger (front top missing 11-12 %, back top extra 15-19 %); lobe
spread (front +-0.31 vs back +-0.35: front w/h +6 %, back -4 %); the side drawing's tail-root gap vs the
back drawing's tails fanning from the rump (side centre extra 10 %: the hanging hook and wisp root). These
cap the overlap near 0.80-0.82 per view.
Next: the --final bake build (8 builds done).

## Report
Final build 9 (`--final`, baked). Last lines:
BUILT lumina_warden {"triangles": 99263, "dimensions_m": [0.675, 1.247, 0.993], "materials": ["M_lumina_warden"], "glb": "assets/models/blue_fox_evolution/lumina_warden.glb", "glb_bytes": 42772520}
BAKE lumina_warden: base_color, emission, normal, orm at 4096 px in 666.2 s (atlas smart_project, channels, normal, AO 32 samples; no Mix Shader note)
Checks against the definition of good:
- OUTLINE: FAIL on the number: overlap front 0.82, side 0.79, back 0.81 (target 0.90); w/h front +6 %, side -1 %,
  back -4 %. The three drawings disagree with each other (the user said so too: "the angles are different"):
  front ears drawn ~10 % bigger than in side/back (front top missing 11-12 %, back top extra 15-19 %), lobe
  spread +-0.31 in front vs +-0.35 in back (one width cannot hit both w/h), and the back view hides the tail arc
  that the side view needs. The model sits between them. KEY RATIOS from the side view hold: length:height 1.23
  (R1 1.24), withers 0.60, nose height 0.68, tail mass from Y 0.10 to 0.61.
- PARTS: PASS: every inventory row built (body clay with legs, paws with toes and creases, cheek/nape/elbow/
  belly locks, chest ruff; 2 ears with bowls, 5 cream tufts each; eyes, lid liners, nose with nostrils; collar
  ring, arcs, scroll curls, 8 tendrils with leaf buds, gem bezel, faceted gem; 9 shoulder locks per side in two
  layers; tail A with constellation, 2 lateral coiled tails with coil plugs, 2 wisps, 5 curl tips; 11 star domes).
  Copies differ by seeded variation (locks, tufts, tendrils, cheek spikes, stars, tails).
- DETAILS: PASS: flank haunch spiral, back strokes and thigh dots show in the side view (since the
  object-space normal fix of Cycle 5); forehead flame, brow spots, under-eye strokes, ear spirals and star
  specks, chest glow feathers, constellation 6+1 stars with lines on tail A, starry indigo zone, tail bands,
  toe creases, smile line.
- MATERIALS: PASS: cv sample side view: flank #9dcfdf ref / #a5cae5 render; starry zone #697ea1 / #697fa1;
  overall colour side #8297af / #8196ab, back #859cb3 / #899fb2, front L0.58 / 0.56. CHECK flat colour none.
  Back "top lighter by 0.12-0.15" = the ear backs filling the area the back drawing leaves to background
  (outline difference, not shading).
- FORM: PASS: clay rows show the sculpted body, joints, toe lobes, cheek and ruff locks, bowl ears, coiled tails.
- CLEAN: PASS: floating none, without material none, non-manifold 0, open 0; 99,263 tris within the 100,000
  budget; BUILT, BAKE and RENDERED without errors. Baked renders and turnaround match the cycle-8 renders
  (side mean #8196ab both).
Materials: procedural Principled surfaces with painted numpy masks (LW_marks / LW_decal projections, LW_ears
atlas, LW_tail_col / LW_tail_emi atlases), all mixed on the inputs of one Principled BSDF per surface: M_fur,
M_fur_cream, M_ear_outer, M_ear_inner, M_cream_tuft, M_eye, M_liner, M_nose, M_gem, M_silver, M_feather,
M_tail, M_star; baked into M_lumina_warden. No library material fitted the painted style (Analysis).
Skills: blender-image-to-3d (method), scenario-blender-sculpting (bx_sculpt Clay SDF body, nose, project),
scenario-blender-retopology (kit.quad_remesh 14,500), scenario-blender-texturing-shading (input mixing, AO
crevices, bump), scenario-blender-expert (5.2 names; turntable-normal trap).
Still differs and why: outline overlap below 0.90 for the drawing disagreements above; the front face is drawn
with the head tilted down (nose 0.08 under the eyes vs 0.04 in profile) - the model follows the side profile;
the ears' pale glow halo of the front drawing is not modelled (it is a 2D effect around the outline).

## Cycle 9
(Build 9 was the --final bake; reviewed by the critic in lumina_warden_review_1.md, 29 PASS / 39 FAIL.)
CV: overlap front 0.82, side 0.79, back 0.81; w/h front 0.679 vs 0.638 (+6 %), side 1.23 vs 1.24, back 0.68 vs 0.71 (-4 %).
Front extra bottom-left/right 0.13-0.14 and middle 0.10-0.13 (tail lobes spread too wide), missing top-left/right
0.11-0.12 (ears 13 % short in front). CHECK all clean, 99,263 tris.
Matches (keep): body proportions (R1, R3, R4, R6, R7, R10 within 5 %), flank markings, starry zone and side
constellation, collar silver and gem, chest cream and navy paws colours.
Differs, cause, fix (the review's measurements; answered one by one under ## Review 1):
- Side ground lobe is a knot: the lateral tail's path crossed tail A's lower coil -> re-route all tails (fix 1).
- Back view has no centre spiral: tail A ended in a knob -> tail A coils in a back-facing plane.
- Plume reads as a smooth tube with horns: no lock tips -> 8 tapering locks; bands 3 -> 6 per circumference.
- Grey speckled patches in the baked tails: bake rays inside the knotted tubes -> knot removed, UV strip padding.
- Ears 0.06 H too far back, tufts thin sticks, no split tip, weak spiral -> ear base forward, fan tufts, split tip.
- Hind legs vertical, paws without toes, hard leg colour step -> stifle/hock angles, toe-lobe paws, Z colour ramp.
- One cheek-to-cheek glow band, no smile crease, flat collar band, straight tendrils -> nobridge mask, crease_mouth,
  V collar arcs, S tendrils.
- Feathers stand off as a wing -> 7 broad locks lying on the shoulder.

## Review 1
(Builder 3; budget now 200,000 triangles. Applied in the generator before build 10, checked with helper previews.)
1. Tail knot / missing centre lobe: tail_paths() rewritten. Tail A keeps its side-view arc, then comes down the back and
   coils in a back-facing plane (LOBE_A centre (0.025, 0.50, 0.15), R0 0.108, 1.75 turns): the back view's centre spiral.
   Lateral tails run inside tail A's ribbon to its back edge, sweep forward under the starry zone and coil in tilted
   planes (LOBE_B +X centre (0.19, 0.30, 0.15), normal (0.90, 0.44, 0), R0 0.15, sv 0.72 = the side view's ground spiral;
   -X centre (-0.195, 0.34, 0.16), normal (-0.62, 0.78, 0), R0 0.10). No tube passes through another lobe; coil plugs at
   the three coil centres.
2. Plume locks: the 5 horn tips replaced by 8 tapering locks (LockTopL/TopR/Hook/Hang/Flick/Front/Right/Root). Wisps leave
   the rump sideways out to x +-0.35, tips turning DOWN (both the back and the front drawing show them pointing down).
   Bands 6 per circumference on tails A/B with uneven cream / light / dark widths and tints; star specks in the dark bands
   of the lateral tails and wisps; glow streaks near the roots (A 6, B 3, C 2).
3. Artefacts: the grey speckled patches were in the BAKED renders where tubes ran through each other (the knot): knot
   gone; 1.5-texel pad at each tail UV strip edge. Chest cream only on forward-facing normals, belly only underneath.
4. Ears/head: ear bases forward (Y -0.437), tips spread; ear tuft = one overlapping fan of 5 blades 40-52 mm wide pointing
   up and a little out in the inner lower bowl; split tip on the far ear; spiral stroke 9.5 mm with halo.
5. Legs/paws: stifle forward at z 0.30, hock back at z 0.165; fine-clay paws with 4 toe lobes and 3 crease grooves
   (build_paw, now called in build()); leg colour is a Z ramp z 0.20-0.43.
6. Face/collar: nobridge mask on the side face stroke; blue bridge wider (wb to 0.05); shorter under-eye strokes; cheeks
   cream to |x| 0.15; W smile crease pressed into the body (crease_mouth, now called); collar arcs meet in a V at the
   gem; S-curved tendrils with half-turn tips.
7. Shoulder feathers: 7 broad locks per side lying on the shoulder for their first third, tips lifting and curling.
8. Belly fringe 7 locks per side, elbow tufts, blue nape/cheek ruff locks; back constellation 6 stars + 4 lines. Body
   remesh 14,500 -> 26,000 quads.
BlendKit (logged in, Free plan, is_free:true): searched fox, stylized fox, kitsune, fox tail, crystal gem, filigree,
necklace. Downloaded and rendered "Stellar Fox (Rigged)" (royalty_free, 4,250 faces, a chibi purple blob) and "Stylized
fox character" (royalty_free, 6,338 faces, realistic orange fox with one tail and small ears, walking). Neither matches
this design's shape, colour or detail; the gems and filigree found are other shapes. None used.

## Cycle 10
CV: overlap front 0.80 (was 0.82), side 0.76 (0.79), back 0.78 (0.81); w/h front 0.72 vs 0.64 (+13 %), side 1.21 vs 1.24
(-3 %), back 0.71 vs 0.71 (+1 %). CHECK: 93 parts, floating none, no material none, flat colour none, non-manifold 0,
open 0, mirror 0.0159. 185,728 tris (budget 200,000). Dimensions 0.722 x 1.242 x 1.013 m.
Matches (keep): the knot is gone; the back view has three spiral lobes (left, centre, right) and its w/h now matches;
the side view's ground lobe is a spiral in the right place (Y 0.13-0.45); the side constellation, starry zone and plume
arc; paws with toe lobes; ear tufts read as cream fans in the bowl; flank markings; colours of body (side mean #8197ac
vs #8297af), lobes (back right lobe #8798a4 vs #8c96a7).
Differs (measured), cause, fix: see the Handoff's Comparison and Next step (one build per builder from now on).

## Handoff
State: builder 4 changed the generator (cycle 11 work) but did NOT build. The run was stopped for a commit before
the build. The last full build is still build 10 (185,728 tris, CHECK clean, overlap front 0.80 / side 0.76 / back
0.78; w/h front +13 %, side -3 %, back +1 %). Generator: /home/user/asset-pipeline/tools/blender/assetgen/packs/blue_fox_evolution/lumina_warden.py
(it passes `python3 -m py_compile`; the new tail fur code has never run in Blender). The first preview crashed in
`tail_lock` (a float offset); that is fixed. The second preview was stopped before it finished. The critic's
review 1 (lumina_warden_review_1.md) is answered under `## Review 1`.

### Understanding (what each thing is, and the approach it calls for)
- Lumina Warden: the phase-3 evolution of a stylised blue fox, drawn as painted anime game art (soft cel shading,
  dark navy ink outlines, painted fur strokes, glowing cyan markings). A slender young magical fox standing square
  on four legs, head up, facing -Y. It is clean and groomed: no wear or dirt. Its imperfections are asymmetry, ragged
  fur edges, uneven stars and uneven bands.
- Body: a furred animal body (skeleton, muscle, skin, fur). Built as signed-distance clay (sculpting skill), then
  quad-remeshed. Painted fur strokes and glow marks are in the shader. Cream zones are cut with kit.mark.
- Tail (user: "In all 3 the tails are wrong. It's fur in the tail."): five tails, and they are FUR. A tail is a thin
  core (bone, skin, dense dark underfur) under long guard hairs that grow from the root toward the tip. The hairs
  group into locks. The locks are shingled (each tip lies over the next lock's root), twist along the tail, part at
  the edges, taper to points with dark roots and light tips, and end in a brush. In this art style the cream / blue /
  indigo bands are separate locks. Build each tail as a dark core plus layered, twisted fur locks, never as one
  smooth shell. The three spiral masses on the ground are the tail ends curled up (tail curls): a soft core with fur
  locks following the spiral into the centre, like a cinnamon roll. The cream, mid-blue and indigo streams of locks
  make the painted spiral.
- Shoulder fur ("feather-like fur tufts"): magical fur locks, not feathers or planks. Soft, flame-shaped, iridescent
  (lavender, cyan, mint). The roots grow out of the body fur; the locks sweep up and back and the tips lift and curl.
  Built with the same fur-lock construction.
- Ears: a thin cartilage leaf with skin and fur on both sides. The bowl is indigo, star-speckled and glowing, with a
  cream fur fan at its base. Built as a lofted leaf with a bowl, plus ear-tuft locks.
- Eye: a ball set behind lids. The almond opening comes from the lid skin folds, with pointed corners and a fuller
  upper arc. The dark lash line sits on the lid margin. Built as a cut through the skin plus rolled lid folds, with
  the eyeball sunk behind them (cycle 11). The iris and highlights are painted on the eyeball.
- Collar: a silver filigree torque (drawn and cast silver wire): a neckband mostly buried in the ruff, antler
  branches from the gem setting up and out beside the face, tines with leaf tips, and C/S scrolls by the gem. A
  faceted glowing blue crystal sits in a rhombus setting. Built as swept wire paths snapped onto the clay.
- Scale: 1/4 sheet, about 1.00 m tall to the ear tips, 1.24 m long, 0.64-0.71 m wide.

### Key reference measurements (metres; Y = side-view distance from the nose tip - 0.62; x from the centre line)
- Ratios: length:height 1.24; ear length 0.27 H (side) / 0.31 H (front); withers 0.60; leg (chest bottom to ground) :
  withers 0.55; head length 0.30 H; nose z 0.68; tail mass Y 0.12-0.62 (0.40 of the length); front w/h 0.64, back 0.71.
- Side: nose tip Y -0.62 z 0.68; eye Y -0.50 z 0.72; crown z 0.84; ear tips z 1.00; back line z 0.60-0.62; chest bottom
  z 0.33; belly z 0.37-0.40; front paws Y -0.45..-0.32 / -0.35..-0.24; hind paws Y -0.07..0.03 / 0.08..0.18; stifle z 0.30,
  hock z 0.13. Tail: root Y 0.10 z 0.55; plume outer top z 0.70 at Y 0.28-0.45; outer back edge Y 0.60 at z 0.45; dark
  starry interior Y 0.23-0.47 z 0.30-0.58 holding the 6-star constellation; inner hook tip Y 0.20 z 0.36; ground curl Y
  0.09-0.53 z 0-0.30 with its spiral eye at Y 0.32 z 0.17; flick tip Y 0.56 z 0.05; hanging lock Y 0.55-0.58 z 0.10-0.30;
  lock tips at the top: Y 0.19 z 0.71 (pointing forward) and Y 0.53 z 0.73 (curling up); the gap (background) under the
  tail root at Y 0.10-0.20 z 0.28-0.50.
- Back (1403 px = 1 m): curls +X x 0.19 z 0.15 r 0.14 (to x 0.35); centre x 0.036 z 0.13 r 0.16 (x -0.135..0.19, the
  biggest and nearest); -X x -0.25 z 0.165 (to -0.34); thin tails leave at x +-0.12..0.15 z 0.38-0.40, out to x +-0.33
  z 0.33-0.35, tips turning DOWN to x +-0.35 z 0.27; constellation on the centre curl: stars (0.085, 0.217) (0.028,
  0.172) (0.015, 0.110) (0.006, 0.104) (-0.111, 0.199) + a short line up-left from the first.
- Front (1546 px = 1 m, drawn ~10 % bigger than side/back): ear tips x +-0.21 z 0.99; eyes x +-0.055 z 0.665; nose z
  0.595 (head drawn tilted down); cheek fur spikes to x +-0.16 at z 0.60; collar z 0.38-0.55 span +-0.17; gem 0.06 x 0.11
  centre z 0.41; tails: -X a low banded mass out to x -0.31 with a thin tail's tip hooking down at x -0.31 z 0.20-0.30;
  +X a mass out to x +0.31 that hooks UP to a curled tip at x 0.18 z 0.38. Nothing outside x +-0.18 above z 0.38.
- The three drawings disagree (user: "the angles are different"): ear size (front bigger), curl spread (front +-0.31,
  back +-0.35), and the back drawing hides the side drawing's tail arc. Build between them; never chase one view.
- Eye (front crop, eyes_front.png): a large almond, inner corner low and pointed toward the nose, tilt 15-18 deg,
  h:w about 0.45, width about 0.050; a thick navy upper lid line (3.5-4 mm) ending in a flick that rises about 8 mm;
  a thin lower line; a light-blue iris (#97bbd3, lighter #cfe4e9 below, #3a5a9a under the lid) about 70 % of the
  opening height and cut by the upper lid; a small dark pupil; a white highlight at the upper inner side.

### Part inventory (generator function -> part; names are what each thing is)
| part | count | construction | connection, overlap |
|---|---|---|---|
| body (torso, neck, head, muzzle, jaw, legs, cheek / nape / chest / elbow / belly fur locks) | 1 | `body_clay()` SDF clay (bx_sculpt), voxel 4.2 mm, `kit.quad_remesh(26000)`, `close_holes`, `crease_mouth` (W smile) | all fused; legs end at z 0.03 inside the paws |
| eye openings and lid folds | 2 | `cut_eye_opening()` inside `body_clay()`: almond cut 12 mm deep along the eye normal (lens from two circular arcs, `eye_rim()`), rolled upper (2.6 mm) and lower (1.4 mm) lid folds; stores the frame and rim points in `EYE[side]` | part of the body |
| eyeballs | 2 | `build_eye()`: flattened ball EYEBALL radii (0.034, 0.020, 0.025), front 1 mm in front of the skin level, faces (+-0.62, -0.78, 0.04); `eye_material(side)` (M_eye_L / M_eye_R) | behind the lid folds |
| lash lines | 2 x 2 | `build_lid_lines()`: eyelid_upper (on the upper rim, 3.5-4.2 mm wide, flick projected on the skin), eyelid_lower (thin) | on the lid margins |
| paws | 4 | `build_paw()` fine clay 1.6 mm, 4 toe lobes, 3 creases, remesh 1300 | overlap the leg ends |
| cream fur zones | - | `kit.mark(body, make_cream_field(body), m_cream)` | ragged edge |
| ears | 2 | `build_ear()` lofted leaf with a bowl (26 x 11 rings, Subsurf 1); `ear_image()` bowl glow | bases sunk in the skull |
| ear tufts | 2 x 5 (+ far ear's second tip) | `ear_tufts()` swept fur blades (still named EarTuft_*, EarTipSplit: rename to ear_tuft_* / ear_tip_second) | rooted in the bowl |
| nose | 1 | `build_nose()` fine clay with nostrils | on the muzzle tip |
| collar | neckband, 2x2 branches, 2x2 scrolls, 2x4 tines + leaf tips, gem setting | `collar_paths()` + `build_collar()` swept silver wire, objects collar_<kind>_<k> | rests on the chest ruff |
| gem | 1 | `build_gem()` faceted rhombus, flat shaded, emission | back apex on the ruff |
| shoulder fur | 2 x 6 locks | `build_shoulder_fur()` (cycle 11): Fur locks, flame outline, roots sunk, lift after half the length; `shoulder_fur_material()` reads lu/lv attributes | grows from the shoulders |
| tails (fur) | centre 1, side 2, thin 2 | `tail_paths()` centre lines -> `build_tails()`: `fur_core()` (dark underfur core, radii x0.8) + `fur_bundle()` (K locks around per layer, staggered layers along the length, twisted, tips lifting) per tail, one object each (tail_centre, tail_side_left/right, tail_thin_left/right) | roots in the rump; side and thin tails' roots run inside the centre tail |
| loose tail locks | 8 | `TAIL_LOCKS` -> `tail_lock()`: 2-3 strand clumps each, parting at the tip, in the tail_centre object | leave the outline |
| tail curls | 3 | `build_tail_curl()`: clay core (ellipsoid in the coil plane + the tail's entry, seated on the ground, remesh 1600) + spiral fur locks on both faces in 3 streams per turn (cream / mid blue / indigo), objects tail_curl_centre / _left / _right | the tails end on them |
| constellation stars | 7 side + 6 back | `star_dome()` raycast onto tail_centre (from +X) and tail_curl_centre (from behind) | half sunk |
Materials (one Principled each, variation mixed on the inputs): M_fur / M_fur_cream, M_ear_outer / M_ear_inner,
M_cream_tuft, M_shoulder_fur, M_silver, M_gem, M_eye_L / M_eye_R, M_nose, M_liner (lash lines: rename to M_lash_line),
M_constellation_star, M_tail_fur (`tail_fur_material()`: colour band ramp from the `band` attribute, darker root /
lighter tip from `lu`, fine strands along each lock from `lv` / `lu` noise in colour and bump, AO crevices between
locks, the starry zone (`starry` attribute) in indigo with Voronoi star specks, constellation lines from the
LW_tail_marks side / back projection (`pys`, `pzs`, `pxf`), glowing streaks on a few locks near the root from
`lglow`). The final build bakes everything to base colour, ORM, normal and emission at 4096.

### Comparison (latest full build = build 10; eye head tests from cycle 11; reference crops in the work folder)
Build 10 (lumina_warden_compare.png): the tails read as smooth banded shells and coiled hoses, not fur. That is the
user's complaint, and the cycle 11 fur rebuild below answers it but is not yet rendered. Silhouette: the front view
has extra 21-22 % middle left/right (the thin tails stood out beside the chest; they are rerouted in cycle 11); the
side view is missing top-left 12 % (ears drawn forward/larger) and has extra bottom-centre 18 % (the ground curl);
in the back view the curls looked like hoses with grooves, and the centre tail rose behind the head as a striped
pillar 0.17 wide. Face: the lower face was mostly cream (render #a8adad vs reference #98adbb); the muzzle top and
bridge should be light blue (changed in cycle 11). Ear bowl: no glowing cluster (render #576a91 vs #6e82aa); the
spiral was a small neon "3" (changed). Chest side: blue with cream islands; it should be clean cream back to Y
-0.33 (changed). Shoulder fur: a stiff stack of planks (rebuilt as fur locks). Collar: a thin wire cage (thickened).
Material texture strength is lower than the reference (0.07-0.11 vs 0.18-0.39).
Eye head test (cycle 11, work folder prev/hF_z.png and prev/hS_z.png, rendered BEFORE the last lash-line and iris
tweak): the eye now reads as an eyeball behind lids. The almond opening has its inner corner low, the iris is
large and light-blue with a dark rim, a pupil and two highlights, and the flick reads in both views. Still
different: the upper and lower lash lines were broken (they sank into the lid folds) and the iris sat fully inside
the opening rather than being cut by the upper lid. Both are changed (lines lifted 1.2 / 0.9 mm off the rim, iris
r 0.0145 centred 2.6 mm up) but not yet seen.

### Changed this cycle, not built or checked (check each in the first preview)
1. Eye (`eye_rim`, `eye_frame_at`, `cut_eye_opening`, `build_eye`, `build_lid_lines`, `eye_material(side)`): almond
   opening cut through the skin with rolled lid folds, the eyeball behind it, the lash lines on the rims (upper with
   a flick projected on the skin, lower thin). The eye faces (+-0.62, -0.78, 0.04).
2. Tails as fur (`Fur`, `lock_profile`, `fur_bundle`, `fur_core`, `tail_lock`, `build_tail_curl`,
   `tail_fur_material`, `tail_marks_image`, `fur_attributes`, `star_dome`, `build_tails`; the old swept tails,
   UV-strip images, coil plugs and the painted lobe bulbs are gone). Per tail (spec in `build_tails`): centre K 14 x
   4 layers, twist 0.55; side tails K 10 x 2; thin tails K 6 x 2. Each tail is cut 0.40-0.42 of a turn after it
   reaches its curl (`cut_into_curl`). The plume holds rv 0.155 to k_arc + 0.06 (no cap). The thin tails' roots run
   inside the centre tail and leave its back edge at z 0.34 (+X) / 0.37 (-X), out to x +-0.355, tips down, r 0.024.
   The loose locks are 1.5 x thicker with tips moved: top front (0.03, 0.165, 0.72), top back (0.03, 0.55, 0.745),
   hanging (0.07, 0.56, 0.10), front hook tip (0.19, 0.20, 0.37), meeting the inner hook in the side view.
3. Shoulder fur rebuilt as 6 fur locks per side (`build_shoulder_fur`, `shoulder_fur_material`).
4. Face cream (step 6): muzzle cream top line lowered 0.02 to 0.010 (zb 0.656 / 0.662 / 0.676 at Y -0.60 / -0.55 /
   -0.50); bib wc 0.06 at z 0.62 and 0.08 at 0.66; under-eye strokes end at |x| 0.080; cheek fur cones 15 % longer.
5. Chest and belly cream (step 8): chest normal term (n.y + 0.05) * 0.1, yb moved back about 0.03 at z 0.33-0.58; field
   noise 0.0012; the fringe's normal test removed.
6. Ear bowl (step 7): one big curl at t 0.66 of the ear length, r 0.04, stroke 3-12 mm, halo 0.6 / 12 mm; the second
   stroke removed; 200 star specks at 0.6 x radius.
7. Collar (step 10): neckband r 0.004 sunk (lift 0.2); branches, scrolls, tines and leaf tips r x1.3; tine tips at z
   0.50-0.585, x up to 0.19.
8. Names: objects eye_left/right, eyelid_upper/lower_*, tail_*, tail_curl_*, tail_lock_*, constellation_star_*,
   collar_<neckband|branch|scroll|tine|leaf_tip|gem_setting>_k, shoulder_fur_left/right; materials M_tail_fur,
   M_shoulder_fur, M_constellation_star, M_eye_L/R.
Unknowns: the triangle count. The estimate is about 215-225k, over the 200,000 budget. Ways to bring it down, in
order: curl locks M 6 -> 5 and 10 -> 8 rings; centre tail 4 -> 3 layers; `n_lock` 14 -> 11; body remesh 26000 ->
24000. The fur's look (lock width, lift, twist, colour order) is unseen.

### Next step (in this order; compare each part with its reference crop after every change)
1. The tail is fur: render it and tune it until it reads as fur. Run `cd /home/user/asset-pipeline/.scratch/assetgen/work/blue_fox_evolution/lumina_warden
   && timeout 1500 blender -b --factory-startup --python preview.py > prev/preview.log 2>&1` in the background. It
   prints `PREVIEW parts` (triangles per part) and `PREVIEW tris`, and renders prev/view_0/90/180.png and
   prev/headF/headS.png. Then run `PYTHONPATH=/home/user/asset-pipeline/.scratch/pydeps python3 pcompare.py`
   (writes prev/sheet.png). Fix any error first.
   Put prev/view_90.png next to tgt/tail_side.png, and prev/view_180.png next to tgt/tail_back.png, at the same
   scale. Check that the tails read as fur from every view: locks with pointed tips breaking the outline, partings
   showing the dark core, shingled layers, darker roots and lighter tips, cream / blue / indigo bands as separate
   locks twisting along the tail; the curls as fat cinnamon rolls of locks spiralling into a dark centre; the starry
   indigo zone on the plume's +X face with the constellation lines and stars.
   Tune `build_tails` spec (K, windows, twist, bands), `fur_bundle` (lift 0.28, width_k 1.5, th_frac 0.42, embed
   0.80) and `build_tail_curl` (J 3 streams, lock length 0.10-0.15, width 0.046, thickness 0.016). If locks float or
   show gaps, raise width_k or embed; if the outline is still smooth, raise lift. Bring the triangles under 200,000
   with the levers listed above.
2. Eye: check prev/headF.png and headS.png against eyes_front.png and eyes_side.png (crop and enlarge with zoom.py).
   You want a full navy outline with a thick upper line and flick, the iris cut by the upper lid, and no buried or
   dashed lash lines. Tune `build_lid_lines` offsets and radii, and `eye_material` iris centre / radius.
3. Check the shoulder fur against tgt/shoulder_side.png: 5-6 soft flame-shaped locks sweeping up and back, the
   highest at z 0.72, bases blending into the body. Then check the collar against tgt/collar_front.png: thick antler
   branches rising beside the face to z 0.55 at x +-0.17, C/S scrolls by the gem, the neckband hidden in the ruff.
4. The face cream, chest / belly cream and ear bowl (items 4-6 above): run `cv.py sample` on view 1 box 0.40 0.30
   0.60 0.45 (aim: mostly light blue) and box 0.12 0.05 0.25 0.20 (aim: a light cluster near #cef6fc at ~20 %), and
   the closeup on view 2 box 0 0 0.5 1.
5. Then the cycle's one build (`blender -b --factory-startup --python <generator> --`), `## Cycle 11` in the notes,
   cv.py compare and closeups of every changed part (tails: --view 2 --box 0.5 0.2 1 1, --view 3 --box 0 0.45 1 1;
   head: --view 1 --box 0.1 0 0.9 0.6; chest: --view 1 --box 0 0.4 1 1).
6. Remaining open items: texture strength (stronger painted strokes and ink accents in M_fur and the ears); the
   side view's chest / front legs about 0.015 behind the drawing; rename the remaining shape names (EarTuft_*,
   EarTipSplit, M_liner, M_cream_tuft -> M_ear_tuft). When the compare passes: the `--final` build and `pack.py done`.

### Do not undo
- The tails are fur (core + layered, twisted locks; curls as spiral locks on a core), never a smooth shell. Tail
  routing: no tail crosses another curl; the side and thin tails' roots run inside the centre tail; curl positions
  and planes (CURL_CENTRE faces the back; CURL_SIDE[+1] (0.90, 0.44, 0) stretched along the ground, sv 0.72;
  CURL_SIDE[-1] (-0.62, 0.78, 0)).
- The centre tail's side-view arc control points up to (0.44, 0.39), the starry zone ellipse (0.37, 0.42; 0.165 x
  0.185) and the side constellation (CONST_SIDE) with its lines.
- The eye as an eyeball behind lid folds round an almond opening (not a disc on the face); the eye facing 38 deg
  outward and level.
- The fur shader uses object-space normals (Texture Coordinate > Normal), because the kit turns the model on a
  turntable per view.
- Generated images get their colourspace BEFORE their pixels (`new_image`), else Cycles renders them black.
- Paws as separate fine clay; legs with stifle / hock angles; cream by kit.mark + close_holes; ear tuft fans;
  collar V at the gem.
- Mix material inputs into one Principled BSDF (never a Mix Shader: the bake averages it).

### Files
- Reference views: /home/user/asset-pipeline/production/qa/evidence/blue_fox_evolution/lumina_warden/lumina_warden_ref_view_1.png
  (front), _ref_view_2.png (side, main focus), _ref_view_3.png (back); source sheet
  /home/user/asset-pipeline/design/asset-packs/blue_fox_evolution/source.jpg (bottom row).
- Latest compare (build 10): /home/user/asset-pipeline/production/qa/evidence/blue_fox_evolution/lumina_warden/lumina_warden_compare.png;
  renders lumina_warden_view_1/2/3.png, clay lumina_warden_clay_1/2/3.png, CV numbers lumina_warden_cv.json, review
  lumina_warden_review_1.md, closeups lumina_warden_cv_closeup_1/2/3.png.
- Work folder /home/user/asset-pipeline/.scratch/assetgen/work/blue_fox_evolution/lumina_warden:
  reference target crops tgt/tail_side.png, tgt/tail_back.png, tgt/tail_side_starry.png, tgt/collar_front.png,
  tgt/shoulder_side.png; eye targets eyes_front.png, eyes_side.png (reference left); cycle 11 eye head tests
  prev/hF.png, prev/hS.png and their magnifications prev/hF_z.png, prev/hS_z.png; build-10 preview head renders
  prev/headF.png, prev/headS.png, prev/eyeF_zoom.png, prev/eyeS_zoom.png. Helpers: preview.py (full preview,
  triangles per part, not a build), headtest.py (head only: body clay without remesh, eyes, lash lines, nose; about
  50 s; writes prev/hF.png, prev/hS.png), zoom.py (crop and enlarge: `zoom.py src x0 y0 x1 y1 scale out`, needs
  PYTHONPATH=/home/user/asset-pipeline/.scratch/pydeps), pcompare.py (IoU and w/h per view from the preview),
  rows.py (outline extents per height vs the latest build), g_front.png / g_tailside.png / g_back.png (references
  with a 5 cm grid); src/tail_fur.py (the tail fur section as written this cycle, for reference).

### Standing rules
- One render cycle per builder: make the changes, build once, compare, then write the next `## Handoff` (replacing this
  one, standing alone) and end with `HANDOFF blue_fox_evolution lumina_warden`. `DONE` only after the `--final` build and
  `python3 tools/assetgen/pack.py done blue_fox_evolution lumina_warden`.
- What the user wants: the doubled budget in pack.json (200,000 triangles), perfect details, polygons spent where the
  detail is (tail locks and spiral curls, ear fans and tufts, hocks and toes, filigree collar, shoulder fur, face),
  close attention to every detail.
- The tail is fur.
- Think about what you see and build that (builder_guide.md section 1).
- Understand the thing you are making, conceptually (an eye, wood, a body, a tree root), and let that choose the
  approach (builder_guide.md section 1).
- Multitask: Blender builds and renders in the background while you keep working; independent steps together
  (blender_tools_guide.md section 6).
- Compare to the reference often, part by part, after every change, not only at the end of the cycle (builder_guide.md
  section 6).
- Use the installed Blender add-ons where they help, enabled in the generator: `kit.enable_addon("bl_ext.blender_org.<id>",
  with_preferences=True)` or `addon_utils.enable("bl_ext.blender_org.<id>", default_set=True)`. Ids: looptools
  (bl_ext.user_default.looptools), edit_mesh_tools, CurveFitting, bsurfaces_gpl_edition, bool_tool, print3d_toolbox,
  copy_attributes_menu, align_tools, extra_mesh_objects (bl_ext.user_default), zeeks_auto_uv_unwrap
  (bl_ext.user_default); UI only: EdgeFlow, auto_mirror, f2, snap_utilities_line, PolyQuilt. Strands and fur: the
  scenario-blender-hair skill (hair cards or mesh hair converted to MESH, the kit keeps only meshes) or tapered
  locks converted to mesh.
- Use BlendKit free models through plugins/blendkit/headless.py (logged in, Free plan): `headless.enable()`,
  `headless.search("asset_type:model is_free:true <words>")`, check `asset["license"]`, `headless.append(asset)`, and
  restyle anything appended until it matches the reference in shape, colour and detail. (Searched in cycle 10: fox,
  stylized fox, kitsune, fox tail, crystal gem, filigree, necklace: nothing matched; see Review 1.)
- The sheet (source.jpg bottom row) is the reference; its views disagree with each other (ear size, curl spread, the
  tail arc hidden in the back view): build between them.
- Read before working: /tmp/claude-0/-home-user-asset-pipeline/2396fed5-5999-5364-b5d1-d9749bebc958/scratchpad/builder_guide.md
  and /tmp/claude-0/-home-user-asset-pipeline/2396fed5-5999-5364-b5d1-d9749bebc958/scratchpad/blender_tools_guide.md.
- Compare the whole, details, exact shapes, texture and volume before every Handoff. COMPARISON: run cv.py compare, then
  put each reference view next to the same render and go over every part, large to small:
  - The whole: silhouette and outline from every view; proportions and size ratios; orientation and stance; placement
    and balance of the parts; how parts meet, connect and overlap.
  - Shapes: exact contours; curves and where curvature changes; straight against curved; tapering; thickness; where
    each part starts and ends; symmetry and asymmetry; edges (sharp, soft, bevelled, rounded).
  - Volume and depth: roundness or flatness; depth front to back; how forms turn away, overlap and hide one another;
    recesses and protrusions; layering; gaps and holes.
  - Surface detail: small shapes, ornaments, seams, joins, grooves, ridges, folds, bumps, cracks, dents, chips, holes.
  - Wear and imperfection: worn and rounded edges; scratches, scuffs, dirt, grime, stains; fading and discolouration;
    irregular and uneven areas; how repeated parts differ from each other.
  - Texture and material: pattern, its scale and direction, and how it follows the form; colour, value, saturation,
    gradients and transitions, light and dark patches; roughness and gloss, metal or not, transparency, glow.
  - Art style: how the reference is drawn or rendered (level of simplification, edge and outline treatment, shading,
    palette, painted or realistic) and whether the build matches it.
  - Reads as what it is: each part reads as the thing it is (fur as fur, an eye as an eye) from every view and up close.
  - Anything the reference shows that the build lacks, or the build adds that the reference lacks.
- Handoff format (builder_guide.md section 7): Understanding and part inventory, Comparison, Next step (name the tool or
  add-on), Do not undo, Files, Standing rules.
- Never project the reference image onto the model; never a flat-colour surface; change only the generator, the notes,
  the evidence folder and the work folder; no git; never ask "May I".
