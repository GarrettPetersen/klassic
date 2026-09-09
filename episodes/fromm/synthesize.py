"""Resume supplied episode takes; reject stale inputs instead of reusing them."""
import argparse
from pathlib import Path
import tempfile
from klassic.audio import make_synthesizer, run, pcm, executable
from klassic.project import load_episode, read_json, write_json, digest


def synthesize_takes(episode_path, voices_path, output):
    episode = load_episode(episode_path)
    voices_path, output = Path(voices_path).resolve(), Path(output).resolve()
    config = read_json(voices_path)
    for settings in config.values():
        settings['reference'] = str((voices_path.parent/settings['reference']).resolve())
    output.mkdir(parents=True, exist_ok=True)
    synth = None
    # Check every completed take before loading a model or generating anything.
    pending = []
    for turn in episode['turns']:
        target = output/f"{turn['id']}.wav"
        metadata = {'text':turn['text'],'speaker':turn['speaker'],'settings':config[turn['speaker']],
                    'reference_sha256':digest(config[turn['speaker']]['reference']),
                    'backend':'chatterbox','device':'cpu','cpu_compute_threads':2}
        if target.exists():
            saved = read_json(target.with_suffix('.json'))
            if any(saved[k] != v for k,v in metadata.items()) or saved['audio_sha256'] != digest(target):
                raise ValueError(f'Saved take does not match current inputs: {target}')
            print(f"Retaining complete {turn['id']}", flush=True)
        else:
            pending.append((turn,target,metadata))
    if pending:
        synth = make_synthesizer('chatterbox',config,'cpu')
    for turn,target,metadata in pending:
        print(f"Generating {turn['id']} ({turn['speaker']}): {len(turn['text'].split())} words",flush=True)
        with tempfile.TemporaryDirectory(dir=output) as tmp:
            raw=Path(tmp)/'raw.wav'
            normalized=Path(tmp)/'take.wav'
            synth(turn,raw)
            run([executable('ffmpeg'),'-v','error','-y','-i',raw,'-ac','1','-ar','48000','-c:a','pcm_s16le',normalized])
            samples=pcm(normalized)
            metadata.update(audio_sha256=digest(normalized),duration=len(samples)/2/48000)
            normalized.replace(target)
            write_json(target.with_suffix('.json'),metadata)
        print(f"Saved {target}: {metadata['duration']:.2f}s",flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode',type=Path)
    parser.add_argument('--voices',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    synthesize_takes(args.episode,args.voices,args.out)
