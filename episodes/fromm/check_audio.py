"""Write word-timed ASR comparisons for human review; this does not grade voice similarity."""
from pathlib import Path
import argparse, json, re, difflib
from faster_whisper import WhisperModel
from klassic.project import digest, load_episode

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('episode',type=Path)
parser.add_argument('--takes',required=True,type=Path)
parser.add_argument('--available-only',action='store_true',help='Check completed takes while synthesis is still running')
parser.add_argument('--model',choices=['small.en','base.en'],default='small.en')
parser.add_argument('--reports',type=Path,help='Separate directory for a second recognizer or review pass')
parser.add_argument('--turn',nargs='+',help='Check only these explicit turn IDs')
args=parser.parse_args()
episode=load_episode(args.episode)
if args.turn and set(args.turn)-{t['id'] for t in episode['turns']}:
    raise ValueError('Requested ASR turn IDs are not in the episode')
if args.model != 'small.en' and args.reports is None:
    raise ValueError('Use --reports DIR for a second recognizer to preserve the primary checks')
model=None
def words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",text.lower())
for turn in episode['turns']:
    if args.turn and turn['id'] not in args.turn:
        continue
    path=args.takes/f"{turn['id']}.wav"
    if not path.is_file() or (args.available_only and not path.with_suffix('.json').is_file()):
        if args.available_only:
            continue
        raise FileNotFoundError(path)
    signature={'audio_sha256':digest(path),'expected':turn['text'],'model':args.model,'device':'cpu','comparison_version':2}
    report=(args.reports/f"{turn['id']}.asr.json") if args.reports else path.with_suffix('.asr.json')
    if report.is_file():
        saved=json.loads(report.read_text())
        if any(saved.get(key)!=value for key,value in signature.items()):
            raise ValueError(f'Stale ASR report; archive before rechecking: {report}')
        print(f"Retaining checked {turn['id']}",flush=True)
        continue
    if model is None:
        model=WhisperModel(args.model,device='cpu',compute_type='int8',cpu_threads=2,local_files_only=True)
    segments, info=model.transcribe(str(path),beam_size=5,word_timestamps=True)
    rows=[{'start':s.start,'end':s.end,'text':s.text,'words':[{'start':w.start,'end':w.end,'word':w.word} for w in s.words]} for s in segments]
    recovered=' '.join(s['text'].strip() for s in rows)
    expected=words(turn['text']);actual=words(recovered)
    differences=[{'kind':tag,'expected':expected[a:b],'recovered':actual[c:d]} for tag,a,b,c,d in difflib.SequenceMatcher(None,expected,actual).get_opcodes() if tag!='equal']
    result={**signature,'recovered':recovered,'differences':differences,'segments':rows}
    temporary=report.with_suffix('.partial.json')
    report.parent.mkdir(parents=True,exist_ok=True)
    temporary.write_text(json.dumps(result,indent=2))
    temporary.replace(report)
    print(f"{turn['id']}: {json.dumps(differences)}",flush=True)
