> Superseded by [revision 07](../revision-07/README.md). The user identified wrong-hand appearance in the far-arm grips and incomplete outlines at the joins. The earlier visual checks recorded below did not catch those problems.

# Complete arm poses with fixed left/right hands

[Motion preview](../../../build/fromm-full-05/motion-preview.mp4) ·
[Pose and video review](../../../build/fromm-full-05/review.html)

Each pose is a continuous drawing from the shoulder through the sleeve, elbow,
cuff and wrist to the hand. There is no separate wrist join. The far arm renders
behind the torso; the near arm renders over it, with the shoulder seam as the
attachment. The front of the chair remains in front of the trousers and behind
the near arm.

Anatomical side is fixed for every pose:

| Character | Near/free arm | Far/cigarette arm |
| --- | --- | --- |
| Krusty | Right | Left |
| Fromm | Left | Right |

The four arm banks contain 20 drawings: four free-arm poses and six cigarette-arm
poses per character. Cigarette poses include palm-up with the cigarette pointing
down and an edge-on return. Every drawing was visually inspected for thumb/palm
orientation and three fingers plus one thumb (four digits total; some digits
are hidden by the grip or perspective). The two initial cigarette sheets were
superseded by corrected art. No pose is mirrored at runtime.

The loader checks each drawing's declared anatomical hand and digit count against
its bank and arm assignment. Tests also check that shoulder transforms preserve
orientation and arm length. These checks prevent configuration/transform errors;
they do not classify anatomy from pixels. New art still requires visual review.

Poses change at deliberate keys, with intermediate turn drawings and held
palm-up/sweep poses. There is no looping hand sway. Complete arms follow the
limited torso lean at their shoulders. Both characters retain the generated
pupil-free eye plates from revision 04, separate pupils and blinking; Krusty
looks toward the audience during his opening and closing address.

The 54.292-second preview includes six excerpts covering both free arms, both
cigarette arms, the title/music transition and the closing audience gaze. It uses
1440×1080 at 24 fps and the existing captions. Audio comes from the revision-02
mix. The full exported interview remains revision 02.

## Sources and registration

Selected sources are `host-free-arms.png`, `guest-free-arms.png`,
`host-cigarette-arms-handed.png` and `guest-cigarette-arms-handed.png` in
`assets/episodes/fromm-v5/`. The built-in image tool generated these from crops
of the existing characters. Exact prompts are saved beside this README.
`source.json` records source hashes, rejected alternatives and the visual audit.

The offline builder removes the measured green matte while retaining partial
black outline coverage. Extraction includes overscan beyond nominal sprite-grid
borders, then isolates the connected arm to retain fingertips and cigarette ends
without fragments from adjacent drawings. It registers each arm at its shoulder and uses one
uniform scale per bank, preserving the proportions across poses. The body core
is cut from the existing artwork; small suit underlays cover the removed
original hands. The existing clean stage supplies exposed chair/background.
A separate generated handless-stage edit was rejected by the image tool and
produced no asset; it is not part of this rig.

## Rebuild and verification

Use the [active revision-07 workflow](../revision-07/README.md). Its renderer and body-layer format replace this prototype. The revision-05 cels remain source assets for the selected open-palm and near-arm drawings.
