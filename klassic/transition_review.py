"""A local flipbook for inspecting every authored transition in context."""
import html
import json
from pathlib import Path

from .render import Compositor


def review_transitions(rig, output, speaker="host"):
    output = Path(output)
    if output.exists():
        raise ValueError(f"Review output already exists: {output}")
    timeline = {"scratch":False, "turns":[], "shots":[]}
    comp = Compositor(timeline, rig, 960)
    if speaker not in comp.transitions:
        raise ValueError(f"{speaker} has no authored transition library")
    bank = comp.transitions[speaker][1]
    x,y = comp.cels[speaker][0]
    w,h = bank.cells["X"].size
    crop = (max(0,x-round(w*.65)), max(0,y-round(h*1.4)),
            min(comp.scene.width,x+round(w*1.25)), min(comp.scene.height,y+round(h*1.1)))
    drawings = dict(bank.cells)
    for pair, frames in bank.pairs.items():
        drawings.update({f"{pair}-{i}":cel for i,cel in enumerate(frames,1)})
    output.mkdir(parents=True)
    (output/"frames").mkdir()
    for name, cel in drawings.items():
        frame = comp.scene.copy()
        comp.paint_cel(frame,speaker,cel)
        frame.crop(crop).save(output/"frames"/f"{name}.png")
    pair_frames = {p:[p[0],f"{p}-1",f"{p}-2",p[1]] for p in bank.pairs}
    rows = "".join(f'<tr><th><button class="choose" data-pair="{p}">{p[0]} ↔ {p[1]}</button></th>'+"".join(f'<td><img loading="lazy" src="frames/{n}.png" alt="{n}"><small>{label}</small></td>' for n,label in zip(frames,[p[0],"⅓","⅔",p[1]]))+"</tr>" for p,frames in pair_frames.items())
    character = html.escape(comp.rig["mouths"][speaker]["character"])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CHARACTER mouth transitions</title>
<style>
body{margin:32px auto;max-width:1050px;padding:0 20px;background:#202020;color:#eee;font:16px/1.5 system-ui}
h1{font-family:Georgia;font-weight:normal}button,select{padding:8px 12px;background:#ddd;color:#111;border:0;border-radius:3px;font:inherit;cursor:pointer}button:focus-visible,select:focus-visible{outline:3px solid #ffd970}.controls{display:flex;gap:16px;flex-wrap:wrap;align-items:center}#stage{display:block;height:420px;max-width:100%;object-fit:contain;margin:18px auto;background:#aaa}#phase{display:block;text-align:center}input{width:100%;margin:16px 0}table{width:100%;border-collapse:collapse;margin-top:32px}th,td{border-bottom:1px solid #555;padding:8px}td img{width:100%;display:block}small{display:block;text-align:center}thead th{font-weight:normal}tr.selected{background:#383838}.choose{white-space:nowrap}p{color:#ccc}a{color:#eee}
</style>
<h1>CHARACTER — drawn mouth transitions</h1>
<p>36 pairs · 72 in-between cels · original endpoints. Each pair uses the same drawings in reverse when closing. Choose a row to inspect its motion; pause and scrub to check individual drawings.</p>
<div class="controls"><label>Pair <select id="pair"></select></label><button id="play">Pause</button><button id="reverse">Reverse</button><label>Speed <select id="speed"><option value="1">Normal · 24 fps</option><option value="0.25" selected>Slow · ¼ speed</option></select></label></div>
<img id="stage" alt="Selected mouth transition on Krusty's face"><output id="phase"></output><input id="scrub" aria-label="Cel position" type="range" min="0" max="3" step="1" value="0">
<p>The flipbook holds each endpoint for six frames and each in-between for one. Dialogue playback fits transitions to phoneme timing; fast syllables may use only one intermediate. Artwork is selected directly, with no geometric morphing or crossfades.</p>
<table><thead><tr><th>Transition</th><th>Start</th><th>In-between 1</th><th>In-between 2</th><th>End</th></tr></thead><tbody>ROWS</tbody></table>
<script>
const pairs=PAIRS;
const choose=document.querySelector('#pair'), stage=document.querySelector('#stage'), phase=document.querySelector('#phase'), scrub=document.querySelector('#scrub'), play=document.querySelector('#play');
Object.keys(pairs).forEach(p=>choose.add(new Option(p[0]+' ↔ '+p[1],p)));
choose.value='BC';let playing=true,reversed=false,tick=0,last=0;
const cycle=[0,0,0,0,0,0,1,2,3,3,3,3,3,3,2,1];
function show(i){const names=reversed?[...pairs[choose.value]].reverse():pairs[choose.value];stage.src='frames/'+names[i]+'.png';phase.textContent=choose.options[choose.selectedIndex].text+' · '+names[i];scrub.value=i;}
function select(p){choose.value=p;tick=0;last=0;show(0);document.querySelectorAll('tr.selected').forEach(r=>r.classList.remove('selected'));document.querySelector('[data-pair="'+p+'"]').closest('tr').classList.add('selected');}
choose.onchange=()=>select(choose.value);document.querySelectorAll('.choose').forEach(b=>b.onclick=()=>{select(b.dataset.pair);window.scrollTo({top:0,behavior:'smooth'});});
play.onclick=()=>{playing=!playing;play.textContent=playing?'Pause':'Play';last=0;};
document.querySelector('#reverse').onclick=()=>{reversed=!reversed;tick=0;show(0);};
scrub.oninput=()=>{playing=false;play.textContent='Play';show(Number(scrub.value));};
function animate(now){let interval=1000/(24*Number(document.querySelector('#speed').value));if(playing&&now-last>=interval){show(cycle[tick++%cycle.length]);last=now;}requestAnimationFrame(animate);}
select('BC');requestAnimationFrame(animate);
</script></html>'''
    page = page.replace('CHARACTER',character).replace('ROWS',rows).replace('PAIRS',json.dumps(pair_frames))
    (output/"index.html").write_text(page)
    return output/"index.html"
