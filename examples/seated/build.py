"""Bake existing artwork into independent, drawing-only character packages.

This adapter knows about the old film layout. The browser runtime does not.
No mesh transforms, skeletal animation, morphs, or generated audio run here.
"""
import argparse
import math
from pathlib import Path
import shutil
import statistics
import subprocess

from klassic.host import native_python
native_python()

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from klassic.cels import remove_green_matte
from klassic.motion import MouthTrack
from klassic.project import digest, read_json, write_json
from klassic.render import Compositor, subtitle_chunks
from postures import add_postures, table_foreground

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(__file__).parent
DEFAULT=ROOT/'build/seated-mvp'


def original_turn(speaker, folder, reference):
    """Extract the saved middle hand pose with a connected, overscanned matte."""
    atlas=Image.open(ROOT/f'assets/episodes/fromm-v5/{speaker}-cigarette-arms.png').convert('RGB')
    w,h=atlas.width//3,atlas.height//2
    rgb=atlas.crop((w-32,0,2*w+32,h+32))
    border=[rgb.getpixel((x,0)) for x in range(rgb.width)]
    key=round(statistics.median(g-max(r,b) for r,g,b in border))
    raw=remove_green_matte(rgb,background_green=key)
    mask=raw.getchannel('A').point(lambda v:255 if v>12 else 0)
    seed=(128,110) if speaker=='host' else (420,110)
    if mask.getpixel(seed)!=255:raise ValueError('Source shoulder seed moved')
    ImageDraw.floodfill(mask,seed,128)
    keep=mask.point(lambda v:255 if v==128 else 0).filter(ImageFilter.MaxFilter(3))
    raw.putalpha(ImageChops.multiply(raw.getchannel('A'),keep))
    dark=ImageChops.multiply(raw.convert('L').point(lambda v:255 if v<90 else 0),keep)
    top=dark.getbbox()[1]
    xs=[x for y in range(top+3,top+13) for x in range(dark.width) if dark.getpixel((x,y))]
    anchor=(statistics.median(xs),top)
    scale=reference['registration']['scale'];target=reference['anchor']
    offset=(target[0]-anchor[0]*scale,target[1]-anchor[1]*scale)
    cel=raw.transform((800,600),Image.Transform.AFFINE,(1/scale,0,-offset[0]/scale,0,1/scale,-offset[1]/scale),Image.Resampling.BICUBIC)
    curve=read_json(folder/'library.json')['gray_curve']
    return cel.point(curve*3+list(range(256)))


def cigarette_tip(cel,anchor):
    alpha=cel.getchannel('A');gray=cel.convert('L')
    pixels={(x,y) for y in range(cel.height) for x in range(cel.width)
            if alpha.getpixel((x,y))>128 and gray.getpixel((x,y))>230}
    candidates=[]
    while pixels:
        seed=pixels.pop();component=[seed];todo=[seed]
        while todo:
            x,y=todo.pop()
            for neighbor in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if neighbor in pixels:pixels.remove(neighbor);component.append(neighbor);todo.append(neighbor)
        if 8<len(component)<1200:
            candidates.append([sum(p[i] for p in component)/len(component) for i in (0,1)])
    if not candidates:raise ValueError('Cigarette cap is missing from transition drawing')
    return max(candidates,key=lambda p:math.dist(p,anchor))


