"""Register complete arm drawings at suit shoulder seams, with fixed handedness."""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image,ImageChops,ImageDraw
from klassic.cels import remove_green_matte
from klassic.project import digest,read_json,write_json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'assets/episodes/fromm-v7'
BASE=ROOT/'assets/episodes/fromm-v4'
PREVIOUS=ROOT/'assets/episodes/fromm-v5'
SIZE=(1448,1086)
ATTACHMENTS={('host','free'):([165,402],240,'right','near'),
             ('host','cigarette'):([393,412],204,'left','far'),
             ('guest','free'):([1324,403],262,'left','near'),
             ('guest','cigarette'):([1039,406],214,'right','far')}
TORSOS={
 'host':[(265,371),(144,395),(150,430),(162,473),(176,515),(165,537),
         (257,580),(243,637),(215,700),(450,750),(534,674),(479,615),
         (442,544),(435,501),(440,461),(431,425),(387,401),(376,389)],
 'guest':[(1040,391),(1010,406),(1005,438),(1001,499),(985,550),(976,593),
          (945,699),(1060,750),(1210,710),(1267,705),(1280,592),
          (1294,548),(1288,507),(1293,459),(1307,418),(1322,402),(1226,369),(1204,357)]}


def polygon(points):
    mask=Image.new('L',(SIZE[0]*4,SIZE[1]*4))
    ImageDraw.Draw(mask).polygon([(x*4,y*4) for x,y in points],fill=255)
    return mask.resize(SIZE,Image.Resampling.LANCZOS)


def seam_ink(points):
    """An authored continuous seam, drawn at the original ink's thickness."""
    canvas=Image.new('RGBA',(SIZE[0]*4,SIZE[1]*4))
    samples=[]
    p=[points[0],*points,points[-1]]
    for a,b,c,d in zip(p,p[1:],p[2:],p[3:]):
        for step in range(16):
            t=step/16
            samples.append(tuple(4*.5*((2*b[j])+(-a[j]+c[j])*t+
                (2*a[j]-5*b[j]+4*c[j]-d[j])*t*t+
                (-a[j]+3*b[j]-3*c[j]+d[j])*t*t*t) for j in (0,1)))
    samples.append(tuple(4*v for v in points[-1]))
    ImageDraw.Draw(canvas).line(samples,fill=(12,12,12,255),width=10,joint='curve')
    return canvas.resize(SIZE,Image.Resampling.LANCZOS)


CANVAS=(800,600)
ANCHOR=(400,90)
NEAR_SCALE=1.10


def largest_component(binary):
    count,labels,stats,_=cv2.connectedComponentsWithStats(binary.astype(np.uint8),8)
    if count<2:raise ValueError('No arm component found')
    return labels==1+np.argmax(stats[1:,cv2.CC_STAT_AREA])


def atlas_arm(path,index):
    atlas=Image.open(path).convert('RGB');w,h=atlas.width//3,atlas.height//2
    x,y=index%3*w,index//3*h
    # Overscan preserves ink and cigarette tips extending across nominal cells.
    source=atlas.crop((max(0,x-32),max(0,y-32),min(atlas.width,x+w+32),min(atlas.height,y+h+32)))
    rgb=np.asarray(source).astype(np.int16)
    excess=rgb[:,:,1]-np.maximum(rgb[:,:,0],rgb[:,:,2])
    key=int(np.median(np.concatenate((excess[0],excess[-1],excess[:,0],excess[:,-1]))))
    cel=remove_green_matte(source,background_green=key)
    rgba=np.array(cel);keep=largest_component(rgba[:,:,3]>12)
    keep=cv2.dilate(keep.astype(np.uint8),np.ones((3,3),np.uint8))>0
    rgba[~keep]=0;cel=Image.fromarray(rgba)
    sleeve=(rgba[:,:,:3].max(axis=2)<90)&(rgba[:,:,3]>128)
    sleeve=largest_component(cv2.erode(sleeve.astype(np.uint8),np.ones((7,7),np.uint8)))
    yy,xx=np.where(sleeve);top=int(yy.min())-3
    anchor=(float(np.median(xx[yy<=yy.min()+10])),top)
    return cel,anchor,int(yy.max())+3,key


def registered(cel,source_anchor,scale,angle=0):
    # One uniform shoulder-anchored scale; never stretch or mirror a limb.
    offset=(ANCHOR[0]-source_anchor[0]*scale,ANCHOR[1]-source_anchor[1]*scale)
    out=cel.transform(CANVAS,Image.Transform.AFFINE,
        (1/scale,0,-offset[0]/scale,0,1/scale,-offset[1]/scale),Image.Resampling.BICUBIC)
    if angle:out=out.rotate(-angle,resample=Image.Resampling.BICUBIC,center=ANCHOR)
    box=out.getchannel('A').point(lambda v:255 if v>12 else 0).getbbox()
    if not box or min(box[:2])<2 or box[2]>CANVAS[0]-2 or box[3]>CANVAS[1]-2:
        raise ValueError(f'Arm clipped at scale {scale}: {box}')
    return out


