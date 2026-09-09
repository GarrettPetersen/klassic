# Production workflow

## 1. Lock the excerpt

Store the input in ignored `inputs/`, with a source URL and page or time range. Correct OCR against the source. Mark speaker changes yourself; stage directions, announcers, and examiners must not become somebody else's dialogue. Import a small excerpt and preserve the text in the episode JSON. Record deliberate edits using each turn's `provenance`.

The initial target is a single coherent 60–90 second exchange. Long episodes multiply the amount of audio and visual quality control. A short excerpt is an editorial choice, not a universal copyright safe harbor.

## 2. Build reusable art once

Generate the master set, then derive all poses and angles from that approved master. Reuse the saved prompts. The base must have clean replacement regions. For Krusty, remove the fixed muzzle and jaw silhouette so whole muzzle cels can move over a clean plate. For each guest, define the replacement region from that person's own lip, cheek, and chin construction. See [character design](character-design.md). Fit `assets/rig.json` to the actual output; do not assume generated coordinates will match the prompt.

Current asset contract:

| Asset | Purpose |
| --- | --- |
| `set-master.png` | Original closed-mouth design reference |
| `set-rig.png` | Clean plate with Krusty's fixed muzzle removed |
| `host-sip.png` | Matching full-scene listening pose, mouth covered by mug |
| `rig.json` | Normalized mouth locations, camera crops, cigarette tips, pose bindings |

Full-scene pose replacements are intentional at this prototype stage. Changes happen across cuts, avoiding visible arm teleportation. For a more elaborate production, commission or generate separate close-up views and three arm cels (rest, lift, sip), then register each mouth and prop position. The current renderer does not pretend to interpolate an arm, turn a head, or create unseen views.

## 3. Direct the voices

**Host:** a tired, gravelly show-business baritone, deliberate phrasing, slightly pinched nasal resonance. In this setting Krusty wants to be taken seriously. Use the isolated game-line reference described in [voice sourcing](voice-sourcing.md), then direct the synthesized delivery. Simply pitch-shifting a generic TTS voice will not reliably produce the character.

**Guest:** measured, articulate, distinct from the host. For Fromm, aim for calm, deliberate delivery with a light German accent; verify the performance against the source interview. A substitute performance should be described as a recreated guest voice, not authenticated historical audio.

Use roughly 10–20 seconds of clean, dry reference speech per voice as an audition starting point. No music, another speaker, laughter track, or strong room echo. Quality matters more than accumulating noisy clips. Audition the same few lines with both voices before generating the full script. The `reference` command prepares explicitly selected game lines and records their provenance.

[Chatterbox's official repository](https://github.com/resemble-ai/chatterbox) documents reference-conditioned generation and expressive controls; its [license](https://github.com/resemble-ai/chatterbox/blob/master/LICENSE) is MIT. The adapter uses `ChatterboxTTS` for English and exposes per-voice exaggeration and CFG settings. Install the model in a separate environment using its official instructions. Chatterbox 0.1.7 has generated a Krusty audition on this machine using MPS. Speech recognition recovered its requested words; that does not validate voice likeness. macOS scratch and supplied WAV modes are separate, explicit paths.

[XTTS documentation](https://coqui-tts.readthedocs.io/en/latest/models/xtts.html) provides the reference-WAV workflow used by the optional adapter. Its [model license](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt) restricts commercial use of the model and outputs. That makes it a less convenient default for a project that might eventually be monetized. Model licensing does not grant rights to a character, a performance, or a source recording.

Generate one turn at a time, listen, and keep takes. If TTS mispronounces a term, make an explicit speech-script correction or rerecord the take; do not silently alter the historical transcript. For final delivery, the `files` mode makes an edited set of approved WAVs the source of truth. Re-run timing after any audio edit.

## 4. Time and animate

The workflow normalizes speech to mono 48 kHz PCM, measures each take, and adds deliberate inter-turn pauses. [Rhubarb](https://github.com/DanielSWolf/rhubarb-lip-sync) analyzes each take with its dialogue text as a recognition aid. Its A–F shapes plus G/H/X select the replacement mouth drawings. Quiet gaps use the closed resting shape. This is phoneme-driven timing, not a volume meter opening and closing a mouth.

The compositor renders at 24 fps, selecting original keys and saved in-between cels from the complete 36-pair Krusty library. It anticipates cue boundaries while preserving closure holds. See [authored mouth transitions](mouth-transitions.md) for baking and visual review. Edit the JSON cues when a syllable looks wrong. Inspect labial closures, rounded vowels, and the first/last consonants. Krusty now uses registered PNG muzzle/jaw cels based on the original neutral chart. The guest sketch still uses a clearly marked prototype. Each historical guest needs an independent portrait and cel set; no guest inherits Krusty's muzzle.

Use wide setup, speaker close-ups, and occasional listening cutaways. The pilot automatically places a sip on an eligible long guest turn. A speaker cannot sip over their own dialogue. Camera shots are editable, so repeat gestures less often in a longer episode. Smoke is drawn as independent moving wisps rather than regenerated with every frame.

## 5. Review and finish

`review.html` puts the film, transcript provenance, timing, and contact sheet together. Captions follow measured take boundaries, with proportional phrase timing inside a take. Word-level forced alignment is a future improvement; check caption changes by eye.

Watch the whole export. Listen for missing/extra words, repetition, distorted consonants, and inconsistent guest identity. Check that the quiet character's mouth stays closed; the mug isn't duplicated; the speaking character never has a covered mouth; the captions are readable; and no cut reveals mismatched props.

The export is 4:3 H.264/AAC with a modest radio-like filter and loudness normalization. Keep any final film dirt restrained. A stable drawing with authentic pacing matters more than fake VHS damage. For true broadcast polish, add authored blinks, a few gaze changes, further direction of the authored mouth transitions, and dedicated angle drawings before adding more motion.

## Reproducibility

Prepared builds retain normalized takes, recognition outputs, script snapshots, and hashes. Rendering uses saved assets and timing; re-rendering does not regenerate voices or pictures. Neural synthesis has a seed but is not guaranteed bit-identical across backends/model versions. Record your voice environment with `pip freeze` and the exact model revision before producing a final batch.
