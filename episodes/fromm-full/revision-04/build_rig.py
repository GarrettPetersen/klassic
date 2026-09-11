"""Register four-digit hand drawings and pupil-free plates on the frozen stage."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from klassic.cels import remove_green_matte
from klassic.project import digest, read_json, write_json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'assets/episodes/fromm-v4'
BASE = ROOT/'assets/episodes/fromm-v3'
SIZE = (1448,1086)
# Cuff centers and interior areas measured from the stage reference crops.
CUFFS = {
    ('host','free'): ((165.5,569.9),8251/9),
    ('host','cigarette'): ((494.1,513.9),6085/9),
    ('guest','free'): ((1301.7,580.5),7618/9),
    ('guest','cigarette'): ((931.0,537.8),7230/9),
}
HAND_BOXES={('host','free'):(142,544,261,646),('host','cigarette'):(470,405,563,537),
            ('guest','free'):(1215,552,1325,668),('guest','cigarette'):(906,422,999,558)}


def hand_mask(scene,speaker,arm):
    box=HAND_BOXES[speaker,arm];rgb=scene.crop(box).convert('RGB')
    parts=components(rgb,min_area=2)
    local=np.zeros((rgb.height,rgb.width),dtype='uint8')
    for area,center,gray,region in parts:local[region]=255
    contours,_=cv2.findContours(local,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(local,contours,-1,255,cv2.FILLED)
    mask=Image.new('L',SIZE)
    mask.paste(Image.fromarray(local).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(.35)),box[:2])
    target,_=CUFFS[speaker,arm]
    target=(target[0]-box[0],target[1]-box[1])
    cuff=min((p for p in parts if p[2]>220),key=lambda p:math.dist(p[1],target))
    if math.dist(cuff[1],target)>12:raise ValueError('Cuff cap registration failed')
    cap=Image.new('L',SIZE)
    cap.paste(Image.fromarray(cuff[3].astype('uint8')*255).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(.35)),box[:2])
    cap.save(OUT/f'{speaker}-{arm}-cuff-cap.png')
    return mask


def components(rgb,min_area=50):
    a=np.asarray(rgb)
    threshold=((a[:,:,0]>175)&(a[:,:,1].astype('int16')-a[:,:,0]<30)).astype('uint8')
    count,labels,stats,centers=cv2.connectedComponentsWithStats(threshold)
    return [(int(s[4]),centers[i],float(a[:,:,0][labels==i].mean()),labels==i)
            for i,s in enumerate(stats) if i and s[4]>min_area]


def bake_hands(speaker,arm,character):
    prefix=f'{speaker}-{arm}'
    atlas=OUT/(prefix+('-atlas-four-digits.png' if prefix=='guest-cigarette' else '-atlas.png'))
    raw=Image.open(atlas).convert('RGB')
    drawings={}
    for i,name in enumerate(('relaxed','turn','up','sweep')):
        x,y=i%2,i//2
        drawings[name]=(raw.crop((round(x*raw.width/2),round(y*raw.height/2),
                                  round((x+1)*raw.width/2),round((y+1)*raw.height/2))),atlas)
    if arm=='cigarette':
        path=OUT/f'{prefix}-down.png';drawings['down']=(Image.open(path).convert('RGB'),path)
    folder=OUT/prefix;folder.mkdir(exist_ok=True)
    target,area=CUFFS[speaker,arm]
    bone=character['arms'][arm];bone['wrist']=list(target)
    angle=math.degrees(math.atan2(target[1]-bone['elbow'][1],target[0]-bone['elbow'][0]))
    poses={}
    for name,(rgb,path) in drawings.items():
        parts=components(rgb)
        white=[p for p in parts if p[2]>245]
        if not white:raise ValueError(f'No white cuff in {prefix}/{name}')
        cuff=max(white,key=lambda p:p[0]);anchor=cuff[1];scale=math.sqrt(area/cuff[0])
        pixels=np.asarray(rgb).astype('int16')
        excess=np.maximum(0,pixels[:,:,1]-np.maximum(pixels[:,:,0],pixels[:,:,2]))
        border=np.concatenate([excess[0],excess[-1],excess[:,0],excess[:,-1]])
        key_strength=int(np.median(border))
        cel=remove_green_matte(rgb,background_green=key_strength)
        scaled=cel.resize((round(cel.width*scale),round(cel.height*scale)),Image.Resampling.LANCZOS)
        actual=(scaled.width/cel.width,scaled.height/cel.height)
        offset=(round(200-anchor[0]*actual[0]),round(200-anchor[1]*actual[1]))
        box=scaled.getchannel('A').getbbox()
        placed=tuple(box[i]+offset[i%2] for i in range(4))
        if min(placed[:2])<1 or max(placed[2:])>399:
            raise ValueError(f'Hand cel clipped: {prefix}/{name} {placed}')
        canvas=Image.new('RGBA',(400,400));canvas.paste(scaled,offset)
        canvas.save(folder/f'{name}.png')
        pose={'file':f'{name}.png','anchor':[200,200],'canonical_angle':angle,
              'digits':4,'source':path.name,'source_sha256':digest(path),
              'registration':{'source_cuff':anchor.tolist(),'scale':actual,'offset':offset,
                              'green_key_strength':key_strength}}
        if arm=='cigarette':
            # The small, disconnected white endcap is farther from the cuff
            # than the cigarette body. This also handles a downward cigarette.
            ends=[p for p in white if p is not cuff]
            if not ends:raise ValueError(f'No cigarette end in {prefix}/{name}')
            end=max(ends,key=lambda p:math.dist(p[1],anchor))[1]
            pose['cigarette_tip']=[end[j]*actual[j]+offset[j] for j in (0,1)]
        poses[name]=pose
    write_json(folder/'library.json',{'version':1,'canvas':[400,400],
        'digit_convention':'Three fingers and one thumb; four digits total.', 'poses':poses})
    bone['library']=f'{prefix}/library.json'


def eye_plate(speaker,box):
    left,top,right,bottom=box
    image=Image.open(OUT/f'{speaker}-eyes-clean.png').convert('RGBA').resize(
        (right-left,bottom-top),Image.Resampling.LANCZOS)
    # Feather only the crop boundary, well outside both eyeballs.
    mask=Image.new('L',image.size)
    ImageDraw.Draw(mask).rectangle((2,2,image.width-3,image.height-3),fill=255)
    image.putalpha(mask.filter(ImageFilter.GaussianBlur(.7)))
    plate=Image.new('RGBA',SIZE);plate.paste(image,(left,top));plate.save(OUT/f'{speaker}-eye-plate.png')


def event(start,arm,down=False):
    hold='down' if down else 'up'
    keys=[[0,'relaxed',0],[.18,'relaxed',.22],[.32,'turn',.6],
          [.5,hold,1],[1.25,hold,1],[1.48,'sweep',.8],[2.15,'sweep',.8],
          [2.32,hold,.8],[2.48,'turn',.4],[2.65,'relaxed',0],[3,'relaxed',0]]
    return {'start':round(start,6),'end':round(start+3,6),'keys':keys}


def performance(timeline):
    original=read_json(BASE/'performance.json');duration=timeline['duration']
    result={'turns':original['turns'],'characters':{},'gestures':{}}
    runs=[]
    for turn in timeline['turns']:
        if runs and runs[-1]['speaker']==turn['speaker']:
            runs[-1]['end']=turn['end']
        else:runs.append(dict(turn))
    for speaker in ('host','guest'):
        channels={n:original['characters'][speaker][n] for n in ('blink','gaze')}
        lean={0:0,duration:0};last=0;sign=1 if speaker=='host' else -1
        tracks={'free':[],'cigarette':[]};index=0
        for run in runs:
            start,end=run['start'],run['end'];length=end-start
            if length<4:continue
            active=run['speaker']==speaker
            target=sign*(1.8 if active else -.65)
            lean[round(start,6)]=last
            lean[round(start+min(1.2,length*.2),6)]=target
            lean[round(end,6)]=target;last=target
            if not active:continue
            # One complete gesture at a conversational beat, then a held rest.
            arm='free' if index%2==0 else 'cigarette'
            tracks[arm].append(event(start+min(1.3,(length-3)/2),arm,arm=='cigarette'))
            if length>22:
                other='cigarette' if arm=='free' else 'free'
                tracks[other].append(event(start+length*.57,other,other=='cigarette'))
            index+=1
        channels['lean']=[[t,v] for t,v in sorted(lean.items())]
        result['characters'][speaker]=channels;result['gestures'][speaker]=tracks
    return result


def main():
    scene=Image.open(BASE/'neutral.png').convert('L')
    spec=read_json(BASE/'puppet.json');spec['version']=2
    background=Image.open(BASE/'clean-plate.png').convert('L')
    # Keep the static legs over a complete empty stage. Patching the chair only
    # inside the old silhouette leaves a visible hand-shaped upholstery seam.
    lower=Image.new('L',SIZE)
    for box in [(333,688,656,953),(837,688,1149,955)]:
        patch=scene.crop(box).point(lambda v:255 if v<85 else 0)
        lower.paste(patch,box[:2])
    lower=lower.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.35))
    background.paste(scene,(0,0),lower)
    background.save(OUT/'background.png')
    spec['background']='background.png'
    for speaker,char in spec['characters'].items():
        # Constrain the broad foreground matte to traced ink and actual jacket.
        mask=Image.open(BASE/char['mask']).convert('L')
        allowed=scene.point(lambda v:255 if v<85 else 0)
        ImageDraw.Draw(allowed).rectangle((0,0,SIZE[0],399),fill=255)
        shirt=[(262,370),(391,388),(431,535),(310,573)] if speaker=='host' else [(1038,376),(1210,355),(1230,541),(1050,583)]
        ImageDraw.Draw(allowed).polygon(shirt,fill=255)
        mask=ImageChops.multiply(mask,allowed.filter(ImageFilter.MaxFilter(3)))
        mask.save(OUT/char['mask'])
        char['eye_plate']=f'{speaker}-eye-plate.png'
        char.pop('cigarette_tip')
        # The space under a lifted hand is chair upholstery. Only restore the
        # small region of Fromm's jacket that the original hand actually covers.
        char['joint_overlaps']=([
            {'polygon':[[245,580],[269,588],[251,650],[235,681],[216,700],[219,625]],'gray':29}]
            if speaker=='host' else [
            {'polygon':[[1190,578],[1272,615],[1261,705],[1208,705],[1180,700]],'gray':29},
            {'polygon':[[970,438],[975,422],[995,410],[1018,407],[1018,546],[969,558],[969,510],[966,470]],'gray':27}])
        for arm,bone in char['arms'].items():
            mask=hand_mask(scene,speaker,arm)
            mask.save(OUT/bone['mask'])
            bone['cuff_cap']=f'{speaker}-{arm}-cuff-cap.png'
            bone['degrees']=(-32 if speaker=='host' else 32) if arm=='free' else (12 if speaker=='host' else -12)
            bone['joint_radius']=29 if arm=='free' else 22
            paths={('host','free'):[[149,441],[130,492],[111,554]],
                   ('host','cigarette'):[[424,441],[438,514],[472,553]],
                   ('guest','free'):[[1325,437],[1351,500],[1361,563]],
                   ('guest','cigarette'):[[990,433],[990,503],[961,567]]}
            bone['elbow']=paths[speaker,arm][-1]
            bake_hands(speaker,arm,char)
    spec['characters']['guest']['pupils']=[
        {'rest':[1017,253],'camera':[1029,253],'radius':4.2},
        {'rest':[1086,266],'camera':[1101,266],'radius':5}]
    eye_plate('host',(320,225,433,307));eye_plate('guest',(981,218,1154,304))
    write_json(OUT/'puppet.json',spec)
    write_json(OUT/'performance.json',performance(read_json(ROOT/'build/fromm-full-02/timeline.json')))
    rig=read_json(BASE/'rig.json');write_json(OUT/'rig.json',rig)
    print(OUT/'rig.json')


if __name__=='__main__':main()
