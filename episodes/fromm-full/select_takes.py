"""Assemble an explicit, hash-checked final take selection without overwriting recordings."""
import argparse
from pathlib import Path
import shutil
import tempfile

from klassic.project import digest, load_episode, read_json, write_json


def select_takes(episode_path, base, overrides_path, output):
    episode = load_episode(episode_path)
    overrides = read_json(overrides_path)
    if set(overrides)-{t['id'] for t in episode['turns']}:
        raise ValueError('Unknown turn IDs in take overrides')
    if output.exists():
        raise ValueError('Final take selection needs a new directory')
    selections = []
    for turn in episode['turns']:
        source = Path(overrides[turn['id']]) if turn['id'] in overrides else base/f"{turn['id']}.wav"
        metadata = read_json(source.with_suffix('.json'))
        report = read_json(source.with_suffix('.asr.json'))
        audio_hash = digest(source)
        if metadata['text'] != turn['text'] or metadata['speaker'] != turn['speaker']:
            raise ValueError(f"Take does not match script or speaker: {turn['id']}")
        if metadata['audio_sha256'] != audio_hash or report['audio_sha256'] != audio_hash:
            raise ValueError(f"Recording or ASR hash changed: {turn['id']}")
        if report['expected'] != turn['text']:
            raise ValueError(f"ASR checked different text: {turn['id']}")
        if digest(metadata['settings']['reference']) != metadata['reference_sha256']:
            raise ValueError(f"Voice reference changed: {turn['id']}")
        selections.append({'id':turn['id'],'source':str(source.resolve()),'audio_sha256':audio_hash,
                           'duration':metadata['duration'],'override':turn['id'] in overrides,
                           'word_check_differences':report['differences']})
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.selection-',dir=output.parent) as temporary:
        work = Path(temporary)
        for selection in selections:
            source = Path(selection['source'])
            for suffix in ('.wav','.json','.asr.json'):
                shutil.copyfile(source.with_suffix(suffix),work/f"{selection['id']}{suffix}")
        write_json(work/'selection.json',{'episode_sha256':digest(episode_path),'takes':selections,
                                        'full_listening_review_complete':False})
        work.rename(output)
    print(f'Selected {len(selections)} takes into {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode',type=Path)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--overrides',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    select_takes(args.episode,args.base,args.overrides,args.out)
