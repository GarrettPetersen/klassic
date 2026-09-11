"""Bake complete drawn bodies with chair occlusion and separate heads/arms."""
import copy
import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from klassic.cels import remove_green_matte
from klassic.project import read_json, digest


def mask_polygon(image, points):
    mask=Image.new('L',image.size)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in points],fill=255)
    result=image.copy();result.putalpha(ImageChops.multiply(image.getchannel('A'),mask))
    return result,mask


def rigid(point,transform):
    a=math.radians(transform['degrees']);x=point[0]-transform['origin'][0];y=point[1]-transform['origin'][1]
    return [transform['position'][0]+x*math.cos(a)-y*math.sin(a),
            transform['position'][1]+x*math.sin(a)+y*math.cos(a)]


def body_atlas(folder,entry):
    """Normalize export resolution, retaining the authored cell coordinates."""
    image=Image.open(folder/entry['file']).convert('RGB');size=entry['reference_size']
    if abs(image.width/image.height-size[0]/size[1])>.002:
        raise ValueError(f"Body atlas aspect changed: {entry['file']}")
    image=remove_green_matte(image).resize(tuple(size),Image.Resampling.LANCZOS)
    cols,rows=entry['grid'];w,h=size[0]//cols,size[1]//rows
    if w*cols!=size[0] or h*rows!=size[1]:raise ValueError('Body atlas cells must have integer dimensions')
    pad=entry['overscan'];cells=[]
    for y in range(rows):
        for x in range(cols):
            cel=image.crop((x*w-pad,y*h,(x+1)*w+pad,(y+1)*h))
            mask=cel.getchannel('A').point(lambda v:255 if v>128 else 0)
            seed=None
            for row in range(h):
                xs=[col for col in range(pad,w+pad) if mask.getpixel((col,row))]
                if len(xs)>5:seed=(xs[len(xs)//2],row);break
            if seed is None:raise ValueError('Empty body atlas cell')
            ImageDraw.floodfill(mask,seed,128)
            keep=mask.point(lambda v:255 if v==128 else 0)
            if keep.histogram()[255]<5000:raise ValueError('Disconnected or empty body silhouette')
            cel.putalpha(ImageChops.multiply(cel.getchannel('A'),keep.filter(ImageFilter.MaxFilter(3))))
            cells.append(cel)
    return cells


def add_postures(baker,spec,folder):
    registration=read_json(folder/'registration.json')
    if registration['version']!=2:raise ValueError('Expected complete-body pose registration v2')
    cfg=registration[spec['id']]
    def read_drawing(name):
        d=spec['drawings'][name];canvas=Image.new('RGBA',(720,960))
        canvas.alpha_composite(Image.open(baker.folder/d['file']),tuple(d['position']));return canvas
    def save(name,image,position=(0,0)):
        return baker.drawing(name,image,[position[i]+baker.crop[i] for i in (0,1)])
    def fit_head(image):
        """Uniformly size all face cels around the same neck attachment."""
        scale=cfg['head_scale'];x,y=cfg['head_anchor']
        if not math.isfinite(scale) or scale<=0:raise ValueError('Invalid head scale')
        if scale==1:return image
        # Premultiplied linear sampling avoids bright overshoot along cutout seams.
        return image.convert('RGBa').transform(image.size,Image.Transform.AFFINE,
            (1/scale,0,x*(1-1/scale),0,1/scale,y*(1-1/scale)),Image.Resampling.BILINEAR).convert('RGBA')
    head,_=mask_polygon(read_drawing('body'),cfg['head_polygon'])
    if 'head_silhouette' in cfg:
        head.putalpha(ImageChops.multiply(head.getchannel('A'),read_drawing(cfg['head_silhouette']).getchannel('A')))
    save('posture-head',fit_head(head))
    face_drawings={name for overlay in spec['overlays'].values() for name in overlay['drawings'].values()}
    for name in face_drawings:save(name,fit_head(read_drawing(name)))
    neck=cfg.get('neck_patch')
    if neck:
        source=Image.open(folder/neck['file']).convert('RGBA').resize(tuple(neck['reference_size']),Image.Resampling.LANCZOS)
        width=source.width//2;gray=neck['skin_gray']
        curve=[round(v*gray/170) if v<170 else gray if v<231 else round(gray+(v-230)*(255-gray)/25) for v in range(256)]
        for i,polygon in enumerate(neck['polygons']):
            patch,_=mask_polygon(source.crop((i*width,0,(i+1)*width,source.height)),polygon)
            patch=patch.point(curve*3+list(range(256)))
            canvas=Image.new('RGBA',head.size);canvas.alpha_composite(patch,tuple(neck['position']))
            save(f'posture-neck-{i}',fit_head(canvas))
    # Corrected whole near arms have fixed anatomical handedness in both cels.
    entry=cfg['qualify'];im=Image.open(folder/entry['file'])
    if entry['matte']=='green':im=remove_green_matte(im.convert('RGB'))
    elif im.mode!='RGBA' or im.getchannel('A').getextrema()[0]!=0:raise ValueError('Qualify requires transparent art')
    w=im.width//2
    if 2*w!=im.width:raise ValueError('Qualify atlas cell width changed')
    for i,(name,anchor) in enumerate(zip(('turn','up'),entry['anchors'],strict=True)):
        cel=im.crop((i*w,0,(i+1)*w,im.height)).resize((round(w*entry['scale']),round(im.height*entry['scale'])),Image.Resampling.LANCZOS)
        save('free-'+name,cel,[cfg['shoulders']['free'][j]-anchor[j]*entry['scale'] for j in (0,1)])
    atlases={name:body_atlas(folder,entry) for name,entry in cfg['atlases'].items()}
    for name,pose in cfg['poses'].items():
        entry=cfg['atlases'][pose['atlas']];cel=atlases[pose['atlas']][pose['cell']]
        position=[entry['position'][i]+pose['body_offset'][i] for i in (0,1)]
        body=Image.new('RGBA',(800,960));body.alpha_composite(cel,(position[0]-entry['overscan'],position[1]))
        save('posture-body-'+name,body)
        # These copies share pixels and placement with the complete body. They
        # only specify which side of the chair/head an existing contour occupies.
        for part,polygon in [('legs-front',pose['leg_front_polygon']),('collar',pose['collar_polygon'])]:
            piece,_=mask_polygon(body,polygon);save('posture-'+part+'-'+name,piece)
        if neck and pose['neck_rim']:
            ox,oy=pose['head_offset']
            rim,_=mask_polygon(body,[[x+ox,y+oy] for x,y in neck['rim_polygon']])
            face=Image.new('L',body.size)
            face.paste(read_drawing('mouth-X').getchannel('A'),(round(ox),round(oy)))
            rim.putalpha(ImageChops.subtract(rim.getchannel('A'),face))
            save('posture-neck-rim-'+name,rim)
    old_poses=copy.deepcopy(spec['poses']);old_actions=copy.deepcopy(spec['actions'])
    view='three-quarter-right' if spec['id']=='krusty-study' else 'three-quarter-left'
    spec['activities']={'seated':{'label':'Seated conversation','views':[view]}}
    spec['poses']={};spec['actions']={};spec['states']={}
    def state_name(upper,lower):
        return {('upright','crossed'):'seated',('upright','open'):'seated_uncrossed',
                ('back','crossed'):'reclined_crossed',('back','open'):'reclined_uncrossed'}[upper,lower]
    def create_pose(upper,lower,gesture='neutral'):
        body_name=f'{upper}-{lower}';name=f'{body_name}-{gesture}'
        if name in spec['poses']:return name
        registration=cfg['poses'][body_name];offset=registration['head_offset'];arms=registration['arms'];base=old_poses[gesture]
        layers=[{'drawing':'posture-body-'+body_name,'z':20},
                {'drawing':'posture-legs-front-'+body_name,'z':32},
                {'drawing':'posture-head','z':35,'transform':{'origin':[0,0],'position':offset,'degrees':0}},
                {'drawing':'posture-collar-'+body_name,'z':36}]
        if neck:
            layers.append({'drawing':f'posture-neck-{registration["neck_cell"]}','z':51,
                'transform':{'origin':[0,0],'position':offset,'degrees':0}})
            if registration['neck_rim']:layers.append({'drawing':'posture-neck-rim-'+body_name,'z':52})
        for arm,depth in [('cigarette',10),('free',40)]:
            drawing=next(l['drawing'] for l in base['layers'] if l['drawing'].startswith(arm+'-'))
            layers.append({'drawing':drawing,'z':depth,'transform':arms[arm]})
        anchors={'neck':[cfg['head_anchor'][i]+offset[i] for i in (0,1)]}
        for arm in ('free','cigarette'):
            side=spec['artwork']['hands'][arm]
            anchors['shoulder-'+side]=arms[arm]['position']
        contacts=[{'id':'seat','kind':'seat','point':[350,635],'locked':True}]
        # Register floor contacts from the two isolated lower-leg silhouettes.
        # These are review markers; visual acceptance remains a separate step.
        body_image=read_drawing('posture-body-'+body_name)
        alpha=body_image.getchannel('A');floor=alpha.getbbox()[3]
        spans=[];start=None
        for x in range(alpha.width):
            visible=any(alpha.getpixel((x,y))>128 for y in range(max(0,floor-12),floor))
            if visible and start is None:start=x
            if start is not None and (not visible or x==alpha.width-1):
                if x-start>10:spans.append((start,x))
                start=None
        for i,(left,right) in enumerate(spans):contacts.append({'id':f'foot-{i}','kind':'foot','point':[(left+right)/2,floor-1],'locked':lower=='open'})
        spec['poses'][name]={'layers':layers,'anchors':anchors,'contacts':contacts,'attachments':{'cigarette':rigid(base['attachments']['cigarette'],arms['cigarette'])},
            'overlay_offsets':{'mouth':offset,'eyes':offset}}
        return name
    def clip(name,label,intent,start,end,frames):
        spec['actions'][name]={'label':label,'intent':intent,'from':start,'to':end,'loop':False,
            'frames':[{'pose':p,'ticks':t} for p,t in frames]}
    for upper in ('upright','back'):
        for lower in ('crossed','open'):
            state=state_name(upper,lower);neutral=create_pose(upper,lower);idle='idle-'+state
            spec['states'][state]={'pose':neutral,'idle':idle,'activity':'seated','view':view}
            spec['actions'][idle]={'from':state,'to':state,'loop':True,'frames':[{'pose':neutral,'ticks':24}]}
            for action in ('offer','concede','qualify'):
                name=action if state=='seated' else f'{action}-{state}'
                frames=[(create_pose(upper,lower,f['pose']),f['ticks']) for f in old_actions[action]['frames']]
                clip(name,action.capitalize(),action,state,state,frames)
            opposite='open' if lower=='crossed' else 'crossed';destination=state_name(upper,opposite)
            frames=[(create_pose(upper,l),t) for l,t in [('crossed',3),('lifting',5),('open',6)]]
            if lower=='open':frames=list(reversed(frames))
            intent='uncross' if lower=='crossed' else 'cross'
            clip(f'{intent}-{state}','Uncross legs' if intent=='uncross' else 'Cross legs',intent,state,destination,frames)
            destination=state_name('back' if upper=='upright' else 'upright',lower)
            frames=[(create_pose(u,lower),t) for u,t in [('upright',3),('leaning',4),('back',5)]]
            if upper=='back':frames=list(reversed(frames))
            intent='lean_back' if upper=='upright' else 'sit_upright'
            clip(f'{intent}-{state}','Lean back' if intent=='lean_back' else 'Sit upright',intent,state,destination,frames)
    # Do not ship unused film cutouts or the superseded stitched-body drawings.
    used={l['drawing'] for p in spec['poses'].values() for l in p['layers']}
    used.update(d for overlay in spec['overlays'].values() for d in overlay['drawings'].values())
    spec['drawings']={name:asset for name,asset in spec['drawings'].items() if name in used}
    spec['artwork']['postures']={'registration_sha256':digest(folder/'registration.json'),
        'sources':{entry['file']:digest(folder/entry['file']) for entry in [*cfg['atlases'].values(),cfg['qualify'],*([neck] if neck else [])]},
        'construction':'Complete torso-and-leg drawings; identical-pixel masks control chair/head occlusion. Separate rigid whole arms.'}
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
        [(964,909),(978,910),(994,969),(993,974),(986,975),(981,972)],
        [(530,775),(520,774),(510,778),(504,786),(501,801),(504,815),(511,824),(530,831)],
        [(940,787),(951,783),(962,790),(967,802),(965,824),(958,839),(946,846),(940,845)],
        [(664,799),(675,794),(717,792),(755,794),(771,800),(771,829),(760,835),(687,837),(666,832)]
    ]:d.polygon(polygon,fill=255)
    # Mug handles are rings: preserve the view of the moving legs through them.
    d.polygon([(519,786),(525,787),(525,814),(518,812),(514,807),(513,796),(515,790)],fill=0)
    d.polygon([(948,795),(955,798),(957,805),(956,816),(951,823),(948,824)],fill=0)
    im.putalpha(mask);box=mask.getbbox();path=output/'scene/table-front.png';im.crop(box).save(path)
    return {'file':'scene/table-front.png','sha256':digest(path),'position':list(box[:2]),'z':70}
