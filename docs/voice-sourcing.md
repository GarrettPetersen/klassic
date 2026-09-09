# Krusty's game voice reference

The working source is [Krusty from LEGO Dimensions (Wii U), The Sounds Resource](https://sounds.spriters-resource.com/wii_u/legodimensions/asset/404055/). Its ZIP contains 213 entries across languages; 35 filenames end in `_ENG.OGG`. The selected clips are mono 44.1 kHz. The archive was accessed through its normal public browser page and downloaded through its download link on September 9, 2026. Search-tool access returned 403, but the browser and download link worked without login.

The downloaded ZIP is in `voices/source/krusty-lego-dimensions.zip`. Raw clips and the assembled reference stay in the git-ignored `voices/` directory. This archive is a source for the local voice experiment, not a redistribution package.

## Selected reference

`voices/krusty-reference-v2.wav` is 8.66 seconds, assembled in this order:

1. `DX_KRUSTY_HOMERYOURETHE_ENG.OGG`
2. `DX_KRUSTY_LETSSEEWHAT_ENG.OGG`
3. `DX_KRUSTY_BETTERGETBACKON_ENG.OGG`

The earlier `krusty-reference.wav` included laughter, detected during local ASR screening, so v2 uses different material. ASR is a screening aid, not a listening-quality assessment. The reference needs a human ear before final voice approval.

Preparation converts to mono 24 kHz PCM16, inserts 180 ms between clips, and applies one global gain to a -3 dBFS peak. It does not denoise, remove internal pauses, change pitch, or time-stretch the performance. A `.source.json` beside the WAV records selected archive members, segment positions, durations, gain, source URL, and SHA-256 hashes.

```sh
python3 -m klassic reference voices/source/krusty-lego-dimensions.zip \
  --clips DX_KRUSTY_HOMERYOURETHE_ENG.OGG \
          DX_KRUSTY_LETSSEEWHAT_ENG.OGG \
          DX_KRUSTY_BETTERGETBACKON_ENG.OGG \
  --source-url 'https://sounds.spriters-resource.com/wii_u/legodimensions/asset/404055/' \
  --out voices/krusty-reference-v2.wav
```

Use a new output filename for a new selection. This command works for any ZIP of isolated audio, using explicit member names; it never guesses a language or speaker.

## Audition without needing a guest voice

The `audition` command generates one Chatterbox line from a reference. It avoids requiring a second speaker's reference just to test Krusty.

```sh
python3 -m venv .venv-voice
.venv-voice/bin/pip install 'chatterbox-tts==0.1.7' -e .
.venv-voice/bin/python -m klassic audition \
  --reference voices/krusty-reference-v2.wav \
  --text 'Tonight we are discussing the institutions of industrial society. What happens when the interests of management and ownership diverge?' \
  --out build/voice-auditions/new-take.wav --device cpu
```

Use `cuda` or `cpu` on other hardware. This is local synthesis, not an upload of the reference to a voice service. An audition sidecar records the generated text, reference hash, audio hash, backend, and device. The output is explicitly synthetic.

For a film assembled from generated host takes and an existing scratch guest, use `prepare --voice-mode files --scratch`. State the mixture in the episode disclosure; scratch labeling must survive the change of input mode.

## Voice revision: lower register and rasp

The user rejected `krusty-02.wav`: too high, too smooth/generic, not gravelly enough. Intelligibility did not establish character likeness. Keep this take as a rejected experiment, not a production voice.

The audition command now exposes `--cfg-weight`, `--exaggeration`, `--temperature`, and `--seed`, and records these settings alongside the audio. Initial comparisons keep identical text and seed while changing reference conditioning and clip selection. The installed English Chatterbox model uses the first six seconds for speech conditioning and the first ten for decoder conditioning, so clip order matters. Its speaker embedding also uses the reference. These controls are experiments, not guaranteed pitch or rasp controls.

An additional source is [Krusty in The Simpsons Cartoon Studio](https://sounds.spriters-resource.com/pc_computer/thesimpsonscartoonstudio/asset/450560/), downloaded from the page's public link on September 9, 2026. It contains 33 WAV files, including speech and non-speech reactions. Local archive: `voices/source/krusty-cartoon-studio.zip`. Screen speech clips separately from laughs, cries, and screams before selecting a reference.

The Cartoon Studio reference uses coffee, don't-hang-around, everyday, Danish, and bookie clips, totaling 9.06 seconds after joins. It is saved as `voices/krusty-reference-cartoon.wav` with clip-level provenance. Neither the LEGO nor Cartoon Studio reference is pitch-shifted or artificially distorted.

## Recovery after the interrupted comparison

The machine crashed during the first MPS comparison. No new synthesized comparison WAV survived; the previously completed audition and all reference files did. The cause was not established. Resume with one CPU synthesis process and two Torch compute threads; do not automatically restart the GPU batch. Save logs under ignored `logs/` so a restart does not erase the evidence.

The Cartoon Studio source files checked here are mono 22,050 Hz, 8-bit PCM. Recording noise is not evidence of the desired vocal rasp. Final judgment must compare the generated performance with the character, not just its pitch or noise level.

The recovery comparison uses identical text and parameters on CPU: CFG 0.7, exaggeration 0.3, temperature 0.8, seed 42. `d-cartoon-cpu.wav` and `e-lego-cpu.wav` differ only in reference recording. Listen in `build/voice-comparison/review.html`. CLI CPU synthesis now limits Torch compute threads to two.

```sh
HF_HUB_OFFLINE=1 .venv-voice/bin/python -m klassic audition \
  --reference voices/krusty-reference-cartoon.wav \
  --text 'Tonight, we are discussing the institutions of industrial society. What happens when the interests of management and ownership diverge?' \
  --out build/voice-comparison/new-cartoon-take.wav --device cpu \
  --cfg-weight 0.7 --exaggeration 0.3 --temperature 0.8 --seed 42
```

Offline mode requires the already-downloaded model cache. Omit it on a fresh machine to obtain the official weights.

The user reported the Cartoon Studio CPU audition (`d-cartoon-cpu.wav`) sounded much better and shifted review to the animation. Use its reference and settings as the working Krusty voice. The matching LEGO CPU take also completed; it has not been preferred by the user.

## Fromm production reference

The full short episode uses a separate 9.5-second Erich Fromm reference from his 1958 Mike Wallace interview. [The source record](../episodes/fromm/voice-reference.json) gives the archive URL, exact 232–241.5-second interval, processing, and hashes. [The production recipe](../episodes/fromm/README.md) documents saved takes and CPU synthesis.
