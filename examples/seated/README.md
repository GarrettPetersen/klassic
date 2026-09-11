# Seated conversation MVP

A playable, drawing-based conversation using the existing interview test cast.
Character poses and action playback are separate from the story and the scene.
The game can request the same action from either character without knowing
which drawing files, proportions or anatomical hands that character uses.

## Run

From the repository root, with the project's Python/Pillow and FFmpeg available:

```sh
npm run build:mvp
npm run build:production
npm test
npm run serve:mvp
```

Open [the conversation](http://127.0.0.1:8765/web/player/).
The static server is bound to localhost. No synthesis or image service runs
while playing. The build reuses the prepared full-interview inputs in ignored
`build/fromm-full-02/` and the selected artwork in `assets/episodes/fromm-v7/`.

Choose an opening question, listen to the response and select the next line.
The work branch offers a more probing follow-up; the society branch offers a
change of topic. Pause freezes animation and audio together. Skip advances the
line, and Start over cancels the line and returns to the initial choices.

The **Perform a gesture** buttons are always visible below the stage. Select
either performer, then use Offer, Concede, Qualify, the posture controls or
camera gaze while dialogue continues. A manual action takes priority over the
pending automatic cue for that speaker's current line. The posture buttons
change to their reverse actions as appropriate.

The Rehearsal room interrupts the conversation and lets you select either
performer, play each gesture, change gaze, pause, and step one frame at a time.
Leaving rehearsal starts a fresh conversation. Speech interruption closes the
mouth immediately; a short gesture completes its existing recovery to neutral.

Use **Uncross legs** and **Lean back** independently for either performer.
The reverse controls are **Cross legs** and **Sit upright**. Both changes can
coexist, and Offer/Concede/Qualify recover to the current settled posture.
**Play speech sample** demonstrates lip sync in that posture. Frame stepping
pauses sample audio as well as the animation clock.

## Files

- `cast.json`: the only mapping between prototype roles, source speakers and
  existing film coordinates. This knowledge stays in the offline adapter.
- `story.json`: choices, state conditions, source takes and semantic gestures.
- `build.py`: exports independent character packages, furniture layers, audio,
  mouth-frame schedules and a hashed project manifest.
- `postures.py`: registers complete torso-and-leg drawings with separate heads
  and whole arms, plus identical-pixel masks for chair overlap.
- `../../assets/episodes/seated-postures/registration.json`: atlas placement,
  head masks, shoulder attachments and rigid arm angles for each drawn pose.
- `../../web/player/runtime.js`: generic clip sampling, actor state and dialogue.
- `../../web/player/renderer.js`: ordered drawing composition and prop effects.
- `../../web/player/assets.js`: strict asset loading and hash verification.
- `../../web/player/app.js`: playable conversation and rehearsal controls.

`build/seated-mvp/project.json` is the exported project entry point. PNGs, audio
and character manifests are self-contained under that directory. Exported
character drawings use local coordinates and a local origin; scene placements
provide position, uniform scale and depth. Rendered parts never undergo mesh
warping, skeletal deformation, optical flow or crossfades.

Each pose is an ordered list of drawings, so the same format handles a layered
seated character or a single full-body drawing. Actions connect named states
and hold frames for integer ticks at 24 fps. Transition drawings are already
saved in the source atlases; playback never generates images. The source
mouth library supplies its existing two drawn in-betweens for every shape pair.

## Chair composition

The chair belongs to the scene. Rear-chair images draw below the hips, body and
legs; near-chair-arm images draw above them. A near hand resting on the arm draws
last. The source room plate also includes the chair rear; the independently
exported rear layer records the scene composition explicitly. A production set
should supply a clean room plate and separately drawn furniture from the start.
Character packages do not contain chair parts. Trouser-edge layers keep original
ink in front of the far sleeve.
Each character now has four complete torso-and-leg drawings, plus four complete
transition drawings. Jackets, hips, butts and thighs are drawn together.
The uncrossed upright, reclined and intermediate-lean bodies use the
`*-bodies-uncrossed*.png` sheets, with distinct thigh contours and planted feet.
Their prompts and source lineage are in
[`UNCROSSED-PROMPTS.md`](../../assets/episodes/seated-postures/UNCROSSED-PROMPTS.md).
The full body renders behind the chair foreground; a mask exposes the front
legs above it using the exact same source pixels and position. This controls
occlusion without joining separately generated anatomy. Masks follow the
chair's existing inked foreground contour; an arbitrary cut through the cushion
would create an unoutlined step in the hip. A production chair can supply its
own drawn cushion lip in that foreground layer.
A collar cutout from the body preserves the rim above the neck and below the
animated jaw. Fromm's fitted neck repair covers the obsolete inner jaw edge;
the back collar rim remains in front of the neck. His shirt ends above the crotch.
Head sizing is baked uniformly around the registered neck anchor, including all
mouth, eye and neck cels. Fromm uses a 90% head scale and a rearward placement
adjustment across settled poses and transition drawings.
Qualify uses corrected
whole-arm drawings with the anatomical thumb on the viewer-facing side of
the palm. The remaining arm bank is reused across all postures.
The original coffee table and cups also render as an independent foreground
layer, above moving legs.

## Deliberate scope

The existing grayscale Krusty/Fromm artwork is a test cast, not the intended
original game cast. There is one seated viewpoint, three gesture actions per
character and four settled postures (upright/reclined × crossed/spread).
The shared runtime now supports session saves, replay, scene paths and whole-body
locomotion. See the [production workflow](../../docs/production-workflow.md) and
[original-character arrival study](../arrival/README.md). This seated cast still
has only its authored viewpoint and postures; new views and history simulation
require further content.

## Interface direction

The stage is the main visual, beside a readable spoken-line and choice column.
Midnight blue (`#1e2e40`), silver (`#c7c9cb`), paper (`#e9e5dc`), brass (`#bca572`)
and a broadcast red (`#a52b3d`) surround the existing monochrome art. Georgia
carries the title and dialogue; Helvetica/Arial handles transport controls.
The rounded silver screen frame refers to a television, while the conversation
choices remain visibly interactive. This replaces a generic dashboard layout.
On narrow screens the dialogue and choices sit below the stage. Keyboard focus
is explicit; reduced-motion preference disables decorative smoke and idle blinks.

## Verification

`npm test` covers exact drawing boundaries, action recovery/queueing, invalid
references, state changes with whole-body poses, placement at different scales,
conditional dialogue, stale completion callbacks, mouth timing and chair depth.

The browser check is `tests-js/browser-check.cjs` (requires Playwright and an
installed Chrome). It checks both branches, pause/resume, skip/restart, rehearsal
and mobile layout, and saves screenshots and a report under the exported build.
`tests-js/postures-browser.cjs` checks all four postures for both actors,
gestures in each posture, reuse of arm sprites, face anchors, speech samples,
reverse actions, frame-step pause, reset and mobile controls.

Verified on 2026-09-10: 12 JavaScript tests and both Chrome browser suites passed.
The earlier seated MVP also passed all 45 existing Python tests. All four
postures, held gestures and desktop/mobile layouts were visually inspected.

`tests-js/boundary-review.cjs` uses the production renderer to save native-size
compositions of all four postures and all four transition drawings, collar
contact sheets for all nine mouth keys, and held-gesture galleries for both
speakers. Run it with the same Playwright/Chrome setup as the
browser checks. Review the hip origin, thigh ink, collar rim and ear/neck overlap
in `build/seated-mvp/boundary-*.png` and `collars-*.png`; passing state-machine
checks alone does not establish that these visual joins are correct.
The project manifest records every referenced character, drawing, furniture
and audio hash; the browser rejects assets that no longer match it.
The new raster art used the built-in imagegen tool; its final prompts and source
references are in [PROMPTS.md](../../assets/episodes/seated-postures/PROMPTS.md).
