"""Render the new puppet picture, preserving the previous film's exact audio mix."""
import argparse
import concurrent.futures
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess

from PIL import Image,ImageEnhance
from klassic.captions import CaptionTrack
from klassic.project import digest,read_json,write_json
from klassic.render import Compositor,load_build
from klassic.presentation import title_at

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'build/fromm-full-02'
BUILD=ROOT/'build/fromm-full-07'
RIG=ROOT/'assets/episodes/fromm-v7/rig.json'
FPS=24


class FilmFrames:
    def __init__(self):
        self.timeline=load_build(SOURCE)
        self.comp=Compositor(self.timeline,RIG,1440,False)
        self.captions=CaptionTrack(SOURCE/'episode.srt')
        self.cut=title_at(self.timeline)
        self.dialogue_end=self.timeline['duration']+6.25
        self.total=self.dialogue_end+40
        self.title=Image.open(SOURCE/'title.png').convert('RGB')
        self.credits=[Image.open(SOURCE/f'{name}-credits.png').convert('RGB')
                      for name in ['cast','creator','voices','source','music']]

    def frame(self,at):
        if not 0<=at<self.total:raise ValueError('Frame outside finished film')
        fade=1
        if self.cut<=at<self.cut+6.25:
            local=at-self.cut;image=self.title.copy()
            fade=min(1,local/.4,(6.25-local)/.4)
        elif at>=self.dialogue_end:
            local=at-self.dialogue_end;index=int(local//8)
            image=self.credits[index].copy()
            if index==4:fade=min(1,(40-local)/.8)
        else:
            dialogue=at if at<self.cut else at-6.25
            image=self.comp.frame(dialogue)
            if at<self.cut:fade=min(1,(self.cut-at)/.25)
            else:fade=min(1,(at-self.cut-6.25)/.25,(self.dialogue_end-at)/.5)
        if fade<1:image=ImageEnhance.Brightness(image).enhance(max(0,fade))
        self.captions.paint(image,at)
        return image


def render_chunk(job):
    index,start,end,folder=job
    folder=Path(folder);partial=folder/f'{index:02d}.partial.mp4';final=folder/f'{index:02d}.mp4'
    frames=FilmFrames()
    command=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1440x1080',
             '-r',str(FPS),'-i','-','-an','-c:v','libx264','-threads','1','-preset','fast',
             '-crf','18','-pix_fmt','yuv420p',str(partial)]
    with (folder/f'{index:02d}.log').open('w+') as log:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for frame in range(start,end):
                process.stdin.write(frames.frame(frame/FPS).tobytes())
                if (frame-start)%240==0:
                    write_json(folder/f'{index:02d}-progress.json',{'done':frame-start,'total':end-start})
            process.stdin.close()
            if process.wait():
                log.seek(0);raise RuntimeError(log.read())
        except BaseException:
            process.kill();process.wait();partial.unlink(missing_ok=True);raise
    partial.replace(final)
    write_json(folder/f'{index:02d}-progress.json',{'done':end-start,'total':end-start})
    return index,str(final)


def input_hashes():
    paths={'timeline':SOURCE/'timeline.json','audio_film':SOURCE/'episode.mp4',
           'srt':SOURCE/'episode.srt','rig':RIG,'renderer':Path(__file__),
           'puppet_code':ROOT/'klassic/puppet.py','gestures_code':ROOT/'klassic/gestures.py',
           'compositor':ROOT/'klassic/render.py','captions_code':ROOT/'klassic/captions.py'}
    return {**{name:digest(path) for name,path in paths.items()},
            'puppet':FilmFrames().comp.puppet.hashes()}


def render(mode):
    BUILD.mkdir(exist_ok=True)
    timeline=load_build(SOURCE)
    old_manifest=read_json(SOURCE/'episode-manifest.json')
    if digest(SOURCE/'episode.mp4')!=old_manifest['episode_sha256']:
        raise ValueError('Previous film no longer matches its audio provenance')
    total=timeline['duration']+46.25
    count=round(total*FPS)
    if mode=='proof':
        intervals=[(0,6*FPS),(25*FPS,40*FPS),(73*FPS,83*FPS),(232*FPS,241*FPS),(612*FPS,620*FPS),(1564*FPS,round((timeline['duration']+6.25)*FPS))]
        name='motion-preview.mp4'
    else:
        intervals=[(i*count//4,(i+1)*count//4) for i in range(4)]
        name='episode-captioned.mp4'
    folder=BUILD/f'{mode}-chunks';folder.mkdir(exist_ok=True)
    frozen=input_hashes()
    jobs=[(i,start,end,str(folder)) for i,(start,end) in enumerate(intervals)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        outputs=list(pool.map(render_chunk,jobs))
    # Rendering must not publish a mixture of different rigs or scripts.
    if frozen!=input_hashes():
        raise ValueError('Render inputs changed during rendering; render again')
    (folder/'concat.txt').write_text(''.join(f"file '{Path(path).name}'\n" for _,path in sorted(outputs)))
    temporary=BUILD/(name.removesuffix('.mp4')+'.partial.mp4')
    cmd=['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(folder/'concat.txt'),'-i',str(SOURCE/'episode.mp4')]
    if mode=='proof':
        n=len(intervals)
        filters=[f'[1:a]asplit={n}'+''.join(f'[a{i}]' for i in range(n))]
        for i,(start,end) in enumerate(intervals):
            filters.append(f'[a{i}]atrim=start={start/FPS}:end={end/FPS},asetpts=PTS-STARTPTS[s{i}]')
        filters.append(''.join(f'[s{i}]' for i in range(n))+f'concat=n={n}:v=0:a=1[a]')
        cmd+=['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[a]','-c:a','aac','-b:a','160k']
    else:
        cmd+=['-map','0:v:0','-map','1:a:0','-c:a','copy']
    subprocess.run(cmd+['-c:v','copy','-movflags','+faststart',str(temporary)],check=True)
    temporary.replace(BUILD/name)
    for filename in ['episode.srt','episode.json','timeline.json']:
        shutil.copyfile(SOURCE/filename,BUILD/filename)
    write_json(BUILD/f'{mode}-manifest.json',{'file':name,'sha256':digest(BUILD/name),
        'inputs':frozen,'source_film_intervals':[(a/FPS,b/FPS) for a,b in intervals],
        'frames':sum(b-a for a,b in intervals),'fps':FPS,'audio':'source AAC stream copied' if mode=='full' else 'source mix excerpts',
        'captions':'same SRT and typography as revision 02','title_seconds':6.25,'title_at':title_at(timeline)})
    print(BUILD/name,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['proof','full'])
    render(parser.parse_args().mode)
