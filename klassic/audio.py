"""Local take production and phoneme timing; no silent provider substitution."""
import shutil
import math
import subprocess
import tempfile
import wave
import array
import sys
from pathlib import Path

from .project import digest, load_episode, make_shots, read_json, validate_cues, write_json
from .motion import close_pauses

RATE = 48000
SILENCE_SETTINGS = {"threshold_dbfs": -35, "minimum_seconds": 0.12}


def detect_pauses(frames, threshold_dbfs=-35, minimum_seconds=0.12):
    """Find sustained below-threshold PCM runs, leaving short consonant gaps alone."""
    if not frames or len(frames) % 2:
        raise ValueError("Pause detection needs nonempty 16-bit PCM")
    if not math.isfinite(threshold_dbfs) or threshold_dbfs >= 0:
        raise ValueError("Silence threshold must be finite and below 0 dBFS")
    if not math.isfinite(minimum_seconds) or minimum_seconds <= 0:
        raise ValueError("Minimum silence duration must be finite and positive")
    samples = array.array("h", frames)
    if sys.byteorder != "little":
        samples.byteswap()
    threshold = 32768 * 10 ** (threshold_dbfs / 20)
    minimum = math.ceil(minimum_seconds * RATE)
    pauses, start = [], None
    for index, sample in enumerate(samples):
        if abs(sample) < threshold:
            if start is None:
                start = index
        elif start is not None:
            if index-start >= minimum:
                pauses.append({"start": start/RATE, "end": index/RATE})
            start = None
    if start is not None and len(samples)-start >= minimum:
        pauses.append({"start": start/RATE, "end": len(samples)/RATE})
    return pauses


def executable(name):
    found = shutil.which(str(name))
    if not found:
        raise ValueError(f"Required executable not found: {name}")
    return found


def run(args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}):\n{result.stderr[-4000:]}")
    return result.stdout


