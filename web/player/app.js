import {speechFrame} from './runtime.js';
import {loadProject} from './assets.js';
import {DrawingRenderer} from './renderer.js';
import {GameSession} from './performance.js';

const el = id => document.getElementById(id);
const audio = el('voice');
let bundle, actors, conversation, renderer, game;
let clock = 0, last = null, paused = false, failed = false, lab = false;
let active = null, gestureFired = false, nodeGeneration = 0;
let controlsSignature = '';
let replay=null,mediaWaiting=false,mediaSerial=0,cancelMediaLoad=null,replayMediaKey=null;

const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function report(error) {
  failed = true; audio.pause();
  el('error').hidden = false;
  el('error').textContent = `${error.message}\nReload the page after correcting the missing or changed asset.`;
  el('loading').hidden = true;
  console.error(error);
}
function guarded(fn) { return (...args) => Promise.resolve().then(() => fn(...args)).catch(report); }
function setCaption(text) {
  if (el('caption').textContent !== text){el('caption').textContent = text;if(game&&!replay&&game.caption!==text)game.dispatch({type:'caption',text},clock);}
}
function paintChoices(choices) {
  el('choices').replaceChildren(...choices.map(({label, action}) => {
    const button = document.createElement('button'); button.className = 'choice'; button.textContent = label;
    button.onclick = guarded(action); return button;
  }));
}
function settle() { game.dispatch({type:'settle'},clock); }
function cancelAudio() {
  mediaWaiting=false;cancelMediaLoad?.();mediaSerial++;game.dispatch({type:'speech_stop'},clock);nodeGeneration++; active = null; audio.pause(); audio.removeAttribute('src'); audio.load();
  settle(); el('skip').disabled = true; el('signal').classList.remove('live'); el('signal').textContent = 'Off air';
}
async function enterNode() {
  cancelAudio();
  const node = conversation.node;
  el('hint').textContent = '';
  if (node.kind === 'choice') {
    el('speaker').textContent = 'Your interview'; el('heading').textContent = node.prompt;
    setCaption(conversation.id === bundle.project.story.start ? 'Freedom, work, and what makes a good life.' : 'Listen, question, or change direction.');
    paintChoices(conversation.choices().map((choice, i) => ({label: choice.label, action: async () => {
      game.dispatch({type:'choice',index:i},clock); await enterNode();
    }})));
    el('hint').textContent = 'Your choice becomes the next spoken line.';
  } else if (node.kind === 'end') {
    el('speaker').textContent = 'Off air'; el('heading').textContent = node.heading??'Until next time.';
    setCaption(node.text); paintChoices([{label: 'Begin another interview', action: restart}]);
  } else {
    const take = bundle.project.takes[node.take];
    active = {node, take, revision: conversation.revision, generation: nodeGeneration};
    gestureFired = node.gesture === null;
    el('speaker').textContent = 'On air'; el('heading').textContent = actors[node.actor].spec.name;
    setCaption(take.captions[0].text); paintChoices([]); el('skip').disabled = false;
    audio.src = bundle.audio.get(node.take);
    if (!paused) await playAudio(active.generation);
  }
}
async function playAudio(generation) {
  try {
    await audio.play();
    if (generation !== nodeGeneration) return;
    el('signal').textContent = 'On air'; el('signal').classList.add('live');
  } catch (error) {
    if (generation !== nodeGeneration) return;
    if (error.name === 'NotAllowedError') {
      el('signal').textContent = 'Ready';
      paintChoices([{label: 'Play this line', action: async () => { paintChoices([]); await playAudio(generation); }}]);
    } else throw error;
  }
}
async function finishLine() {
  if (!active) return;
  if (active.rehearsal) { cancelAudio(); setCaption('Try another posture or gesture.'); return; }
  const revision = active.revision;
  if (revision===conversation.revision) {game.dispatch({type:'finish_line'},clock);await enterNode();}
}
async function restart() {
  replay=null;replayMediaKey=null;el('replay-position-wrap').hidden=true;
  lab = false; el('lab').hidden = true; el('lab-toggle').setAttribute('aria-expanded', 'false');
  paused = false; el('pause').textContent = 'Pause';
  clock=0;last=null;game=new GameSession(bundle);actors=game.actors;conversation=game.conversation;renderer.scene=game.scene;
  controlsSignature = '';
  await enterNode();
}
function blinkFrame(index) {
  if (reducedMotion) return 'open';
  const phase = (clock + index * 1.73) % (4.9 + index * .63);
  if (phase < .05 || phase >= .15 && phase < .2) return 'half';
  return phase >= .05 && phase < .15 ? 'closed' : 'open';
}
function snapshots() {
  return Object.entries(actors).map(([id, actor], index) => {
    let mouth = 'X';
    if (active?.node.actor === id && !audio.ended) mouth = speechFrame(active.take, audio.currentTime);
    const speech=game.speechSample(clock);if(!active&&speech?.actor===id)mouth=speechFrame(bundle.project.takes[speech.take],speech.at);
    const overlays={};if(actor.spec.overlays.mouth)overlays.mouth=mouth;if(actor.spec.overlays.eyes)overlays.eyes=`${game.gaze[id] ?? 'partner'}-${blinkFrame(index)}`;
    return actor.snapshot(clock,overlays);
  });
}
function draw() {
  if(replay){
    clock=Math.min(clock,replay.recording.duration);
    while(replay.index<replay.recording.events.length&&replay.recording.events[replay.index].at<=clock){const entry=replay.recording.events[replay.index++];game.dispatch(entry.event,entry.at);}
    if(clock===replay.recording.duration){paused=true;audio.pause();el('pause').textContent='Replay again';el('session-status').textContent='Performance replay complete.';replay.complete=true;}
    el('replay-position').value=clock;
  }
  game.advance(clock);
  el('performance').disabled=!!replay;el('lab-toggle').disabled=!!replay;
  if(actors!==game.actors){actors=game.actors;renderer.scene=game.scene;controlsSignature='';el('performer').replaceChildren(...Object.entries(actors).map(([id,a])=>new Option(a.spec.name,id)));}
  if(replay||!active){const sample=game.speechSample(clock);syncTimelineAudio(sample);if(sample){setCaption(sample.caption);el('heading').textContent=actors[sample.actor].spec.name;}}
  if(game.caption&&!active&&!game.speechSample(clock))setCaption(game.caption);
  if (active) {
    const at = audio.currentTime;
    const caption = active.take.captions.find(c => c.start <= at && at < c.end);
    if (caption) setCaption(caption.text);
    if (!gestureFired && !paused && !audio.paused && at >= active.node.gesture_at) {
      // If the tab slept through the whole beat, do not perform it on a later phrase.
      if (at - active.node.gesture_at < .5) game.dispatch({type:'gesture',actor:active.node.actor,intent:active.node.gesture},clock);
      gestureFired = true;
    }
  }
  const views = snapshots(); renderer.render(views, clock, {smoke: !reducedMotion});
  if (lab) {
    const id = el('performer').value; const i = Object.keys(actors).indexOf(id);
    const view = views[i]; el('pose-status').textContent = `${actors[id].spec.name}: ${view.action} / ${view.pose} / drawing ${view.frame + 1}`;
  }
  const performer = el('performer').value;
  const signature = performer + ':' + actors[performer].availableActions(clock).map(([name]) => name).join(',');
  if (signature !== controlsSignature) buildGestureButtons();
  return views;
}
function animate(now) {
  if (failed) return;
  if (last !== null && !paused && !mediaWaiting) clock += (now - last) / 1000;
  last = now;
  try { draw(); } catch (error) { report(error); return; }
  requestAnimationFrame(animate);
}
function buildGestureButtons() {
  const actor = actors[el('performer').value];
  el('sample').disabled=!Object.values(bundle.project.takes).some(t=>t.actor===el('performer').value);
  const available = actor.availableActions(clock);
  controlsSignature = el('performer').value + ':' + available.map(([name]) => name).join(',');
  el('gestures').replaceChildren(...available.map(([name, action]) => {
    const button = document.createElement('button'); button.textContent = action.label;
    button.onclick = guarded(() => {
      const id = el('performer').value;
      // A user's direction takes priority over the pending cue for this line.
      if (active?.node.actor === id) gestureFired = true;
      game.dispatch({type:'gesture',actor:id,intent:action.intent},clock);
      draw();
    }); return button;
  }));
  const camera = game.gaze[el('performer').value] === 'camera';
  el('gaze').disabled=!actor.spec.overlays.eyes;el('gaze').setAttribute('aria-pressed', String(camera)); el('gaze').textContent = camera ? 'Look at partner' : 'Look at camera';
}

