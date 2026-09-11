"""Verify the finished full-length export and create manageable visual review pages."""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from klassic.audio import executable, run
from klassic.project import digest, read_json, write_json
from klassic.render import Compositor, load_build, srt_time, subtitle_chunks
from klassic.presentation import screen_time, title_at


def verify(build, rig):
    timeline = load_build(build)
    manifest = read_json(build/'episode-manifest.json')
    if digest(build/'episode.mp4') != manifest['episode_sha256']:
        raise ValueError('Finished film changed after assembly')
    if digest(build/'episode.srt') != manifest['captions_sha256']:
        raise ValueError('Captions changed after assembly')
    picture = read_json(build/'render-manifest.json')
    if digest(build/'render-manifest.json') != manifest['render_manifest_sha256']:
        raise ValueError('Picture manifest changed after assembly')
    if digest(rig) != picture['rig_sha256'] or digest(build/'timeline.json') != picture['timeline_sha256']:
        raise ValueError('Rig or timeline does not match the rendered picture')
    cut = title_at(timeline)
    if abs(cut-manifest.get('title_at_seconds', 0)) > .001:
        raise ValueError('Finished title does not match its requested insertion point')
    probe = json.loads(run([executable('ffprobe'), '-v', 'error', '-show_streams',
                            '-show_format', '-of', 'json', build/'episode.mp4']))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    if (video['width'], video['height'], video['r_frame_rate'], video['codec_name']) != (1440,1080,'24/1','h264'):
        raise ValueError('Video does not meet the 1440×1080 / 24fps / H.264 contract')
    if audio['codec_name'] != 'aac' or audio['sample_rate'] != '48000':
        raise ValueError('Audio does not meet the AAC / 48kHz contract')
    expected = manifest['title_seconds'] + timeline['duration'] + manifest['credit_seconds']
    if abs(float(probe['format']['duration'])-expected) > .1:
        raise ValueError('Finished duration does not match dialogue plus titles and credits')
    captions = [c for t in timeline['turns'] for c in subtitle_chunks(t)]
    if not captions or captions[-1]['end'] > timeline['duration']+.001:
        raise ValueError('Captions extend beyond dialogue')
    expected_srt = '\n\n'.join(
        f"{i+1}\n{srt_time(screen_time(c['start'],cut,manifest['title_seconds']))} --> "
        f"{srt_time(screen_time(c['end'],cut,manifest['title_seconds'],end=True))}\n{c['text']}"
        for i,c in enumerate(captions))+'\n'
    if (build/'episode.srt').read_text() != expected_srt:
        raise ValueError('Finished caption text or timing does not match the dialogue and title placement')
    if any(c['start'] < cut < c['end'] for c in captions):
        raise ValueError('A caption straddles the inserted title')

    comp = Compositor(timeline, rig, 1440, burn_captions=False)
    listener_checks = 0
    quiet_checks = 0
    for turn in timeline['turns']:
        listener = 'guest' if turn['speaker'] == 'host' else 'host'
        track, _, span = comp.transitions[listener]
        for frame in range(math.ceil(turn['start']*24), math.ceil(turn['end']*24)):
            if track.sample(frame/24, span) != ('X','X',0.0):
                raise ValueError(f"Listener mouth moves during {turn['id']} at {frame/24}")
            listener_checks += 1
        track, _, span = comp.transitions[turn['speaker']]
        for pause in turn['silences']:
            for frame in range(math.ceil((turn['start']+pause['start'])*24),
                               math.ceil((turn['start']+pause['end'])*24)):
                if track.sample(frame/24, span) != ('X','X',0.0):
                    raise ValueError(f"Mouth moves in silence during {turn['id']} at {frame/24}")
                quiet_checks += 1
    for shot in timeline['shots']:
        if shot.get('pose') == 'host_sip':
            if any(t['speaker']=='host' and t['start'] < shot['end'] and t['end'] > shot['start']
                   for t in timeline['turns']):
                raise ValueError('Krusty sips over his own speech')

    pages = []
    shots = timeline['shots']
    for first in range(0,len(shots),20):
        group = shots[first:first+20]
        sheet = Image.new('RGB',(1600,math.ceil(len(group)/4)*325),(20,20,20))
        draw = ImageDraw.Draw(sheet)
        for i,shot in enumerate(group):
            at = min(shot['start']+1,(shot['start']+shot['end'])/2)
            x,y = (i%4)*400,(i//4)*325
            sheet.paste(comp.frame(at).resize((400,300)),(x,y))
            draw.text((x+10,y+305),f"{first+i+1}: {screen_time(at,manifest.get('title_at_seconds',0),manifest['title_seconds']):.2f}s / {shot['camera']}",fill='white')
        path = build/f'camera-review-{first//20+1:02d}.jpg'
        sheet.save(path,quality=92)
        pages.append(path.name)
    # Decode every frame and audio packet, not just a thumbnail or container header.
    run([executable('ffmpeg'),'-v','error','-xerror','-threads','2','-i',build/'episode.mp4',
         '-f','null','-'])
    report = {'episode_sha256':digest(build/'episode.mp4'),'duration_seconds':float(probe['format']['duration']),
              'dialogue_seconds':timeline['duration'],'turns':len(timeline['turns']),
              'captions_checked':len(captions),'title_at_seconds':cut,
              'shots':len(shots),'listener_frames_checked':listener_checks,'quiet_frames_checked':quiet_checks,
              'full_decode_passed':True,'width':1440,'height':1080,'fps':24,
              'camera_review_pages':pages,'full_listening_review_complete':False,
              'limitations':'ASR and frame-state checks do not establish voice likeness or replace listening review.'}
    write_json(build/'verification.json',report)
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--rig',type=Path,default=Path('assets/episodes/fromm/rig.json'))
    args = parser.parse_args()
    verify(args.build,args.rig)
