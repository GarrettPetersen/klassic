"""Render an edited interview, then add its jazz opening and closing credits."""
import argparse
import html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from klassic.audio import executable, run
from klassic.project import read_json, write_json, digest
from klassic.render import load_build, render, srt_time, subtitle_chunks

ROOT = Path(__file__).resolve().parents[2]
INTRO_SECONDS = 6.25
CREDIT_SECONDS = 8


def card(path, lines):
    font_path = Path('/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf')
    if not font_path.is_file():
        raise ValueError(f'Title font missing: {font_path}')
    image = Image.new('RGB', (1440,1080), (24,24,24))
    draw = ImageDraw.Draw(image)
    for text, y, size in lines:
        draw.text((720,y),text,anchor='mm',font=ImageFont.truetype(str(font_path),size),fill=(225,225,225))
    image.save(path)


def finish(build, timeline):
    """Reuse only a picture render that still matches the prepared timeline."""
    manifest = read_json(build/'render-manifest.json')
    if manifest['video_sha256'] != digest(build/'preview.mp4') or manifest['timeline_sha256'] != digest(build/'timeline.json'):
        raise ValueError('Picture or timeline changed; render again before finishing')
    music_path = ROOT/'assets/music/george-street-shuffle.mp3'
    music = read_json(ROOT/'assets/music/source.json')
    if digest(music_path) != music['sha256']:
        raise ValueError('Music no longer matches its source record')
    card(build/'title.png', [('CLASSIC KRUSTY',350,100),('ERICH FROMM',530,61),('The Personality Market',630,44)])
    credits = [
        ('cast', [('CLASSIC KRUSTY',240,80),('Your host',405,37),('KRUSTY',475,64),('Tonight’s guest',635,37),('ERICH FROMM',710,64)]),
        ('creator', [('CREATED BY',300,45),('Garrett M. Petersen',430,68),('with',590,36),('GPT 6 Astra',690,62)]),
        ('voices', [('RECREATED VOICES',260,50),('Chatterbox',405,74),('Resemble AI',495,39),('Krusty reference: The Simpsons: Cartoon Studio',670,31),('Fromm reference: his 1958 interview',745,33)]),
        ('source', [('TRANSCRIPT SOURCE',220,48),('The Mike Wallace Interview',350,58),('Erich Fromm · May 25, 1958',450,42),('Harry Ransom Center',605,43),('The University of Texas at Austin',680,36),('Archive recording HRC_WAL0025',785,30)]),
        ('music', [('MUSIC',220,54),('“George Street Shuffle”',350,60),('KEVIN MACLEOD',440,54),('incompetech.com',520,35),('Creative Commons Attribution 4.0',655,32),('creativecommons.org/licenses/by/4.0/',715,29),('Excerpted, faded, and mixed in mono',805,30)]),
    ]
    for name, lines in credits:
        card(build/f'{name}-credits.png', lines)
    duration = timeline['duration']
    credit_duration = CREDIT_SECONDS*len(credits)
    total = INTRO_SECONDS + duration + credit_duration
    outro_at = INTRO_SECONDS + duration - 2
    intro = music['edits']['intro_seconds']
    outro = music['edits']['outro_seconds']
    if abs(outro - (credit_duration+2)) > 0.001:
        raise ValueError('Closing music must cover the credits plus the two-second lead-in')
    tone = 'aresample=48000,aformat=channel_layouts=mono,highpass=f=100,lowpass=f=6500,loudnorm=I=-20:TP=-3:LRA=7'
    filters = [
        f'[0:v]trim=duration={INTRO_SECONDS},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.4,fade=t=out:st={INTRO_SECONDS-.4}:d=0.4[v0]',
        f'[1:v]setpts=PTS-STARTPTS,fade=t=out:st={duration-.5}:d=0.5[v1]',
    ]
    inputs = ['-loop','1','-framerate','24','-i',build/'title.png','-i',build/'preview.mp4']
    for i, (name, _) in enumerate(credits, 2):
        inputs.extend(['-loop','1','-framerate','24','-i',build/f'{name}-credits.png'])
        fade = f',fade=t=out:st={CREDIT_SECONDS-.8}:d=0.8' if i==len(credits)+1 else ''
        filters.append(f'[{i}:v]trim=duration={CREDIT_SECONDS},setpts=PTS-STARTPTS{fade}[v{i}]')
    count = len(credits)+2
    inputs.extend(['-i',music_path])
    filters.extend([
        ''.join(f'[v{i}]' for i in range(count))+f'concat=n={count}:v=1:a=0[v]',
        f'[1:a]aresample=48000,aformat=channel_layouts=mono,adelay={round(INTRO_SECONDS*1000)}:all=1,apad=whole_dur={total}[speech]',
        f'[{count}:a]asplit=2[opening][closing]',
        f'[opening]atrim=start=0:duration={intro},asetpts=PTS-STARTPTS,{tone},afade=t=in:st=0:d=0.15,afade=t=out:st={INTRO_SECONDS}:d=2[imusic]',
        f"[closing]atrim=start={music['edits']['outro_source_start']}:duration={outro},asetpts=PTS-STARTPTS,{tone},afade=t=in:st=0:d=0.4,afade=t=out:st={outro-.4}:d=0.4,volume='0.3+0.7*clip((t-1.5)/1,0,1)':eval=frame,adelay={round(outro_at*1000)}:all=1[omusic]",
        '[speech][imusic][omusic]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95:latency=1[a]',
    ])
    final = build/'episode.mp4'
    temporary = build/'episode.partial.mp4'
    run([executable('ffmpeg'),'-v','error','-y',*inputs,
         '-filter_complex_threads','2','-filter_complex',';'.join(filters),
         '-map','[v]','-map','[a]','-t',str(total),'-r','24',
         '-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p',
         '-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',temporary])
    temporary.replace(final)
    captions = [c for turn in timeline['turns'] for c in subtitle_chunks(turn)]
    (build/'episode.srt').write_text('\n\n'.join(f"{i+1}\n{srt_time(c['start']+INTRO_SECONDS)} --> {srt_time(c['end']+INTRO_SECONDS)}\n{c['text']}" for i,c in enumerate(captions))+'\n')
    (build/'music-credit.txt').write_text(music['credit']+'\n')
    write_json(build/'episode-manifest.json',{'title_seconds':INTRO_SECONDS,'dialogue_seconds':duration,
        'credit_seconds':credit_duration,'credits':[{'card':name,'lines':[line[0] for line in lines]} for name,lines in credits],'width':1440,'height':1080,'fps':24,'episode_sha256':digest(final),
        'captions_sha256':digest(build/'episode.srt'),'render_manifest_sha256':digest(build/'render-manifest.json'),
        'music':{'sha256':digest(music_path),'source_url':music['source_url'],'license_url':music['license_url'],
                 'intro_seconds':intro,'outro_at':outro_at,'outro_seconds':outro},
        'script':timeline['source']['notes']})
    title = html.escape(timeline['title'])
    (build/'review.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title>
<style>body{{background:#181818;color:#eee;font:17px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px}}video{{width:100%}}a{{color:#ddd}}</style>
<h1>{title}</h1><video controls poster="title.png" src="episode.mp4"></video>
<p>{html.escape(timeline['disclosure'])}</p><p><a href="episode.srt">Captions</a> · <a href="timeline.json">Dialogue timeline (starts after the 6.25-second title)</a></p>
<p>{html.escape(music['credit'])}</p></html>''')
    print(final)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--rig',type=Path,default=ROOT/'assets/episodes/fromm/rig.json')
    parser.add_argument('--finish-only',action='store_true',help='Reuse a verified picture render and rebuild titles, credits, and music')
    args=parser.parse_args()
    build=args.build.resolve()
    timeline=load_build(build)
    if not args.finish_only:
        render(build,args.rig,1440,burn_captions=False)
    finish(build,timeline)
