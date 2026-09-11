"""Cut the complete interview by speaker runs rather than synthesis chunks."""
import argparse
from pathlib import Path

from klassic.project import write_json
from klassic.render import load_build


def edit_camera(build):
    timeline = load_build(build)
    runs = []
    for turn in timeline['turns']:
        end = turn['end'] + turn['pause_after']
        if runs and runs[-1]['speaker'] == turn['speaker']:
            runs[-1]['end'] = end
        else:
            runs.append({'start': turn['start'], 'end': end, 'speaker': turn['speaker']})
    shots = []
    last_wide, last_sip = -180, -180

    def shot(start, end, camera, pose=None):
        if end <= start:
            raise ValueError('Camera segment must have positive duration')
        data = {'start': start, 'end': end, 'camera': camera}
        if pose:
            data['pose'] = pose
        if shots and shots[-1]['camera'] == camera and shots[-1].get('pose') == pose:
            shots[-1]['end'] = end
        else:
            shots.append(data)

    for run in runs:
        cursor, end, speaker = run['start'], run['end'], run['speaker']
        if cursor == 0 or (cursor-last_wide >= 150 and end-cursor >= 12):
            stop = min(end, cursor+(6 if cursor == 0 else 4))
            shot(cursor, stop, 'wide')
            last_wide, cursor = cursor, stop
        while end-cursor > 32:
            cut = cursor+22
            shot(cursor, cut, speaker)
            listener = 'host' if speaker == 'guest' else 'guest'
            pose = None
            if speaker == 'guest' and cut >= 60 and cut-last_sip >= 240:
                pose = 'host_sip'
                last_sip = cut
            shot(cut, cut+2.5, listener, pose)
            cursor = cut+2.5
        if end > cursor:
            shot(cursor, end, speaker)
    shots[-1]['end'] = timeline['duration']
    timeline['shots'] = shots
    write_json(Path(build)/'timeline.json', timeline)
    load_build(build)
    print(f"Edited {len(runs)} speaker runs into {len(shots)} shots; "
          f"{sum(s.get('pose') == 'host_sip' for s in shots)} drinking cutaways")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    edit_camera(parser.parse_args().build)
