# Klassic

Turn a two-person interview transcript into a black-and-white, limited-animation **Classic Krusty** fan parody. Keep the discussion dry. The incongruity of Krusty earnestly conducting it is the joke.

The first production source is **Erich Fromm on The Mike Wallace Interview (May 25, 1958)**, discussing personality as a marketable product. The complete archive transcript has been retrieved and verified. See [the episode brief](docs/pilot.md) and [source record with excerpt boundaries](episodes/fromm/source.json).

## What runs today

- Strict speaker-labeled transcript import and provenance for each turn.
- Audio from supplied WAV takes, Chatterbox, XTTS, or explicitly selected macOS scratch voices.
- Rhubarb phoneme recognition, nine chart-informed Krusty muzzle/jaw cels, independent character timing.
- Generated grayscale set and matching drinking pose, camera crops, listening cutaways, moving cigarette smoke.
- 24fps playback with 72 authored Krusty in-between cels covering all 36 mouth-pose pairs, encoded as H.264/AAC MP4, burned captions, SRT, contact sheet, editable JSON camera timeline, and a local HTML review page.
- Input hashes, retained takes, deterministic compositing, and errors for missing inputs or invalid timelines. No automatic replacement with a different voice provider.

The complete first short episode is **The Personality Market**, a concise adaptation of Fromm's argument with original Krusty framing and a closing sign-off. It uses the preferred Cartoon Studio Krusty voice reference and a separate Fromm reference from his 1958 interview. The portrait has a foreground nose, guest-specific skin treatment, and all 72 authored mouth transitions. See [the production recipe](episodes/fromm/README.md).

The film is 4:3 at 1440×1080 and 24 fps, with a title card, clean picture, and optional SRT captions. Close-ups crop the master set; the drinking pose changes across cuts. Blinks and full arm animation are not implemented.

## Run the included proof

