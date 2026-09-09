"""Stage a separately authored guest portrait using existing set artwork."""
from pathlib import Path
import copy
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from .guest import GuestPortrait, polygon_mask
from .project import read_json, write_json, digest


def stage_fromm(spec_path, output):
    spec_path, output = Path(spec_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError(f"Staging output already exists: {output}")
    spec = read_json(spec_path)
    root = spec_path.parent
    portrait = GuestPortrait(root/spec['portrait'])
    base_rig_path = (root/spec['set_rig']).resolve()
    base = read_json(base_rig_path)
    source = Image.open(base_rig_path.parent/base['scene']).convert('L')
    head_mask = polygon_mask(portrait.portrait.size, spec['head_polygon'])
    # Follow the skin boundary beneath the chin, retaining its ink but
    # excluding the portrait's unrelated shirt and jacket from the head layer.
    skin = portrait.portrait.convert('L').point(lambda v: 255 if v == portrait.tone else 0)
    ImageDraw.floodfill(skin, (800, 580), 128)
    jaw = skin.point(lambda v: 255 if v == 128 else 0).filter(ImageFilter.MaxFilter(11))
    lower = Image.new('L', head_mask.size, 255)
    lower.paste(jaw.crop((0, 650, jaw.width, jaw.height)), (0, 650))
    head_mask = ImageChops.multiply(head_mask, lower)
    crop = tuple(spec['head_crop'])
    rect = spec['placement']
    size = (rect[2]-rect[0], rect[3]-rect[1])
    cells = {}
    for name, image in portrait.cells.items():
        head = image.copy()
        head.putalpha(ImageChops.multiply(head.getchannel('A'), head_mask))
        cells[name] = head.crop(crop).resize(size, Image.Resampling.LANCZOS)
    # Clean only the outgoing guest's footprint, using existing wall/panel
    # artwork. This is deterministic layer compositing, not new illustration.
    repair = source.copy()
    for patch in spec['wall_patches']:
        dst = patch['destination']
        tile = source.crop(tuple(patch['source'])).resize((dst[2]-dst[0], dst[3]-dst[1]), Image.Resampling.LANCZOS)
        repair.paste(tile, tuple(dst[:2]))
    outgoing = polygon_mask(source.size, spec['outgoing_head_polygon'])
    output.mkdir(parents=True)
    guest_dir = output/'guest'
    guest_dir.mkdir()
    for name, cel in cells.items():
        cel.save(guest_dir/f'{name}.png')
    names = sorted(portrait.bank.pairs)
    library = {'version':1, 'canvas':list(size), 'inbetweens_per_pair':2,
        'endpoint_sha256':{s:digest(guest_dir/f'{s}.png') for s in portrait.bank.cells},
        'pairs':{p:[f'{p}-1.png', f'{p}-2.png'] for p in names},
        'cel_sha256':{f'{p}-{i}.png':digest(guest_dir/f'{p}-{i}.png') for p in names for i in (1,2)},
        'processing':'Approved portrait and additive mouth masks, separate foreground nose, head matte, uniform offline scaling.',
        'stage_spec_sha256':digest(spec_path), 'portrait_spec_sha256':digest(root/spec['portrait'])}
    write_json(guest_dir/'library.json',library)
    scenes = {'scene.png':source}
    scenes.update({f'{name}.png':Image.open(base_rig_path.parent/pose['scene']).convert('L') for name,pose in base['poses'].items()})
    for filename, scene in scenes.items():
        scene.paste(repair, (0,0), outgoing)
        neck = polygon_mask(source.size, spec['neck_polygon'])
        scene.paste(portrait.tone, (0,0), neck)
        scene.save(output/filename)
    rig = copy.deepcopy(base)
    rig['scene'] = 'scene.png'
    for name, pose in rig['poses'].items():
        pose['scene'] = f'{name}.png'
    # Store paths relative to the new rig, without assuming its output folder.
    import os
    for s, filename in rig['mouths']['host']['cels'].items():
        rig['mouths']['host']['cels'][s] = os.path.relpath(base_rig_path.parent/filename, output)
    motion = rig['mouths']['host']['transitions']
    motion['library'] = os.path.relpath(base_rig_path.parent/motion['library'], output)
    rig['mouths']['guest'] = {'kind':'cels','character':'Erich Fromm, 1958',
        'construction':'Portrait head with non-muzzle mouth, additive front outline, and separate foreground nose',
        'box':[v/source.size[i%2] for i,v in enumerate(rect)],
        'cels':{s:f'guest/{s}.png' for s in portrait.bank.cells}, 'foreground':[],
        'transitions':{'seconds':.09,'library':'guest/library.json'}}
    write_json(output/'rig.json',rig)
    write_json(output/'source.json',{'stage_spec_sha256':digest(spec_path),'base_rig_sha256':digest(base_rig_path),
        'portrait_spec_sha256':digest(root/spec['portrait']), 'shared_mouth_library':portrait.library_hashes})
    return output/'rig.json'
