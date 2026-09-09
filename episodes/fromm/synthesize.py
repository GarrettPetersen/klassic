"""Resume the nine production takes; reject stale inputs instead of reusing them."""
from pathlib import Path
import tempfile
from klassic.audio import make_synthesizer, run, pcm, executable
from klassic.project import read_json, write_json, digest

episode=read_json('episodes/fromm/episode.json')
config=read_json('episodes/fromm/voices.reference.example.json')
for settings in config.values():
    settings['reference']=str((Path('episodes/fromm')/settings['reference']).resolve())
out=Path('voices/takes/fromm-episode-01')
out.mkdir(parents=True,exist_ok=True)
synth=make_synthesizer('chatterbox',config,'cpu')
for turn in episode['turns']:
    target=out/f"{turn['id']}.wav"
    metadata={'text':turn['text'],'speaker':turn['speaker'],'settings':config[turn['speaker']],
              'reference_sha256':digest(config[turn['speaker']]['reference']),'backend':'chatterbox','device':'cpu','cpu_compute_threads':2}
    if target.exists():
        saved=read_json(target.with_suffix('.json'))
        if any(saved[k]!=v for k,v in metadata.items()) or saved['audio_sha256']!=digest(target):
            raise ValueError(f'Saved take does not match current inputs: {target}')
        print(f"Retaining complete {turn['id']}",flush=True)
        continue
    print(f"Generating {turn['id']} ({turn['speaker']}): {len(turn['text'].split())} words",flush=True)
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        raw=Path(tmp)/'raw.wav';normalized=Path(tmp)/'take.wav'
        synth(turn,raw)
        run([executable('ffmpeg'),'-v','error','-y','-i',raw,'-ac','1','-ar','48000','-c:a','pcm_s16le',normalized])
        samples=pcm(normalized)
        metadata.update(audio_sha256=digest(normalized),duration=len(samples)/2/48000)
        normalized.replace(target)
        write_json(target.with_suffix('.json'),metadata)
    print(f"Saved {target}: {metadata['duration']:.2f}s",flush=True)
