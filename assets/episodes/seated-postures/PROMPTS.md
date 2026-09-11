# Seated posture artwork

Generated with the built-in imagegen tool on 2026-09-10. The runtime consumes
the `*-uncross.png`, `*-torsos-wide.png`, `*-upright.png` and `*-qualify.png`
atlases registered in `registration.json`. Source hashes are recorded in the
exported character manifests. Near-arm turn/up drawings correct the old
handedness error; other whole-arm drawings come from the v7 banks. Every posture
reuses these registered arm drawings with rigid placement only.

The `*-study-reference.png` images were assembled from the existing neutral
character package. The combined `*-lean.png` studies were intermediate references
for the torso extraction; their new hands were discarded. Fromm's attempted
transparent study contained a painted checkerboard, so a subsequent edit supplied
a solid green matte. `fromm-lean-green.png` records that input. The final green
background is removed deterministically during export.

## Lower-body sheets

Reference: the corresponding `krusty-study-reference.png` or
`fromm-study-reference.png`. The actual prompts below differ only by facing.

### krusty-uncross.png

Use case: illustration-story. Create a production animation sprite sheet for the seated man's LOWER BODY ONLY, matching the supplied grayscale Simpsons-style reference. One wide image, three equal cells in a single row, generous empty padding, no labels. Transparent background. Draw only black suit trousers from waist/hips through both shoes, NO torso, head, arms, chair, table, cup, floor, or background. Same view as reference: seated facing screen-right, near leg originally crossed over other. Three successive hand-drawn uncrossing poses: cell 1 lifts the crossed knee slightly and begins freeing its ankle; cell 2 separates both knees, formerly crossed foot suspended just above floor; cell 3 settled with BOTH FEET PLANTED on same floor, thighs foreshortened toward screen-right. Each cell same scale, pelvis same position and shoes share floor baseline. Keep full hip volume, same adult proportions and black suit fabric tone, black clean continuous outlines, two legs/two shoes only. Preserve line weight and cartoon style. This is an animation asset, not a scene. Do not reproduce table/cup fragments from reference.

### fromm-uncross.png

Use case: illustration-story. Create a production animation sprite sheet for the seated man's LOWER BODY ONLY, matching the supplied grayscale Simpsons-style reference. One wide image, three equal cells in a single row, generous empty padding, no labels. Transparent background. Draw only black suit trousers from waist/hips through both shoes, NO torso, head, arms, chair, table, cup, floor, or background. Same view as reference: seated facing screen-left, near leg originally crossed over other. Three successive hand-drawn uncrossing poses: cell 1 lifts the crossed knee slightly and begins freeing its ankle; cell 2 separates both knees, formerly crossed foot suspended just above floor; cell 3 settled with BOTH FEET PLANTED on same floor, thighs foreshortened toward screen-left. Each cell same scale, pelvis same position and shoes share floor baseline. Keep full hip volume, same adult proportions and black suit fabric tone, black clean continuous outlines, two legs/two shoes only. Preserve line weight and cartoon style. This is an animation asset, not a scene. Do not reproduce table/cup fragments from reference.

## Final torso extraction prompts

### krusty-torsos.png (reference: krusty-lean.png)

Use case: precise-object-edit. These two leaning torso poses will use separately layered EXISTING arms and legs. Edit BOTH sprites: REMOVE both complete arms, hands, cuffs, cigarettes, and all leg/knee shapes. Keep only the HEADLESS ARMLESS black-suit TORSO with white collar, neck stub, lapels, shirt and tie down through waist/jacket hem. Fill missing torso behind removed arms naturally as closed black suit fabric, black shoulder seam contours at each shoulder. The jacket must be whole down to its waist/hem, with no crossed knee remaining. Preserve EXACT neck and shoulder positions, lean angles, scale and placement of the two source poses; don't center or enlarge. Transparent background. No head, arms, hands, legs, chair, text, checkerboard. Each shoulder should end at its armhole seam, ready to place the original full-arm sprite on it.

