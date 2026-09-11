> Motion experiment superseded by [revision 07](../revision-07/README.md), which uses complete arms with fixed left/right anatomy and pupil-free eye art. This page retains the accent evaluation and historical preview findings.

# Revision 03: performance rig and accent review

[Motion preview](../../../build/fromm-full-03/motion-preview.mp4) ·
[Accent listening review](../../../build/fromm-motion-test/accent-review.html)

## Animation

The reusable renderer is `klassic/puppet.py`, integrated into `Compositor` by
the `puppet` entry in [the Fromm rig](../../../assets/episodes/fromm-v3/rig.json).
The rig uses the existing character drawings and mouth cels. A light 2D mesh
leans each torso around its waist; heads, necks, collars, eyes and mouths follow
together, while the legs and furniture stay fixed. Four separate forearm/hand
cutouts rotate around elbows that follow the torso. Hands keep their original
drawn poses; this pass articulates those drawings rather than inventing new
finger poses. Small suit-colored overlap shapes keep the elbow joints covered.

The generated empty stage fills areas revealed by motion. Its exact successful
prompt is [clean-plate-prompt.txt](clean-plate-prompt.txt), using the built-in
image generation tool. The selected raster is
[clean-plate.png](../../../assets/episodes/fromm-v3/clean-plate.png).
Subsequent blink and torso-underlay generations were rejected by the image
tool; those rejected outputs are not used. Eyelids and joint overlaps are
native rig geometry. The corresponding rejected prompts are retained here as
production records.

`build_rig.py` traces and refines cutout masks against the existing artwork.
Hand/cuff masks explicitly exclude chair upholstery. The deterministic
`performance.json` contains editable, smoothly interpolated keys for lean,
free-hand gesture, cigarette-hand gesture, blink and camera gaze for both
speakers. The current range is ±3° of torso lean, 18° at the free elbow, and 6°
at the cigarette elbow. Speech drives intermittent gestures; each speaker has
a separate blink schedule. Krusty looks toward the audience during the teaser,
welcome and closing, and toward Fromm during the interview. Fromm's gaze stays
on Krusty. Existing drinking cutaways retain their authored complete pose with
live eyelids, pupils and the guest's mouth animation.

The initial deforming-arm experiment produced duplicate fingertips. It was
replaced with rigid arm layers. Silhouette refinement removed clipped hair;
separate hand/cuff mattes removed strips of upholstery and duplicate cuffs.
Motion outside the supported range requires additional drawn body coverage.

## Accent check

`klassic/accent.py` runs the MIT-licensed
[CommonAccent ECAPA model](https://huggingface.co/Jzuluaga/accent-id-commonaccent_ecapa)
locally, pinned to model revision `14bebf44b7e7a34204d0acc2c897935945fb5c51`.
Four provisional baseline takes form an equally weighted embedding centroid.
Ten other Krusty takes are held out. The original reported bad `t015` and its
replacement are scored separately. Audio stays on this machine; only model
weights are downloaded. Hashes freeze all input takes in `accent-samples.json`.

The reported drift is **not reliably separated**:

| Worst-window cosine distance | 6-second windows | 8-second windows |
| --- | ---: | ---: |
| Original flagged take | 0.13685 | 0.09508 |
| Highest provisional holdout | 0.13678 | 0.11569 |

At six seconds the separation is only 0.00007; at eight seconds it disappears.
The replacement also scores farther from the baseline. This does not establish
which recording sounds better. All tested windows receive the broad `us`
label; this model has no Texas or German category. Delivery, phonemes, noise
and synthesis artifacts can affect embedding distance. The baseline/holdout
labels remain provisional, not individually confirmed good performances.

Automatic rejection and regeneration are disabled. The result is a review
ranking with audio windows, not a production accent gate. No voice recordings
were changed for this revision.

## Reproduce

From the repository root, build the frozen accent experiment in a separate
environment so the voice-generation environment is unaffected:

```sh
python3.11 -m venv .venv-accent
.venv-accent/bin/pip install -r episodes/fromm-full/revision-03/accent-requirements.txt
PYTHONPATH=. .venv-accent/bin/python -m klassic.accent episodes/fromm-full/revision-03/accent-samples.json --out build/fromm-motion-test/accent-report.json
PYTHONPATH=. .venv-accent/bin/python -m klassic.accent episodes/fromm-full/revision-03/accent-samples.json --window 8 --out build/fromm-motion-test/accent-report-8s.json
PYTHONPATH=. python3 episodes/fromm-full/revision-03/review_accent.py
```

Mask authoring additionally uses OpenCV 4.13.0.92 and NumPy. The normal film
renderer needs only the project's Pillow dependency; it consumes saved masks.

```sh
.venv-voice/bin/pip install --target .tools/rigdeps --no-deps opencv-python-headless==4.13.0.92
PYTHONPATH=.:.tools/rigdeps .venv-voice/bin/python episodes/fromm-full/revision-07/build_rig.py
PYTHONPATH=. python3 episodes/fromm-full/revision-07/render_film.py proof
PYTHONPATH=. python3 episodes/fromm-full/revision-07/render_film.py full
python3 -m unittest discover -s tests -v
```

The film renderer uses the repository compositor, the existing camera timeline,
title-after-teaser mapping, six title/credit images and the exact revision-02
SRT. It renders four picture chunks, then copies the revision-02 finished AAC
stream into the full export. The title music, archival room tone, Fromm ducking,
all dialogue and the closing music therefore retain the previous mix exactly.
The preview uses excerpts of that mix. Full picture and audio hashes, source
intervals, rig and renderer hashes are saved alongside each export.
