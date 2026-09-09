# The personality market

A second host-only animation example with original dialogue, not an archival quotation. It uses the accepted Cartoon Studio Krusty reference and the complete authored mouth-transition library.

Saved take: `voices/takes/voice-test-02/t001.wav` (ignored), with the synthesis parameters and reference/audio hashes in its adjacent JSON. CPU synthesis uses two compute threads, CFG 0.7, exaggeration 0.3, temperature 0.8, seed 42.

```sh
python3 -m klassic prepare episodes/voice-test-02/episode.json \
  --voice-mode files --takes voices/takes/voice-test-02 \
  --rhubarb .tools/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb \
  --out build/voice-test-02
python3 -m klassic render build/voice-test-02 --rig assets/rig.json --width 1440
```

Preparation requires a new build directory; rendering can be repeated after camera edits. The takes and built video remain local. Source art, episode text, and transition library are retained in the repository.
