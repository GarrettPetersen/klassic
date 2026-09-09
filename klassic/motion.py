"""Speech timing and playback of authored, character-local transition cels."""
import bisect
import math

from itertools import combinations

from .project import SHAPES


def close_pauses(cues, pauses, duration):
    """Overlay measured quiet intervals on recognizer cues; preserve speech shapes."""
    previous = 0.0
    for pause in pauses:
        start, end = pause["start"], pause["end"]
        if not (math.isfinite(start) and math.isfinite(end) and previous <= start < end <= duration):
            raise ValueError("Silences must be ordered, non-overlapping and inside the take")
        previous = end
    boundaries = sorted({0.0, duration} | {
        max(0.0, min(duration, item[key]))
        for item in [*cues, *pauses] for key in ("start", "end")})
    result = []
    for start, end in zip(boundaries, boundaries[1:]):
        at = (start+end)/2
        silent = any(p["start"] <= at < p["end"] for p in pauses)
        shape = "X" if silent else next((c["value"] for c in cues if c["start"] <= at < c["end"]), "X")
        if result and result[-1]["value"] == shape:
            result[-1]["end"] = end
        else:
            result.append({"start": start, "end": end, "value": shape})
    return result



class MouthTrack:
    def __init__(self, turns, speaker, duration):
        self.segments = []
        cursor = 0.0
        for turn in turns:
            if turn["speaker"] != speaker:
                continue
            for cue in turn["cues"]:
                start, end = turn["start"]+cue["start"], turn["start"]+cue["end"]
                if start > cursor:
                    self._append(cursor, start, "X")
                self._append(start, end, cue["value"])
                cursor = end
        if cursor < duration:
            self._append(cursor, duration, "X")
        self.starts = [s[0] for s in self.segments]

    def _append(self, start, end, shape):
        if end <= start:
            return
        if self.segments and self.segments[-1][2] == shape and abs(self.segments[-1][1]-start) < 1e-6:
            previous = self.segments.pop()
            start = previous[0]
        self.segments.append((start, end, shape))

    def sample(self, at, transition_seconds):
        """Close by a pause boundary; begin opening only after speech resumes."""
        index = bisect.bisect_right(self.starts, at)-1
        if index < 0 or at >= self.segments[-1][1]:
            return "X", "X", 0.0
        start, end, shape = self.segments[index]
        if shape == "X":
            return "X", "X", 0.0
        if index > 0 and self.segments[index-1][2] == "X":
            span = min(transition_seconds, (end-start)*.5)
            if span > 0 and at < start+span:
                progress = (at-start)/span
                return "X", shape, progress*progress*(3-2*progress)
        if index+1 == len(self.segments):
            return shape, shape, 0.0
        next_start, next_end, target = self.segments[index+1]
        span = min(transition_seconds, (end-start)*.5, (next_end-next_start)*.5)
        if span <= 0 or at <= end-span:
            return shape, shape, 0.0
        progress = (at-(end-span))/span
        return shape, target, progress*progress*(3-2*progress)


class CelTransitions:
    """Select saved inked drawings; never warp, morph, or crossfade artwork."""
    def __init__(self, cells, pairs):
        expected = {"".join(pair) for pair in combinations(sorted(SHAPES), 2)}
        if set(cells) != SHAPES:
            raise ValueError("Transition endpoints must cover every mouth shape")
        if set(pairs) != expected:
            raise ValueError(f"Transition library must cover all 36 pairs; missing={sorted(expected-set(pairs))}, unexpected={sorted(set(pairs)-expected)}")
        size = cells["X"].size
        for pair, frames in pairs.items():
            if len(frames) != 2:
                raise ValueError(f"Transition {pair} needs two authored in-between cels")
            if any(cel.mode != "RGBA" or cel.size != size for cel in frames):
                raise ValueError(f"Transition {pair} must match endpoint canvas and alpha mode")
        self.cells, self.pairs = cells, pairs

    def frame(self, source, target, progress):
        if source not in SHAPES or target not in SHAPES:
            raise ValueError("Unknown mouth shape")
        if not math.isfinite(progress) or not 0 <= progress <= 1:
            raise ValueError("Transition progress must be within 0..1")
        if source == target or progress == 0:
            return self.cells[source]
        if progress == 1:
            return self.cells[target]
        pair = "".join(sorted((source, target)))
        frames = self.pairs[pair]
        if source != pair[0]:
            frames = frames[::-1]
        # Two intervals for two drawings. Cue timing holds the source before
        # this interval and puts the exact target on its phoneme boundary.
        return frames[0 if progress < .5 else 1]