function downloadJSON(name,data) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function adoptSession(next,at) {
  replay=null;replayMediaKey=null;el('replay-position-wrap').hidden=true;mediaWaiting=false;cancelMediaLoad?.();mediaSerial++;
  lab=false;el('lab').hidden=true;el('lab-toggle').setAttribute('aria-expanded','false');
  audio.pause();nodeGeneration++;active=null;game=next;actors=game.actors;conversation=game.conversation;
  clock=at;last=null;paused=true;renderer.scene=game.scene;controlsSignature='';
  el('pause').textContent='Resume';el('signal').textContent='Paused';el('signal').classList.remove('live');
  el('performer').replaceChildren(...Object.entries(actors).map(([id,a])=>new Option(a.spec.name,id)));
  paintChoices([]);el('skip').disabled=true;
}
async function loadMedia(take,at){
 cancelMediaLoad?.();const serial=++mediaSerial;mediaWaiting=true;
 if(audio.src!==bundle.audio.get(take)||audio.readyState<1){
  const ready=await new Promise((resolve,reject)=>{
   const cleanup=()=>{audio.removeEventListener('loadedmetadata',loaded);audio.removeEventListener('error',broken);cancelMediaLoad=null;};
   const loaded=()=>{cleanup();resolve(true);},broken=()=>{cleanup();reject(new Error('Could not load the recorded take'));};
   cancelMediaLoad=()=>{cleanup();resolve(false);};audio.addEventListener('loadedmetadata',loaded);audio.addEventListener('error',broken);audio.src=bundle.audio.get(take);
  });if(!ready)return false;
 }
 if(serial!==mediaSerial)return false;audio.currentTime=at;mediaWaiting=false;return true;
}
function syncTimelineAudio(sample){
 const key=sample?`${sample.take}/${sample.started}/${sample.offset}`:null;
 if(!sample){if(replayMediaKey!==null){audio.pause();cancelMediaLoad?.();mediaSerial++;mediaWaiting=false;}replayMediaKey=null;return;}
 if(key!==replayMediaKey){replayMediaKey=key;guarded(async()=>{if(await loadMedia(sample.take,sample.at)&&!paused&&replayMediaKey===key)await playAudio(nodeGeneration);})();}
}
function seekReplay(recording,at){
 const next=GameSession.fromRecording(bundle,recording,at);adoptSession(next,at);
 replay={recording,index:recording.events.filter(e=>e.at<=at).length,complete:false};
 el('replay-position-wrap').hidden=false;el('replay-position').max=recording.duration;el('replay-position').value=at;draw();
}

