# Production workflow revisions

Implemented the drawing-based game foundation and revised the workflow around
independent acceptance, authoritative sources and a small seated reference.

- Individual drawings and deterministic atlas exports.
- Separate drawing, body pose, exact face case, timed clip, scene and performance
  review records, with source-bound stale detection and PNG proofs.
- Registration editing through pointer drag or coordinates, linked whole-arm and
  neck/face bindings, undo/redo and checked before/after patches.
- Canonical character and scene packages; explicit import proposals compare old
  exporter output before any source replacement.
- A fixed-body Adrian seated reference with three whole-arm cels, intact chair
  contact and same-pixel far-arm depth masks.
- Path planning over authored strides, steps, stopping/approach actions and turns;
  the arrival study includes a short stop and ends facing the camera.
- One timeline for choices, movement, gaze, captions and speech starts/stops/seeks;
  version-2 saves and recordings restore and replay audio positions.

The original seated cast still exercises mouth variants, blinking, audience gaze,
whole-arm gestures and combined torso/leg poses. Adrian's seated reference is the
small animation target; his wider walking study remains draft until alternate
footfalls and planted-foot registration receive another art pass. No voice or
face overlays have been authored for Adrian yet.

Commands, review requirements and limitations: [production workflow](production-workflow.md).

Verification: 53 Python tests and 26 JavaScript tests passed, along with the
interview, production and revision browser suites. Browser checks include actual
pointer dragging after an error, patch export/undo, distinct approval scopes,
audio seek/replay, saved spoken lines, mobile layout, and the complete arrival.
Three seated body poses and the offering clip have specific Codex visual reviews;
the seated reference composition has its own project review. Other subjects keep
their existing unreviewed status. These approvals are not a release approval for
the whole Adrian package.
