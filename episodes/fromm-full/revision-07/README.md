# Neutral cigarette holds and intentional offering gestures

[Motion preview](../../../build/fromm-full-07/motion-preview.mp4) ·
[Arm and seam review](../../../build/fromm-full-07/review.html)

The default far-hand pose is a neutral cigarette grip. Open palms are brief
questioning, conciliatory or inviting gestures; both arms return to rest after
each gesture. The opening, title lead-in, closing and listening poses stay neutral.

`gesture-cues.json` contains 26 editorial cues, each attached to a transcript
turn, offset, phrase and conversational meaning. This replaces the periodic
speaking-time gesture schedule for the entire interview. Gesture poses are
held drawings with deliberate changes, not finger morphing or continuous sway.
Blinking, gaze and torso lean retain the previous performance tracks.

Far hands use the original cigarette atlases with thumbs on the outward side
of the palm-up pose. Krusty's far hand is his left; Fromm's is his right. The
later “handed” atlases selected by revision 06 had the wrong orientation in the
seated scene and are no longer used. All hands use three fingers plus one thumb;
neutral curled grips can occlude a digit. Fromm's original raised-palm drawing
has ambiguous finger separation, so his clear sweep drawing is raised as a
complete arm for that pose. Sixteen named poses use fifteen source drawings.

Far sleeve heights are now 204 pixels for Krusty and 214 for Fromm, previously
177 and 186 (about 15% larger). Near arms are 10% larger. Each complete arm is
scaled uniformly about its shoulder; hand-to-sleeve proportions and outlines
are preserved. Far arms stay behind the torso and near arms in front. Original
suit pixels and moving seam ink stay above the repair underlays. Far shoulder
anchors move inward by 26 and 28 pixels, placing upper arms behind the torso.
A grayscale render curve matches sleeve midtones to jacket gray 27/25 while
preserving black ink, skin, cuffs and alpha. Original crossed-trouser contour
pixels render above the far sleeves. The first 30% enlargement was reduced
after user review.

## Rebuild and verification

No new image generation was needed. The builder mattes and registers existing
whole-arm artwork with overscan to retain tips crossing atlas cell boundaries.
OpenCV and NumPy are available through the existing offline rig environment.

```sh
PYTHONPATH=.:.tools/rigdeps .venv-voice/bin/python episodes/fromm-full/revision-07/build_rig.py
python3 -m unittest discover -s tests -q
PYTHONPATH=. python3 episodes/fromm-full/revision-07/review_rig.py
PYTHONPATH=. python3 episodes/fromm-full/revision-07/render_film.py proof
PYTHONPATH=. python3 episodes/fromm-full/revision-07/verify_preview.py
```

The runtime tests passed (45 tests). Review sheets show every pose in the seated
scene at lean extremes, alongside isolated arms. `verify_preview.py` checks the
movie's input hashes, decodes every frame and creates encoded-frame samples.
It also checks original trouser-ink pixels across all four far poses at three
lean angles and confirms neutral opening/closing arm states.
Side and digit metadata checks validate configuration; they do not establish
anatomical correctness. User visual review remains pending.

The preview includes neutral opening and closing poses, the title/music break,
Krusty's first question, Fromm's concession and his agreement with the host.
Voices, audio mix and captions use revision 02. Existing full-art drinking
cutaways retain their original arms. The completed full film remains revision
02; this revision exports a motion preview only. For a full export, run
`render_film.py full` followed by `finalize.py` in this directory.
