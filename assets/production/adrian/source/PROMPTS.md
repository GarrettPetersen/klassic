# Adrian Vale source prompts

Generated with the built-in ImageGen tool on 2026-09-10. These are draft references; the word “approved” in an extraction prompt described preserving that reference, not a recorded production approval. Actual review status lives in production.json. Portrait outputs are 1086×1448 despite requested canvas dimensions; registration uses their actual dimensions.

## Model

Use case: illustration-story. One original adult male character, Adrian Vale, for a 1960s narrative adventure game. Grayscale hand-drawn Simpsons-style TV cartoon: clean bold black contours, flat gray fills, three fingers plus one thumb on each hand. A tall lean adult with a SMALL proportionate long angular face, straight dark side-parted hair, thin pencil moustache, no glasses, no clown features. Dark open blazer over a mid-gray turtleneck, light-gray slim trousers, plain black shoes. One full-body neutral STANDING pose, three-quarter profile facing SCREEN RIGHT. Both complete arms relaxed by sides; both feet on the same ground, no props. Clearly adult proportions about six heads tall, long legs. Neutral closed mouth, pupils looking screen right. Exact 720x960 portrait composition: top of hair around y90, soles around y900, figure centered x350; generous clear padding all sides. Solid PURE GREEN RGB(0,255,0) background for compositing. No shadow, chair, scene, text, frames, labels or second figure. This single drawing is the canonical character model and standing pose; preserve all outlines.

## Initial poses

{
  "walk-contact": "Use case: precise-object-edit. This exact original character is the canonical reference. Draw ONE full-body walking contact pose traveling SCREEN RIGHT, same three-quarter view, same scale and clothing, face proportions, hairstyle/moustache, gray palette and outline thickness. Near/anatomical RIGHT leg is forward with heel on the floor, far LEFT leg trails with toe touching floor. Arms naturally counter-swing; four digits each. Modest adult stride, no extreme stretch. Keep head at same approximate height, soles around same floor baseline, same portrait canvas and center. Solid pure green background; no floor shadow, furniture, text or additional poses. A discrete hand-drawn walk cel, not a rotated or warped standing cutout.",
  "seated-context": "Use case: illustration-story. Use this exact original adult character model, Adrian Vale, without changing his small angular head, hair/moustache, dark blazer, gray turtleneck and light trousers. Draw ONE complete seated pose in context on a simple 1960s ARMLESS wooden side chair with a flat mid-gray upholstered cushion and straight wooden legs, facing three-quarter SCREEN RIGHT. Relaxed uncrossed legs, both feet on floor, knees aligned naturally and distinct thighs projecting from hips. Hands resting on thighs, four digits each. Real butt/pelvis seated on cushion, jacket drapes over hips. Long adult legs and small head proportions, six-head adult model. Full character and whole chair visible, no cropping. Grayscale Simpsons-style flat animation cels, black continuous outlines. Pure green background, no floor shadow, set, objects, text or second drawing. This is the canonical contextual seated proof; preserve a usable complete body silhouette for subsequent extraction."
}

## Related drawings

[
  [
    "seated",
    "Use case: precise-object-edit. Remove ONLY the chair from this approved seated context drawing, replacing chair pixels with pure green. Preserve the complete original seated man EXACTLY including position, proportions, pelvis/jacket shape, legs, head, hands, shoes, every outline and original canvas. Do not enlarge or recenter him. Reconstruct any tiny character contour hidden by the chair naturally. One complete seated character sprite on solid pure green; no furniture, shadow or scene.",
    "seated-context"
  ],
  [
    "chair",
    "Use case: precise-object-edit. Remove ONLY the man from this seated context drawing. Reconstruct the complete empty armless wooden chair with gray upholstered seat and backrest in exactly its original position, perspective and scale. Keep the full original canvas and fill all background with pure green. Chair must have a complete seat cushion and back where man was, four coherent legs and continuous black outlines. No person, ghost limbs, shadows, labels or other objects. Do not enlarge or recenter the chair.",
    "seated-context"
  ],
  [
    "walk-opposite",
    "Use case: precise-object-edit. One alternate walking CONTACT cel of this exact character, same screen-right facing and same head/torso proportions and clothing. Swap which leg leads anatomically: far LEFT leg now reaches forward, near RIGHT leg trails. Swap arm counter-swing naturally; maintain correct left/right hands, four digits each. Do not mirror the sprite: head still faces screen right, near arm stays anatomically right. Modest stride same magnitude as source, feet same implied floor, source canvas/scale retained. Pure green background, no shadows or extra images.",
    "walk-contact"
  ]
]

## Transitions and gesture

