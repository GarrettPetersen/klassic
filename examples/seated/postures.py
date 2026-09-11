"""Register drawn postures and reuse the approved whole-arm banks.

All coordinates here are character-local. Rigid placements are authored per cel;
there is no runtime interpolation of a body mesh or a synthetic limb drawing.
"""
import copy
import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from klassic.cels import remove_green_matte
from klassic.project import read_json, digest


def mask_polygon(image, points):
    mask=Image.new('L', image.size)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in points],fill=255)
    result=image.copy();result.putalpha(ImageChops.multiply(image.getchannel('A'),mask))
    return result,mask


def rigid(point, transform):
    a=math.radians(transform['degrees']);x=point[0]-transform['origin'][0];y=point[1]-transform['origin'][1]
    return [transform['position'][0]+x*math.cos(a)-y*math.sin(a),
            transform['position'][1]+x*math.sin(a)+y*math.cos(a)]


def add_postures(baker, spec, folder):
    registration=read_json(folder/'registration.json');cfg=registration[spec['id']]
    def read_drawing(name):
        d=spec['drawings'][name];canvas=Image.new('RGBA',(720,960))
        canvas.alpha_composite(Image.open(baker.folder/d['file']),tuple(d['position']));return canvas
    def save(name,image,position=(0,0)):
        return baker.drawing(name,image,[position[i]+baker.crop[i] for i in (0,1)])
    def sheet(kind,count):
        entry=cfg[kind];path=folder/entry['file'];im=Image.open(path)
        if entry.get('matte')=='green':im=remove_green_matte(im.convert('RGB'),background_green=255)
        else:
            if im.mode!='RGBA' or im.getchannel('A').getextrema()[0]!=0:raise ValueError(f'{path}: expected genuine transparency')
        if 'gray_scale' in entry:
            curve=[round(v*entry['gray_scale']) for v in range(256)]
            im=im.point(curve*3+list(range(256)))
        w=im.width//count
        if w*count!=im.width:raise ValueError(f'{path}: inconsistent atlas cells')
        return [im.crop((i*w,0,(i+1)*w,im.height)).resize((round(w*entry['scale']),round(im.height*entry['scale'])),Image.Resampling.LANCZOS) for i in range(count)]
    body=read_drawing('body');head,_=mask_polygon(body,cfg['head_polygon'])
    if 'head_silhouette' in cfg:
        # The original film neck was not registered to the replacement face.
        # Keep only pixels inside its actual silhouette, including below the ear.
        head.putalpha(ImageChops.multiply(head.getchannel('A'),read_drawing(cfg['head_silhouette']).getchannel('A')))
    save('posture-head',head)
    if 'neck_bridge' in cfg:
        bridge=cfg['neck_bridge']
        reference=Image.open(folder/bridge['file']).convert('RGBA').resize(tuple(bridge['reference_size']),Image.Resampling.LANCZOS)
        neck,_=mask_polygon(reference,bridge['polygon'])
        # Match the portrait's flat skin gray; generated crop lighting must not
        # introduce a visible polygon-shaped shade change inside the cheek.
        gray=bridge['skin_gray']
        curve=[round(v*gray/170) if v<170 else gray if v<231 else round(gray+(v-230)*(255-gray)/25) for v in range(256)]
        neck=neck.point(curve*3+list(range(256)))
        save('posture-neck-bridge',neck,bridge['position'])
    original_collar,_=mask_polygon(body,cfg['original_collar'])
    save('posture-original-collar',original_collar)
    lap,_=mask_polygon(body,cfg['lap_polygon'])
    # Keep the original ink contour and original crossed-leg silhouette.
    save('posture-crossed-lap',lap)
    # Complete jackets are drawn behind the thighs. Cutting a jacket out of the
    # crossed pose cannot recover the hem that the original knee concealed.
    upright=sheet('upright',1)[0]
    save('posture-upright',upright,cfg['upright']['position'])
    def save_collar(name,cel,entry,points):
        collar,_=mask_polygon(cel,[[v*entry['scale'] for v in p] for p in points])
        save(name,collar,entry['position'])
    save_collar('posture-upright-collar',upright,cfg['upright'],cfg['upright']['collar'])
    # A complete seated pelvis supplies the volume beneath the jacket. It is
    # independent of the moving thigh cels and is never cropped at the waist.
    save('posture-pelvis',sheet('pelvis',2)[cfg['pelvis']['cell']],cfg['pelvis']['position'])
    for i,cel in enumerate(sheet('thighs',3)):
        save(f'posture-thighs-{i}',cel,cfg['thighs']['position'])
    for i,cel in enumerate(sheet('torso',2)):
        _,neck_mask=mask_polygon(cel,[[v*cfg['torso']['scale'] for v in p] for p in cfg['lean'][i]['neck_cutout']])
        cel.putalpha(ImageChops.subtract(cel.getchannel('A'),neck_mask))
        save(f'posture-torso-{i}',cel,cfg['torso']['position'])
        save_collar(f'posture-collar-{i}',cel,cfg['torso'],cfg['lean'][i]['collar'])
    # Replacement whole-arm drawings retain anatomical handedness; never flip
    # a hand or stretch a sleeve independently. Register at the shoulder cap.
    for name,cel,anchor in zip(('turn','up'),sheet('qualify',2),cfg['qualify']['anchors'],strict=True):
        position=[cfg['shoulders']['free'][j]-anchor[j]*cfg['qualify']['scale'] for j in (0,1)]
        save('free-'+name,cel,position)
    old_poses=copy.deepcopy(spec['poses']);old_actions=copy.deepcopy(spec['actions'])
    for pose in spec['poses'].values():
        pose['layers'].append({'drawing':'posture-original-collar','z':36})
    # Four settled postures share the same arm art and dialogue interface.
    def state_name(upper,lower):
        return {('upright','crossed'):'seated',('upright','open'):'seated_uncrossed',
                ('back','crossed'):'reclined_crossed',('back','open'):'reclined_uncrossed'}[upper,lower]
    def pose_name(upper,lower,gesture='neutral'):
        return gesture if (upper,lower)==('upright','crossed') else f'{upper}-{lower}-{gesture}'
    def create_pose(upper,lower,gesture='neutral'):
        name=pose_name(upper,lower,gesture)
        if name in spec['poses']:return name
        base=old_poses[gesture];layers=[];offset=[0,0];arm_transforms={}
        if upper=='upright':
            layers.extend([{'drawing':'posture-upright','z':20},{'drawing':'posture-head','z':35},
                           {'drawing':'posture-upright-collar','z':36}])
        else:
            i=0 if upper=='leaning' else 1;lean=cfg['lean'][i];entry=cfg['torso']
            place=lambda p:[round(p[j]*entry['scale']+entry['position'][j],3) for j in (0,1)]
            offset=[place(lean['neck'])[j]-cfg['head_anchor'][j] for j in (0,1)]
            layers.extend([{'drawing':f'posture-torso-{i}','z':20},
                {'drawing':'posture-head','z':35,'transform':{'origin':[0,0],'position':offset,'degrees':0}},
                {'drawing':f'posture-collar-{i}','z':36}])
            if 'neck_bridge' in cfg:
                layers.append({'drawing':'posture-neck-bridge','z':51,
                               'transform':{'origin':[0,0],'position':offset,'degrees':0}})
            for arm in ('free','cigarette'):
                arm_transforms[arm]={'origin':cfg['shoulders'][arm],'position':place(lean[arm]),'degrees':lean['degrees'][arm]}
        if lower=='crossed':
            layers.extend([{'drawing':'legs','z':0},{'drawing':'posture-crossed-lap','z':25},{'drawing':'lap-front','z':26}])
        else:
            index={'lifting':0,'lowering':1,'open':2}[lower]
            layers.extend([{'drawing':'posture-pelvis','z':15},
                           {'drawing':f'posture-thighs-{index}','z':25}])
        for arm,depth in [('cigarette',10),('free',40)]:
            drawing=next(l['drawing'] for l in base['layers'] if l['drawing'].startswith(arm+'-'))
            layer={'drawing':drawing,'z':depth}
            if arm in arm_transforms:layer['transform']=arm_transforms[arm]
            layers.append(layer)
        tip=base['attachments']['cigarette']
        if 'cigarette' in arm_transforms:tip=rigid(tip,arm_transforms['cigarette'])
        spec['poses'][name]={'layers':layers,'attachments':{'cigarette':tip},'overlay_offsets':{'mouth':offset,'eyes':offset}}
        return name
    def clip(name,label,intent,start,end,frames):
        spec['actions'][name]={'label':label,'intent':intent,'from':start,'to':end,'loop':False,
            'frames':[{'pose':p,'ticks':t} for p,t in frames]}
    for upper in ('upright','back'):
        for lower in ('crossed','open'):
            state=state_name(upper,lower);neutral=create_pose(upper,lower)
            idle='idle' if state=='seated' else 'idle-'+state
            spec['states'][state]={'pose':neutral,'idle':idle}
            spec['actions'][idle]={'from':state,'to':state,'loop':True,'frames':[{'pose':neutral,'ticks':24}]}
            for action in ('offer','concede','qualify'):
                name=action if state=='seated' else f'{action}-{state}'
                frames=[(create_pose(upper,lower,f['pose']),f['ticks']) for f in old_actions[action]['frames']]
                clip(name,action.capitalize(),action,state,state,frames)
            opposite='open' if lower=='crossed' else 'crossed';destination=state_name(upper,opposite)
            steps=[(create_pose(upper,l),t) for l,t in [('crossed',3),('lifting',4),('lowering',4),('open',5)]]
            if lower=='open':steps=list(reversed(steps))
            intent='uncross' if lower=='crossed' else 'cross'
            clip(f'{intent}-{state}','Uncross legs' if intent=='uncross' else 'Cross legs',intent,state,destination,steps)
            destination=state_name('back' if upper=='upright' else 'upright',lower)
            steps=[(create_pose(u,lower),t) for u,t in [('upright',3),('leaning',4),('back',5)]]
            if upper=='back':steps=list(reversed(steps))
            intent='lean_back' if upper=='upright' else 'sit_upright'
            clip(f'{intent}-{state}','Lean back' if intent=='lean_back' else 'Sit upright',intent,state,destination,steps)
    spec['artwork']['postures']={'registration_sha256':digest(folder/'registration.json'),
        'sources':{cfg[k]['file']:digest(folder/cfg[k]['file']) for k in ('pelvis','thighs','torso','upright','qualify')},
        'arms':'Registered whole-arm sprites, including corrected anatomical near-hand qualify cels; rigid translation/rotation only.'}
    if 'neck_bridge' in cfg:spec['artwork']['postures']['sources'][cfg['neck_bridge']['file']]=digest(folder/cfg['neck_bridge']['file'])
    return spec


