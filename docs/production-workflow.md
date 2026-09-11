# Drawing production and game workflow

The editable source lives in `assets/production/`. Builds read that source,
validate it, and pack atlases. They never regenerate or import artwork silently.
Layered seated characters and complete-body movement drawings use the same player.

## Run

```sh
npm run build:production
npm run build:reference
npm run build:arrival
npm run serve:mvp
```

- [Interview player](http://127.0.0.1:8765/web/player/)
- [Interview workbench](http://127.0.0.1:8765/web/review/)
- [Adrian seated reference](http://127.0.0.1:8765/web/player/?project=../../build/adrian-seated/project.json)
- [Adrian arrival study](http://127.0.0.1:8765/web/player/?project=../../build/arrival/project.json)

Open **Save, replay and animation tools → Play scene study** in either Adrian
example. The seated reference demonstrates rest, anticipation, a held offering
gesture and recovery. The body remains fixed while whole arms change drawings.
Its feet and seat have three planted contacts. The arrival study exercises paths,
a shorter stopping step, a chair interaction and a turn. Adrian has no recorded
voice or face overlays yet; the interview demonstrates those capabilities.

## Authoring and acceptance

Establish the complete character in its intended scene first. Keep the existing
Simpsons-style drawing direction: clear silhouette, consistent adult proportions,
four-digit hands, fixed anatomical sides, flat palette and strong ink contours.
Use drawn replacements for silhouette changes. Uniform placement and rotation are
allowed; deforming limbs and mirroring hands are not substitutes for missing art.

Choose replacement units by the action. Seated bodies combine torso and legs;
arms and facial drawings can be separate. Walking can replace the whole body.
Retain hidden contours. Chair fronts and backs are independent layers. When one
drawing crosses depth planes, complementary masks must use the **same pixels**.
Adrian's far arm uses this rule: upper sleeve behind the body, hand over the thigh.
Both pieces share one registration binding, so editing cannot separate the wrist.

Character sources contain `model.png`, individual `drawings/*.png`,
`character.json` and a version-2 `production.json` catalog. Canonical scene
packages are under `assets/production/scenes/`, including scene art, audio,
`project.json` and `reviews.json`. Generated references and prompts are retained
for provenance; runtime drawings are explicit registered RGBA files.

Reviews are independent, content-bound subjects:

| Subject | What its approval covers |
| --- | --- |
| `model` | Character model and design brief |
| `drawing:<name>` | One source drawing |
| `pose:<name>` | Body composition, registration and contacts |
| `face:<pose>:eyes=…:mouth=…` | One exact face combination on that body |
| `clip:<name>` | Drawings, order, timing, recovery and root motion |
| `scene:<name>` | Cast, furniture, placement and scene composition |
| `performance` | Project story, takes, scenes and authored performance cues |

IDs encode punctuation in names. Use the workbench's exported subject IDs when
calling tools. Accepting one scope never accepts another. Drawing changes stale
its users; changing one mouth leaves other face cases intact; timing changes
stale the clip; scene changes stale scene/performance reviews. Missing reviews
are unreviewed, not implicitly accepted. Inspect clips at normal speed as well as
frame by frame. The workbench requires a complete normal-speed pass before a
clip timing approval and exports coverage statuses separately from combinations.

Enter a reviewer and concrete observations, select a scope, and export decisions
with clean PNG proofs. Apply character and project bundles separately:

```sh
python3 -m klassic.production apply-review \
  assets/production/krusty-study/production.json /path/to/character-reviews.json
python3 -m klassic.production apply-project-review \
  --project assets/production/scenes/seated/project.json \
  --catalog-root assets/production /path/to/project-reviews.json
```

For model inspection, use an actual model/context proof:

```sh
python3 -m klassic.production review assets/production/adrian/production.json \
  --subject model --decision approved --reviewer 'Reviewer name' \
  --notes 'Specific visual observations.' --proof /path/to/model-proof.png
```

Performance review bundles use the project's `performance` subject and signature;
inspect the complete performance in the player before recording that decision.
Technical checks and automated screenshots never automatically approve artwork.
The catalogs keep uninspected subjects unreviewed, and the broad walking study
remains a draft pending additional alternating footfall drawings and registration.

## Registration editing

In the workbench select an anchor, contact, attachment or whole drawing. Enable
**Edit registration**, then drag its marker or enter X/Y and choose **Move target**.
Shoulder bindings move the complete arm and its prop/depth masks; neck bindings
move the head and face overlays together. Foot/seat markers edit contact metadata.
Undo/redo are available. Changing registration blocks approval until it is saved
and rebuilt as a new source revision.

```sh
python3 -m klassic.production apply-registration \
  assets/production/krusty-study/production.json /path/to/registration.json
npm run build:production
```

Patches contain exact before/after poses and a base revision. They cannot change
drawings, layer order, contact identity, locks or bindings. A stale patch fails.
For direct PNG edits, explicitly register new bytes before rebuilding:

```sh
python3 -m klassic.production register assets/production/adrian/production.json
```

## Source imports and release exports

The old film adapter is an explicit import candidate generator, not the normal
game build. To adopt its output, prepare a new comparison directory first:

```sh
npm run build:mvp
python3 -m klassic.production prepare-import \
  assets/production/krusty-study/production.json \
  --incoming build/seated-mvp/characters/krusty-study/character.json \
  --out build/krusty-import-proposal
```

Inspect `proposal.json`, its before/after drawing and field diffs, and incoming
PNGs. The canonical source has not changed. Apply only that checked proposal:

```sh
python3 -m klassic.production apply-import \
  assets/production/krusty-study/production.json build/krusty-import-proposal/proposal.json
```

Changed incoming bytes, a modified diff, or a stale canonical revision fail.
Normal exports are deterministic and preserve source pixels. Omit `--draft` for
a release; every character and project review subject must have a current
approval and intact proof. An unregistered asset change fails even draft builds.

```sh
python3 -m klassic.production bundle \
  --project assets/production/scenes/seated/project.json \
  --catalog-root assets/production --out build/release
```

## Movement and the shared timeline

Activities declare authored views. States select an activity/view and idle pose;
scene placements can select an initial state. Actions contain exposure ticks and,
for movement, one local root offset per drawing plus total displacement. The
runtime commits that displacement even when a frame or seek skips over a clip.

Movement actions declare `navigation: {family: "walk", kind: "stride"}` (or
`step`, `stop`, `approach`, `turn`). The path planner searches matching actions and
state transitions. It can combine strides and shorter steps and finish in an
explicit `end_state`, such as facing front. Stops/approaches end at the waypoint.
Unsupported distances/directions fail with an authoring error; the planner never
stretches strides, mirrors artwork, or snaps feet to make a path fit. Paths are
authored waypoints, not obstacle avoidance. Chair interactions have a radius and
intent; seated contact alignment requires a settled compatible seated state.

The contact checker measures consecutive planted points, including loop seams.
Missing contact coverage is reported as missing, not a pass. It cannot infer
correct anatomy or certify a walk without the appropriate foot registrations.

`GameSession` owns timestamped choices, captions, gaze, scene changes, movements,
schedules and speech starts/stops/seeks. Audio uses the selected take and offset;
lips and captions use that same speech sample during replay. The browser pauses
the performance clock while audio loads/buffers. No microphone recording occurs.

**Save session** preserves the story, actors, queues, schedule progress and speech
position. **Load session** restores paused. **Export performance** and **Replay
performance** preserve voiced events as well as blocking. The replay slider seeks
through the shared timeline, including into a spoken line. Saves and recordings
are version 2 and tied to the complete project revision. Old/incompatible files
fail explicitly. The separate film workflow still produces cinematic video.

## Verification

```sh
npm test
python3 -m unittest discover -s tests -q
node tests-js/browser-check.cjs
node tests-js/production-browser.cjs
node tests-js/revisions-browser.cjs
node tests-js/reference-browser.cjs
```

Browser tests need Playwright, Chrome and the local server. Set `NODE_PATH` to an
installed Playwright dependency directory if necessary. Tests cover independent
review invalidation, checked imports/patches, atlas pixels, pointer registration,
source-bound save/replay, audio seeking, captions, mixed movement and chair use.
Review screenshots and timed cels visually before accepting any art.