### fromm-torsos.png (reference: fromm-lean-green.png)

Use case: precise-object-edit. These two leaning torso poses will use separately layered EXISTING arms and legs. Edit BOTH sprites: REMOVE both complete arms, hands, cuffs, cigarettes, and all leg/knee shapes. Keep only the HEADLESS ARMLESS black-suit TORSO with white collar, neck stub, lapels, shirt and tie down through waist/jacket hem. Fill missing torso behind removed arms and crossed knee naturally as closed black suit fabric, black shoulder seam contours at each shoulder. The jacket must be whole down to its waist/hem, with NO crossed knee remaining. Preserve EXACT neck and shoulder positions, lean angles, scale and placement of the two source poses; don't center or enlarge. Keep perfectly solid chroma green RGB(0,255,0) background. No head, arms, hands, legs, chair, text, checkerboard. Each shoulder should end at its armhole seam, ready to place the original full-arm sprite on it.

## Registration and composition

`registration.json` stores atlas cell scale/position, shoulder attachments,
rigid arm angles and head cutout/attachment coordinates. Each arm remains its
original whole sleeve/cuff/hand drawing with a rigid transform. Face overlays
receive the same translation as the head. The four upright/reclined and
crossed/uncrossed combinations are composed from these drawings rather than
requesting a fresh full-body image for every combination.

## Collar, jacket and handedness revision

The first reclined collar holes shrank to roughly 50 pixels after registration,
far narrower than the original head bases. The wide atlases retain head scale
and supply openings approximately 120–145 pixels wide at display scale.
Collar-front polygons are source-cel coordinates, exported above the neck.

Final asset lineage (built-in imagegen output IDs):

- `krusty-torsos-wide.png`: `exec-92da930d-b55c-4e52-a147-e69b1e6ebe0a.png`.
  Edit of `krusty-torsos.png`, intermediate `exec-bdc4f256-d0a8-4ed6-946e-89b2dca1cc54.png`.
  Prompt: preserve the two armless torso poses and shoulder seams, widen both
  neck openings and collars to 2.5 times their width, retain neck centers,
  complete the untucked jacket hem and remove internal trouser details.
  Follow-up: preserve both sprites exactly and replace the painted checkerboard
  with uniform pure green RGB 0,255,0.
- `fromm-torsos-wide.png`: `exec-3bad2a93-a76e-4b4e-9468-edd87652003f.png`.
  Edit of `fromm-torsos.png`. Prompt: preserve two-cell layout and armless
  shoulders, widen both openings/collars to 2.6 times their width, broad cartoon
  necks, complete untucked jacket hem, no heads/arms/legs, pure green background.
- `krusty-upright.png`: `exec-40591d04-e6c9-47c2-afbc-99c6250a0665.png`.
  Initial `exec-4d524739-30ef-4bfe-9fce-3193828a5085.png` edited the exported
  `posture-upright.png`: remove head/neck and crossed legs; reconstruct the
  complete hidden armless jacket, preserving collar/lapels/shoulders, facing
  right, pure green background. Follow-up shortened the hem to about source
  y1000, below the top button, preserving upper artwork coordinates and canvas.
- `fromm-upright.png`: `exec-69f48b5a-90b1-4f49-81d2-3b909e91f4b7.png`.
  Initial `exec-6ba6b4cb-20e7-4313-bcb4-189227226745.png` used the analogous
  exported upright drawing, facing left. Follow-up shortened the jacket to a
  seated hip-length hem around source y1050, preserving the upper registration.
- `krusty-qualify.png`: `exec-6ed92e22-6a79-4dc1-be06-9e30a17b71c0.png`.
  References: exported near-arm free-turn/free-up drawings. Prompt: two cells,
  half-turn then palm-up, anatomical RIGHT arm pointing screen right; thumb
  projects toward viewer on LOWER screen edge, three long fingers plus one
  shorter thumb, four digits total, preserve whole sleeve/cuff/shoulder, never
  mirror the whole arm, continuous ink, transparent background.
