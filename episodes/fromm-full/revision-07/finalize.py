"""Verify the revision's unchanged mix and publish standard build records."""
import importlib.util
from pathlib import Path
import shutil
import subprocess

from klassic.project import digest,read_json,write_json

ROOT=Path(__file__).resolve().parents[3]
BUILD=ROOT/'build/fromm-full-07'
SOURCE=ROOT/'build/fromm-full-02'
RIG=ROOT/'assets/episodes/fromm-v7/rig.json'


def audio_hash(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0',
                                    '-c:a','copy','-f','hash','-hash','sha256','-'],text=True).strip()


def main():
    full=read_json(BUILD/'full-manifest.json')
    video=BUILD/full['file']
    if digest(video)!=full['sha256']:raise ValueError('Full export changed after rendering')
    original_audio=audio_hash(SOURCE/'episode.mp4');new_audio=audio_hash(video)
    if new_audio!=original_audio:raise ValueError('Finished audio is not bit-for-bit identical')
    if digest(BUILD/'episode.srt')!=digest(SOURCE/'episode.srt'):raise ValueError('Captions changed')
    for filename in ['dialogue.wav','atmosphere.wav','title.png','cast-credits.png','creator-credits.png',
                     'voices-credits.png','source-credits.png','music-credits.png','music-credit.txt']:
        shutil.copyfile(SOURCE/filename,BUILD/filename)
    alias=BUILD/'episode.mp4'
    if alias.exists() or alias.is_symlink():
        if not alias.is_symlink() or alias.readlink()!=Path(full['file']):
            raise ValueError('Unexpected existing main-film alias')
    else:alias.symlink_to(full['file'])
    write_json(BUILD/'render-manifest.json',{'rig_sha256':digest(RIG),
        'timeline_sha256':digest(BUILD/'timeline.json'),'video_sha256':full['sha256'],
        'scope':'finished captioned film, including titles and credits','file':full['file'],
        'puppet_assets':full['inputs']['puppet'],'animation_fps':24,'output_fps':24,
        'width':1440,'height':1080,'burned_captions':True,'render_record':'full-manifest.json'})
    manifest=read_json(SOURCE/'episode-manifest.json')
    manifest.update(episode_sha256=full['sha256'],render_manifest_sha256=digest(BUILD/'render-manifest.json'),
                    audio_bitstream_hash=new_audio,audio_source='build/fromm-full-02/episode.mp4',
                    captions_sha256=digest(BUILD/'episode.srt'),revision='06',burned_captions=True)
    write_json(BUILD/'episode-manifest.json',manifest)
    spec=importlib.util.spec_from_file_location('full_episode_verify',ROOT/'episodes/fromm-full/verify.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.verify(BUILD,RIG)
    verification=read_json(BUILD/'verification.json')
    verification.update(audio_bitstream_identical=True,audio_bitstream_hash=new_audio,
                        accent_automatic_rejection_enabled=False,rig='assets/episodes/fromm-v7/rig.json')
    write_json(BUILD/'verification.json',verification)
    review=(SOURCE/'review.html').read_text().replace('src="episode.mp4"','src="episode-captioned.mp4"')
    review=review.replace('<h1>', '<p>Revision 06 · complete arm poses with fixed left/right hands, pupil-free eyes, blinking and audience gaze. '
                         '<a href="motion-preview.mp4">Motion preview</a> · '
                         '<a href="../fromm-motion-test/accent-review.html">Accent listening review</a></p><h1>',1)
    (BUILD/'review.html').write_text(review)
    print('Verified unchanged AAC mix and finished film',flush=True)


if __name__=='__main__':main()
