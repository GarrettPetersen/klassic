"""Write word-timed ASR comparisons for human review; this does not grade voice similarity."""
from pathlib import Path
import argparse, json, re, difflib
from faster_whisper import WhisperModel

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('episode',type=Path)
parser.add_argument('--takes',required=True,type=Path)
args=parser.parse_args()
episode=json.loads(args.episode.read_text())
model=WhisperModel('small.en',device='cpu',compute_type='int8',cpu_threads=2,local_files_only=True)
def words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?",text.lower())
for turn in episode['turns']:
    path=args.takes/f"{turn['id']}.wav"
    if not path.is_file():
        raise FileNotFoundError(path)
    segments, info=model.transcribe(str(path),beam_size=5,word_timestamps=True)
    rows=[{'start':s.start,'end':s.end,'text':s.text,'words':[{'start':w.start,'end':w.end,'word':w.word} for w in s.words]} for s in segments]
    recovered=' '.join(s['text'].strip() for s in rows)
    expected=words(turn['text']);actual=words(recovered)
    differences=[{'kind':tag,'expected':expected[a:b],'recovered':actual[c:d]} for tag,a,b,c,d in difflib.SequenceMatcher(None,expected,actual).get_opcodes() if tag!='equal']
    result={'expected':turn['text'],'recovered':recovered,'differences':differences,'segments':rows,'model':'small.en','device':'cpu'}
    path.with_suffix('.asr.json').write_text(json.dumps(result,indent=2))
    print(f"{turn['id']}: {json.dumps(differences)}",flush=True)