- `fromm-qualify.png`: `exec-5ecd4c90-8f0f-4be7-8a7d-f1e5dfafee68.png`.
  Analogous exported arm references. Prompt: anatomical LEFT arm pointing screen
  left, thumb on LOWER screen edge toward viewer, three long fingers plus one
  thumb, four digits, preserve whole sleeve/cuff/shoulder, no mirroring, green
  background. The two poses are deliberately similar, with a changed thumb arc.

Export operations are deterministic matte removal, cropping, uniform sizing,
rigid registration and authored depth masks. Waist and forward-thigh passes
come from the same leg cel. No limb is stretched or independently flipped.
The old film face/foreground masks are tightened to exclude captured room
pixels; no closed mouth is baked into body or head artwork.

## Foreground thigh and collar-boundary revision

The final foreground leg atlas is `*-thighs-forward.png`. Its rear hip mass
is removed so the legs emerge at seat height instead of covering the abdomen.
`seated-pelves.png` supplies the complete rear seat/waist pass; the foreground
art has a continuous upper ink contour, including the transition poses.
The runtime source of truth remains `registration.json`.

Final imagegen lineage:

- `krusty-thighs-forward.png`: `exec-ebb1ddc4-5596-4095-a168-9661da0a287d.png`.
- `fromm-thighs-forward.png`: `exec-3025a3aa-d455-4e96-a561-7e0e2f8843b3.png`.

References are the saved `*-thigh-guide.png` atlas cutouts of the original legs.
The guides specify the foreground silhouette; their polygon edges are reference
cuts, not the shipped artwork. Final prompt: preserve three 724-pixel cells,
canvas 2172×724, scale, foot/knee locations and calf/shoe details; trace the
exposed upper boundaries with continuous smooth black cartoon ink approximately
4 source pixels wide, round small polygon corners and remove narrow clipping
spikes. Do not add hips, buttocks, waistband or rear seat mass. The low rear
edge begins near seat level and rises forward to the knee. Preserve the green
space above it and the recess between thigh tops. Pure green background.

Fromm's current torso inputs are `fromm-upright-shirt.png`
(`exec-7be906da-263c-4e43-9c86-c2eba9bd8882.png`) and
`fromm-torsos-shirt.png` (`exec-9b9755b2-5062-4b78-8a3c-552a33a1a6f3.png`).
They edit the prior upright/wide torso references while retaining canvas,
neck/collar/shoulder registration and outer suit contours. Prompts requested a
shorter tie and a wider, connected white shirt panel below it, opening the
lower lapel toward screen left so shirt shows between separately layered thighs.
No detached white patches, new limbs or changed outer torso proportions.

Collar and neck cleanup uses authored source-coordinate cutouts. Preserve all
of the front collar's black rim and its antialiasing. Remove placeholder neck
stubs above that rim. The front collar passes over the neck-base drawing but
under the jaw/mouth overlay, so it cannot cut a notch into an animated chin.
Fromm's old underlying neck is constrained to the replacement portrait's alpha
silhouette, preventing an old ear/neck fragment from protruding on a recline.

### Complete seated pelvis and fitted neck connector

`seated-pelves.png` comes from `exec-a2c6bbd5-0e45-4569-8951-bbbcfcb57c16.png`.
References: both original uncrossing sheets. Prompt: two equal cells of full
seated waist/hips/buttocks, left facing right and right facing left; deep rounded
posterior with a slightly flattened cushion contact, contiguous mass connecting
both forward thighs, dark charcoal matching the suit, continuous black outline,
pure green background, no upper body/chair/feet. The generator included short
thigh roots, which remain behind the separately outlined foreground thighs.
One all-green rightmost column was trimmed from the 2171-pixel output to pack
two equal 1085-pixel cells. A whole registered pelvis persists during leg motion;
it is not a cropped waist band and does not need duplicate per-leg-pose exports.

