import argparse
import sys
from pathlib import Path

from .audio import audition, prepare
from .project import import_transcript, load_episode, write_json
from .render import render
from .reference import build_reference
from .cels import bake_transitions
from .transition_review import review_transitions
from .guest import review_guest


def main():
    parser = argparse.ArgumentParser(description="Transcript → voices → timed mouth cels → interview film")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("import", help="Import an explicitly speaker-labeled UTF-8 transcript")
    ingest.add_argument("transcript", type=Path)
    ingest.add_argument("--host-label", required=True)
    ingest.add_argument("--guest-label", required=True)
    ingest.add_argument("--title", required=True)
    ingest.add_argument("--source-url", required=True)
    ingest.add_argument("--out", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("episode", type=Path)
    prep = sub.add_parser("prepare", help="Generate/normalize per-turn takes and run Rhubarb")
    prep.add_argument("episode", type=Path)
    prep.add_argument("--out", required=True, type=Path)
    prep.add_argument("--voice-mode", required=True, choices=["macos", "files", "chatterbox", "xtts"])
    prep.add_argument("--voices", type=Path)
    prep.add_argument("--takes", type=Path)
    prep.add_argument("--rhubarb", default="rhubarb")
    prep.add_argument("--device", choices=["cpu", "cuda", "mps"], default="cpu")
    prep.add_argument("--scratch", action="store_true", help="Retain scratch labeling for supplied or neural draft takes")
    film = sub.add_parser("render")
    film.add_argument("build", type=Path)
    film.add_argument("--rig", required=True, type=Path)
    film.add_argument("--width", type=int, default=960)
    ref = sub.add_parser("reference", help="Prepare selected isolated game lines from a ZIP")
    ref.add_argument("archive", type=Path)
    ref.add_argument("--clips", nargs="+", required=True)
    ref.add_argument("--source-url", required=True)
    ref.add_argument("--out", required=True, type=Path)
    voice = sub.add_parser("audition", help="Test Krusty with one Chatterbox take")
    voice.add_argument("--text", required=True)
    voice.add_argument("--reference", required=True, type=Path)
    voice.add_argument("--out", required=True, type=Path)
    voice.add_argument("--device", choices=["cpu", "cuda", "mps"], default="cpu")
    voice.add_argument("--exaggeration", type=float, default=0.3)
    voice.add_argument("--cfg-weight", type=float, default=0.5)
    voice.add_argument("--temperature", type=float, default=0.8)
    voice.add_argument("--seed", type=int, default=42)
    bake = sub.add_parser("bake-transitions", help="Extract and register all 36 authored mouth transition pairs")
    bake.add_argument("spec", type=Path)
    bake.add_argument("--out", required=True, type=Path)
    review = sub.add_parser("review-transitions", help="Create a local flipbook of every mouth transition")
    review.add_argument("--rig", required=True, type=Path)
    review.add_argument("--out", required=True, type=Path)
    review.add_argument("--speaker", default="host", choices=["host", "guest"])
    guest = sub.add_parser("review-guest", help="Fit shared mouth drawings to a layered guest portrait")
    guest.add_argument("spec", type=Path)
    guest.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "import":
            if args.out.exists():
                raise ValueError(f"Output exists: {args.out}")
            episode = {"version": 1, "title": args.title,
                       "source": {"url": args.source_url, "notes": "User-supplied transcript; verify OCR and excerpt context before production."},
                       "disclosure": "Unofficial fan parody. AI animation and recreated voices. Interviewer performed as Krusty.",
                       "turns": import_transcript(args.transcript.read_text(), args.host_label, args.guest_label)}
            args.out.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.out, episode)
            try:
                load_episode(args.out)
            except ValueError:
                args.out.unlink()
                raise
            print(args.out)
        elif args.command == "validate":
            print(f"Valid: {len(load_episode(args.episode)['turns'])} turns")
        elif args.command == "prepare":
            prepare(args.episode, args.out, args.voice_mode, args.rhubarb, args.voices, args.takes, args.device, args.scratch)
        elif args.command == "render":
            render(args.build, args.rig, args.width)
        elif args.command == "review-transitions":
            print(review_transitions(args.rig,args.out,args.speaker))
        elif args.command == "review-guest":
            print(review_guest(args.spec, args.out))
        elif args.command == "bake-transitions":
            print(bake_transitions(args.spec, args.out))
        elif args.command == "reference":
            build_reference(args.archive, args.clips, args.out, args.source_url)
        elif args.command == "audition":
            audition(args.text, args.reference, args.out, args.device, args.exaggeration, args.cfg_weight, args.temperature, args.seed)
    except (ValueError, RuntimeError, OSError, ImportError, KeyError) as error:
        print(f"klassic: {error}", file=sys.stderr)
        return 1
    return 0