def cigarette_tip(cel):
    rgba=np.asarray(cel)
    white=(rgba[:,:,0]>230)&(rgba[:,:,3]>128)
    count,labels,stats,centers=cv2.connectedComponentsWithStats(white.astype(np.uint8),8)
    candidates=[centers[i] for i in range(1,count) if 8<stats[i,cv2.CC_STAT_AREA]<1200]
    if not candidates:raise ValueError('Cigarette cap not found')
    return list(map(float,max(candidates,key=lambda p:np.linalg.norm(p-ANCHOR))))


def bank(speaker,arm):
    shoulder,height,hand,layer=ATTACHMENTS[speaker,arm]
    name=f'{speaker}-{arm}';folder=OUT/name;folder.mkdir(exist_ok=True)
    poses={}
    if arm=='free':
        old=read_json(PREVIOUS/name/'library.json')
        for pose_name,old_pose in old['poses'].items():
            source=PREVIOUS/name/old_pose['file']
            cel=registered(Image.open(source).convert('RGBA'),old_pose['anchor'],NEAR_SCALE)
            cel.save(folder/f'{pose_name}.png')
            poses[pose_name]={'file':f'{pose_name}.png','anchor':list(ANCHOR),
                'anatomical_hand':hand,'digits':4,'source':str(source.relative_to(ROOT)),
                'source_sha256':digest(source),'scale_from_previous':NEAR_SCALE}
    else:
        source=PREVIOUS/f'{speaker}-cigarette-arms.png'
        _,origin,bottom,_=atlas_arm(source,0)
        scale=height/(bottom-origin[1])
        # Outward thumbs in the seated pose. The guest's source UP cell has an
        # ambiguous hidden finger, so use the clear three-finger sweep drawing
        # raised as a whole arm. No finger morphing or runtime hand mirroring.
        plan={'relaxed':(0,0),
              'up':(2,0) if speaker=='host' else (3,14),
              'sweep':(3,0),'down':(4,0)}
        for pose_name,(index,angle) in plan.items():
            raw,source_anchor,_,key=atlas_arm(source,index)
            cel=registered(raw,source_anchor,scale,angle);cel.save(folder/f'{pose_name}.png')
            poses[pose_name]={'file':f'{pose_name}.png','anchor':list(ANCHOR),
                'anatomical_hand':hand,'digits':4,'source':str(source.relative_to(ROOT)),
                'source_sha256':digest(source),'source_cell':index,
                'registration':{'source_shoulder':list(source_anchor),'scale':scale,
                    'green_key_strength':key,'shoulder_rotation_degrees':angle},
                'cigarette_tip':cigarette_tip(cel)}
    for path in folder.glob('*.png'):
        if path.name not in {p['file'] for p in poses.values()}:path.unlink()
    curve=list(range(256))
    if arm=='cigarette':
        # A render palette aligns cloth luminance while preserving black ink,
        # white cuffs, skin and alpha. No geometry is redrawn.
        source_gray,target_gray=(32,27) if speaker=='host' else (34,25)
        curve=[round(float(v)) for v in np.interp(range(256),[0,12,source_gray,64,255],[0,12,target_gray,64,255])]
    write_json(folder/'library.json',{'version':2,'canvas':list(CANVAS),'gray_curve':curve,
        'construction':'Uniformly scaled complete arms. Outward thumbs on far palm-up hands.',
        'anatomical_hand':hand,'poses':poses})
    return {'shoulder':shoulder,'degrees':0,'layer':layer,'anatomical_hand':hand,'library':name+'/library.json'}


