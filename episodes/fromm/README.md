# Fromm episode production

This directory contains the short production test adapted from Fromm's argument. The full 26:54 interview is now rendered separately in [build/fromm-full-02](../../build/fromm-full-02/episode.mp4); see [its production notes](../fromm-full/README.md) for the complete script and review status. The nine-turn script is a concise paraphrase with original opening, connecting remarks, and sign-off. It is not presented as a verbatim historical interview. Each turn records its provenance.

## Voices

Krusty uses the user-preferred Cartoon Studio game reference in `voices/krusty-reference-cartoon.wav`. Fromm uses his own voice in the archive interview, from 03:52.000 to 04:01.500. The uninterrupted reference was checked against the source transcript and a transcription of the surrounding 30-second window. [The reference record](voice-reference.json) stores URLs, timestamps, processing, and hashes. Source video and reference audio remain in ignored local directories.

The downloaded recording is `inputs/fromm-1958/interview.mp4`; the prepared 9.5-second mono reference is `voices/fromm-reference-1958.wav`. Processing used 24 kHz PCM16, highpass 75 Hz, lowpass 7500 Hz, and peak normalization to −3 dBFS with no pitch change.

Synthesis uses Chatterbox on CPU with two Torch threads, one process at a time. The saved configuration is [voices.reference.example.json](voices.reference.example.json). Run from the repository root, with the existing voice environment and downloaded models:

```sh
HF_HUB_OFFLINE=1 PYTHONPATH=. .venv-voice/bin/python episodes/fromm/synthesize.py episodes/fromm/episode.json --voices episodes/fromm/voices.reference.example.json --out voices/takes/fromm-episode-01
HF_HUB_OFFLINE=1 .venv-voice/bin/python episodes/fromm/check_audio.py episodes/fromm/episode.json --takes voices/takes/fromm-episode-01
```

Completed takes are retained in `voices/takes/fromm-episode-01/`. Each carries its text, reference/configuration, and audio hashes. A changed take fails rather than silently reusing stale audio; archive that take's WAV/JSON before regenerating it. ASR comparisons flag missing or changed words for review. They do not establish voice similarity or replace listening. The first t004 take confused “right smile”; its revised take uses “an attractive smile, agreeable opinions.”

## Picture and edit

The guest stage uses the approved Fromm portrait, an extracted head matte, separate foreground nose, and shared authored mouth cels. Lower-jaw matting removes the source portrait's collar without cutting away the jaw ink. Existing set tiles replace the previous guest's head. A neck layer joins the head to the seated body. The stage is saved at `assets/episodes/fromm/`.

To rebake into a new folder:

```sh
python3 -m klassic stage-fromm assets/characters/fromm/stage.json --out build/fromm-stage-rebake
```

To rebuild the production test from the saved takes:

```sh
python3 -m klassic prepare episodes/fromm/episode.json \
  --out build/fromm-episode-01 --voice-mode files \
  --takes voices/takes/fromm-episode-01 \
  --rhubarb .tools/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb
PYTHONPATH=. python3 episodes/fromm/assemble.py build/fromm-episode-01
```

Preparation requires a new directory. Assembly can be rerun after picture changes. Assembly preserves the measured camera edit in `timeline.json` and accepts any number of turns. The existing test timeline includes wide shots, speaker close-ups, and a 2.5-second Krusty drinking cutaway during Fromm's answer; fresh preparation generates its own timeline. Silent intervals close the mouth; all mouth transitions use saved drawings. The clean 1440×1080, 24 fps export now has a 6.25-second title, a jazz cue that fades into the opening, and 40 seconds of closing credits. Title rendering requires macOS Times New Roman Bold; a missing font fails explicitly.

Outputs are `episode.mp4`, `episode.srt`, `review.html`, the dialogue-only `preview.mp4`, and manifests with input/output hashes. SRT timestamps include the title offset. No disclosure text is burned into the film; disclosure remains in script/review metadata and is intended for the accompanying post. The project does not publish to X.

This is limited animation: camera crops, mouth cels, smoke, and a cut to a saved drinking pose. It does not yet animate blinking, gestures, or continuous arm movement.

## Music and credits

[George Street Shuffle](../../assets/music/source.json) by Kevin MacLeod provides the opening and closing music. The composer's site explicitly offers the recording under CC BY 4.0. The checked-in recording has a source hash and [credit text](../../assets/music/CREDITS.md). The mono mix is filtered to match the dialogue; the closing cue uses the natural ending of the piece and starts quietly beneath the sign-off before rising over the credits.

The five eight-second credit cards list the cast; Garrett M. Petersen with GPT 6 Astra; Chatterbox by Resemble AI and the voice references; the historical transcript source; and the required music attribution and edit notice. They are ordinary end credits, with no top disclosure banner.

To rebuild only the titles, music, and credits from a verified picture render:

```sh
PYTHONPATH=. python3 episodes/fromm/assemble.py build/fromm-music-review --finish-only
```

The music review is a copy of the short test, **not the full episode**. Its duration is 147.26 seconds including the longer titles/credits. The prior 104.026-second export is preserved at `build/fromm-episode-01/episode.mp4`. Input timeline and picture hashes are checked before finishing; changed picture inputs require another render.

## Full-length status

The user-designated complete local transcript at `inputs/fromm-1958/transcript.txt` is the source for the full interview. The full script at `episodes/fromm-full/episode.json` contains 4,141 spoken words in 119 takes, with a source copy and explicit edit map. The complete film is `build/fromm-full-02/episode.mp4` (26:54). Export and visual checks passed; full listening review remains pending. See `episodes/fromm-full/README.md` for the production record. The short test remains separate.

Voice generation now accepts an explicit episode, reference configuration, and output directory. It checks all saved takes before generating any new ones and loads the speech model only when needed. The assembly tool no longer restricts the edit to nine turns. The full episode uses its own script, selected take directory, and build.
