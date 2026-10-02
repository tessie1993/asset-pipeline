REFINE blue_fox_evolution blue_fox

Review round 1 of build 9 (final bake). Judged on blue_fox_compare.png, blue_fox_turnaround.png, the clay
renders, view renders vs ref_view crops, closeups (view 1 head/chest, view 2 head/tail/legs, view 3 whole)
and cv.py samples. Silhouette numbers below come from width/column profiles of the largest mask component
(so the back-view fox inside the view-2 box is excluded), as fractions of each object's own bbox W/H.
Boxes are fractions of the object box (x0 y0 x1 y1).

## Verdicts
| # | expectation | PASS / FAIL / UNKNOWN | judged on (view, box) | for a FAIL: the difference as a measurement |
|---|---|---|---|---|
| 1 | V1 silhouette follows reference | PASS | view 1, whole | overlap 0.917, w/h 0.490 vs 0.479 (+2.3 %); width profile within 4 % from 0.05H to 0.45H |
| 2 | V1 tail sides showing behind the shoulders | FAIL | view 1, 0 0.45 1 0.6 | width at 0.55H 0.62W vs 0.71W (-13 %); the render's tail bulges sit at 0.29-0.51H, the reference's at 0.46-0.58H; the reference's carry cream stripes, the render's are plain blue |
| 3 | V1 tail tip peeking above the head between the ears | FAIL | view 1, 0.3 0 0.7 0.15 | reference: cream-white tip ~0.20W wide x 0.08H tall; render: one cream spike ~0.05W wide |
| 4 | V1 form (clay) | FAIL | view 1 clay, 0 0 1 0.45 | ears are flat leaves with no visible bowl/cup; eyes are spheres bulging out of the face with a ring, no upper-lid ridge over them; cheeks are round where the reference's cheek ruff makes 2 pointed side tufts each side at mouth height |
| 5 | V1 eyes size and spacing | FAIL | view 1, 0.2 0.3 0.8 0.42 | eye width 0.107W vs 0.143W (-25 %); eye centre spacing 0.29W vs 0.35W (-17 %) |
| 6 | V1 iris / sclera colour | FAIL | view 1, 0.3 0.34 0.38 0.375 | render mean #515155 (dark #18171c) vs reference #7d7577; reference has 29 % cream sclera #c3b5b0 on the outer side, render 0 %; iris 0.17 darker |
| 7 | V1 upper lid line | FAIL | view 1, 0.2 0.3 0.8 0.42 | reference: thick dark upper lid with outer wing, thin lower line; render: uniform dark ring all round the eye, no wing |
| 8 | V1 nose | FAIL | view 1, 0.4 0.4 0.6 0.46 | nose width 0.062W vs 0.089W (-30 %) |
| 9 | V1 mouth | FAIL | view 1, 0.35 0.42 0.65 0.48 | render has a vertical philtrum line ~0.03H under the nose; the reference has none, only the soft smile curve with a slight central dip |
| 10 | V1 brow dots | PASS | view 1, 0.25 0.3 0.75 0.35 | - |
| 11 | V1 ear inner face markings | FAIL | view 1, 0 0 1 0.3 | reference: blue rim band on both edges of the tan face, ear tips dark blue; render: tan reaches the outer lower edge (no rim, left ear x<0.08), ear tips light blue; spiral stroke ~1/3 the reference's width, spiral radius ~0.6x, and its tail stroke runs straight down instead of sweeping along the ear edge |
| 12 | V1 ear fur tufts | FAIL | view 1, 0.05 0.12 0.4 0.3 | reference: 3 broad cream lobes lying in the ear; render: 4-5 thin pale spikes, half the lobe width |
| 13 | V1 collar braid | FAIL | view 1, 0.2 0.45 0.8 0.6 | reference shows ~9 twist lozenges with dark grooves per side between neck and pendant; render cord reads as a smooth brown tube, 0 visible lozenges; reference drapes in a V to the pendant, render in a U |
| 14 | V1 pendant gem | FAIL | view 1, 0.45 0.625 0.55 0.665 | reference colours #4d74c3 37 % / #1c38a5 34 % / highlight #9cafd7 29 %; render dominant #1f2b60, light only 9 %: gem ~0.2 darker, no lighter centre, highlight too small |
| 15 | V1 pendant bezel / bail | FAIL | view 1, 0.4 0.58 0.6 0.68 | bezel rim ~half the reference's width; bail ~0.02H tall vs ~0.035H |
| 16 | V1 chest cream shape and colour | PASS | view 1, 0.42 0.55 0.58 0.6 | render #c6b7a7 vs reference cream #d8c6b0 (within 0.05) |
| 17 | V1 clean | PASS | build.json | 0 open, 0 non-manifold, 0 floating, 0 without material |
| 18 | V2 silhouette | FAIL | view 2, 0 0 0.35 0.3 and 0.85 0.1 1 0.45 | far ear seen edge-on: 0.04W wide vs 0.08W (-50 %); at x 0.10 the render's top is at 0.25H, the reference's at 0.12H (far ear missing); tail thickness at 90 % of the length 0.31H vs 0.22H (+41 %, blunt round tip instead of a tapering point). Overlap 0.695 is capped by the back-view fox in the box (bottom-right missing 0.51) |
| 19 | V2 ear tufts | FAIL | view 2, 0.15 0.1 0.35 0.4 | 3 separate horn-like cones standing out of the ear front; the reference has one flat cream tuft with 3 soft points lying in the bowl |
| 20 | V2 eye shape | FAIL | view 2, 0.1 0.25 0.3 0.45 | eye width -25 %, round bead vs the reference's almond with a lid line; muzzle (nose tip to eye centre) 12 % shorter |
| 21 | V2 elbow / chest edge tufts | FAIL | view 2 clay, 0.15 0.5 0.4 0.75 | reference has a pointed tuft hanging behind the near front leg at the chest bottom; clay render has none (no chest-edge tufts in relief either) |
| 22 | V2 hind legs | FAIL | view 2, 0.45 0.6 0.75 1 | shin (hock to paw) slants ~30 deg forward vs ~16 deg; the reference's hind legs are near-straight columns, the render's an S with the hock pushed back |
| 23 | V2 front legs, paws, toe grooves | PASS | view 2, 0.1 0.6 0.4 1 | - |
| 24 | V2 tail pattern | FAIL | view 2, 0.65 0.15 0.85 0.3 | cream share 73 % vs 16 %: a solid cream cap over the upper distal half instead of flame tongues interleaved with blue; spiral radius ~1/3 the reference's (~0.02 vs ~0.06 of tail length); render cream #fffaf4 vs #d4dae0 (+0.1 brighter, pure white) |
| 25 | V2 tail tip tufts | FAIL | view 2, 0.85 0.05 1 0.35 | reference: 3 sharp pointed tufts (main tip up-back, top spike, lower hook) with grey shading in the folds; render: rounded blob with 2 small nubs |
| 26 | V2 tail volume (clay) | FAIL | view 2 clay, 0.55 0.1 1 0.6 | smooth ovoid, no fur clump relief along the top/lower edge where the reference's outline has jagged points |
| 27 | V2 lower leg darkening | FAIL | view 2, 0.23 0.8 0.3 0.9 | render #56718c vs #6585a3 (0.06 darker); view 1 0.33 0.85 0.45 0.95: #597698 vs #7091af (0.08 darker) |
| 28 | V2 belly tan | FAIL | view 2, 0.3 0.6 0.6 0.75 | reference tan band 30-50 px high (in a 380 px closeup) running into the inner thigh; render a 10-15 px strip (~-65 %) |
| 29 | V2 body blue colour | PASS | view 2, 0.35 0.5 0.45 0.6 | #9ac2d8 vs #96bed3 |
| 30 | V2 fur streaks | FAIL | view 2, 0.35 0.5 0.45 0.6 and 0.6 0.4 0.7 0.5 | render texture 0.044-0.053 vs 0.023-0.040: fine high-frequency grain (plush noise) instead of the reference's long soft painted strokes along the flow |
| 31 | V2 cheek ruff / muzzle cream | PASS | view 2, 0.05 0.3 0.35 0.5 | cream border and cheek spikes present |
| 32 | V2 clean | PASS | build.json | - |
| 33 | V3 silhouette: tail width (R10) | FAIL | view 3, 0 0.3 1 0.56 | tail width 0.88-0.90W vs 0.76-0.77W at 0.35-0.45H (+16 %); 0.72W vs 0.61W at 0.55H (+18 %) |
| 34 | V3 cheek tufts from behind | FAIL | view 3, 0 0.35 0.15 0.45 | reference shows pointed cheek tufts beyond the tail on both sides; render none (covered by the over-wide tail) |
| 35 | V3 tail top | FAIL | view 3 clay, 0.4 0.1 0.6 0.3 | two round bead-like knobs on the tail top centre; the reference shows crumpled white tip fur, no knobs |
| 36 | V3 tail blaze and curls | FAIL | view 3, 0.25 0.3 0.75 0.56 | blaze reaches 0.55H vs 0.46H (+20 % long), rectangular "beard" vs tongues; curls radius ~0.6x the reference's and placed on the sides instead of at the blaze's lower tips; two extra long vertical cream lines; render cream #a19a95 vs #c2b7b1 (0.1 darker) |
| 37 | V3 tail underside dark blue | PASS | view 3, 0.3 0.85 0.42 0.95 | #526d8d vs #4d6b90 |
| 38 | V3 ear back patch and spiral | FAIL | view 3, 0 0 0.3 0.25 | dark patch covers the top ~44 % of the ear vs ~60 %; light spiral radius ~0.6x, stroke ~half the width |
| 39 | V3 undertail patch | FAIL | view 3, 0.35 0.6 0.65 0.85 | one oval 0.22W x ~0.13H on the reference; render a flat-topped half-disc 0.21W x ~0.055H (-58 % height) plus a separate tan block lower between the legs |
| 40 | V3 legs and spacing | PASS | view 3, 0 0.7 1 1 | width profile 0.61/0.61 vs 0.62/0.61 at 0.65-0.75H |
| 41 | V3 clean | PASS | build.json | - |
| 42 | R1 ear length : height | PASS | view 1, 0 0 1 0.3 | ear silhouette overlaps; width at 0.05-0.15H 0.97-0.99 vs 0.99 |
| 43 | R2 back height | PASS | view 2 columns 0.35-0.45 | back top 0.46-0.50H vs 0.48-0.50H |
| 44 | R3 belly clearance | PASS | view 2 columns 0.35-0.45 | belly 0.76-0.79H vs 0.75-0.79H |
| 45 | R4 body length | PASS | view 2 columns 0.3-0.6 | - |
| 46 | R5 tail length | PASS | view 2 columns 0.6-1.0 | tail ends at the same column |
| 47 | R6 tail max thickness | FAIL | view 2 columns 0.7-0.8 | 0.39-0.41H vs 0.35-0.38H (+8 %), +41 % at 0.9 |
| 48 | R7 head length : height | FAIL | view 2, 0 0.2 0.35 0.5 | nose-to-eye 12 % shorter; overall head length within 4 % |
| 49 | R8 head width over cheeks | PASS | view 1 rows 0.35-0.45 | 0.81-0.82W vs 0.79-0.85W |
| 50 | R9 eye spacing | FAIL | view 1 | 0.29 vs 0.35 (-17 %) |
| 51 | R10 back tail width | FAIL | view 3 | 0.89 vs 0.76 (+16 %) (the analysis' 0.69 is also low against the image) |
| 52 | Part 1 head | PASS | views 1-2 | - |
| 53 | Part 3 ears (cupped bowl) | FAIL | turnaround az 90, clay 1 | ears are flat blades: edge-on at az 45-90, no bowl depth visible |
| 54 | Part 5 eyes set in sockets with lid ridge | FAIL | clay 1, clay 2 | eyeballs protrude as spheres |
| 55 | Part 7-8 neck, torso | PASS | clay 2 | - |
| 56 | Part 12 paws with toe grooves | PASS | clay 1, clay 2 | 2 grooves per paw |
| 57 | Part 15 collar geometry (2-strand twist) | PASS | clay 2 | twist relief exists in clay (fine pitch) |
| 58 | S3 cream fur colour | PASS | view 1 chest | - |
| 59 | S5 ear inner tan colour | PASS | view 1 | - |
| 60 | S9 nose colour | PASS | view 1 | - |
| 61 | S11 silver | PASS | view 1, 2 | metallic grey with bright rim |
| 62 | S10 leather twist shading | FAIL | view 1, 0.2 0.45 0.8 0.6 | see #13: lozenge highlight/groove contrast not visible |
| 63 | Imperfections: jagged cream edges, asymmetric curls | PASS | views 1-3 | jagged edges present (though edges read as torn-paper outlines rather than fur flames) |
| 64 | Clean overall | PASS | build.json | mirror error 0.0012; bake coverage 0.222 of the 4096 atlas (note only) |

## Fixes
1. Tail pattern (#24, #36) - most visible. The tail's top distal half is painted as one solid cream cap.
   Rebuild the side pattern as the reference's flame band: 3-4 cream tongues pointing back toward the base,
   blue between them, cream share in box 0.65 0.15 0.85 0.3 of view 2 ~15-20 %. Make the side spiral ~3x
   larger (radius ~0.015 m as the analysis itself says) with a thick stroke (~0.005 m). Keep pure cream-white
   only on the last ~25 % of the tail (tip), and set the cream to #d4d0cc, not #fffaf4. From behind: end the
   central blaze at 0.46H with tongues, put the two curls (r ~0.012 m, different sizes) at the blaze's lower
   ends, remove the two long vertical side lines.
2. Tail shape (#18, #25, #33, #35, R6, R10). Narrow the tail from behind by ~15 % (scale the tail
   ellipsoid chain X by 0.85) and taper the distal 20 % to a point: thickness at 90 % of the length to 0.22H
   (half-thickness ~0.012 m instead of ~0.02). Model 3 sharp tufts (cones bent up-back, top spike, lower hook,
   0.015-0.03 m) instead of the rounded nubs; remove the two bead knobs on the tail top. Add a few jagged
   fur-clump points along the tail outline (top and lower edge).
3. Ears (#11, #12, #18, #19, #38, part 3). Give the ear a real cup: bend the leaf so the edges curl forward
   (~4-6 mm bowl depth) so the far ear in view 2 reads 0.08W wide instead of an edge-on blade; the reference's
   far ear shows its back. Replace the 3 horn cones with one flat cream tuft with 3 soft lobes lying on the
   inner face (thickness ~2 mm, fused into the bowl). Paint a light blue rim band (~3 mm) along both edges of
   the inner face, a dark blue tip gradient (#4a6a9a), and a thick spiral (stroke ~3 mm, radius ~1.6x current)
   whose tail sweeps down along the ear edge. On the ear back extend the dark patch to ~60 % of the ear length
   and enlarge the light spiral to the same scale.
4. Eyes (#5-#7, #20, part 5). Enlarge the eyes 30 % and move them apart to a centre spacing of 0.35W in the
   front view (~+0.004 m each side); sink them into sockets under a modelled upper-lid ridge instead of
   protruding spheres. Repaint: iris lighter grey-brown #7d7577 graded darker at top, cream sclera visible on
   the outer side, thick dark upper lid line with an outer wing, thin lower line, no full ring.
5. Pendant and collar (#13-#15, S10). Gem base #3a5ec8 centre to #1c38a5 rim with a larger white highlight
   (the reference's light share is 29 %); bezel rim twice as wide; bail ~0.006 m tall. Make the braid read:
   halve the twist count (lozenges ~4 mm long) and raise the crest/groove contrast (crest #c08a64, groove
   #5a3b2a) so ~9 lozenges show per side in the front view; let the cord drop in a V to the pendant.
6. Nose and mouth (#8, #9). Nose 1.4x wider (~0.018 m); remove the vertical philtrum line, keep only the soft
   smile curve with a slight central dip.
7. Hind legs (#22). Straighten the shin: hock to paw ~16 deg instead of ~30, hock less pushed back.
8. Belly, undertail, lower legs (#27, #28, #39). Belly tan band ~3x taller, running into the inner thigh;
   undertail patch one oval ~0.04 m wide x 0.05 m tall from under the tail down between the thighs (no
   separate block); lower legs lighter by 0.06-0.08 (#6d90ad target, currently ~#56718c).
9. Tufts and cheek ruff (#4, #21, #34). Add the pointed elbow tuft behind the front legs and 2-3 chest-edge
   tufts in relief; make the cheek ruff stick out sideways with 2 pointed tufts per side so they show past the
   head in the front view and past the tail from behind (after fix 2).
10. Front view tail sides (#2, #3). After fix 2, check that the tail sides behind the shoulders sit at
   0.46-0.58H with cream stripes, and that the tail tip rises between the ears ~0.2W wide.
11. Fur grain (#30). Lengthen the fur streak noise along the flow (stretch ~5-10x along the flow axis,
   lower the bump amplitude ~50 %) so it reads as long painted strokes, not plush grain.
Note: the GLB is 39.6 MB and the bake atlas uses 22 % of the 4096 texture; packing the UVs tighter would give
the same detail at 2048.
