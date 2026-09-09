"""Build a reproducible voice reference from explicitly selected game clips."""
import array
import math
import tempfile
import wave
import zipfile
from pathlib import Path

from .audio import executable, run
from .project import digest, write_json


def build_reference(archive, clips, output, source_url):
    archive, output = Path(archive), Path(output)
    if output.exists() or output.with_suffix(".source.json").exists():
        raise ValueError(f"Reference output already exists: {output}")
    if output.suffix.lower() != ".wav":
        raise ValueError("Reference output must be a WAV file")
    if not clips or len(set(clips)) != len(clips):
        raise ValueError("Choose distinct archive clip names in performance order")
    ffmpeg = executable("ffmpeg")
    rate = 24000
    joined = array.array("h")
    sources = []
    with zipfile.ZipFile(archive) as pack, tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        for index, name in enumerate(clips):
            # Read only explicitly selected audio; never extract arbitrary archive paths.
            if Path(name).suffix.lower() not in {".ogg", ".wav", ".mp3", ".flac"}:
                raise ValueError(f"Not an audio clip: {name}")
            if pack.namelist().count(name) != 1:
                raise ValueError(f"Missing or duplicate archive member: {name}")
            raw = directory / f"source-{index}{Path(name).suffix}"
            raw.write_bytes(pack.read(name))
            wav = directory / f"decoded-{index}.wav"
            run([ffmpeg, "-v", "error", "-y", "-i", raw, "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", wav])
            with wave.open(str(wav), "rb") as reader:
                samples = array.array("h", reader.readframes(reader.getnframes()))
            if len(samples) < rate*.3 or max(map(abs, samples), default=0) < 100:
                raise ValueError(f"Empty, silent, or too-short reference clip: {name}")
            start = len(joined)/rate
            joined.extend(samples)
            sources.append({"member": name, "sha256": digest(raw), "start": start, "end": len(joined)/rate})
            if index < len(clips)-1:
                joined.extend([0]*round(rate*.18))
    duration = len(joined)/rate
    if not 3 <= duration <= 30:
        raise ValueError(f"Reference is {duration:.2f}s; select 3–30 seconds of speech")
    peak = max(map(abs, joined))
    gain = (32767 * 10**(-3/20))/peak
    normalized = array.array("h", (round(s*gain) for s in joined))
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(normalized.tobytes())
    write_json(output.with_suffix(".source.json"), {
        "source_url": source_url, "archive_sha256": digest(archive), "reference_sha256": digest(output),
        "sample_rate": rate, "duration": duration, "gain_db": 20*math.log10(gain), "clips": sources,
        "processing": "Mono PCM16 at 24 kHz; 180ms joins; one global gain to -3 dBFS peak; no denoising or pitch change."
    })
    print(f"Prepared {duration:.2f}s reference: {output}")