[
  [
    "walk-pass",
    "Use case: precise-object-edit. One WALK PASSING pose of this same original character traveling screen RIGHT. Near RIGHT leg is planted vertically directly under the hip, far LEFT leg bends at the knee with heel lifted and passes the planted leg, moving forward. Legs must NOT be in a wide contact stride. Both arms pass close to body mid-swing, same head/torso height and proportions, same clothes and gray palette, four fingers, complete visible outlines, exactly same canvas. One cel on pure green, no ground shadow, scene or labels.",
    "standing"
  ],
  [
    "sit-transition",
    "Use case: precise-object-edit. Draw this exact character midway between standing and sitting: body halfway lowered, hips moving backward screen-left toward a chair, both knees bent, torso leans forward slightly screen-right, both hands reaching to rest on thighs. This is a single crouching transition pose, NOT fully seated and NOT standing. Feet flat on same implied floor, adult long-leg proportions, same face/hair/moustache and clothes. Same three-quarter facing screen right, exact same canvas and sprite scale. Do NOT include the chair or other objects. Solid pure green background, clear complete silhouette, black outlines. Preserve anatomical hands with exactly four digits.",
    "seated"
  ],
  [
    "offer",
    "Use case: precise-object-edit. Change ONLY the anatomical RIGHT arm (near arm on screen-left) in this complete seated character pose. Raise it into a modest explanatory palm-up gesture toward screen right, with four digits: three fingers and one thumb, correct right-hand thumb orientation. Keep far hand resting on far thigh. Preserve ALL body, legs, head, closed mouth, shoulders, seat height, garment tone, source canvas, scale and placement exactly. A distinct whole-body seated gesture cel on pure green, no chair or new objects.",
    "seated"
  ]
]

## Room

Use case: illustration-story. Empty 1960s television-studio waiting room, grayscale Simpsons-style hand-drawn cartoon background, clean black contours and flat gray fills. Wide 4:3 composition, eye-level stage view. Quiet light-gray walls, horizontal wooden dado molding, dark entrance doorway at far left, dark exit doorway at far right, small rectangular frosted high window centered, simple ceiling light. The lower 42 percent is an unobstructed gray linoleum floor with subtle perspective seams. Completely empty center for character animation and a separately composited chair. NO chairs or other furniture, NO people, NO objects on floor, NO text or lettering, no film damage or grain. Clear uncluttered readable stage, different from a talk-show set. Exact 1448x1086 composition.

## Raised-hand correction

Correct only the raised hand: exactly four digits total (one thumb and three fingers), exactly two internal finger separation lines. Preserve all other artwork. The corrected source is offer.png.

## Extraction

Green matte removed using background_green=175 to account for the generated backgrounds' non-pure green. Whole drawings are uniformly resized and translated, with no deformations or painted repairs. Individual RGBA drawings in ../drawings are the editable source after registration. Scene chair is keyed independently and rendered behind the actor. The seated-context drawing is retained as model.png.


## 2026-09-11 seated reference revision

The seated silhouette is now fixed. New ImageGen edits/extractions produced an
armless seated body and separate near-arm rest, low anticipation and offering
cels. The anatomical left/far arm remains at rest. All requests specified the
same 1086×1448 canvas, grayscale palette, complete ink contours, and one thumb
plus three fingers. No generated take is approved merely because its prompt
requested those properties.

Final generation outputs (from the Codex generated-images directory):

| Source | Output |
| --- | --- |
| seated-base.png | exec-1dd437fc-d89b-4040-8817-95f9dcfd7cac.png |
| near-rest.png | exec-086b12eb-edeb-473d-98d3-b32db94c1634.png |
| near-low.png | exec-5521aca3-6841-4779-ba11-13d11270b3c4.png |
| near-offer.png | exec-2023aada-4381-4983-b7d6-f155de02a802.png |
| far-rest.png | exec-cf0fc039-fc69-4033-87a7-67fa5dbd9fb2.png |
| front.png | exec-801d5533-102c-4478-aa46-8a9252e52339.png |
| short-step.png | exec-fdefdf57-b8cb-4872-80e9-5e08a7c91a84.png |

Body cleanup prompt: preserve head, neck, lapels, shirt, pelvis, legs and shoes;
remove the leftover internal sleeve seam curving from (323,393) toward (375,650),
filling it with matching jacket charcoal. Preserve the outer silhouette.

Low-arm cleanup prompt: the first extraction retained a lapel fragment. Remove
that fragment, using the sleeve's curved seam as its closed outer shoulder edge.
Match the offering arm's rounded shoulder topology while preserving the low hand
and elbow coordinates. This correction was inspected in the actual composite.

Far-arm extraction prompt: retain shoulder, elbow, cuff and hand from the seated
reference, with the hand resting on the far thigh. The result shifted, so its
whole drawing was registered by translation before inspection. It is split into
two complementary depth masks, not separately generated wrist/hand pieces.

Short-step prompt requested a narrower right-facing walking contact with the same
identity and adult proportions. Front requested a separately drawn front view,
not a mirror. These extend the navigation study; their motion is still draft.

RGBA preparation uses `remove_green_matte` with background_green=175 to remove
faint green remnants, then uniform Lanczos scaling: seated sources to 608×811
at [2,221], standing/step sources to 673×898. Front registration is [27,92].
The far arm is registered at [-8,148]. Its rear mask keeps rows below round(515×.56)
and above round(850×.56); the lower mask keeps rows from round(850×.56) onward.
The upper discarded overlap would otherwise protrude above the shoulder; the
body fully covers that boundary. Both masks retain the original source pixels,
share one anchor binding and meet at the same exact row. No contour is repainted.

The canonical `drawings/*.png` and `character.json` remain the source used by
builds. These notes document preparation; normal builds never rerun ImageGen.