Python 3.11+, FFmpeg (including ffprobe), and [Rhubarb Lip Sync 1.14.0](https://github.com/DanielSWolf/rhubarb-lip-sync/releases/tag/v1.14.0) are required. Extract Rhubarb with its supporting files intact. Either put its executable on PATH or pass `--rhubarb /path/to/rhubarb`.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m klassic validate episodes/pilot/episode.json
.venv/bin/python -m klassic prepare episodes/pilot/episode.json \
  --out build/pilot \
  --voice-mode macos --voices episodes/pilot/voices.scratch.json \
  --rhubarb .tools/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb
.venv/bin/python -m klassic render build/pilot --rig assets/rig.json
open build/pilot/review.html
```

The `.tools` path above is the locally installed macOS Rhubarb binary for this checkout, ignored by git. Other machines must install the appropriate release. Scratch mode requires macOS with Alex and Daniel installed (`say -v '?'` lists available voices); configure actual installed names in `voices.scratch.json`. A missing voice fails the build.

Preparation requires a **new output directory** so an interrupted run cannot silently reuse old audio. Rendering may be repeated after editing `timeline.json` or the rig. Keep dialogue text changes in the episode and prepare again: audio and episode snapshot hashes are checked on render.

## Import a real excerpt

Use a UTF-8 text file with explicit labels, e.g. `BUCKLEY: …` and `JENKINS: …`, with continuation lines underneath. First review OCR manually. Moderator or audience turns must be deliberately edited or omitted before import; they are never guessed to be the guest.

```sh
.venv/bin/python -m klassic import inputs/excerpt.txt \
  --host-label BUCKLEY --guest-label JENKINS \
  --title 'Klassic Krusty — Union monopoly' \
  --source-url 'https://digitalcollections.hoover.org/objects/6008' \
  --out episodes/union-monopoly.json
```

Imported lines remain quotations even when the host is recast as Krusty. If you rewrite a line, set its provenance to `adaptation` or `original`. Record source page/time ranges in `source.notes`. Split very long answers into takes of at most 1000 characters. Set internal `pause_after` to zero when splitting one continuous answer. This version handles sequential dialogue; overlapping interruptions require an editorial choice before import.

## Produce the voices

The working Krusty reference uses isolated Cartoon Studio game lines; the earlier LEGO reference was rejected as too smooth and high. Fromm uses a separate 9.5-second reference from his 1958 interview. Sources and preparation details are in [voice sourcing](docs/voice-sourcing.md) and [the Fromm recipe](episodes/fromm/README.md).

Chatterbox is the initial neural candidate; [XTTS has noncommercial model/output restrictions](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt). See [voice setup and direction](docs/production.md). Install either model's dependencies in its own environment using its official instructions, then install this repo there with `pip install -e .`. The base install intentionally does not download multi-gigabyte models. Model licensing is separate from rights in reference recordings or the voice performance.

```sh
# Run with a Python environment containing chatterbox-tts.
python -m klassic prepare episodes/pilot/episode.json \
  --out build/neural-take-01 --voice-mode chatterbox \
  --voices episodes/pilot/voices.reference.example.json --device cpu \
  --rhubarb /path/to/rhubarb
```

Use `--device cuda` for a suitable GPU. Use CPU for current local auditions; Torch compute threads are limited to two. An earlier MPS audition completed, but a later GPU comparison was interrupted by a machine crash of undetermined cause. The recovery comparison runs one CPU process at a time in `.venv-voice`. There is no silent CPU fallback. XTTS uses the same reference JSON with `--voice-mode xtts`; accept its license through the model's own installation flow. The program does not auto-accept it. CPU neural generation can be slow. Listen to every take before trusting pronunciation, cadence, or speaker similarity.

Alternatively, place one audio file per turn (`t001.wav`, `t002.wav`, …) in a takes directory. These may be human performances, an externally generated voice, or edited final takes:

```sh
python -m klassic prepare episodes/pilot/episode.json \
  --out build/final-takes --voice-mode files --takes voices/takes \
  --rhubarb /path/to/rhubarb
python -m klassic render build/final-takes --rig assets/rig.json --width 1440
```

Update the episode disclosure to accurately describe the finished audio. macOS builds retain scratch status in their metadata; use `--scratch` to mark supplied or neural draft takes. The picture has no burned disclosure banner; retain accurate disclosure with the shared post. Supplied-file builds otherwise rely on the declared provenance of your audio. Reference and raw source recordings belong in ignored `voices/` and `inputs/` directories.

## Editing and verification

`timeline.json` retains local mouth cues, measured turn start/end times, and camera shots. Change camera cuts there, including optional `pose: "host_sip"`. Shots must cover the entire timeline with no gaps or overlaps, and drinking poses cannot cover a speaking character. Mouth timings are editable for difficult consonants. Captions have exact take boundaries but proportional phrase timing; word-level alignment is not implemented.

The master and pose PNGs are checked into `assets/`. Coordinates in `assets/rig.json` are normalized to the full scene. The mouthless base was generated specifically for replacement animation. Missing pose art is an error. Image generation is an explicit art-production step in Codex using the built-in imagegen tool and the saved [prompts](prompts/); the CLI does not silently call a paid image API.

```sh
python3 -m unittest discover -s tests -v
ffprobe -v error -show_streams -show_format build/pilot/preview.mp4
```

Before sharing, watch the full film with audio and inspect `contact-sheet.jpg`. [Sharing notes](docs/sharing.md) cover parody labeling, archive rights, and X. The project does not post to any account.

## Character and mouth study

[Character design rules](docs/character-design.md) require a separately researched period portrait and mouth rig for every historical guest. The original `assets/rig.json` guest sketch is a prototype; the complete Fromm episode uses `assets/episodes/fromm/rig.json`. The integrated Krusty study is `build/mouth-study-v2/preview.mp4`, with original test dialogue and the preferred Cartoon Studio voice. Reproduce it from `episodes/voice-test/episode.json` and the saved take through `--voice-mode files`; render with `assets/rig.json`.

[Authored mouth transitions](docs/mouth-transitions.md) documents the complete drawing library, saved imagegen prompts, deterministic baking, and the all-pairs flipbook. Runtime mouth warping has been removed.