class CharacterBaker:
    def __init__(self, out, config, comp):
        self.out=out;self.config=config;self.comp=comp;self.speaker=config['source_speaker']
        self.folder=out/'characters'/config['id'];self.folder.mkdir(parents=True,exist_ok=True)
        self.drawings={};self.crop=config['crop']

    def drawing(self,name,image,position=(0,0)):
        image=image.convert('RGBA');box=image.getchannel('A').getbbox()
        if not box:raise ValueError(f'Empty drawing {name}')
        path=self.folder/f'{name}.png';image.crop(box).save(path)
        self.drawings[name]={'file':path.name,'sha256':digest(path),
            'position':[position[0]+box[0]-self.crop[0],position[1]+box[1]-self.crop[1]],
            'size':[box[2]-box[0],box[3]-box[1]]}
        return name

    def build(self):
        comp=self.comp;p=comp.puppet;s=self.speaker;char=p.spec['characters'][s]
        # The scene already has a mouth-free face. Mouth keys (including the
        # resting X cel) belong exclusively to the overlay, never the body/head.
        source=comp.scene.copy()
        original=source.convert('RGBA');original.putalpha(p.masks[s])
        body=Image.alpha_composite(p.body_patches[s],original)
        body=Image.alpha_composite(body,p.body_ink[s])
        foregrounds=[]
        for description,(position,foreground,mask) in zip(comp.rig['mouths'][s]['foreground'],comp.foregrounds[s],strict=True):
            clean_mask=mask
            if description['name']=='far_hair':
                # Hair/ink is below 110; the accidentally captured wall is not.
                clean_mask=ImageChops.multiply(mask,foreground.convert('L').point(lambda v:255 if v<110 else 0))
                removed=ImageChops.subtract(mask,clean_mask)
                cutout=Image.new('L',body.size);cutout.paste(removed,position)
                body.putalpha(ImageChops.subtract(body.getchannel('A'),cutout))
            foregrounds.append((position,foreground,clean_mask))
        # A silhouette mask inherited from the closed muzzle can include room
        # pixels outside the mouth-free face. Those pixels belong to the set.
        for polygon in self.config.get('mouth_background_cutouts',[]):
            cutout=Image.new('L',body.size)
            ImageDraw.Draw(cutout).polygon([tuple(point) for point in polygon],fill=255)
            body.putalpha(ImageChops.subtract(body.getchannel('A'),cutout))
        # The film's masks could include set pixels because the head never moved
        # away from that background. A moving sprite needs its actual silhouette.
        if s=='guest':
            face=Image.new('L',body.size)
            face.paste(comp.cels[s][1]['X'].getchannel('A'),comp.cels[s][0])
            region=Image.new('L',body.size)
            ImageDraw.Draw(region).rectangle((self.crop[0],0,self.crop[2],self.crop[1]+310),fill=255)
            outside=ImageChops.subtract(region,face)
            body.putalpha(ImageChops.subtract(body.getchannel('A'),outside))
        self.drawing('body',body)
        arm_drawings={};turn_tip=None
        for arm in ('free','cigarette'):
            library=p.arm_libraries[s][arm];bone=char['arms'][arm]
            selected=('relaxed','turn','up') if arm=='free' else ('relaxed','up','down')
            poses={name:library.cels[name] for name in selected}
            metadata=library.spec['poses']
            if arm=='cigarette':
                poses['turn']=original_turn(s,library.paths[0].parent,metadata['relaxed'])
                turn_tip=cigarette_tip(poses['turn'],metadata['relaxed']['anchor'])
            for name,cel in poses.items():
                anchor=metadata['relaxed']['anchor']
                position=[bone['shoulder'][i]-anchor[i] for i in (0,1)]
                arm_drawings[arm,name]=self.drawing(f'{arm}-{name}',cel,position)
        poses={}
        for name,free,far in [('neutral','relaxed','relaxed'),('offer-turn','relaxed','turn'),
            ('offer','relaxed','up'),('concede','relaxed','down'),
            ('qualify-turn','turn','relaxed'),('qualify','up','relaxed')]:
            layers=[(arm_drawings['cigarette',far],10),(arm_drawings['free',free],40)]
            # Props remain attached to the selected drawing, not a global point.
            tip=turn_tip if far=='turn' else p.arm_libraries[s]['cigarette'].spec['poses'][far]['cigarette_tip']
            anchor=p.arm_libraries[s]['cigarette'].spec['poses']['relaxed']['anchor']
            shoulder=char['arms']['cigarette']['shoulder']
            poses[name]={'layers':[{'drawing':drawing,'z':z} for drawing,z in layers],
                'attachments':{'cigarette':[tip[i]-anchor[i]+shoulder[i]-self.crop[i] for i in (0,1)]}}
        bank=comp.transitions[s][1];mouths=dict(bank.cells)
        for pair,cels in bank.pairs.items():
            mouths.update({f'{pair}-{i}':cel for i,cel in enumerate(cels,1)})
        mouth_ids={}
        mouth_names={id(cel):name for name,cel in mouths.items()}
        for name,cel in mouths.items():
            layer=Image.new('RGBA',comp.scene.size)
            layer.alpha_composite(cel,comp.cels[s][0])
            for position,foreground,mask in foregrounds:
                front=foreground.convert('RGBA');front.putalpha(mask);layer.alpha_composite(front,position)
            mouth_ids[name]=self.drawing('mouth-'+name,layer)
        eye_ids={}
        for gaze_name,gaze in [('partner',0),('camera',1)]:
            for blink_name,blink in [('open',0),('half',.5),('closed',1)]:
                eye_image=comp.scene.copy();p.eyes(eye_image,s,{'gaze':gaze,'blink':blink})
                eye_image=eye_image.convert('RGBA')
                eye_mask=Image.new('L',comp.scene.size)
                for mask in p.eye_masks[s]:eye_mask=ImageChops.lighter(eye_mask,mask)
                eye_image.putalpha(eye_mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(.5)))
                name=f'{gaze_name}-{blink_name}';eye_ids[name]=self.drawing('eyes-'+name,eye_image)
        def action(transition,hold):
            frames=[('neutral',2),(transition,2),(hold,23),(transition,2),('neutral',3)]
            return {'from':'seated','to':'seated','loop':False,
                'frames':[{'pose':pose,'ticks':ticks} for pose,ticks in frames]}
        actions={'idle':{'from':'seated','to':'seated','loop':True,'frames':[{'pose':'neutral','ticks':24}]},
            'offer':action('offer-turn','offer'),'concede':action('offer-turn','concede'),
            'qualify':action('qualify-turn','qualify')}
        spec={'version':1,'id':self.config['id'],'name':self.config['name'],'fps':24,
            'origin':[char['waist'][i]-self.crop[i] for i in (0,1)],
            'initial_state':'seated','states':{'seated':{'pose':'neutral','idle':'idle'}},
            'drawings':self.drawings,'poses':poses,'actions':actions,
            'overlays':{'mouth':{'z':50,'drawings':mouth_ids},'eyes':{'z':60,'drawings':eye_ids}},
            'artwork':{'status':'Existing interview test cast; not the original game cast.',
                'hands':{'free':char['arms']['free']['anatomical_hand'],'cigarette':char['arms']['cigarette']['anatomical_hand']},
                'digits':4,'playback':'Saved drawings only; no bone/mesh deformation or crossfades.'}}
        add_postures(self,spec,ROOT/'assets/episodes/seated-postures')
        write_json(self.folder/'character.json',spec)
        return spec,mouth_names


