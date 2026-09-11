# Classic Krusty — The Sane Society

[Watch the captioned full film](../../build/fromm-full-02/episode-captioned.mp4) · [Clean film](../../build/fromm-full-02/episode.mp4) · [Captions](../../build/fromm-full-02/episode.srt) · [Review player](../../build/fromm-full-02/review.html)

Runtime: **26:54.294**, 1440×1080, 24 fps.

Revision 02 fixes Krusty’s far-side hair and Fromm’s collar and shoulders, moves
the title and opening jazz after the teaser, adds matched room tone ducked
during Fromm’s answers, and replaces the Krusty question flagged at 4:14.
All 72 Fromm recordings are preserved. See [revision notes and rebuild steps](revision-02/README.md).
The [first cut](../../build/fromm-full-01/episode.mp4) is retained.

The complete discussion from the user-designated `inputs/fromm-1958/transcript.txt`
is preserved here as `transcript.txt`. The final `episode.json` has 4,141 spoken
words across 119 takes. `edit-map.json` maps every take to its original speaker
block and records edits. All substantive questions and answers are retained,
including the ending missing from the pasted excerpt.

Wallace is recast as Krusty. Network announcements, unspoken stage directions,
and the obsolete next-programme promotion are omitted. Minor transcript repairs
are recorded, including two slips checked against the original recording.
Two host cues are lightly adapted for delivery: the opening question is reordered,
and the book-title cue says “Your book, The Sane Society.” The discussion and its
historical claims remain in their 1958 context.

Production uses the existing Fromm stage and authored mouth cels, the approved
Cartoon Studio Krusty reference, and Fromm’s 1958 reference. Chatterbox runs on
CPU with two compute threads. `voice-environment.txt` and `model-revisions.json`
record the environment. Long turns are divided at sentence or clause boundaries
without extra pauses between chunks of one source block.

## Audio selection

The frozen `synthesis-script.json` produced the 119 raw recordings in
`voices/takes/fromm-full-01`. Seed-43 retakes use `retake-script.json` and
`voices.retake-01.json`; the two adapted host cues use `retake-script-03.json`
and `voices.retake-03.json` (seed 46). Raw takes and rejected candidates remain
available. `take-overrides.json` selects replacements explicitly. Three repairs
remove repeated speech, and two unchanged recordings have corrected transcript
metadata. Their edit manifests retain source hashes.

All selected takes have audio-hashed speech-recognition reports. The review
record in `audio-review.json` distinguishes spelling variants, removed hesitations,
repeated speech repairs, and differences checked using a second recognizer or
adjacent dialogue. `context-checks.json` and the secondary ASR reports preserve
that evidence. `audio-measurements.json` records pauses and brief full-scale
peaks in raw TTS. Listening review is still needed for voice likeness, consonant
quality, and the smoothness of audio edits.

## Reproduce the first cut from its saved selection

Run from the repository root. Selection and preparation require new output
directories; choose a new suffix when rebuilding an existing export.

```sh
PYTHONPATH=. python3 episodes/fromm-full/select_takes.py episodes/fromm-full/episode.json --base voices/takes/fromm-full-01 --overrides episodes/fromm-full/take-overrides.json --out voices/takes/fromm-full-selected-01
python3 -m klassic prepare episodes/fromm-full/episode.json --out build/fromm-full-01 --voice-mode files --takes voices/takes/fromm-full-selected-01 --rhubarb .tools/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb
PYTHONPATH=. python3 episodes/fromm-full/edit_camera.py build/fromm-full-01
PYTHONPATH=. python3 episodes/fromm/assemble.py build/fromm-full-01
PYTHONPATH=. python3 episodes/fromm-full/verify.py build/fromm-full-01
```

Camera editing follows continuous speaker runs, with occasional wide shots,
listening cuts, and infrequent drinking cutaways. The export is 1440×1080 at
24 fps, with clean picture, a jazz opening, five credit cards, optional SRT
captions, and local playback in `review.html`. Caption phrases are timed
proportionally within measured takes, as in the repository workflow.

`verify.py` checks the complete video/audio decode, export dimensions and duration,
source and output hashes, listener-mouth closure and silence at every frame,
and sip placement. It creates a contact-sheet page for every 20 camera shots.
The former short production test remains separate.

Status: revision 02 is rendered. All 31 repository tests passed. The entire
export decodes successfully; 36,402 listener frames and 3,616 quiet frames have
closed mouths. All 323 caption cues match the script and inserted title timing.
All 135 camera shots, sixteen encoded frames, and every title and credit card
have been visually reviewed. See `build/fromm-full-02/verification.json` and its
`production/` evidence folder. The noise layer's measured duck is 18.02 dB.

The user reviewed the first cut and identified the Krusty retake. The revised
voice accent and perceived noise match remain for listening review; ASR and
visual checks cannot establish those qualities.

Current animation review: [revision 07](revision-07/README.md) uses larger complete arms, outward far-hand thumbs, neutral cigarette holds, and offering gestures tied to questions and conciliatory lines. Pupil-free eye art, blinking and held leans remain. The full-film links above remain the completed revision-02 export.
