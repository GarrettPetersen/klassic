> Superseded by [revision 07](../revision-07/README.md). The separate hand/cuff joins in this prototype looked pasted on; the active rig uses complete arms attached at the shoulders. This page records the earlier experiment.

# Discrete hand poses and separate pupils

[Motion preview](../../../build/fromm-full-04/motion-preview.mp4) ·
[Pose and video review](../../../build/fromm-full-04/review.html)

This revision replaces the revision-03 hand sway with held drawings: relaxed,
turn, palm-up, outward sweep, and return. Each cigarette hand also has a
palm-up/cigarette-down drawing. The cigarette sits between the index and middle
fingers. All 18 new hand drawings were visually checked for **three fingers and
one thumb**, four digits total. Two five-digit Fromm poses were corrected before
extraction. The rejected atlas remains as a production source, but is not loaded
by the rig. The existing cup-holding cutaway was also inspected.

The runtime switches drawings at authored keys; it interpolates only the elbow
rotation. Holds have constant joint values. Gestures occupy short conversational
beats, with long rests between them. Leaning also holds its target instead of
continually oscillating. The performance covers all 119 existing turns.

Both faces now use generated pupil-free eye plates. Separate pupil layers are
clipped to the eye interiors; eyelids close over those layers. Krusty's intro and
outro gaze uses the same pupil layer. No old pupil is erased at runtime.

The 54.292-second preview contains six film excerpts: opening gesture; teaser,
title and welcome; Krusty's cigarette gesture; Fromm's free-hand gesture;
Fromm's cigarette gesture; and the closing audience address. The picture is
1440×1080 at 24 fps, with the revision-02 caption design. The title music and
archival noise mix come from the existing film. No voice take was regenerated.
The full exported interview remains revision 02; this is the current animation
review cut, not a replacement full-film export.

## Assets and registration

Image generation used the built-in `image_gen` tool. Every successful prompt is
saved beside this file. Source and generated files live in
`assets/episodes/fromm-v4/`; the registered pose libraries are `host-free/`,
`host-cigarette/`, `guest-free/`, and `guest-cigarette/`. Their manifests record
source hashes, cuff anchors and scale. `source.json` records the selected assets
and the visual digit audit. No runtime path points outside the repository.

The green matte calculation retains partially covered black contour pixels.
Registration scales each whole drawing uniformly to its reference cuff and
attaches it at the wrist. Cuffs close over the original sleeve; small native
jacket overlap panels fill areas exposed by the removed hands. The body remains
a limited cutout rig, rather than a fully redrawn set of torso poses.

## Rebuild

The shared renderer now uses the complete-arm format. Use the [revision-07 rebuild commands](../revision-07/README.md). The revision-04 builder remains the offline source for the reused eye plates and background masks.

The experimental accent listening review and its limitations remain documented
in [revision 03](../revision-03/README.md). Automatic accent rejection is disabled:
the small calibration set did not consistently distinguish the known drift.