def main():
    spec=read_json(BASE/'puppet.json');spec['version']=5
    spec['background']='../fromm-v4/background.png'
    for speaker,char in spec['characters'].items():
        core=polygon(TORSOS[speaker]);ImageDraw.Draw(core).rectangle((0,0,SIZE[0],385),fill=255)
        mask=ImageChops.multiply(Image.open(BASE/f'{speaker}-mask.png').convert('L'),core)
        for arm in ('free','cigarette'):
            mask=ImageChops.subtract(mask,Image.open(BASE/f'{speaker}-{arm}-arm.png').convert('L'))
        mask.save(OUT/f'{speaker}-body-mask.png');char['mask']=f'{speaker}-body-mask.png'
        char['eye_plate']='../fromm-v4/'+char['eye_plate']
        patch=Image.new('RGBA',SIZE)
        panels=([([(165,532),(257,570),(268,583),(244,685),(215,710),(203,602)],27)] if speaker=='host' else
                [([(1205,594),(1293,608),(1268,705),(1243,701),(1205,702)],26),
                 ([(1248,515),(1295,504),(1320,574),(1284,608),(1236,594)],27),
                 ([(1000,515),(1040,530),(1010,620),(968,620),(980,562)],27)])
        for points,gray in panels:
            alpha=polygon(points)
            solid=Image.new('RGBA',SIZE,(gray,gray,gray,255));patch.paste(solid,(0,0),alpha)
        patch.save(OUT/f'{speaker}-body-patch.png');char['body_patch']=f'{speaker}-body-patch.png'
        # The torso overlaps the far sleeve at this inked shoulder/side seam.
        # It moves with the torso, so the seam remains attached during a lean.
        seam=([(389,402),(427,426),(438,462),(435,500),(442,542)] if speaker=='host' else
              [(1026,399),(1010,407),(1005,440),(1001,499),(985,550),(976,590),(968,620)])
        ink=seam_ink(seam)
        ink.save(OUT/f'{speaker}-body-ink.png');char['body_ink']=f'{speaker}-body-ink.png'
        # The front of each outer chair arm sits in front of the trousers,
        # while the near hand/arm sits above it. Reuse the existing empty stage.
        front=([(0,594),(160,594),(181,599),(195,609),(205,626),(213,650),
                (220,697),(230,757),(240,792),(225,817),(0,817)] if speaker=='host' else
               [(1308,591),(1288,600),(1278,618),(1270,644),(1263,684),
                (1253,742),(1238,798),(1246,820),(1448,820),(1448,591)])
        chair=Image.open(ROOT/'assets/episodes/fromm-v3/clean-plate.png').convert('RGBA')
        chair.putalpha(polygon(front));chair.save(OUT/f'{speaker}-chair-front.png')
        char['chair_front']=f'{speaker}-chair-front.png'
        # Crossed trousers are in front of the far sleeve. Preserve the source
        # contour as an independent foreground layer rather than flattening it
        # into the stage behind all arms.
        lap_points=([(400,520),(421,529),(442,540),(456,563),(472,585),
                     (487,607),(502,630),(518,652),(532,668),(480,708),
                     (448,739),(398,740)] if speaker=='host' else
                    [(1072,526),(1110,530),(1115,741),(1008,760),(940,697),
                     (945,685),(958,665),(971,645),(984,625),(996,605),
                     (1009,585),(1023,565),(1040,545),(1052,535)])
        lap=Image.open(ROOT/'assets/episodes/fromm-v3/neutral.png').convert('RGBA')
        lap_mask=ImageChops.multiply(polygon(lap_points),lap.convert('L').point(lambda v:255 if v<45 else 0))
        lap.putalpha(lap_mask);lap.save(OUT/f'{speaker}-lap-front.png')
        char['lap_front']=f'{speaker}-lap-front.png'

        char.pop('joint_overlaps')
        char['arms']={arm:bank(speaker,arm) for arm in ('free','cigarette')}
    write_json(OUT/'puppet.json',spec)
    performance=read_json(BASE/'performance.json')
    timeline=read_json(ROOT/'build/fromm-full-02/timeline.json')
    turns={t['id']:t for t in timeline['turns']}
    performance['gestures']={speaker:{'free':[],'cigarette':[]} for speaker in ('host','guest')}
    # Gesture meanings are authored alongside the transcript, not triggered by
    # a periodic timer or by whether somebody happens to be speaking.
    for cue in read_json(Path(__file__).with_name('gesture-cues.json')):
        turn=turns[cue['turn']];start=round(turn['start']+cue['offset'],6)
        length=cue.get('duration',3.0);end=round(start+length,6)
        if start<turn['start'] or end>turn['end']:
            raise ValueError(f'Gesture exceeds its spoken line: {cue}')
        pose=cue['pose'];arm=cue['arm']
        if pose not in ('up','down','sweep') or (pose=='down' and arm!='cigarette'):
            raise ValueError(f'Invalid offering pose: {cue}')
        keys=[[0,'relaxed',0],[round(length*.16,6),pose,1],
              [round(length*.70,6),pose,1],[round(length*.88,6),'relaxed',0],[length,'relaxed',0]]
        performance['gestures'][turn['speaker']][arm].append({
            'start':start,'end':end,'keys':keys,'turn':cue['turn'],
            'meaning':cue['meaning'],'phrase':cue['phrase']})
    for tracks in performance['gestures'].values():
        for events in tracks.values():events.sort(key=lambda e:e['start'])
    write_json(OUT/'performance.json',performance)
    write_json(OUT/'rig.json',read_json(BASE/'rig.json'))
    print(OUT/'rig.json')


if __name__=='__main__':main()
