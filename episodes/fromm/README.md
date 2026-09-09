# The Personality Market

A complete short Classic Krusty episode, adapted from Erich Fromm's argument in his May 25, 1958 Mike Wallace interview. The nine-turn script is a concise paraphrase with original opening, connecting remarks, and sign-off. It is not presented as a verbatim historical interview. Each turn records its provenance.

## Voices

Krusty uses the user-preferred Cartoon Studio game reference in `voices/krusty-reference-cartoon.wav`. Fromm uses his own voice in the archive interview, from 03:52.000 to 04:01.500. The uninterrupted reference was checked against the source transcript and a transcription of the surrounding 30-second window. [The reference record](voice-reference.json) stores URLs, timestamps, processing, and hashes. Source video and reference audio remain in ignored local directories.

The downloaded recording is `inputs/fromm-1958/interview.mp4`; the prepared 9.5-second mono reference is `voices/fromm-reference-1958.wav`. Processing used 24 kHz PCM16, highpass 75 Hz, lowpass 7500 Hz, and peak normalization to −3 dBFS with no pitch change.

Synthesis uses Chatterbox on CPU with two Torch threads, one process at a time. The saved configuration is [voices.reference.example.json](voices.reference.example.json). Run from the repository root, with the existing voice environment and downloaded models:

```sh
HF_HUB_OFFLINE=1 PYTHONPATH=. .venv-voice/bin/python episodes/fromm/synthesize.py
HF_HUB_OFFLINE=1 .venv-voice/bin/python episodes/fromm/check_audio.py
```

Completed takes are retained in `voices/takes/fromm-episode-01/`. Each carries its text, reference/configuration, and audio hashes. A changed take fails rather than silently reusing stale audio; archive that take's WAV/JSON before regenerating it. ASR comparisons flag missing or changed words for review. They do not establish voice similarity or replace listening. The first t004 take confused “right smile”; its revised take uses “an attractive smile, agreeable opinions.”

## Picture and edit

The guest stage uses the approved Fromm portrait, an extracted head matte, separate foreground nose, and shared authored mouth cels. Lower-jaw matting removes the source portrait's collar without cutting away the jaw ink. Existing set tiles replace the previous guest's head. A neck layer joins the head to the seated body. The stage is saved at `assets/episodes/fromm/`.

To rebake into a new folder:

```sh
python3 -m klassic stage-fromm assets/characters/fromm/stage.json --out build/fromm-stage-rebake
```

To rebuild the complete film from the saved takes:

```sh
python3 -m klassic prepare episodes/fromm/episode.json \
  --out build/fromm-episode-01 --voice-mode files \
  --takes voices/takes/fromm-episode-01 \
  --rhubarb .tools/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb
PYTHONPATH=. python3 episodes/fromm/assemble.py build/fromm-episode-01
```

Preparation requires a new directory. Assembly can be rerun after picture changes. The authored cut uses wide shots, speaker close-ups, and a 2.5-second Krusty drinking cutaway during Fromm's answer. Silent intervals close the mouth; all mouth transitions use saved drawings. The clean 1440×1080, 24 fps export has a three-second title card and closing fade. Title rendering requires macOS Times New Roman Bold; a missing font fails explicitly.

Outputs are `episode.mp4`, `episode.srt`, `review.html`, the dialogue-only `preview.mp4`, and manifests with input/output hashes. SRT timestamps include the title offset. No disclosure text is burned into the film; disclosure remains in script/review metadata and is intended for the accompanying post. The project does not publish to X.

This is limited animation: camera crops, mouth cels, smoke, and a cut to a saved drinking pose. It does not yet animate blinking, gestures, or continuous arm movement.
