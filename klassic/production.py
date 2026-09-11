"""Individual-drawing authoring, content-bound visual reviews and deterministic atlases.

This module never generates or repairs artwork. A technical pass is not a visual
approval. Production export requires recorded model and in-context pose reviews.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
from .host import native_python
native_python()
from PIL import Image
from .project import digest, read_json, write_json
from .reviews import signature, character_reviews, project_reviews, review_states, require_approved


def checked_file(folder, entry):
    path=(folder/entry['file']).resolve()
    if not path.is_relative_to(folder.resolve()):raise ValueError('Source files must be inside the authoring package')
    if digest(path)!=entry['sha256']:raise ValueError(f'Source changed: {entry["file"]}; register the new revision before review')
    return path


def load_catalog(path):
    path=Path(path);catalog=read_json(path)
    if catalog['version']!=2:raise ValueError('Unsupported authoring catalog')
    spec=read_json(path.parent/catalog['character'])
    if spec['id']!=catalog['id']:raise ValueError('Catalog character mismatch')
    for asset in [catalog['model'],*spec['drawings'].values()]:checked_file(path.parent,asset)
    review_states(catalog['reviews'],character_reviews(catalog,spec))
    return catalog,spec


def review_signature(catalog,spec,subject):
    return character_reviews(catalog,spec)[subject]['signature']


def import_character(character,model,out,notes):
    character=Path(character);out=Path(out)
    if (out/'production.json').exists():raise ValueError('Authoring catalog already exists; edit individual sources in place')
    spec=read_json(character);spec.pop('production',None);out.mkdir(parents=True,exist_ok=True);(out/'drawings').mkdir(exist_ok=True)
    for name,asset in spec['drawings'].items():
        source=character.parent/asset['file']
        if digest(source)!=asset['sha256']:raise ValueError(f'Source hash mismatch: {source}')
        im=Image.open(source).convert('RGBA')
        if 'region' in asset:
            x,y,w,h=asset.pop('region')
            if min(x,y)<0 or min(w,h)<=0 or x+w>im.width or y+h>im.height:raise ValueError(f'Atlas region outside source: {name}')
            im=im.crop((x,y,x+w,y+h))
        if im.size!=tuple(asset['size']):raise ValueError(f'Invalid drawing dimensions: {name}')
        target=out/'drawings'/f'{name}.png';im.save(target)
        asset.update(file=f'drawings/{name}.png',sha256=digest(target))
    model_path=out/'model.png';shutil.copyfile(model,model_path)
    catalog={'version':2,'id':spec['id'],'character':'character.json',
        'model':{'file':'model.png','sha256':digest(model_path)},'design':notes,
        'workflow':'Model and complete poses in context → individual drawings → visual review → atlas export.',
        'reviews':{}}
    write_json(out/'character.json',spec);write_json(out/'production.json',catalog)
    return out/'production.json'


def register_revision(path):
    """Explicitly accept edited source bytes; their old approvals become stale."""
    path=Path(path);catalog=read_json(path);spec=read_json(path.parent/catalog['character'])
    for asset in [catalog['model'],*spec['drawings'].values()]:
        source=(path.parent/asset['file']).resolve()
        if not source.is_relative_to(path.parent.resolve()):raise ValueError('Source escapes package')
        asset['sha256']=digest(source)
        if asset is not catalog['model']:
            with Image.open(source) as im:asset['size']=list(im.size)
    manifest=character_reviews(catalog,spec)
    catalog['reviews']={name:record for name,record in catalog['reviews'].items() if name in manifest}
    write_json(path.parent/catalog['character'],spec);write_json(path,catalog)


def record_review(path,pose,decision,reviewer,notes,proof):
    path=Path(path);catalog,spec=load_catalog(path)
    if pose not in character_reviews(catalog,spec):raise ValueError(f'Unknown review subject {pose}')
    if decision not in ('approved','changes'):raise ValueError('Review decision must be approved or changes')
    if not reviewer.strip() or not notes.strip():raise ValueError('Reviewer and observations are required')
    proof=Path(proof)
    with Image.open(proof) as im:
        if im.format!='PNG':raise ValueError('Review proof must be a PNG')
        im.verify()
    folder=path.parent/'proofs';folder.mkdir(exist_ok=True)
    dest=folder/f'{hashlib.sha256(pose.encode()).hexdigest()[:16]}-{digest(proof)[:16]}.png';shutil.copyfile(proof,dest)
    catalog['reviews'][pose]={'decision':decision,'reviewer':reviewer,'notes':notes,
        'signature':review_signature(catalog,spec,pose),
        'proof':{'file':str(dest.relative_to(path.parent)),'sha256':digest(dest)}}
    write_json(path,catalog)


def check_reviews(path,production=False):
    path=Path(path);catalog,spec=load_catalog(path)
    report=review_states(catalog['reviews'],character_reviews(catalog,spec))
    for key,record in catalog['reviews'].items():
        if not record.get('reviewer') or not record.get('notes'):raise ValueError('Incomplete review record')
        checked_file(path.parent,record['proof'])
    if production:require_approved(report)
    return report


def export_character(path,out,draft=False,max_size=2048):
    path=Path(path);catalog,spec=load_catalog(path);reviews=check_reviews(path,production=not draft)
    manifest=character_reviews(catalog,spec);source_signature=signature(spec)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    # Stable shelf packing; drawing order never depends on filesystem order.
    pages=[];placements={};padding=2;x=y=padding;row_h=0;page=Image.new('RGBA',(max_size,max_size))
    for name,asset in sorted(spec['drawings'].items()):
        im=Image.open(checked_file(path.parent,asset)).convert('RGBA');w,h=im.size
        if [w,h]!=asset['size']:raise ValueError(f'Unregistered drawing dimensions: {name}')
        if max(w,h)+padding*2>max_size:raise ValueError(f'Drawing too large for atlas: {name}')
        if x+w+padding>max_size:x=padding;y+=row_h+padding;row_h=0
        if y+h+padding>max_size:pages.append(page);page=Image.new('RGBA',(max_size,max_size));x=y=padding;row_h=0
        page.paste(im,(x,y));placements[name]=(len(pages),[x,y,w,h]);x+=w+padding;row_h=max(row_h,h)
    pages.append(page);assets=[]
    for i,page in enumerate(pages):
        target=out/f'atlas-{i:03}.png';page.save(target);assets.append({'file':target.name,'sha256':digest(target)})
    for name,asset in spec['drawings'].items():
        i,region=placements[name];asset.update(**assets[i],region=region)
    spec['production']={'catalog_sha256':digest(path),'status':'draft' if draft else 'approved','reviews':reviews,
        'review_manifest':manifest,'source_signature':source_signature}
    write_json(out/'character.json',spec)
    return out/'character.json'


def apply_decisions(records,manifest,bundle,folder):
    if bundle['version']!=2:raise ValueError('Unsupported review bundle')
    if not bundle['reviews'] or len({i['subject'] for i in bundle['reviews']})!=len(bundle['reviews']):raise ValueError('Review subjects must be nonempty and unique')
    prepared=[]
    for item in bundle['reviews']:
        if item['subject'] not in manifest or item['signature']!=manifest[item['subject']]['signature']:raise ValueError('Review was made against a different source revision')
        if not item['proof'].startswith('data:image/png;base64,'):raise ValueError('Review requires a rendered PNG proof')
        data=base64.b64decode(item['proof'].split(',',1)[1],validate=True)
        import io
        with Image.open(io.BytesIO(data)) as im:
            if im.format!='PNG':raise ValueError('Review proof must be PNG')
            im.verify()
        if item['decision'] not in ('approved','changes') or not item['notes'].strip() or not item['reviewer'].strip():raise ValueError('Incomplete review')
        prepared.append((item,data))
    proof_dir=folder/'proofs';proof_dir.mkdir(exist_ok=True)
    for item,data in prepared:
        dest=proof_dir/(hashlib.sha256(data).hexdigest()+'.png');dest.write_bytes(data)
        records[item['subject']]={k:item[k] for k in ('decision','reviewer','notes','signature')}
        records[item['subject']]['proof']={'file':str(dest.relative_to(folder)),'sha256':digest(dest)}
        if 'context' in item:records[item['subject']]['context']=item['context']


def apply_review_bundle(path,bundle_path):
    path=Path(path);bundle=read_json(bundle_path);catalog,spec=load_catalog(path)
    if bundle['character']!=spec['id']:raise ValueError('Review bundle character mismatch')
    apply_decisions(catalog['reviews'],character_reviews(catalog,spec),bundle,path.parent)
    write_json(path,catalog)


def project_review_data(project_path,catalog_root):
    project_path=Path(project_path);project=read_json(project_path)
    characters={id:load_catalog(Path(catalog_root)/id/'production.json')[1] for id in project['characters']}
    manifest=project_reviews(project,characters)
    review_path=(project_path.parent/project['review_file']).resolve()
    if not review_path.is_relative_to(project_path.parent.resolve()):raise ValueError('Project review path escapes source directory')
    records=read_json(review_path)
    if records['version']!=2:raise ValueError('Unsupported project review catalog')
    return project,characters,manifest,review_path,records


def apply_project_reviews(project_path,catalog_root,bundle_path):
    project,characters,manifest,path,records=project_review_data(project_path,catalog_root)
    apply_decisions(records['reviews'],manifest,read_json(bundle_path),path.parent)
    write_json(path,records)


def bundle_project(project_path,catalog_root,out,draft=False):
    project_path=Path(project_path);project,characters,manifest,review_path,records=project_review_data(project_path,catalog_root)
    states=review_states(records['reviews'],manifest)
    for record in records['reviews'].values():checked_file(review_path.parent,record['proof'])
    if not draft:require_approved(states)
    project['production']={'source_signature':signature(project),'review_manifest':manifest,'reviews':states}
    project.pop('review_file')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for id in project['characters']:
        target=export_character(Path(catalog_root)/id/'production.json',out/'characters'/id,draft)
        project['characters'][id]={'file':str(target.relative_to(out)),'sha256':digest(target)}
    scenes=project['scenes'].values()
    assets=list(project['takes'].values())
    for scene in scenes:
        assets += [scene['background'],*scene['foregrounds']]
        assets += [part for chair in scene['furniture'] for part in (chair['rear'],chair['front'])]
    for asset in assets:
        source=project_path.parent/asset['file'];target=out/asset['file']
        if not target.resolve().is_relative_to(out.resolve()):raise ValueError('Asset destination escapes bundle')
        if digest(source)!=asset['sha256']:raise ValueError('Scene/audio source changed')
        target.parent.mkdir(parents=True,exist_ok=True)
        if source.resolve()!=target.resolve():shutil.copyfile(source,target)
    write_json(out/'project.json',project);return out/'project.json'


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('import');p.add_argument('--character',required=True,type=Path);p.add_argument('--model',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--notes',required=True)
    p=sub.add_parser('register');p.add_argument('catalog',type=Path)
    p=sub.add_parser('check');p.add_argument('catalog',type=Path);p.add_argument('--production',action='store_true')
    p=sub.add_parser('review');p.add_argument('catalog',type=Path);p.add_argument('--subject',required=True);p.add_argument('--decision',required=True);p.add_argument('--reviewer',required=True);p.add_argument('--notes',required=True);p.add_argument('--proof',required=True,type=Path)
    p=sub.add_parser('apply-review');p.add_argument('catalog',type=Path);p.add_argument('bundle',type=Path)
    p=sub.add_parser('export');p.add_argument('catalog',type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--draft',action='store_true')
    p=sub.add_parser('apply-registration');p.add_argument('catalog',type=Path);p.add_argument('patch',type=Path)
    p=sub.add_parser('prepare-import');p.add_argument('catalog',type=Path);p.add_argument('--incoming',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p=sub.add_parser('apply-import');p.add_argument('catalog',type=Path);p.add_argument('proposal',type=Path)
    p=sub.add_parser('apply-project-review');p.add_argument('--project',required=True,type=Path);p.add_argument('--catalog-root',required=True,type=Path);p.add_argument('bundle',type=Path)
    p=sub.add_parser('bundle');p.add_argument('--project',required=True,type=Path);p.add_argument('--catalog-root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--draft',action='store_true')
    a=parser.parse_args()
    from .authoring import apply_registration,prepare_import,apply_import
    if a.command=='import':print(import_character(a.character,a.model,a.out,a.notes))
    elif a.command=='register':register_revision(a.catalog)
    elif a.command=='check':print(json.dumps(check_reviews(a.catalog,a.production),indent=2))
    elif a.command=='review':record_review(a.catalog,a.subject,a.decision,a.reviewer,a.notes,a.proof)
    elif a.command=='apply-review':apply_review_bundle(a.catalog,a.bundle)
    elif a.command=='export':print(export_character(a.catalog,a.out,a.draft))
    elif a.command=='apply-registration':apply_registration(a.catalog,a.patch)
    elif a.command=='prepare-import':print(prepare_import(a.catalog,a.incoming,a.out))
    elif a.command=='apply-import':apply_import(a.catalog,a.proposal)
    elif a.command=='apply-project-review':apply_project_reviews(a.project,a.catalog_root,a.bundle)
    elif a.command=='bundle':print(bundle_project(a.project,a.catalog_root,a.out,a.draft))


if __name__=='__main__':main()
