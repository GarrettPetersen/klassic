# Validation — September 9, 2026

The included micro-pilot was prepared with macOS Alex/Daniel scratch voices and Rhubarb 1.14.0, then rendered with local FFmpeg.

- Twelve initial automated checks passed for speaker parsing, malformed episodes, cue boundaries, gaps, camera coverage, caption timing, grayscale output, and refusing a drinking pose on an active speaker.
- The actual pilot exercised all nine Rhubarb shapes across its three turns.
- The film has five shots, including a two-second host listening sip during the guest's answer.
- FFprobe reports H.264 960×720 at 24fps, with AAC audio. Video duration is 18.333 seconds, audio about 18.307 seconds. Their difference is under one delivery frame.
- The rendered contact sheet was visually inspected; mouth placement, grayscale captions, camera framing, cigarette smoke, and the single held mug are visible.

Latest local review: `build/pilot-v2/review.html`; video: `build/pilot-v2/preview.mp4`. Build outputs are ignored by git and can be regenerated with the README commands.

At that stage neural voice generation had not yet been tested. Voice likeness, a longer transcript adaptation, and posting to X remain incomplete. The full source-transcript endpoint returned HTTP 403. The initial separate cigarette-drag pose was rejected by imagegen; the usable drinking pose is included instead. This is an animation/timing proof with scratch voices, not a finished release.

## Game voice and source follow-up

- Selected English Krusty LEGO Dimensions recordings were decoded to a mono 24 kHz reference with clip hashes and source metadata. The revised reference is 8.66 seconds, without the laughter-bearing line used in the first audition.
- Chatterbox 0.1.7, Torch 2.6.0, Apple MPS generated `build/voice-auditions/krusty-02.wav` (8.04 seconds). Local faster-whisper 1.2.1 / base.en recovered every requested word, with punctuation differences only. This checks intelligibility, not likeness or acting quality.
- Two reference-preparation tests cover selected clip order, the join gap, peak normalization, metadata, and missing-member failure.
- The Fromm archive transcript was retrieved in full. `episodes/fromm/source.json` records content hashes and a continuous editorial selection. No Fromm film has been rendered yet.

## Krusty mouth revision

- The user preferred the Cartoon Studio CPU voice take and requested mouths based on the original Simpsons model charts.
- Nine generated muzzle/jaw cels now replace Krusty's fixed gray oval. Alpha compositing uses a clean scene beneath the moving jaw silhouette. The guest is explicitly marked as a separate prototype rig.
- Sixteen automated checks passed, including a regression test that changing Krusty's mouth leaves the rest of the scene registered and a test that missing cels fail instead of using a placeholder.
- `build/mouth-study/preview.mp4`: 8.75 seconds, H.264 960×720 at 24fps with AAC. Full decode passed. Its original test dialogue uses the preferred voice. A nine-shape composited inspection sheet was visually checked for nose attachment, jaw silhouette, teeth, tongue, and pucker changes.
- Every historical guest requires an independently researched character design and mouth rig; see `docs/character-design.md`. Fromm has not yet been drawn or voiced.


## Authored transition revision — September 9, 2026

- Generated and saved 72 in-between PNGs, covering every one of the 36 distinct pairs of nine poses. Original endpoint PNGs are unchanged.
- Removed runtime landmark grids and mesh warping. The renderer selects registered drawings directly and reverses their order for reverse playback.
- 22 tests pass, including all 72 directed pair lookups, missing-pair failure, endpoint/cel hash mismatch rejection, closure timing, and nose occlusion across all 81 drawings.
- Re-rendered `build/mouth-study-v2/preview.mp4`: H.264, 960×720, 24 fps, AAC, 8.71 seconds. The prepared dialogue is the same accepted Cartoon Studio take; no new voice synthesis occurred.
- Inspected the generated sheets, a six-pair registered comparison, facial composites, and the local flipbook. Browser checks verified pause, scrubbing to BC-1, pair selection, and reverse playback. These establish functionality and inspectability; final likeness and movement quality remain artistic judgments.
- Source sheets, reference guides, exact prompts, extraction spec, and hashes are retained. See `docs/mouth-transitions.md`.


## Rounded E/F correction and second example

Replaced both rounded-mouth keys and their 30 connected transition cels to remove the separate upper-lip shelf. Verified that the other 42 in-betweens remain byte-identical. All 22 tests pass with the revised assets, including nose occlusion across the complete 81-drawing library. Inspected corrected full-face E and F composites.

Generated a new Cartoon Studio-conditioned CPU voice take using the accepted settings. Local Whisper small.en recovered the full original script. Prepared the 12.95-second `voice-test-02` build, retaining source audio, cues, text provenance, synthesis metadata, and hashes.
