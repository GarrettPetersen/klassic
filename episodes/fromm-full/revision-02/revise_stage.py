"""Register generated collar and hair corrections in both stage poses."""
from pathlib import Path
import copy,os
from PIL import Image,ImageFilter
from klassic.guest import polygon_mask
from klassic.project import read_json,write_json,digest
spec_path=Path('assets/characters/fromm/stage-corrections.json').resolve()
spec=read_json(spec_path);base_path=(spec_path.parent/spec['base_rig']).resolve();base=read_json(base_path)
art_path=spec_path.parent/spec['torso_art'];art=Image.open(art_path).convert('L')
out=Path('assets/episodes/fromm-v2');out.mkdir(exist_ok=True)
scene=Image.open(base_path.parent/base['scene']).convert('L')
if art.size!=scene.size:raise ValueError('Correction must have the exact original canvas registration')
mask=polygon_mask(scene.size,spec['torso_polygon']).filter(ImageFilter.GaussianBlur(.6))
hair_rect=spec['hair_crop']; hair_path=spec_path.parent/spec['hair_art']
hair=Image.open(hair_path).convert('L').resize((hair_rect[2]-hair_rect[0],hair_rect[3]-hair_rect[1]),Image.Resampling.LANCZOS)
hair_layer=scene.copy();hair_layer.paste(hair,tuple(hair_rect[:2]))
hair_mask=polygon_mask(scene.size,spec['hair_patch_polygon'])
for name,filename in [('scene',base['scene'])]+[(name,pose['scene']) for name,pose in base['poses'].items()]:
 im=Image.open(base_path.parent/filename).convert('L');im.paste(art,(0,0),mask);im.paste(hair_layer,(0,0),hair_mask);im.save(out/f'{name}.png')
rig=copy.deepcopy(base);rig['scene']='scene.png'
for name,pose in rig['poses'].items():pose['scene']=f'{name}.png'
for mouth in rig['mouths'].values():
 for key,file in mouth['cels'].items():mouth['cels'][key]=os.path.relpath(base_path.parent/file,out)
 motion=mouth['transitions'];motion['library']=os.path.relpath(base_path.parent/motion['library'],out)
rig['mouths']['host']['foreground'].insert(0,{'name':'far_hair','polygon':[[x/scene.width,y/scene.height] for x,y in spec['far_hair_polygon']]})
write_json(out/'rig.json',rig)
write_json(out/'source.json',{'base_rig_sha256':digest(base_path),'correction_spec_sha256':digest(spec_path),'torso_art_sha256':digest(art_path),'hair_art_sha256':digest(hair_path),'method':'Built-in image generation for collar, shoulders, and hair root; registered region compositing into both poses; corrected far-side hair retained as foreground above mouth cels.'})