`fromm-neck-repair.png` comes from `exec-90011a69-81c1-41f5-a007-e0ae6e652381.png`.
Reference: `fromm-neck-reference.png`, a 300×210 native crop of the assembled
reclined character. Prompt: fill only the triangular background gap between
back of jaw/ear and white collar with a short neck matching face gray; outside
neck contour begins beneath earlobe and slopes to back collar; chin overlaps
neck front, collar overlaps neck base; remove duplicate inner neck line; retain
all other face/ear/collar/suit positions, shapes and shades. Export normalizes
the crop size and extracts only the neck polygon in registration. That small
connector follows the existing head translation through both lean drawings,
and overlaps the obsolete jaw-edge fragment without replacing the facial cels.

Final palette registration scales the rear pelvis gray by 0.65 to match the
existing trousers. The neck's skin range maps to the portrait's flat gray 205,
retaining dark ink and white collar pixels, so the patch has no diagonal color
seam against the face. The visual review script includes the intermediate lean
and all nine mouth keys, as well as the four settled postures.

## Complete body poses — 2026-09-10

The active v2 registration replaces stitched torso/pelvis/thigh artwork with
four complete torso-and-leg drawings per character. Heads, facial cels and
whole arms remain independent. Four additional complete drawings provide the
uncross and lean transitions. All new raster art used the built-in imagegen tool.

- `krusty-bodies.png`: `exec-351ac68d-0e12-4a0d-8284-5854611ea684.png`
- `fromm-bodies.png`: `exec-cfb43ae5-a54a-4014-8c69-3a96178e8cc2.png`
- `krusty-body-transitions.png`: `exec-abfc6f2f-a0a3-48c3-a8ce-e784b6698ca6.png`
- `fromm-body-transitions.png`: `exec-3604ebd2-5311-4526-8f7b-711eb628d143.png`
- `fromm-body-neck.png`: `exec-c99fa391-f041-4dfb-abf5-cac1b8c5c179.png`

Body prompt: redraw the assembled registration guide as four coherent,
headless, armless suit bodies, collar to shoes, in a 2×2 grid: upright/crossed,
upright/spread, reclined/crossed, reclined/spread. Preserve neck/shoulder anchors,
seat height, scale and shoes; remove all furniture fragments and cutout artifacts.
Draw jacket, low hips, full seated butt and forward thighs together with a
continuous jacket hem, adult anatomy, dark charcoal around RGB32, white shirt,
black tie and clean Simpsons-style black outlines on flat #00ff00. Maintain
Krusty's right-facing and Fromm's left-facing three-quarter views. No head,
neck stub, arms, hands, furniture, text or detached fragments. Fully draw shoes
that were occluded by the table. Fromm's shirt stays above his crotch.

Transition prompt: use the corresponding finished body atlas for exact design
and proportions. Four complete intermediate bodies: upright beginning uncross,
reclined beginning uncross, halfway lean with crossed legs, halfway lean with
spread legs. Preserve planted feet and hip contact; lift the crossed foot
before uncrossing. Retain the same grayscale linework and green background.

Neck prompt: preserve a two-panel crop of Fromm's upright/reclined collar joins;
fill the background wedges between ear/neck and collar with matching flat skin.
Draw one outer neck contour to the back collar point and erase the obsolete
internal jaw edge. Preserve face, ear, collar, tie and shoulder positions.
Export keeps only the registered skin/outline region, with the existing back
collar ink above it. Skin maps to the portrait gray of 205.

Atlas export normalizes resolution to authored 720×760 cells. An overscan and
connected-component matte retain a shoe extending across a nominal cell boundary
without collecting another cel's pixels. Foreground legs and collar rims are
masked copies of the same body drawing, never separate anatomy. This lets chair
foregrounds cover the butt while legs remain in front. The early separate-leg
experiment from this pass was discarded and is not used by registration v2.