function installSessionControls() {
  const key='klassic-save:'+bundle.revision;
  const attempt=fn=>async()=>{try{await fn();}catch(error){el('session-status').textContent=error.message;}};
  el('save-session').onclick=attempt(()=>{
    if(replay)throw new Error('Finish or stop the performance replay before saving a playable session.');
    if(active&&game.speech)game.dispatch({type:'speech_seek',offset:Math.min(active.take.duration,audio.currentTime)},clock);
    localStorage.setItem(key,JSON.stringify({...game.save(clock),rehearsal:lab,gestureFired}));el('session-status').textContent='Saved this scene, performance, choices and audio position.';
  });
  el('load-session').onclick=attempt(async()=>{
    const source=localStorage.getItem(key);if(!source)throw new Error('No save for this version of the project.');
    const data=JSON.parse(source),next=GameSession.restore(bundle,data);adoptSession(next,data.time);
    lab=data.rehearsal===true;el('lab').hidden=!lab;el('lab-toggle').setAttribute('aria-expanded',String(lab));
    const p=game.speechSample(clock);
    if(p){
      const take=bundle.project.takes[p.take],node=p.rehearsal?{actor:take.actor,take:p.take,gesture:null}:conversation.node;
      if(!p.rehearsal&&(node.kind!=='line'||node.take!==p.take||node.actor!==p.actor))throw new Error('Saved audio does not match the story node.');
      active={node,take,revision:conversation.revision,generation:nodeGeneration,rehearsal:p.rehearsal};gestureFired=data.gestureFired;
      await loadMedia(p.take,p.at);el('skip').disabled=false;el('heading').textContent=actors[node.actor].spec.name;
    }else if(lab){el('heading').textContent='Find the performance.';setCaption('Restored rehearsal. Continue with the gesture controls.');
    }else if(conversation.node.kind==='choice'){
      el('heading').textContent=conversation.node.prompt;
      paintChoices(conversation.choices().map((c,i)=>({label:c.label,action:async()=>{game.dispatch({type:'choice',index:i},clock);await enterNode();}})));
    }else if(conversation.node.kind==='end'){
      el('heading').textContent=conversation.node.heading??'Until next time.';setCaption(conversation.node.text);paintChoices([{label:'Start over',action:restart}]);
    }else{
      el('heading').textContent='Continue the interview';paintChoices([{label:'Prepare the current line',action:enterNode}]);
    }
    draw();el('session-status').textContent='Restored. Resume when ready.';
  });
  el('recording-export').onclick=attempt(()=>downloadJSON('performance-recording.json',game.recording(clock)));
  el('recording-import').onchange=attempt(async()=>{
    const file=el('recording-import').files[0];if(!file)return;
    const recording=JSON.parse(await file.text());GameSession.fromRecording(bundle,recording); // Validate the full recording before replacing the session.
    seekReplay(recording,0);el('session-status').textContent='Performance recording loaded. Resume or seek to replay speech, captions, choices and movement.';
  });
  el('replay-position').onchange=attempt(()=>{if(replay)seekReplay(replay.recording,Number(el('replay-position').value));});
  el('run-scene').hidden=!bundle.project.performance;
  el('run-scene').onclick=guarded(async()=>{await restart();game.dispatch({type:'schedule',cues:bundle.project.performance},clock);paintChoices([]);});
}

