import test from 'node:test';
import assert from 'node:assert/strict';
import {Actor, Conversation, sampleClip, validateCharacter, speechFrame, validateStory} from '../web/player/runtime.js';

const hash = '0'.repeat(64);
function character(id = 'different-proportions') {
  const frames = entries => entries.map(([pose,ticks]) => ({pose,ticks}));
  return {version:1,id,origin:[100,200],fps:24,initial_state:'seated',
    drawings:Object.fromEntries(['neutral','turn','open','mouth'].map(name => [name,{file:name+'.png',sha256:hash,position:[30,40],size:[60,80]}])),
    poses:Object.fromEntries(['neutral','turn','open'].map(name => [name,{layers:[{drawing:name,z:20}],attachments:{grip:[180,170]}}])),
    states:{seated:{pose:'neutral',idle:'idle'}},
    actions:{idle:{from:'seated',to:'seated',loop:true,frames:frames([['neutral',24]])},
      offer:{intent:'offer',from:'seated',to:'seated',loop:false,frames:frames([['neutral',2],['turn',2],['open',20],['turn',2],['neutral',2]])}},
    overlays:{mouth:{z:50,drawings:{X:'mouth'}}}};
}

test('clip changes silhouette drawings at exact tick boundaries, with no morph value', () => {
  const action=character().actions.offer;
  assert.equal(sampleClip(action,24,1/24).pose,'neutral');
  assert.equal(sampleClip(action,24,2/24).pose,'turn');
  assert.equal(sampleClip(action,24,4/24).pose,'open');
  assert.equal(sampleClip(action,24,27/24).pose,'neutral');
  assert.equal(sampleClip(action,24,28/24).done,true);
  assert.equal(sampleClip(character().actions.idle,24,12345).pose,'neutral');
  assert.throws(()=>sampleClip(action,24,NaN));
});

test('queued gestures finish their drawn recovery, and idle is neutral', () => {
  const actor=new Actor(character(),{position:[700,900],scale:1,z:0});
  actor.request('offer',0);
  assert.equal(actor.snapshot(.5).pose,'open');
  actor.request('offer',.5);
  assert.equal(actor.snapshot(27/24).pose,'neutral');
  assert.equal(actor.snapshot(30/24).pose,'turn');
  actor.settle(31/24);
  assert.equal(actor.snapshot(3).action,'idle');
  assert.throws(()=>actor.request('missing',3),/Unknown action/);
  assert.throws(()=>actor.snapshot(2),/monotonic/);
});

test('scene placement changes the whole character and prop attachment uniformly', () => {
  const spec=character();
  const a=new Actor(spec,{position:[100,200],scale:1,z:0}).snapshot(0,{mouth:'X'});
  const b=new Actor(spec,{position:[700,500],scale:.6,z:100}).snapshot(0,{mouth:'X'});
  assert.deepEqual(a.layers[0].position,[30,40]);
  assert.deepEqual(b.layers[0].position,[658,404]);
  assert.deepEqual(b.attachments.grip,[748,482]);
  assert.equal(b.layers[0].scale,.6);
  assert.equal(b.layers[1].z,150);
  assert.throws(()=>new Actor(spec,{position:[0,0],scale:-1,z:0}),/placement/);
});

test('full-body state transitions use the same player as layered seated gestures', () => {
  const spec=character('full-body-fixture');
  spec.states.standing={pose:'open',idle:'stand'};
  spec.actions.stand={from:'standing',to:'standing',loop:true,frames:[{pose:'open',ticks:24}]};
  spec.actions.stand_up={from:'seated',to:'standing',loop:false,frames:[{pose:'neutral',ticks:2},{pose:'turn',ticks:2},{pose:'open',ticks:2}]};
  const actor=new Actor(spec,{position:[0,0],scale:1,z:0});
  actor.request('stand_up',0);assert.equal(actor.snapshot(1).action,'stand');
  assert.equal(actor.state,'standing');
  assert.throws(()=>actor.request('offer',1),/requires seated/);
});

test('broken drawing references and discontinuous action endpoints fail loudly', () => {
  let spec=character();spec.poses.open.layers[0].drawing='absent';
  assert.throws(()=>validateCharacter(spec),/unknown drawing/);
  spec=character();spec.actions.offer.frames.at(-1).pose='open';
  assert.throws(()=>validateCharacter(spec),/entry and exit/);
  spec=character();spec.actions.offer.frames[1].ticks=0;
  assert.throws(()=>validateCharacter(spec),/duration/);
});

