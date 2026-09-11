"""Explicit, revision-checked registration edits and incoming-art comparisons."""
import copy
from pathlib import Path
import shutil
from .project import digest,read_json,write_json
from .reviews import signature,character_reviews

def apply_registration(catalog_path,patch_path):
    from .production import load_catalog
    path=Path(catalog_path);catalog,spec=load_catalog(path);patch=read_json(patch_path)
    if patch['version']!=1 or patch['character']!=spec['id'] or patch['base_signature']!=signature(spec):raise ValueError('Registration patch belongs to a different source revision')
    next_spec=copy.deepcopy(spec);seen=set()
    for edit in patch['changes']:
        pose=edit['pose']
        if pose in seen or pose not in spec['poses']:raise ValueError('Unknown or duplicate edited pose')
        seen.add(pose)
        if edit['before']!=spec['poses'][pose]:raise ValueError('Registration before-state mismatch')
        before=edit['before'];after=edit['after']
        if set(before)!=set(after):raise ValueError('Registration cannot add/remove pose fields')
        if len(before['layers'])!=len(after['layers']):raise ValueError('Registration cannot replace layers')
        for old,new in zip(before['layers'],after['layers']):
            if {k:v for k,v in old.items() if k!='transform'}!={k:v for k,v in new.items() if k!='transform'}:raise ValueError('Registration cannot change drawings or layer order')
        if before.get('anchor_bindings')!=after.get('anchor_bindings'):raise ValueError('Registration cannot change anchor bindings')
        editable={'layers','anchors','attachments','overlay_offsets','contacts'}
        if any(before[k]!=after[k] for k in before.keys()-editable):raise ValueError('Registration can only edit coordinates')
        for field in ('anchors','attachments','overlay_offsets'):
            if set(before.get(field,{}))!=set(after.get(field,{})):raise ValueError('Registration cannot add or remove points')
        if [{k:v for k,v in c.items() if k!='point'} for c in before['contacts']]!=[{k:v for k,v in c.items() if k!='point'} for c in after['contacts']]:raise ValueError('Registration cannot change contact identity or locking')
        validate_geometry(after)
        next_spec['poses'][pose]=after
    if not seen:raise ValueError('Empty registration patch')
    write_json(path.parent/catalog['character'],next_spec)

def validate_geometry(pose):
    import math
    def point(p):return isinstance(p,list) and len(p)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in p)
    for field in ('anchors','attachments','overlay_offsets'):
        if not all(point(p) for p in pose.get(field,{}).values()):raise ValueError('Invalid registration point')
    if not all(point(c['point']) and isinstance(c['locked'],bool) for c in pose['contacts']):raise ValueError('Invalid contact registration')
    for layer in pose['layers']:
        if 'transform' in layer:
            t=layer['transform']
            if not point(t['origin']) or not point(t['position']) or not isinstance(t['degrees'],(int,float)) or not math.isfinite(t['degrees']):raise ValueError('Invalid rigid registration')

def prepare_import(catalog_path,incoming,out):
    from .production import load_catalog,import_character
    path=Path(catalog_path);catalog,spec=load_catalog(path);out=Path(out)
    if out.exists():raise ValueError('Use a new proposal directory')
    out.mkdir(parents=True)
    imported=import_character(incoming,path.parent/catalog['model']['file'],out/'incoming',catalog['design'])
    _,new=load_catalog(imported)
    if new['id']!=spec['id']:raise ValueError('Incoming character identity mismatch')
    drawings,fields=import_diff(spec,new)
    proposal={'version':1,'character':spec['id'],'base_signature':signature(spec),'incoming':'incoming/character.json','incoming_sha256':digest(imported.parent/'character.json'),'drawings':drawings,'fields':fields}
    write_json(out/'proposal.json',proposal)
    lines=['# Incoming character comparison','',f"Character: {spec['id']}",f'Changed drawings: {len(drawings)}',f"Changed fields: {', '.join(fields) or 'none'}",'','The canonical package has not changed. Inspect the individual incoming PNGs and this exact JSON diff before applying.','']
    lines += [f'- {name}: '+('added' if d['before'] is None else 'removed' if d['after'] is None else 'changed') for name,d in drawings.items()]
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    return out/'proposal.json'

def import_diff(spec,new):
    drawings={name:{'before':spec['drawings'].get(name),'after':new['drawings'].get(name)} for name in sorted(spec['drawings'].keys()|new['drawings'].keys()) if spec['drawings'].get(name)!=new['drawings'].get(name)}
    fields={key:{'before':spec.get(key),'after':new.get(key)} for key in sorted(spec.keys()|new.keys()) if key!='drawings' and spec.get(key)!=new.get(key)}
    return drawings,fields

def apply_import(catalog_path,proposal_path):
    from .production import load_catalog,checked_file
    path=Path(catalog_path);catalog,spec=load_catalog(path);proposal_path=Path(proposal_path);p=read_json(proposal_path)
    if p['version']!=1 or p['character']!=spec['id'] or p['base_signature']!=signature(spec):raise ValueError('Import proposal is stale')
    incoming=(proposal_path.parent/p['incoming']).resolve()
    if not incoming.is_relative_to(proposal_path.parent.resolve()) or digest(incoming)!=p['incoming_sha256']:raise ValueError('Incoming proposal changed')
    new=read_json(incoming)
    if new['id']!=spec['id']:raise ValueError('Incoming character identity mismatch')
    if import_diff(spec,new)!=(p['drawings'],p['fields']):raise ValueError('Import diff does not match the source and incoming revision')
    files={name:checked_file(incoming.parent,asset) for name,asset in new['drawings'].items()}
    for name,asset in new['drawings'].items():
        target=(path.parent/asset['file']).resolve()
        if not target.is_relative_to((path.parent/'drawings').resolve()):raise ValueError('Drawing destination escapes source directory')
    # All sources and the exact before-state are checked before any mutation.
    for name,source in files.items():
        target=path.parent/new['drawings'][name]['file'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    for name,asset in spec['drawings'].items():
        if name not in new['drawings']:(path.parent/asset['file']).unlink()
    manifest=character_reviews(catalog,new)
    catalog['reviews']={key:value for key,value in catalog['reviews'].items() if key in manifest}
    write_json(path.parent/catalog['character'],new);write_json(path,catalog)
