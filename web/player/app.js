import {Actor, Conversation, speechFrame} from './runtime.js';
import {loadProject} from './assets.js';
import {DrawingRenderer} from './renderer.js';

const el = id => document.getElementById(id);
const audio = el('voice');
let bundle, actors, conversation, renderer;
let clock = 0, last = null, paused = false, failed = false, lab = false;
let active = null, gestureFired = false, nodeGeneration = 0;
let controlsSignature = '';
const gaze = new Map();
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
  if (el('caption').textContent !== text) el('caption').textContent = text;
}
function paintChoices(choices) {
  el('choices').replaceChildren(...choices.map(({label, action}) => {
    const button = document.createElement('button'); button.className = 'choice'; button.textContent = label;
    button.onclick = guarded(action); return button;
  }));
}
function settle() { for (const actor of Object.values(actors)) actor.settle(clock); }
function cancelAudio() {
  nodeGeneration++; active = null; audio.pause(); audio.removeAttribute('src'); audio.load();
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
      conversation.choose(i); await enterNode();
    }})));
    el('hint').textContent = 'Your choice becomes the next spoken line.';
  } else if (node.kind === 'end') {
    el('speaker').textContent = 'Off air'; el('heading').textContent = 'Until next time.';
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
  if (conversation.finishLine(revision)) await enterNode();
}
async function restart() {
  lab = false; el('lab').hidden = true; el('lab-toggle').setAttribute('aria-expanded', 'false'); gaze.clear();
  paused = false; el('pause').textContent = 'Pause';
  for (const placement of bundle.project.scene.actors) actors[placement.id] = new Actor(bundle.specs[placement.character], placement);
  controlsSignature = '';
  conversation.restart(); await enterNode();
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
    return actor.snapshot(clock, {mouth, eyes: `${gaze.get(id) ?? 'partner'}-${blinkFrame(index)}`});
  });
}
function draw() {
  if (active) {
    const at = audio.currentTime;
    const caption = active.take.captions.find(c => c.start <= at && at < c.end);
    if (caption) setCaption(caption.text);
    if (!gestureFired && !paused && !audio.paused && at >= active.node.gesture_at) {
      // If the tab slept through the whole beat, do not perform it on a later phrase.
      if (at - active.node.gesture_at < .5) actors[active.node.actor].requestIntent(active.node.gesture, clock);
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
  if (last !== null && !paused) clock += (now - last) / 1000;
  last = now;
  try { draw(); } catch (error) { report(error); return; }
  requestAnimationFrame(animate);
}
function buildGestureButtons() {
  const actor = actors[el('performer').value];
  const available = actor.availableActions(clock);
  controlsSignature = el('performer').value + ':' + available.map(([name]) => name).join(',');
  el('gestures').replaceChildren(...available.map(([name, action]) => {
    const button = document.createElement('button'); button.textContent = action.label;
    button.onclick = guarded(() => {
      const id = el('performer').value;
      // A user's direction takes priority over the pending cue for this line.
      if (active?.node.actor === id) gestureFired = true;
      actors[id].requestIntent(action.intent, clock);
      draw();
    }); return button;
  }));
  const camera = gaze.get(el('performer').value) === 'camera';
  el('gaze').setAttribute('aria-pressed', String(camera)); el('gaze').textContent = camera ? 'Look at partner' : 'Look at camera';
}

async function main() {
  const url = new URLSearchParams(location.search).get('project') ?? '../../build/seated-mvp/project.json';
  bundle = await loadProject(url, (n, total) => { el('loading').textContent = `Preparing the studio… ${Math.round(n / total * 100)}%`; });
  actors = Object.fromEntries(bundle.project.scene.actors.map(a => [a.id, new Actor(bundle.specs[a.character], a)]));
  conversation = new Conversation(bundle.project.story);
  renderer = new DrawingRenderer(el('stage'), bundle.project.scene, bundle.images);
  el('loading').hidden = true;
  for (const id of ['pause','restart','mute','lab-toggle']) el(id).disabled = false;
  for (const [id, actor] of Object.entries(actors)) el('performer').add(new Option(actor.spec.name, id));
  buildGestureButtons();
  el('performance').disabled = false;
  el('performer').onchange = buildGestureButtons;
  el('pause').onclick = guarded(async () => {
    paused = !paused; el('pause').textContent = paused ? 'Resume' : 'Pause';
    if (paused) { audio.pause(); el('signal').textContent = 'Paused'; el('signal').classList.remove('live'); }
    else if (active) await playAudio(active.generation);
    else el('signal').textContent = 'Off air';
  });
  el('mute').onclick = () => {
    audio.muted = !audio.muted; el('mute').setAttribute('aria-pressed', String(audio.muted)); el('mute').textContent = audio.muted ? 'Unmute' : 'Mute';
  };
  el('skip').onclick = guarded(finishLine);
  el('restart').onclick = guarded(restart);
  audio.onended = guarded(async () => {
    if (active && audio.ended && audio.currentSrc === bundle.audio.get(active.node.take)) await finishLine();
  });
  audio.onerror = () => { if (active) report(new Error(`Audio playback failed for ${active.node.take}`)); };
  el('lab-toggle').onclick = guarded(async () => {
    lab = !lab; el('lab').hidden = !lab; el('lab-toggle').setAttribute('aria-expanded', String(lab));
    if (lab) {
      cancelAudio(); el('speaker').textContent = 'Rehearsal'; el('heading').textContent = 'Find the performance.';
      setCaption('Uncross the legs, lean back, and keep talking. Gestures return to the current posture.'); paintChoices([]);
      el('hint').textContent = 'Pause and step through the saved drawings below.';
    } else await restart();
  });
  el('gaze').onclick = () => {
    const id = el('performer').value; gaze.set(id, gaze.get(id) === 'camera' ? 'partner' : 'camera'); buildGestureButtons();
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
  window.mvp = {actors, project: bundle.project, conversation, get clock() { return clock; },
    get active() { return active; }, get paused() { return paused; },
    snapshot: () => snapshots(), request: (id, action) => actors[id].request(action, clock),
    requestIntent: (id, intent) => actors[id].requestIntent(intent, clock)};
  await enterNode(); requestAnimationFrame(animate);
}
main().catch(report);