const story={version:1,start:'choose',nodes:{
  choose:{kind:'choice',choices:[{label:'Ask',next:'line',set:{tone:'open'}}]},
  line:{kind:'line',actor:'speaker-a',take:'take',gesture:'offer',gesture_at:.2,next:'follow'},
  follow:{kind:'choice',choices:[{label:'Continue',next:'end',set:{},when:{tone:'open'}},{label:'Hidden',next:'end',set:{},when:{tone:'closed'}}]},
  end:{kind:'end',text:'End'}}};

test('dialogue choices change state, filter later choices, and reject cancelled completion', () => {
  const session=new Conversation(story);session.choose(0);
  const old=session.revision;assert.equal(session.node.kind,'line');
  session.restart();assert.equal(session.finishLine(old),false);
  session.choose(0);assert.equal(session.finishLine(session.revision),true);
  assert.equal(session.choices().length,1);session.choose(0);assert.equal(session.node.kind,'end');
});

test('speech is sampled by audio time and closes immediately after the take', () => {
  const take={fps:24,duration:.125,frames:['X','A','B']};
  assert.equal(speechFrame(take,0),'X');assert.equal(speechFrame(take,1/24),'A');
  assert.equal(speechFrame(take,.125),'X');assert.throws(()=>speechFrame(take,-1));
});

test('story validation rejects wrong actors, unexported mouth frames and missing nodes', () => {
  const take={actor:'speaker-a',duration:1,fps:24,frames:Array(24).fill('X'),captions:[{start:0,end:1,text:'hello'}]};
  validateStory(story,{'speaker-a':character()},{take});
  assert.throws(()=>validateStory(story,{'speaker-a':character()},{take:{...take,actor:'someone-else'}}),/mismatched/);
  assert.throws(()=>validateStory(story,{'speaker-a':character()},{take:{...take,frames:Array(24).fill('MISSING')}}),/mouth frame/);
  const broken=structuredClone(story);broken.nodes.line.next='missing';
  assert.throws(()=>validateStory(broken,{'speaker-a':character()},{take}),/Missing story node/);
});


test('frame-rounding tolerance never advances the next clip into the future', () => {
  const spec=character();const actor=new Actor(spec,{position:[0,0],scale:1,z:0});
  actor.request('offer',.731);
  const end=.731+28/24;
  assert.equal(sampleClip(spec.actions.offer,24,28/24-1e-10).done,false);
  assert.doesNotThrow(()=>actor.snapshot(end-1e-10));
  assert.doesNotThrow(()=>actor.snapshot(end));
  assert.equal(actor.snapshot(end+.01).action,'idle');
});

test('reclined face anchors and rigid arm placement preserve drawings and prop depth', () => {
  const spec=character();
  spec.poses.neutral.layers[0].transform={origin:[30,40],position:[80,90],degrees:15};
  spec.poses.neutral.overlay_offsets={mouth:[12,-8]};
  const view=new Actor(spec,{position:[100,200],scale:1,z:0}).snapshot(0,{mouth:'X'});
  assert.deepEqual(view.layers[0].position,[80,90]);assert.equal(view.layers[0].degrees,15);
  assert.deepEqual(view.layers[1].position,[42,32]);
  assert.equal(view.layers[0].image,'different-proportions/neutral');
  const bad=structuredClone(spec);bad.poses.neutral.layers[0].transform.degrees=NaN;
  assert.throws(()=>validateCharacter(bad),/rigid placement/);
  const badFace=structuredClone(spec);badFace.poses.neutral.overlay_offsets.mouth=[0];
  assert.throws(()=>validateCharacter(badFace),/face placement/);
});

test('semantic actions resolve in the destination posture and queue through recovery', () => {
  const spec=character();spec.actions.offer.intent='offer';
  spec.states.back={pose:'open',idle:'back-idle'};
  spec.actions['back-idle']={from:'back',to:'back',loop:true,frames:[{pose:'open',ticks:24}]};
  spec.actions.lean={intent:'lean_back',from:'seated',to:'back',loop:false,frames:[{pose:'neutral',ticks:2},{pose:'turn',ticks:2},{pose:'open',ticks:2}]};
  spec.actions['offer-back']={intent:'offer',from:'back',to:'back',loop:false,frames:[{pose:'open',ticks:2},{pose:'turn',ticks:2},{pose:'open',ticks:2}]};
  const actor=new Actor(spec,{position:[0,0],scale:1,z:0});
  actor.requestIntent('lean_back',0);actor.requestIntent('offer',.1);
  assert.equal(actor.snapshot(.3).action,'offer-back');
  assert.equal(actor.snapshot(1).action,'back-idle');assert.equal(actor.state,'back');
  assert.deepEqual(actor.availableActions(1).map(([name])=>name),['offer-back']);
  assert.throws(()=>actor.requestIntent('unavailable',1),/Expected one/);
});