def table_foreground(background,output):
    """Extract the existing foreground table without repainting its artwork."""
    im=Image.open(background).convert('RGBA');gray=im.convert('L');mask=Image.new('L',im.size)
    for seed in [(700,855),(550,817),(900,819)]:
        region=gray.point(lambda v:255 if v>70 else 0).filter(ImageFilter.MinFilter(5))
        ImageDraw.floodfill(region,seed,128)
        region=region.point(lambda v:255 if v==128 else 0)
        box=region.getbbox()
        if not box or box[0]<340 or box[1]<750 or box[2]>1100 or box[3]>930:
            raise ValueError(f'Table outline no longer encloses region {seed}: {box}')
        mask=ImageChops.lighter(mask,region.filter(ImageFilter.MaxFilter(9)))
    d=ImageDraw.Draw(mask)
    d.ellipse((526,757,601,775),fill=255)
    d.ellipse((873,772,946,791),fill=255)
    for polygon in [
        [(498,885),(519,886),(479,1015),(475,1019),(465,1016),(467,1003)],
        [(904,906),(927,907),(934,1027),(930,1032),(921,1032),(917,1026)],
        [(985,907),(1006,905),(1023,967),(1021,972),(1013,972),(1008,969)],
        [(500,774),(488,774),(479,783),(476,803),(479,824),(488,834),(500,834)],
        [(940,787),(951,783),(962,790),(967,802),(965,824),(958,839),(946,846),(940,845)],
        [(664,799),(675,794),(717,792),(755,794),(771,800),(771,829),(760,835),(687,837),(666,832)]
    ]:d.polygon(polygon,fill=255)
    im.putalpha(mask);box=mask.getbbox();path=output/'scene/table-front.png';im.crop(box).save(path)
    return {'file':'scene/table-front.png','sha256':digest(path),'position':list(box[:2]),'z':70}
