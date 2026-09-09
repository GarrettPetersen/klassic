"""A deterministic compositor with authored mouth transition cels at 24fps."""
import bisect
import html
import math
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .audio import executable, run
from .motion import CelTransitions, MouthTrack
from .cels import load_cel, load_transition_library
from .project import SHAPES, digest, load_episode, number, read_json, validate_cues, write_json


def load_build(build):
    build = Path(build)
    timeline = read_json(build / "timeline.json")
    if timeline["version"] != 1:
        raise ValueError("Unsupported timeline version")
    for file, key in (("dialogue.wav", "dialogue_sha256"), ("episode.json", "episode_sha256")):
        if digest(build / file) != timeline[key]:
            raise ValueError(f"{file} changed after preparation; prepare a new build")
    duration = number(timeline["duration"], "duration", 0.1)
    source_turns = load_episode(build / "episode.json")["turns"]
    if len(source_turns) != len(timeline["turns"]):
        raise ValueError("Timeline dialogue differs from the prepared script; prepare a new build")
    for original, timed in zip(source_turns, timeline["turns"]):
        if any(original[key] != timed[key] for key in ("id", "speaker", "text", "provenance")):
            raise ValueError("Timeline dialogue differs from the prepared script; prepare a new build")
    end = 0
    for turn in timeline["turns"]:
        if abs(turn["start"] - end) > 0.002 or turn["end"] <= turn["start"]:
            raise ValueError("Dialogue turns must be contiguous, including pauses")
        validate_cues(turn["cues"], turn["end"] - turn["start"])
        end = turn["end"] + turn["pause_after"]
    if abs(end - duration) > 0.002:
        raise ValueError("Dialogue timeline duration mismatch")
    end = 0
    for shot in timeline["shots"]:
        start = number(shot["start"], "shot.start")
        stop = number(shot["end"], "shot.end")
        if abs(start - end) > 0.002 or stop <= start or shot["camera"] not in {"wide", "host", "guest"}:
            raise ValueError("Shots must cover the full timeline without gaps or overlaps")
        end = stop
    if abs(end - duration) > 0.002:
        raise ValueError("Shots must cover the full timeline")
    return timeline


def mouth_shape(turn, at):
    local = at - turn["start"]
    if at >= turn["end"] or local < 0:
        return "X"
    starts = [cue["start"] for cue in turn["cues"]]
    index = bisect.bisect_right(starts, local) - 1
    if index < 0 or local >= turn["cues"][index]["end"]:
        return "X"
    return turn["cues"][index]["value"]


def draw_mouth(image, mouth, shape):
    """Small inked replacement cels drawn into a blank mouth region."""
    w, h = image.size
    x, y, width, height = mouth["x"] * w, mouth["y"] * h, mouth["w"] * w, mouth["h"] * h
    draw = ImageDraw.Draw(image)
    ink = max(2, round(w / 560))
    left, right = x - width / 2, x + width / 2
    if shape in "AX":
        draw.line([(left, y + 1), (x, y - 1), (right, y)], fill=15, width=ink)
        return
    if shape in "EF":
        scale = 0.52 if shape == "E" else 0.32
        draw.ellipse((x - width * scale / 2, y - 2, x + width * scale / 2, y + height * 0.8), fill=19, outline=8, width=ink)
        return
    opening = {"B": 0.27, "C": 0.68, "D": 1.0, "G": 0.25, "H": 0.7}[shape]
    bottom = y + height * opening
    polygon = [(left, y), (x, y - 2), (right, y), (right - width * .12, bottom - 1),
               (x, bottom + 2), (left + width * .13, bottom - 1)]
    draw.polygon(polygon, fill=18)
    draw.line(polygon + [polygon[0]], fill=10, width=ink, joint="curve")
    if shape in "BCDGH":
        teeth = min(5, height * opening * .48)
        draw.polygon([(left+ink, y+ink), (right-ink, y+ink), (right-width*.09, y+teeth), (left+width*.09, y+teeth)], fill=235)
    if shape == "H":
        draw.ellipse((x-width*.15, y+height*.22, x+width*.15, bottom), fill=145)
    if shape == "G":
        draw.line([(left+width*.15, bottom), (right-width*.15, bottom)], fill=150, width=ink)