def pcm(path):
    with wave.open(str(path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, RATE):
            raise ValueError(f"Expected mono 16-bit {RATE} Hz WAV: {path}")
        frames = audio.readframes(audio.getnframes())
    if not frames:
        raise ValueError(f"Empty audio file: {path}")
    return frames


def make_synthesizer(mode, config, device):
    if mode == "macos":
        say = executable("say")
        def synth(turn, target):
            # stdin prevents transcript text becoming flags or shell code.
            result = subprocess.run([say, "-v", config[turn["speaker"]]["voice"], "-r", "155", "-o", str(target)],
                                    input=turn["text"], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"macOS scratch voice failed: {result.stderr}")
        return synth
    if mode == "chatterbox":
        import torch
        import torchaudio
        from chatterbox.tts import ChatterboxTTS
        if device == "cpu":
            torch.set_num_threads(2)
        if device == "mps" and not torch.backends.mps.is_available():
            raise ValueError("MPS was requested but is unavailable")
        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA was requested but is unavailable")
        torch.manual_seed(42)
        model = ChatterboxTTS.from_pretrained(device=device)
        def synth(turn, target):
            voice = config[turn["speaker"]]
            torch.manual_seed(voice.get("seed", 42))
            wav = model.generate(turn["text"], audio_prompt_path=voice["reference"],
                                 exaggeration=voice.get("exaggeration", 0.35), cfg_weight=voice.get("cfg_weight", 0.5),
                                 temperature=voice.get("temperature", 0.8))
            torchaudio.save(str(target), wav.cpu(), model.sr)
        return synth
    if mode == "xtts":
        from TTS.api import TTS
        model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        def synth(turn, target):
            model.tts_to_file(text=turn["text"], speaker_wav=config[turn["speaker"]]["reference"],
                              language="en", file_path=str(target))
        return synth
    raise ValueError(f"Unsupported voice mode: {mode}")


def audition(text, reference, output, device="cpu", exaggeration=0.3, cfg_weight=0.5, temperature=0.8, seed=42):
    reference, output = Path(reference).resolve(), Path(output).resolve()
    if not reference.is_file():
        raise ValueError(f"Missing voice reference: {reference}")
    if not text.strip() or len(text) > 1000:
        raise ValueError("Audition text must contain 1–1000 characters")
    if output.suffix.lower() != ".wav" or output.exists():
        raise ValueError("Choose a new WAV output path")
    settings = {"exaggeration": exaggeration, "cfg_weight": cfg_weight, "temperature": temperature, "seed": seed}
    for name, low, high in (("exaggeration", 0, 2), ("cfg_weight", 0, 1), ("temperature", 0.05, 2)):
        if not math.isfinite(settings[name]) or not low <= settings[name] <= high:
            raise ValueError(f"{name} must be finite and between {low} and {high}")
    if not 0 <= seed < 2**32:
        raise ValueError("seed must be between 0 and 2**32 - 1")
    output.parent.mkdir(parents=True, exist_ok=True)
    synth = make_synthesizer("chatterbox", {"host": {"reference": str(reference), **settings}}, device)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        wav = Path(temporary)/"audition.wav"
        synth({"speaker": "host", "text": text}, wav)
        # Verify a decodable, nonempty take before publishing it.
        normalized = Path(temporary)/"normalized.wav"
        run([executable("ffmpeg"), "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le", normalized])
        pcm(normalized)
        normalized.replace(output)
    write_json(output.with_suffix(".json"), {"text": text, "backend": "chatterbox", "device": device,
        "reference_sha256": digest(reference), "audio_sha256": digest(output), "settings": settings,
        "cpu_compute_threads": 2 if device == "cpu" else None, "synthetic": True})
    print(f"Generated voice audition: {output}")


def prepare(episode_path, out, mode, rhubarb, voices=None, takes=None, device="cpu", scratch=False):
    episode_path, out = Path(episode_path).resolve(), Path(out).resolve()
    episode = load_episode(episode_path)
    ffmpeg, rhubarb = executable("ffmpeg"), executable(rhubarb)
    if out.exists():
        raise ValueError(f"Output already exists: {out}. Use a new take directory.")
    config = {}
    if mode == "files":
        if not takes:
            raise ValueError("--takes DIR is required for files mode")
        for turn in episode["turns"]:
            if not (Path(takes) / f"{turn['id']}.wav").is_file():
                raise ValueError(f"Missing take: {turn['id']}.wav")
    else:
        if not voices:
            raise ValueError("--voices JSON is required for synthesized voices")
        config = read_json(voices)
        if set(config) != {"host", "guest"}:
            raise ValueError("Voices file must contain exactly host and guest")
        for speaker, voice in config.items():
            required = "voice" if mode == "macos" else "reference"
            if required not in voice or not isinstance(voice[required], str) or not voice[required].strip():
                raise ValueError(f"{speaker} needs {required}")
            if mode != "macos":
                path = (Path(voices).resolve().parent / voice["reference"]).resolve()
                if not path.is_file():
                    raise ValueError(f"Missing voice reference: {path}")
                voice["reference"] = str(path)
        synth = make_synthesizer(mode, config, device)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".klassic-", dir=out.parent) as temporary:
        work = Path(temporary)
        turns, sample_count = [], 0
        with wave.open(str(work / "dialogue.wav"), "wb") as mix:
            mix.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            for turn in episode["turns"]:
                print(f"Preparing {turn['id']} ({turn['speaker']})", flush=True)
                if mode == "files":
                    raw = Path(takes) / f"{turn['id']}.wav"
                else:
                    raw = work / ("raw.aiff" if mode == "macos" else "raw.wav")
                    synth(turn, raw)
                wav = work / f"{turn['id']}.wav"
                run([ffmpeg, "-v", "error", "-y", "-i", raw, "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le", wav])
                frames = pcm(wav)
                length = len(frames) // 2
                if length / RATE < 0.1:
                    raise ValueError(f"Suspiciously short take: {turn['id']}")
                dialog = work / f"{turn['id']}.txt"
                dialog.write_text(turn["text"])
                cue_path = work / f"{turn['id']}.mouth.json"
                run([rhubarb, "-r", "pocketSphinx", "-f", "json", "--extendedShapes", "GHX", "--threads", "2",
                     "-d", dialog, "-o", cue_path, wav])
                cues = read_json(cue_path)["mouthCues"]
                validate_cues(cues, length / RATE)
                silences = detect_pauses(frames, **SILENCE_SETTINGS)
                cues = close_pauses(cues, silences, length / RATE)
                validate_cues(cues, length / RATE)
                pause = round(turn["pause_after"] * RATE)
                turns.append({**turn, "start": sample_count / RATE, "end": (sample_count + length) / RATE,
                              "pause_after": pause / RATE, "cues": cues, "silences": silences})
                mix.writeframes(frames)
                mix.writeframes(b"\x00\x00" * pause)
                sample_count += length + pause
        duration = sample_count / RATE
        metadata = {"version": 1, "title": episode["title"], "disclosure": episode["disclosure"],
                    "source": episode["source"], "voice_mode": mode, "scratch": mode == "macos" or scratch,
                    "episode_sha256": digest(episode_path), "dialogue_sha256": digest(work / "dialogue.wav"),
                    "duration": duration, "turns": turns, "shots": make_shots(turns, duration),
                    "silence_detection": {"method": "pcm_peak_runs", **SILENCE_SETTINGS},
                    "voice_references": {s: digest(v["reference"]) for s, v in config.items() if "reference" in v},
                    "rhubarb_version": run([rhubarb, "--version"]).strip()}
        write_json(work / "timeline.json", metadata)
        shutil.copyfile(episode_path, work / "episode.json")
        # Publish only a complete build. Interrupted synthesis leaves no stale timeline.
        work.rename(out)
    print(f"Prepared {duration:.2f}s in {out}")
