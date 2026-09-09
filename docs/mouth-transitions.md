# Authored mouth transitions

Krusty's nine Rhubarb mouth poses now have **36 unordered transition pairs, with two new drawings per pair**. That is 72 in-between cels plus the nine original keys. Reversing the two cels covers all 72 directed changes. This library is registered to the current Krusty angle. Guests can reuse its general shapes and movement with character-specific proportions, skin fill, and silhouette masks; a new head angle needs matching artwork.

Playback selects saved PNGs. The renderer contains no mesh warp, optical flow, image morph, or crossfade. The fixed nose layer is composited above every mouth drawing.

## Artwork and generation

The built-in imagegen tool generated nine 4×4 sheets. Each row contains a source key, two in-betweens, and a target key. Only the middle columns are used; the source endpoint PNGs are used directly. The green background is removed, then each new cel gets one uniform scale and translation onto the common 418×418 canvas. This registration does not squeeze individual teeth, lips, or jaw regions.

- Production mapping: `assets/mouths/transitions/spec.json`.
- Reference guides and generated source sheets: `assets/mouths/transitions/atlases/`.
- Registered deliverables and hash manifest: `assets/mouths/transitions/cels/`.
- Exact prompts: `prompts/krusty-transitions-01.txt` through `09.txt`; each uses the matching `guide-01.png` through `guide-09.png` as its edit target.
- The earlier source-only B sheet confused several requested pairs; its prompt is retained as `krusty-transitions-draft.txt`, and the discarded image is in ignored `build/`. It is not used in playback.

The generated set is an initial complete drawing library, not a claim of final animation approval. Inspect transitions in context before a longer film. Lip rounding and teeth/tongue occlusion deserve special attention; a mathematically intermediate pixel shape does not establish good anatomy. The reusable library makes those corrections local and reviewable.

## Rebuild and review

Baking requires a new output directory. No generation service runs during baking or rendering.

```sh
python3 -m klassic bake-transitions assets/mouths/transitions/spec.json \
  --out build/rebaked-transitions
python3 -m klassic review-transitions --rig assets/rig.json \
  --out build/transition-review-new
python3 -m klassic render build/mouth-study-v2 --rig assets/rig.json --width 960
```

To adopt revised artwork, edit the appropriate guide with the saved prompt, save the resulting sheet, and bake a new library. Point `mouths.host.transitions.library` in `assets/rig.json` at that new manifest. Asset paths in the rig are relative to the rig file; image paths in the manifest are relative to the manifest. Both endpoint and transition hashes are verified before rendering. Missing pairs and changed inputs fail explicitly.

`review-transitions` produces a local HTML flipbook with all 36 pairs, four drawings per row, forward/reverse playback, normal/quarter speed, and a frame slider. Its facial composites use the same mouth/nose compositor as the film. The current review is `build/transition-review/index.html`, and the revised 8.71-second voice test is `build/mouth-study-v2/preview.mp4`.

## Timing

Frames are rendered at 24 fps. Within speech, a transition anticipates the next phoneme and reaches its exact key pose on the cue boundary. Rest (`X`) holds are different: closing finishes by the start of the pause, and opening begins only after the next speech cue starts. The default window is at most 90 ms, limited to half of each neighboring cue's duration. Short syllables can show one intermediate or none at the available frame cadence. Do not lengthen the audio merely to force all drawings into every transition.

Preparation also checks the actual normalized audio: continuous samples below −35 dBFS for at least 120 ms become closed resting cues, overriding recognizer mistakes such as teeth-apart `B` during a quiet phrase break. Short consonant gaps remain untouched. This fixed threshold is tuned for the current clean studio takes; noisy source recordings require separate evaluation. Raw Rhubarb output remains in each take's `.mouth.json`; the timeline records detector settings, measured silence intervals, and corrected cues. Re-prepare existing takes to apply this correction.

The pause-corrected example is `build/voice-test-02-pauses/preview.mp4`. Its audio is byte-identical to the preceding example. All 41 rendered frame times inside the five measured take silences select the exact closed `X` cel; the added tail pause stays closed as well. `pause-check.jpg` shows the main gaps before and after the timing correction.

The review flipbook gives each key six frames and each intermediate one frame for inspection; its loop is not the speech timing. Reversible cels are the current production choice. A future performance requiring different opening and closing acting would need separately authored directional drawings and an explicit format change.


## Rounded-mouth correction

The initial E and F drawings accidentally kept a projecting upper-lip shelf above a second rounded lip. Both keys were redrawn with a single smooth convex muzzle contour flowing into the only upper lip. Their 15 connected pairs were regenerated (30 in-betweens); the other 42 in-betweens are byte-identical.

The corrected key atlas, provenance, four endpoint guides, and four transition sheets are in `assets/mouths/rounded-correction/`. Exact built-in imagegen prompts are saved as `prompts/krusty-rounded-key-correction.txt` and `prompts/krusty-rounded-transitions-01.txt` through `04.txt`. The production spec selects the corrected rows and retains unrelated original rows; `null` explicitly marks unused rows in a four-row sheet. The active baked library remains `assets/mouths/transitions/cels/library.json`.

The new example is `build/voice-test-02/preview.mp4` (12.95 seconds, 1440×1080, 24 fps), with fresh original dialogue about the personality market. The same Cartoon Studio reference and accepted settings generated its new voice take. A local Whisper small.en transcription matched every spoken word. `build/transition-review/index.html` now shows the corrected artwork.
