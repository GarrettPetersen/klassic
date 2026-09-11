"""Local, reference-based accent review. Scores are not accent diagnoses."""
import argparse
import math
from pathlib import Path

from .project import digest, read_json, write_json

MODEL = "Jzuluaga/accent-id-commonaccent_ecapa"
REVISION = "14bebf44b7e7a34204d0acc2c897935945fb5c51"


def windows(duration, seconds=6.0, stride=3.0, minimum=3.0):
    if not all(math.isfinite(x) and x > 0 for x in (duration, seconds, stride, minimum)):
        raise ValueError("Window parameters must be finite and positive")
    if minimum > seconds or stride > seconds:
        raise ValueError("Minimum and stride must not exceed window length")
    if duration < minimum:
        return []
    if duration <= seconds:
        return [(0.0, duration)]
    starts = [i * stride for i in range(math.floor((duration-seconds)/stride)+1)]
    if duration-seconds-starts[-1] > .01:
        starts.append(duration-seconds)
    return [(start, start+seconds) for start in starts]


def assess(manifest, out, model_dir, seconds=6.0):
    # Optional ML dependencies live in their own environment, outside the renderer.
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    from huggingface_hub import snapshot_download
    from speechbrain.inference.classifiers import EncoderClassifier

    config = read_json(manifest)
    samples = config["samples"]
    ids = [s["id"] for s in samples]
    if len(set(ids)) != len(ids):
        raise ValueError("Accent sample IDs must be unique")
    for sample in samples:
        if sample["role"] not in {"baseline", "holdout", "known_drift", "candidate"}:
            raise ValueError(f"Unknown calibration role: {sample['role']}")
        if digest(sample["file"]) != sample["sha256"]:
            raise ValueError(f"Accent sample changed: {sample['file']}")
    if sum(s["role"] == "baseline" for s in samples) < 3:
        raise ValueError("Use at least three independent baseline recordings")
    if not all(any(s["role"] == role for s in samples) for role in ("holdout", "known_drift")):
        raise ValueError("Calibration requires held-out examples and known drift")
    model_dir = Path(model_dir).resolve()
    snapshot_download(MODEL, revision=REVISION, local_dir=model_dir,
                      allow_patterns=["*.yaml", "*.ckpt", "*.txt", "README.md"])
    torch.set_num_threads(4)
    classifier = EncoderClassifier.from_hparams(
        source=str(model_dir), savedir=str(model_dir/"loaded"),
        overrides={"pretrained_path": str(model_dir)}, run_opts={"device": "cpu"})
    results, vectors = [], {}
    for sample in samples:
        data, rate = sf.read(sample["file"], dtype="float32", always_2d=True)
        audio = torch.from_numpy(data.mean(axis=1))
        if rate != 16000:
            audio = torchaudio.functional.resample(audio, rate, 16000)
        spans = windows(len(audio)/16000, seconds=seconds, stride=seconds/2)
        records, embeddings = [], []
        for start, end in spans:
            clip = audio[round(start*16000):round(end*16000)].unsqueeze(0)
            rms = float(clip.square().mean().sqrt())
            if rms < .0001:
                continue
            with torch.inference_mode():
                embedding = classifier.encode_batch(clip)
                scores = classifier.mods.classifier(embedding).flatten()
            v = embedding.flatten().numpy()
            v = v/np.linalg.norm(v)
            embeddings.append(v)
            # This checkpoint returns cosine logits, not calibrated probabilities.
            top = scores.argsort(descending=True)[:3].tolist()
            labels = classifier.hparams.label_encoder.decode_ndim(top)
            records.append({"start": start, "end": end, "rms": rms,
                            "top_labels": [{"label": label, "cosine_logit": float(scores[i])}
                                           for i, label in zip(top, labels)]})
        if not embeddings:
            raise ValueError(f"No usable >=3 second windows: {sample['file']}")
        vectors[sample["id"]] = np.stack(embeddings)
        results.append({**sample, "duration": len(audio)/16000, "windows": records})
        print(f"Encoded {sample['id']}: {len(records)} windows", flush=True)
    # Give each baseline take equal weight regardless of its length/window count.
    means = [vectors[s["id"]].mean(axis=0) for s in samples if s["role"] == "baseline"]
    centroid = np.mean(means, axis=0)
    centroid /= np.linalg.norm(centroid)
    for result in results:
        distances = 1-vectors[result["id"]] @ centroid
        for window, distance in zip(result["windows"], distances):
            window["distance"] = float(distance)
        result["worst_window_distance"] = float(distances.max())
        result["mean_distance"] = float(distances.mean())
    holdout = [r["worst_window_distance"] for r in results if r["role"] == "holdout"]
    drift = [r["worst_window_distance"] for r in results if r["role"] == "known_drift"]
    separation = min(drift) - max(holdout)
    report = {
        "model": MODEL, "model_revision": REVISION,
        "manifest_sha256": digest(manifest), "window_seconds": seconds, "stride_seconds": seconds/2,
        "distance": "1 - cosine similarity to the equal-take-weight baseline centroid",
        "calibration": {"known_drift_above_all_holdouts": separation > 0,
                        "separation_margin": separation,
                        "highest_holdout_distance": max(holdout),
                        "lowest_known_drift_distance": min(drift),
                        "automatic_rejection_enabled": False,
                        "reason": "One reported bad take and provisional good labels cannot validate a production rejection threshold."},
        "limitations": ["No Texas or German accent label in this model.",
                        "Similarity can vary with phonemes, delivery, recording noise and synthesis artifacts.",
                        "Baseline and holdout lines are provisional, not individually approved by a listener.",
                        "ASR correctness does not establish accent consistency."],
        "samples": results,
    }
    write_json(out, report)
    print(report["calibration"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model-dir", type=Path, default=Path(".tools/commonaccent"))
    parser.add_argument("--window", type=float, default=6.0)
    args = parser.parse_args()
    assess(args.manifest, args.out, args.model_dir, args.window)


if __name__ == "__main__":
    main()
