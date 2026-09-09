"""Strict input contracts. Dialogue stays verbatim after import."""
import hashlib
import json
import math
import re
from pathlib import Path

SPEAKERS = {"host", "guest"}
SHAPES = set("ABCDEFGHX")


def read_json(path):
    def invalid(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    return json.loads(Path(path).read_text(), parse_constant=invalid)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{label} must be a finite number >= {minimum}")
    return value


def keys(value, required, optional, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    missing, extra = set(required) - value.keys(), value.keys() - set(required) - set(optional)
    if missing or extra:
        raise ValueError(f"{label}: missing fields {sorted(missing)}, unknown fields {sorted(extra)}")


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")


def load_episode(path):
    episode = read_json(path)
    keys(episode, {"version", "title", "source", "disclosure", "turns"}, set(), "episode")
    if episode["version"] != 1:
        raise ValueError("Unsupported episode version")
    for key in ("title", "disclosure"):
        nonempty(episode[key], key)
    keys(episode["source"], {"url", "notes"}, set(), "source")
    for key in ("url", "notes"):
        nonempty(episode["source"][key], f"source.{key}")
    if not isinstance(episode["turns"], list) or not episode["turns"]:
        raise ValueError("Episode needs at least one dialogue turn")
    seen = set()
    for turn in episode["turns"]:
        keys(turn, {"id", "speaker", "text", "provenance", "pause_after"}, {"shot"}, "turn")
        if not isinstance(turn["id"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", turn["id"]) or turn["id"] in seen:
            raise ValueError("Turn IDs must be unique filename-safe strings")
        seen.add(turn["id"])
        if turn["speaker"] not in SPEAKERS:
            raise ValueError(f"Unknown speaker in {turn['id']}")
        if turn["provenance"] not in {"quotation", "original", "adaptation"}:
            raise ValueError("provenance must be quotation, original, or adaptation")
        nonempty(turn["text"], "turn.text")
        if len(turn["text"]) > 1000:
            raise ValueError(f"Split {turn['id']} into takes of at most 1000 characters before synthesis")
        number(turn["pause_after"], "pause_after")
        if turn.get("shot", "wide") not in SPEAKERS | {"wide"}:
            raise ValueError("shot must be wide, host, or guest")
    return episode


def import_transcript(text, host_label, guest_label):
    """Import label: text with continuation lines; reject unknown speakers."""
    labels = {host_label.casefold(): "host", guest_label.casefold(): "guest"}
    if len(labels) != 2 or not all(label.strip() for label in labels):
        raise ValueError("Host and guest labels must be distinct and nonempty")
    turns = []
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^([^:]{1,80}):\s*(.*)$", line)
        if match:
            label, content = match.groups()
            if label.casefold() not in labels:
                raise ValueError(f"Line {lineno}: unknown speaker {label!r}; edit moderator turns explicitly")
            turns.append({"id": f"t{len(turns)+1:03d}", "speaker": labels[label.casefold()], "text": content,
                          "provenance": "quotation", "pause_after": 0.45})
        elif not turns:
            raise ValueError(f"Line {lineno}: dialogue must start with a speaker label")
        else:
            turns[-1]["text"] += " " + line
    if not turns or any(not t["text"].strip() for t in turns):
        raise ValueError("Empty transcript or empty speaker turn")
    return turns


def validate_cues(cues, duration):
    if not isinstance(cues, list) or not cues:
        raise ValueError("Rhubarb returned no mouth cues")
    previous = 0
    for cue in cues:
        keys(cue, {"start", "end", "value"}, set(), "mouth cue")
        start = number(cue["start"], "cue.start")
        end = number(cue["end"], "cue.end")
        if start < previous - 0.001 or end <= start or end > duration + 0.03 or cue["value"] not in SHAPES:
            raise ValueError(f"Invalid or overlapping mouth cue: {cue}")
        previous = end


def make_shots(turns, duration):
    """Use measured audio times. Never cut in the middle of a short reply."""
    shots = []
    for index, turn in enumerate(turns):
        start, end = turn["start"], turn["end"] + turn["pause_after"]
        camera = turn.get("shot", "wide" if index == 0 else turn["speaker"])
        if "shot" not in turn and turn["speaker"] == "guest" and end - start > 7 and index % 3 == 1:
            shots.extend([
                {"start": start, "end": start + 4, "camera": "guest"},
                {"start": start + 4, "end": start + 6, "camera": "host", "pose": "host_sip"},
                {"start": start + 6, "end": end, "camera": "guest"},
            ])
        elif "shot" not in turn and end - start > 12:
            shots.extend([
                {"start": start, "end": start + 7, "camera": camera},
                {"start": start + 7, "end": start + 8.5, "camera": "guest" if turn["speaker"] == "host" else "host"},
                {"start": start + 8.5, "end": end, "camera": camera},
            ])
        else:
            shots.append({"start": start, "end": end, "camera": camera})
    shots[-1]["end"] = duration
    return shots
