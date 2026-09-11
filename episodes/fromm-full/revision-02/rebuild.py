"""Reuse verified timing for unchanged recordings; replace the explicitly retaken line."""
from pathlib import Path
import shutil,wave,copy
from klassic.project import read_json,write_json,digest
from klassic.render import load_build
from klassic.audio import pcm,RATE
old=Path('build/fromm-full-01');new=Path('build/fromm-full-02');retake=Path('build/fromm-retake-015-02')
if new.exists():raise ValueError('Revision output already exists')
timeline=copy.deepcopy(load_build(old)); replacement=load_build(retake)['turns'][0]
assert replacement['id']=='t015'
new.mkdir();shutil.copyfile(old/'episode.json',new/'episode.json')
turns=[];samples=0
with wave.open(str(new/'dialogue.wav'),'wb') as mix:
 mix.setparams((1,2,RATE,0,'NONE','not compressed'))
 for prior in timeline['turns']:
  revised=prior['id']=='t015';source=retake if revised else old;turn=copy.deepcopy(replacement if revised else prior)
  assert all(turn[k]==prior[k] for k in ['id','speaker','text','provenance','pause_after'])
  for suffix in ['.wav','.txt','.mouth.json']:shutil.copyfile(source/f"{turn['id']}{suffix}",new/f"{turn['id']}{suffix}")
  frames=pcm(new/f"{turn['id']}.wav"); length=len(frames)//2;turn['start']=samples/RATE;turn['end']=(samples+length)/RATE
  pause=round(turn['pause_after']*RATE);mix.writeframes(frames);mix.writeframes(b'\x00\x00'*pause);samples+=length+pause;turns.append(turn)
timeline.update(turns=turns,duration=samples/RATE,dialogue_sha256=digest(new/'dialogue.wav'),shots=[{'start':0,'end':samples/RATE,'camera':'wide'}],presentation={'title_after_turn':'t002'})
write_json(new/'timeline.json',timeline);load_build(new)
write_json(new/'revision.json',{'previous_build':str(old),'previous_timeline_sha256':digest(old/'timeline.json'),'replacement':'t015','replacement_sha256':digest(new/'t015.wav'),'unchanged_voice_takes':118,'fromm_audio_unchanged':True,'title_after_turn':'t002'})
print('Prepared revised dialogue',timeline['duration'])