async function main() {
  const url = new URLSearchParams(location.search).get('project') ?? '../../build/seated-production/project.json';
  bundle = await loadProject(url, (n, total) => { el('loading').textContent = `Preparing the studio… ${Math.round(n / total * 100)}%`; });
  document.title=bundle.project.title;
  game=new GameSession(bundle);actors=game.actors;conversation=game.conversation;
  renderer = new DrawingRenderer(el('stage'), game.scene, bundle.images);
  el('loading').hidden = true;
  for (const id of ['pause','restart','mute','lab-toggle']) el(id).disabled = false;
  for (const [id, actor] of Object.entries(actors)) el('performer').add(new Option(actor.spec.name, id));
  buildGestureButtons();
  el('performance').disabled = false;
  el('performer').onchange = buildGestureButtons;
  el('pause').onclick = guarded(async () => {
    if(replay?.complete)seekReplay(replay.recording,0);
    paused = !paused; el('pause').textContent = paused ? 'Resume' : 'Pause';
    if (paused) { audio.pause(); el('signal').textContent = 'Paused'; el('signal').classList.remove('live'); }
    else if (active||game.speechSample(clock)) await playAudio(nodeGeneration);
    else el('signal').textContent = 'Off air';
  });
  el('mute').onclick = () => {
    audio.muted = !audio.muted; el('mute').setAttribute('aria-pressed', String(audio.muted)); el('mute').textContent = audio.muted ? 'Unmute' : 'Mute';
  };
  el('skip').onclick = guarded(finishLine);
  el('restart').onclick = guarded(restart);
  audio.onplaying=guarded(()=>{mediaWaiting=false;if(active&&!replay)game.dispatch({type:'speech_start',take:active.node.take,offset:Math.min(active.take.duration,audio.currentTime),rehearsal:!!active.rehearsal},clock);});
  audio.onwaiting=()=>{if(active||replay)mediaWaiting=true;};audio.oncanplay=()=>{mediaWaiting=false;};
  audio.onseeked=guarded(()=>{if(active&&!replay&&game.speech)game.dispatch({type:'speech_seek',offset:Math.min(active.take.duration,audio.currentTime)},clock);});
  audio.onended = guarded(async () => {
    if (!replay && active && audio.ended && audio.currentSrc === bundle.audio.get(active.node.take)) await finishLine();
  });
  audio.onerror = () => {if(active||replay)report(new Error('Audio playback failed'));};
  el('lab-toggle').onclick = guarded(async () => {
    lab = !lab; el('lab').hidden = !lab; el('lab-toggle').setAttribute('aria-expanded', String(lab));
    if (lab) {
      cancelAudio(); el('speaker').textContent = 'Rehearsal'; el('heading').textContent = 'Find the performance.';
      setCaption('Choose an action below, or open the workbench to inspect individual drawings.'); paintChoices([]);
      el('hint').textContent = 'Pause and step through the saved drawings below.';
    } else await restart();
  });
  el('gaze').onclick = () => {
    const id=el('performer').value;game.dispatch({type:'gaze',actor:id,target:game.gaze[id]==='camera'?'partner':'camera'},clock);buildGestureButtons();
  };
  el('sample').onclick = guarded(async () => {
    cancelAudio();
    const actor = el('performer').value;
    const [id, take] = Object.entries(bundle.project.takes).find(([, take]) => take.actor === actor);
    active = {node: {actor, take: id, gesture: null}, take, generation: nodeGeneration, rehearsal: true};
    gestureFired = true; paused = false; el('pause').textContent = 'Pause';
    el('heading').textContent = actors[actor].spec.name; setCaption(take.captions[0].text);
    audio.src = bundle.audio.get(id); el('skip').disabled = false; await playAudio(nodeGeneration);
  });
  el('step').onclick = guarded(() => {
    paused = true; audio.pause(); el('signal').textContent = 'Paused'; el('signal').classList.remove('live');
    el('pause').textContent = 'Resume'; clock += 1 / 24; draw();
  });
  // Inspection API for deterministic browser verification, using the same player.
  window.mvp = {get actors(){return actors;}, project: bundle.project, get conversation(){return conversation;}, get game(){return game;}, get clock() { return clock; },
    get active() { return active; }, get paused() { return paused; },
    snapshot: () => snapshots(), request: (id, action) => game.dispatch({type:'gesture',actor:id,intent:actors[id].spec.actions[action].intent},clock),
    requestIntent: (id, intent) => game.dispatch({type:'gesture',actor:id,intent},clock)};
  installSessionControls();
  const reviewURL=new URL('../review/',location.href);reviewURL.searchParams.set('project',new URL(url,location.href));el('workbench').href=reviewURL;
  await enterNode(); requestAnimationFrame(animate);
}
main().catch(report);
