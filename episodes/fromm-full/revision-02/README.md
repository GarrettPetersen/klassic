# Revision 02

[Watch the captioned film](../../../build/fromm-full-02/episode-captioned.mp4) · [Clean film](../../../build/fromm-full-02/episode.mp4) · [Captions](../../../build/fromm-full-02/episode.srt) · [Review player](../../../build/fromm-full-02/review.html)

Finished runtime: **26:54.294**. Full decode, 323 captions, 135 camera shots and
16 encoded frames verified. All 31 repository tests passed.

The captioned MP4 burns the verified SRT into the picture with a high-contrast
lower band. The clean MP4 remains available alongside it, and the original SRT
is retained as a separate caption file. Captioned export verification is in
`build/fromm-full-02/production/captioned-verification.json`.

The revision repairs the stage artwork, moves the title after Krusty's opening
teaser, adds continuous archival room tone, and replaces the Krusty question
identified at 4:14. All Fromm recordings and the other 118 takes are preserved.

## Artwork

The revised stage is [fromm-v2](../../../assets/episodes/fromm-v2/rig.json).
Krusty's far-side hair reaches the face and is retained above the animated
mouth cels. Fromm's collar overlaps the neck, and broader shoulders support
his head. Both the ordinary stage and the drinking pose use the corrections.

The raster corrections were made with the built-in image generation tool.
The exact selected prompts are [hair-prompt.txt](hair-prompt.txt) and
[torso-prompt.txt](torso-prompt.txt). Selected workspace assets:

- [Hair root correction](../../../assets/characters/fromm/hair-root-correction.png)
- [Collar and shoulder correction](../../../assets/characters/fromm/torso-correction.png)
- [Registration and foreground specification](../../../assets/characters/fromm/stage-corrections.json)

`revise_stage.py` registers the generated regions in the original canvas and
preserves the existing face and mouth animation. The full-scene hair attempt
was rejected during visual review; only the localized hair correction is used.

## Title and sound

The first 27.58 seconds are the teaser. The existing 6.25-second title starts
after “in a moment”; “Good evening” follows at 33.83 seconds. The opening music
moves with the title. Captions and review-player links use the same time mapping.

`analyze_noise.py` measures quiet regions in the first cut's processed dialogue.
The added room tone uses the positive difference between Fromm's and Krusty's
quiet spectra, including the low-frequency peaks around 117 and 352 Hz at the
analysis resolution. It is band-limited to 90–6,500 Hz and set to approximately
−58.52 dBFS before ducking. Independent random blocks avoid a repeating loop;
no speech samples are copied. `make_atmosphere.py` lowers this added layer by
18 dB throughout Fromm's continuous speaking runs, with smooth transitions.
It also covers the teaser, title, pauses, and credits. The original noise in
Fromm's recordings remains in place. The spectrum and level are measurement
based; their perceived match still needs a listening judgment.

Only `t015` is regenerated, using the approved Krusty reference, seed 47,
reference guidance 0.85, temperature 0.6, and exaggeration 0.2. The replacement
is [t015.wav](../../../voices/takes/fromm-full-revision-02/t015.wav).
Its ASR report recovers the substantive question, simplifying the redundant
hesitation “what meaning, what, what deeper meaning” to “what deeper meaning.”
The script and captions retain the original wording. Accent improvement has
not been established by ASR; the new take is available for listening review.

## Rebuild and evidence

Run commands from the repository root. These scripts target named revision
directories and fail when a new selection or prepared build already exists.
The original full film remains in `build/fromm-full-01`.

```sh
PYTHONPATH=. python3 episodes/fromm-full/revision-02/revise_stage.py
PYTHONPATH=. python3 episodes/fromm-full/select_takes.py episodes/fromm-full/episode.json --base voices/takes/fromm-full-selected-01 --overrides episodes/fromm-full/revision-02/take-overrides.json --out voices/takes/fromm-full-selected-02
```

The selected audio is frozen in `voices/takes/fromm-full-selected-02/selection.json`.
`rebuild.py` reuses the verified first cut's prepared timing and replaces t015
from `build/fromm-retake-015-02`, which was prepared with the ordinary pipeline
using `retake-script.json` and the revision's raw take directory. It regenerates
the sample-accurate dialogue and all subsequent turn times.

```sh
PYTHONPATH=. python3 episodes/fromm-full/revision-02/rebuild.py
PYTHONPATH=. python3 episodes/fromm-full/edit_camera.py build/fromm-full-02
PYTHONPATH=. .venv-voice/bin/python episodes/fromm-full/revision-02/analyze_noise.py
PYTHONPATH=. .venv-voice/bin/python episodes/fromm-full/revision-02/make_atmosphere.py
PYTHONPATH=. python3 episodes/fromm/assemble.py build/fromm-full-02 --rig assets/episodes/fromm-v2/rig.json
PYTHONPATH=. python3 episodes/fromm-full/verify.py build/fromm-full-02 --rig assets/episodes/fromm-v2/rig.json
PYTHONPATH=. python3 episodes/fromm-full/revision-02/burn_captions.py build/fromm-full-02/episode.mp4 build/fromm-full-02/episode.srt build/fromm-full-02/episode-captioned.mp4
```

The build stores the atmosphere hash and envelope settings, selected-take
integrity report, picture and episode manifests, and export verification.
`tests.log` records the 31 passing repository tests, including title insertion
and rejection of invalid boundaries.

After assembly, `review_export.py` extracts sixteen encoded checkpoints and adds
revision jump links to the review player. `production/visual-review.json` records
the completed visual inspection. The original first-cut status is preserved in
`previous-status.json`.
