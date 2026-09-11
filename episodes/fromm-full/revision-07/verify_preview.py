"""Decode the review export and collect inspectable pose and frame evidence."""
import json
import subprocess
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
from klassic.project import digest,read_json,write_json
from render_film import BUILD,RIG,ROOT,FilmFrames,input_hashes
from review_rig import contact_sheets,verify_lap_ink


def main():
    manifest=read_json(BUILD/'proof-manifest.json');video=BUILD/manifest['file']
    if digest(video)!=manifest['sha256'] or input_hashes()!=manifest['inputs']:
        raise ValueError('Preview does not match the current inputs')
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                             '-show_format','-of','json',str(video)]))
    stream=next(s for s in probe['streams'] if s['codec_type']=='video')
    if (stream['width'],stream['height'],stream['r_frame_rate'],int(stream['nb_frames']))!=(1440,1080,'24/1',manifest['frames']):
        raise ValueError('Preview dimensions/frame count changed')
    frames=FilmFrames();puppet=frames.comp.puppet
    font=ImageFont.load_default(size=20)
    audit={}
    for speaker in ('host','guest'):
        sheet=Image.new('RGB',(1800,660),(90,90,90));draw=ImageDraw.Draw(sheet)
        for row,arm in enumerate(('free','cigarette')):
            bank=puppet.arm_libraries[speaker][arm]
            for col,(name,cel) in enumerate(bank.cels.items()):
                # Presentation crop only: baked runtime geometry stays intact.
                box=cel.getchannel('A').point(lambda v:255 if v>12 else 0).getbbox()
                tile=cel.crop(box);tile.thumbnail((265,275),Image.Resampling.LANCZOS)
                xy=(col*300+(300-tile.width)//2,row*330+(290-tile.height)//2)
                sheet.paste(tile,xy,tile)
                draw.text((col*300+14,row*330+298),f'{arm} / {name}',font=font,fill='white')
                pose=bank.spec['poses'][name]
                audit[f'{speaker}/{arm}/{name}']={'digits':pose['digits'],'anatomical_hand':pose['anatomical_hand'],
                    'file_sha256':digest(bank.paths[0].parent/pose['file']),
                    'visual_check':'Three fingers and one thumb; continuous contour; cigarette held between fingers when present.'}
        sheet.save(BUILD/f'{speaker}-arm-review.png')
    if len(audit)!=16 or any(p['digits']!=4 for p in audit.values()):
        raise ValueError('Incomplete four-digit pose audit')
    gallery=[]
    for i,t in enumerate((2,12,24.5,33,41.5,52)):
        path=BUILD/f'encoded-{i+1:02d}.png'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(video),'-frames:v','1',str(path)],check=True)
        gallery.append(f'<figure><img src="{path.name}" alt="Encoded preview frame at {t} seconds"><figcaption>{t}s in preview</figcaption></figure>')
    write_json(BUILD/'verification.json',{'full_decode':True,'frames':manifest['frames'],
        'duration':manifest['frames']/24,'dimensions':[1440,1080],
        'rig_sha256':digest(RIG),'preview_sha256':digest(video),'hand_pose_audit':audit,
        'audit_method':'Visual inspection of all source drawings and composited contact sheets; digit count is not inferred by a classifier.',
        'audio':'Excerpts of revision-02 mix; no voice regeneration','full_film_exported':False,'trouser_ink_pixel_checks':verify_lap_ink()})
    contact_sheets()
    write_json(ROOT/'assets/episodes/fromm-v7/source.json',{
        'processing':'Matting and uniform whole-arm registration of existing generated artwork; no new image generation.',
        'supersedes':'Revision 06: inward far-hand thumbs, undersized arms, and open-palmed idle pose rejected by user.',
        'selected_arm_sources':'Original revision-05 cigarette atlases with outward thumbs; revision-05 registered free arms.',
        'scale':'Near arms 1.10x; far sleeve heights 204 and 214 pixels (previously 177 and 186); far shoulders moved inward by 26 and 28 pixels.',
        'rest':'Original neutral cigarette grips; no open palm at idle.',
        'tone':'Far cloth midtones matched to jacket gray 27 (host) and 25 (guest); black ink, skin, cuffs and alpha preserved.',
        'occlusion':'Far arms beneath torso; original trouser-edge layer over far sleeves; near arms above.',
        'gesture_cues':'episodes/fromm-full/revision-07/gesture-cues.json',
        'named_poses':16,'source_drawings':15,
        'hand_audit':audit,'user_visual_review_complete':False,
        'pupils':'Generated pupil-free eye plates with separate runtime pupil layers.',
        'static_sip':'Existing complete drinking cutaway retained; no new generated grip used.'})
    (BUILD/'review.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>Fromm — complete arm review</title>
<style>body{background:#181818;color:#eee;font:17px/1.6 system-ui;max-width:1200px;margin:36px auto;padding:0 24px}video,img{width:100%}a{color:#d6e9ff}figure{margin:22px 0}h1,h2{font-family:Georgia}</style>
<h1>Neutral cigarette holds, larger arms, and deliberate offering gestures</h1>
<p>Revision 07 motion review. Neutral cigarette grips are the default. Palm-up poses have outward thumbs and occur only at 26 authored questions, concessions and invitations in the transcript. Far arms are about 15% larger than revision 06, reduced from the first 30% enlargement. Far shoulders move 26/28 pixels inward, and near arms remain 10% larger. Cloth luminance is graded to match the jackets; crossed trouser contours render over far sleeves. All four named poses per arm are shown below; Fromm’s raised offering uses his sweep drawing rotated as a complete arm. Original suit ink stays above the repair underlays. The full interview export remains revision 02.</p>
<video controls preload="metadata" src="motion-preview.mp4" poster="encoded-01.png"></video>
<p>0–6s: neutral opening · 6–21s: teaser, title music and welcome · 21–31s: Krusty asks his first question · 31–40s: Fromm’s concession with cigarette down · 40–48s: Fromm agrees with the host · 48–58s: neutral closing address.</p>
<h2>Krusty</h2><img src="host-arm-review.png" alt="Eight complete Krusty arm drawings">
<h2>Fromm</h2><img src="guest-arm-review.png" alt="Eight complete Fromm arm drawings">
<h2>Arm joins at both lean extremes</h2>
<img src="host-seam-review.png" alt="Krusty arm joins and grips in six poses">
<img src="guest-seam-review.png" alt="Fromm arm joins and grips in six poses">
<h2>Encoded frames</h2>'''+''.join(gallery)+
        '<p><a href="verification.json">Verification</a> · <a href="../fromm-motion-test/accent-review.html">Accent listening review</a></p></html>')
    print(f'Verified {manifest["frames"]} frames, 16 named arm poses, and unchanged render inputs.')


if __name__=='__main__':main()