def build(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    cast=read_json(SOURCE/'cast.json');story=read_json(SOURCE/'story.json')
    timeline=read_json(SOURCE/cast['timeline'])
    comp=Compositor(timeline,(SOURCE/cast['rig']).resolve(),1440,False)
    packages={};placements=[];mouth_names={};characters={}
    for config in cast['characters']:
        spec,names=CharacterBaker(output,config,comp).build();actor=config['actor']
        packages[actor]=spec;mouth_names[actor]=names;characters[spec['id']]={'file':f'characters/{spec["id"]}/character.json','sha256':digest(output/f'characters/{spec["id"]}/character.json')}
        placements.append({'id':actor,'character':spec['id'],
            'position':comp.puppet.spec['characters'][config['source_speaker']]['waist'],'scale':1,'z':0})
    (output/'scene').mkdir(exist_ok=True)
    background=ROOT/'assets/episodes/fromm-v3/clean-plate.png'
    shutil.copyfile(background,output/'scene/chair-backs-and-set.png')
    scene={'version':1,'id':'studio','size':list(comp.scene.size),
        'background':{'file':'scene/chair-backs-and-set.png','sha256':digest(output/'scene/chair-backs-and-set.png')},'actors':placements,'furniture':[],
        'paths':{},'seats':{},'interactions':{}}
    scene['foregrounds']=[table_foreground(background,output)]
    for config in cast['characters']:
        # Use the chair's actual inked foreground contour. Cutting an arbitrary
        # polygon through the cushion would create an unoutlined step in the hip.
        speaker=config['source_speaker'];front=comp.puppet.chair_fronts[speaker]
        box=front.getchannel('A').getbbox();path=output/f'scene/{speaker}-chair-near-arm.png'
        front.crop(box).save(path)
        rear=Image.open(background).convert('RGBA')
        rear_box=(0,430,607,925) if speaker=='host' else (840,430,1448,925)
        mask=Image.new('L',rear.size);ImageDraw.Draw(mask).rectangle(rear_box,fill=255)
        rear.putalpha(ImageChops.subtract(mask,front.getchannel('A')))
        rear_path=output/f'scene/{speaker}-chair-rear.png';rear.crop(rear_box).save(rear_path)
        scene['furniture'].append({'id':config['actor']+'-chair','seat':config['actor'],
            'rear':{'file':f'scene/{rear_path.name}','sha256':digest(rear_path),'position':list(rear_box[:2]),'z':-50},
            'front':{'file':f'scene/{path.name}','sha256':digest(path),'position':list(box[:2]),'z':30},
            'ordering':'Rear chair < legs/body/lap < near chair arm < resting near hand'})
        placement=placements[len(scene['seats'])];spec=packages[config['actor']]
        scene['seats'][config['actor']]={'position':[placement['position'][i]+([350,635][i]-spec['origin'][i])*placement['scale'] for i in range(2)],'activity':'seated',
            'view':spec['states']['seated']['view']}
    turns={t['id']:t for t in timeline['turns']};takes={}
    (output/'audio').mkdir(exist_ok=True)
    for node in story['nodes'].values():
        if node['kind']!='line' or node['take'] in takes:continue
        take_id=node['take'];turn=turns[take_id];duration=turn['end']-turn['start'];actor=node['actor']
        source_speaker=next(c['source_speaker'] for c in cast['characters'] if c['actor']==actor)
        if turn['speaker']!=source_speaker:raise ValueError('Story assigned audio to wrong character')
        audio=output/f'audio/{take_id}.m4a'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(turn['start']),'-i',str((SOURCE/cast['dialogue']).resolve()),
            '-t',str(duration),'-c:a','aac','-b:a','128k',str(audio)],check=True)
        local={**turn,'start':0,'end':duration}
        track=MouthTrack([local],source_speaker,duration);bank=comp.transitions[source_speaker][1]
        frames=[mouth_names[actor][id(bank.frame(*track.sample(i/24,.09)))] for i in range(math.ceil(duration*24))]
        captions=subtitle_chunks(local)
        takes[take_id]={'actor':actor,'file':f'audio/{audio.name}','sha256':digest(audio),'duration':duration,
            'fps':24,'frames':frames,'captions':captions,'text':turn['text']}
    project={'version':2,'title':'On the record','characters':characters,'scenes':{'studio':scene},'initial_scene':'studio','story':story,'takes':takes,
        'source_note':'Existing Krusty/Fromm test artwork and recreated voices. Game characters will be original.',
        'provenance':{'cast':digest(SOURCE/'cast.json'),'story':digest(SOURCE/'story.json'),
            'timeline':digest(SOURCE/cast['timeline']),'dialogue':digest(SOURCE/cast['dialogue']),
            'rig':digest(SOURCE/cast['rig']),'puppet_inputs':comp.puppet.hashes()}}
    write_json(output/'project.json',project)
    print(output/'project.json')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=DEFAULT)
    build(parser.parse_args().out)
