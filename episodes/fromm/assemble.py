"""Apply the episode edit, render the picture, and add its three-second title."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from klassic.audio import executable, run
from klassic.project import read_json, write_json, digest
from klassic.render import load_build, render, srt_time, subtitle_chunks


def assemble(build, rig):
    build = Path(build).resolve()
    timeline = load_build(build)
    turns = timeline['turns']
    if [t['id'] for t in turns] != [f't{i:03}' for i in range(1, 10)]:
        raise ValueError('This camera edit requires the nine-turn Fromm episode')
    shots = []
    for i, turn in enumerate(turns):
        start = turn['start']
        end = turns[i+1]['start'] if i+1 < len(turns) else timeline['duration']
        # All cutaway offsets are relative to their measured take, not estimates
        # of preceding speech. A drinking pose only occurs during guest speech.
        cuts = {
            't001': [(0, 'wide', None), (5, 'host', None)],
            't004': [(0, 'guest', None), (8, 'host', 'host_sip'), (10.5, 'guest', None)],
            't006': [(0, 'guest', None), (8, 'wide', None), (11, 'guest', None)],
            't009': [(0, 'host', None), (4, 'wide', None)],
        }.get(turn['id'], [(0, turn['speaker'], None)])
        if cuts[-1][0] >= turn['end']-start:
            raise ValueError(f"Take too short for camera edit: {turn['id']}")
        for j, (offset, camera, pose) in enumerate(cuts):
            shot = {'start': start+offset, 'end': start+cuts[j+1][0] if j+1<len(cuts) else end, 'camera':camera}
            if pose: shot['pose'] = pose
            shots.append(shot)
    timeline['shots'] = shots
    write_json(build/'timeline.json', timeline)
    render(build, rig, 1440, burn_captions=False)
    finish(build, timeline)


def finish(build, timeline):
    title_seconds = 3
    card = Image.new('RGB', (1440,1080), (24,24,24))
    draw = ImageDraw.Draw(card)
    font_path = '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf'
    if not Path(font_path).is_file():
        raise ValueError(f'Title font missing: {font_path}')
    for text, y, size in [('CLASSIC KRUSTY',350,100),('ERICH FROMM',530,61),('The Personality Market',630,44)]:
        draw.text((720,y),text,anchor='mm',font=ImageFont.truetype(font_path,size),fill=(225,225,225))
    draw.line((440,443,1000,443),fill=(130,130,130),width=2)
    card.save(build/'title.png')
    ffmpeg=executable('ffmpeg')
    run([ffmpeg,'-v','error','-y','-loop','1','-framerate','24','-i',build/'title.png',
         '-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',str(title_seconds),
         '-vf','fade=t=in:st=0:d=0.4,fade=t=out:st=2.6:d=0.4',
         '-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-c:a','aac',build/'title.mp4'])
    fade_start=timeline['duration']-1
    run([ffmpeg,'-v','error','-y','-i',build/'title.mp4','-i',build/'preview.mp4',
         '-filter_complex',f'[1:v]fade=t=out:st={fade_start}:d=1[v];[0:v][0:a][v][1:a]concat=n=2:v=1:a=1[outv][outa]',
         '-map','[outv]','-map','[outa]','-c:v','libx264','-threads','2','-preset','fast','-crf','18',
         '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',build/'episode.mp4'])
    captions = [c for turn in timeline['turns'] for c in subtitle_chunks(turn)]
    (build/'episode.srt').write_text('\n\n'.join(f"{i+1}\n{srt_time(c['start']+title_seconds)} --> {srt_time(c['end']+title_seconds)}\n{c['text']}" for i,c in enumerate(captions))+'\n')
    write_json(build/'episode-manifest.json',{'title_seconds':title_seconds,'dialogue_seconds':timeline['duration'],
        'width':1440,'height':1080,'fps':24,'episode_sha256':digest(build/'episode.mp4'),
        'captions_sha256':digest(build/'episode.srt'),'render_manifest_sha256':digest(build/'render-manifest.json'),
        'source_reference':'episodes/fromm/voice-reference.json','script':'concise adaptation with original framing'})
    page=(build/'review.html').read_text().replace('src="preview.mp4"','poster="title.png" src="episode.mp4"').replace('href="captions.srt"','href="episode.srt"')
    (build/'review.html').write_text(page)
    print(build/'episode.mp4')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--rig',type=Path,default=Path('assets/episodes/fromm/rig.json'))
    args=parser.parse_args()
    assemble(args.build,args.rig)
