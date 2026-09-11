"""Separate visual acceptance units. Signatures bind content, never approvals."""
import hashlib
import itertools
import json
from urllib.parse import quote

def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def subject_id(kind,*parts):
    return ':'.join([kind,*(quote(str(p),safe='') for p in parts)])

def character_reviews(catalog,spec):
    result={}
    model={'model':catalog['model'],'design':catalog['design']}
    def add(kind,name,data,**context):
        key=subject_id(kind,name) if name is not None else kind
        result[key]={'kind':kind,**context,'signature':signature(data)}
        return key
    add('model',None,model)
    for name,asset in spec['drawings'].items():
        add('drawing',name,{**model,'sha256':asset['sha256'],'size':asset['size']},drawing=name)
    overlays=sorted(spec['overlays'])
    combinations=list(itertools.product(*(sorted(spec['overlays'][o]['drawings']) for o in overlays))) if overlays else []
    pose_data={}
    for name,pose in spec['poses'].items():
        names={layer['drawing'] for layer in pose['layers']}
        data={**model,'origin':spec['origin'],'pose':pose,'drawings':{n:spec['drawings'][n] for n in sorted(names)}}
        pose_data[name]=data
        add('pose',name,data,pose=name)
        for combination in combinations:
            selected=dict(zip(overlays,combination))
            face={o:{**spec['overlays'][o],'drawings':{k:spec['drawings'][spec['overlays'][o]['drawings'][k]]}} for o,k in selected.items()}
            # Other expression variants do not invalidate this exact face case.
            key=subject_id('face',name,*(f'{o}={selected[o]}' for o in overlays))
            result[key]={'kind':'face','pose':name,'overlays':selected,'signature':signature({'body':data,'face':face})}
    for name,clip in spec.get('actions',{}).items():
        neutral={o:{'definition':definition,'asset':spec['drawings'][definition['drawings'][next(iter(definition['drawings']))]]} for o,definition in spec['overlays'].items()}
        add('clip',name,{'fps':spec['fps'],'clip':clip,'states':spec['states'],'poses':{f['pose']:pose_data[f['pose']] for f in clip['frames']},'face':neutral},clip=name)
    return result

def project_reviews(project,characters):
    result={}
    for name,scene in project['scenes'].items():
        # Placement and every visible drawing/registration belong to composition.
        cast={a['character']:characters[a['character']] for a in scene['actors']}
        result[subject_id('scene',name)]={'kind':'scene','scene':name,'signature':signature({'scene':scene,'cast':cast})}
    result['performance']={'kind':'performance','signature':signature({'scenes':result,'story':project['story'],'cues':project.get('performance',[]),'takes':project['takes']})}
    return result

def review_states(records,manifest):
    if set(records)-set(manifest):raise ValueError('Review inventory contains removed subjects; register the new revision')
    result={}
    for key,subject in manifest.items():
        record=records.get(key)
        if record is None:result[key]='unreviewed';continue
        if record['decision'] not in ('approved','changes'):raise ValueError('Unknown review decision')
        result[key]=record['decision'] if record['signature']==subject['signature'] else 'stale'
    return result

def require_approved(states):
    missing=[f'{key}={state}' for key,state in states.items() if state!='approved']
    if missing:raise ValueError(f'Production export requires {len(missing)} current visual approvals: '+', '.join(missing[:12]))