def draw_smoke(image, tips, at):
    layer = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(layer)
    w, h = image.size
    for index, tip in enumerate(tips):
        x, y = tip[0] * w, tip[1] * h
        for trail in range(2):
            points = []
            for step in range(45):
                rise = step / 44
                px = x + math.sin(rise*8 - at*1.5 + index*2 + trail*.7) * (4 + rise*14)
                points.append((px + rise*8, y - rise*h*.15 - trail*8))
            draw.line(points, fill=(230, 230, 230, 80-trail*25), width=max(2, round(w/480)), joint="curve")
    image.paste(Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB"))


def subtitle_chunks(turn):
    # Turn-exact, proportional phrase timing; these are NOT forced-aligned words.
    lines = textwrap.wrap(turn["text"], width=46, break_long_words=False, break_on_hyphens=False)
    chunks = ["\n".join(lines[i:i+2]) for i in range(0, len(lines), 2)]
    weight = sum(len(chunk) for chunk in chunks)
    cursor = turn["start"]
    result = []
    for chunk in chunks:
        end = cursor + (turn["end"] - turn["start"]) * len(chunk) / weight
        result.append({"start": cursor, "end": end, "text": chunk})
        cursor = end
    return result


def srt_time(seconds):
    total = round(seconds * 1000)
    hours, total = divmod(total, 3600000)
    minutes, total = divmod(total, 60000)
    secs, millis = divmod(total, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


class Compositor:
    def __init__(self, timeline, rig_path, width):
        self.timeline = timeline
        self.rig_path = Path(rig_path).resolve()
        self.rig = read_json(rig_path)
        self.scene_path = self.rig_path.parent / self.rig["scene"]
        self.scene = Image.open(self.scene_path).convert("L")
        if abs(self.scene.width / self.scene.height - 4/3) > 0.005:
            raise ValueError("Master scene must have a 4:3 aspect ratio")
        self.poses = {}
        for name, pose in self.rig.get("poses", {}).items():
            image = Image.open(self.rig_path.parent / pose["scene"]).convert("L")
            if image.size != self.scene.size or not set(pose["hidden_mouths"]) <= {"host", "guest"}:
                raise ValueError(f"Pose {name} has wrong dimensions or unknown hidden mouths")
            self.poses[name] = image
        for shot in timeline["shots"]:
            if "pose" in shot:
                if shot["pose"] not in self.poses:
                    raise ValueError(f"Rig has no pose {shot['pose']}")
                hidden = self.rig["poses"][shot["pose"]]["hidden_mouths"]
                if any(t["speaker"] in hidden and t["start"] < shot["end"] and t["end"] > shot["start"] for t in timeline["turns"]):
                    raise ValueError("A drinking pose cannot cover the active speaker's mouth")
        if set(self.rig["mouths"]) != {"host", "guest"} or set(self.rig["cameras"]) != {"wide", "host", "guest"}:
            raise ValueError("Rig requires host/guest mouths and wide/host/guest cameras")
        for box in self.rig["cameras"].values():
            if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
                raise ValueError("Invalid normalized camera crop")
            if abs((box[2]-box[0])/(box[3]-box[1])-1) > .01:
                raise ValueError("Camera crop must preserve the 4:3 master aspect ratio")
        self.cels = {}
        self.transitions = {}
        self.transition_hashes = {}
        self.foregrounds = {}
        duration = max(s["end"] for s in timeline["shots"]) if timeline["shots"] else 0
        for speaker, mouth in self.rig["mouths"].items():
            if mouth["kind"] == "cels":
                if set(mouth["cels"]) != SHAPES:
                    raise ValueError(f"{speaker} needs a cel for every Rhubarb shape")
                box = mouth["box"]
                if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
                    raise ValueError(f"Invalid {speaker} cel box")
                rect = tuple(round(v*self.scene.size[i % 2]) for i, v in enumerate(box))
                cells = {}
                for shape, filename in mouth["cels"].items():
                    cel = load_cel(self.rig_path.parent / filename)
                    cells[shape] = cel.resize((rect[2]-rect[0], rect[3]-rect[1]), Image.Resampling.LANCZOS)
                self.cels[speaker] = (rect[:2], cells)
                motion = mouth["transitions"]
                span = number(motion["seconds"], "transitions.seconds", .001)
                if span > .2:
                    raise ValueError("Mouth transitions must be at most 200ms")
                pairs, self.transition_hashes[speaker] = load_transition_library(
                    self.rig_path.parent / motion["library"],
                    {s:self.rig_path.parent/f for s,f in mouth["cels"].items()}, cells["X"].size)
                self.transitions[speaker] = (MouthTrack(timeline["turns"], speaker, duration),
                                             CelTransitions(cells, pairs), span)
                layers = []
                for layer in mouth["foreground"]:
                    polygon = layer["polygon"]
                    if len(polygon) < 3 or any(len(point) != 2 or not all(0 <= v <= 1 for v in point) for point in polygon):
                        raise ValueError(f"Invalid {speaker} foreground polygon")
                    pixels = [(x*self.scene.width, y*self.scene.height) for x, y in polygon]
                    bounds = (math.floor(min(p[0] for p in pixels)), math.floor(min(p[1] for p in pixels)),
                              math.ceil(max(p[0] for p in pixels)), math.ceil(max(p[1] for p in pixels)))
                    mask = Image.new("L", ((bounds[2]-bounds[0])*4, (bounds[3]-bounds[1])*4))
                    ImageDraw.Draw(mask).polygon([((x-bounds[0])*4, (y-bounds[1])*4) for x, y in pixels], fill=255)
                    mask = mask.resize((bounds[2]-bounds[0], bounds[3]-bounds[1]), Image.Resampling.LANCZOS)
                    layers.append((bounds[:2], self.scene.crop(bounds), mask))
                self.foregrounds[speaker] = layers
            elif mouth["kind"] == "prototype":
                for key in ("x", "y", "w", "h"):
                    if not 0 < number(mouth[key], f"mouth.{key}") < 1:
                        raise ValueError("Mouth coordinates must be normalized within 0..1")
            else:
                raise ValueError(f"Unknown {speaker} mouth rig kind: {mouth['kind']}")
        if width < 320 or width % 8:
            raise ValueError("Width must be >=320 and divisible by 8 for even 4:3 output")
        self.width, self.height = width, width*3//4
        self.font = ImageFont.load_default(size=round(width / 37))
        self.small = ImageFont.load_default(size=round(width / 62))
        self.subtitles = [c for turn in timeline["turns"] for c in subtitle_chunks(turn)]
        self.turn_starts = [t["start"] for t in timeline["turns"]]
        self.shot_starts = [s["start"] for s in timeline["shots"]]

    def paint_cel(self, image, speaker, cel):
        position, _ = self.cels[speaker]
        image.paste(cel.convert("L"), position, cel.getchannel("A"))
        for offset, foreground, mask in self.foregrounds[speaker]:
            image.paste(foreground, offset, mask)

    def frame(self, at):
        shot = self.timeline["shots"][bisect.bisect_right(self.shot_starts, at)-1]
        pose = shot.get("pose")
        image = (self.poses[pose] if pose else self.scene).copy()
        hidden = self.rig["poses"][pose]["hidden_mouths"] if pose else []
        turn = self.timeline["turns"][bisect.bisect_right(self.turn_starts, at)-1]
        for speaker, mouth in self.rig["mouths"].items():
            if speaker in hidden:
                continue
            shape = mouth_shape(turn, at) if turn["speaker"] == speaker else "X"
            if mouth["kind"] == "cels":
                track, transitions, span = self.transitions[speaker]
                cel = transitions.frame(*track.sample(at, span))
                self.paint_cel(image, speaker, cel)
            else:
                draw_mouth(image, mouth, shape)
        draw_smoke(image, self.rig["cigarettes"], at)
        box = self.rig["cameras"][shot["camera"]]
        image = image.crop(tuple(round(v * image.size[i % 2]) for i, v in enumerate(box)))
        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(image)
        # Disclosure survives reposting and cropping of the surrounding post text.
        label = "FAN PARODY / AI ANIMATION" + (" / SCRATCH VOICES" if self.timeline["scratch"] else "")
        draw.rectangle((0, 0, self.width, round(self.width*.032)), fill=15)
        draw.text((self.width/2, 5), label, font=self.small, fill=220, anchor="mt")
        active = next((c for c in self.subtitles if c["start"] <= at < c["end"]), None)
        if active:
            text = active["text"]
            box = draw.multiline_textbbox((0, 0), text, font=self.font, spacing=5)
            height = box[3] - box[1] + 26
            draw.rectangle((0, self.height-height-8, self.width, self.height), fill=18)
            draw.multiline_text((self.width/2, self.height-height+2), text, font=self.font, fill=242, anchor="ma", align="center", spacing=5)
        return image.convert("RGB")


def render(build, rig, width=960):
    build = Path(build).resolve()
    timeline = load_build(build)
    comp = Compositor(timeline, rig, width)
    ffmpeg = executable("ffmpeg")
    final = build / "preview.mp4"
    temporary = build / "preview.partial.mp4"
    command = [ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size",
               f"{comp.width}x{comp.height}", "-framerate", "24", "-i", "pipe:0", "-i", str(build/"dialogue.wav"),
               "-map", "0:v:0", "-map", "1:a:0", "-af", "highpass=f=100,lowpass=f=6500,loudnorm=I=-16:TP=-1.5:LRA=7",
               "-c:v", "libx264", "-threads", "2", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24",
               "-c:a", "aac", "-b:a", "160k", "-t", str(timeline["duration"]), "-movflags", "+faststart", str(temporary)]
    with (build/"render.log").open("w+") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for index in range(math.ceil(timeline["duration"] * 24)):
                process.stdin.write(comp.frame(index/24).tobytes())
            process.stdin.close()
            code = process.wait()
            if code:
                log.seek(0)
                raise RuntimeError(f"ffmpeg render failed: {log.read()}")
        except BaseException:
            process.kill()
            process.wait()
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(final)
    captions = "\n\n".join(f"{i+1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}" for i, c in enumerate(comp.subtitles))
    (build/"captions.srt").write_text(captions + "\n")
    times = [(s["start"]+min(s["end"], s["start"]+2))/2 for s in timeline["shots"]]
    thumbnails = [comp.frame(at).resize((480, 360)) for at in times]
    sheet = Image.new("RGB", (960, math.ceil(len(thumbnails)/2)*390), (22,22,22))
    draw = ImageDraw.Draw(sheet)
    for i, (thumb, at) in enumerate(zip(thumbnails, times)):
        x, y = (i%2)*480, (i//2)*390
        sheet.paste(thumb, (x,y))
        draw.text((x+12, y+367), f"{at:.2f}s", fill="white", font=ImageFont.load_default(size=16))
    sheet.save(build/"contact-sheet.jpg")
    write_json(build/"render-manifest.json", {"rig_sha256": digest(rig), "scene_sha256": digest(comp.scene_path),
                "timeline_sha256": digest(build/"timeline.json"), "video_sha256": digest(final),
                "pose_sha256": {name: digest(comp.rig_path.parent / pose["scene"]) for name, pose in comp.rig.get("poses", {}).items()},
                "cel_sha256": {speaker: {shape: digest(comp.rig_path.parent / filename) for shape, filename in mouth["cels"].items()}
                               for speaker, mouth in comp.rig["mouths"].items() if mouth["kind"] == "cels"},
                "transitions": comp.transition_hashes,
                "animation_fps": 24, "output_fps": 24, "width": width, "height": comp.height,
                "ffmpeg_version": run([ffmpeg, "-version"]).splitlines()[0]})
    title, disclosure = html.escape(timeline["title"]), html.escape(timeline["disclosure"])
    rows = "".join(f"<tr><td>{t['start']:.2f}</td><td>{html.escape(t['speaker'])}</td><td>{html.escape(t['provenance'])}</td><td>{html.escape(t['text'])}</td></tr>" for t in timeline["turns"])
    (build/"review.html").write_text(f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title>
<style>body{{background:#181818;color:#eee;font:17px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px}}video,img{{width:100%;border-radius:4px}}h1{{font-family:Georgia}}td{{padding:10px;border-bottom:1px solid #555;vertical-align:top}}a{{color:#ddd}}</style>
<h1>{title}</h1><p>{disclosure}</p><p>Voice mode: {html.escape(timeline['voice_mode'])}. Phrase captions use proportional timing within each measured take.</p>
<video controls src="preview.mp4"></video><p><a href="captions.srt">Captions</a> · <a href="timeline.json">Editable camera timeline</a></p>
<table><thead><tr><th>Time</th><th>Speaker</th><th>Provenance</th><th>Dialogue</th></tr></thead><tbody>{rows}</tbody></table><p><img src="contact-sheet.jpg" alt="Camera cut contact sheet"></p></html>""")
    print(f"Rendered {final}")
