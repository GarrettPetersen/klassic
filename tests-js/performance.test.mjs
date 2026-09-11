import test from 'node:test';
import assert from 'node:assert/strict';
import {Actor} from '../web/player/runtime.js';
import {GameSession} from '../web/player/performance.js';
import {planPath,contactDrift} from '../web/player/staging.js';
function fixture(){
 const spec={version:1,id:'actor',name:'Actor',fps:10,origin:[0,0],initial_state:'stand',
  activities:{standing:{label:'Standing',views:['right']},seated:{label:'Seated',views:['right']}},
  drawings:{body:{file:'body.png',sha256:'0'.repeat(64),position:[0,0],size:[30,50]}},
  overlays:{},poses:Object.fromEntries(['stand','step','sit'].map(p=>[p,{layers:[{drawing:'body',z:20}],attachments:{},anchors:{neck:[5,5]},contacts:[{id:p==='sit'?'seat':'right-foot',kind:p==='sit'?'seat':'foot',point:p==='step'?[-5,0]:[0,0],locked:true}]}])),
  states:{stand:{pose:'stand',idle:'idle',activity:'standing',view:'right'},sit:{pose:'sit',idle:'rest',activity:'seated',view:'right'}},
  actions:{idle:{from:'stand',to:'stand',loop:true,frames:[{pose:'stand',ticks:10}]},rest:{from:'sit',to:'sit',loop:true,frames:[{pose:'sit',ticks:10}]},
   walk:{navigation:{family:'walk',kind:'stride'},intent:'walk',from:'stand',to:'stand',loop:false,frames:[{pose:'stand',ticks:2},{pose:'step',ticks:4},{pose:'stand',ticks:4}],motion:{displacement:[10,0],roots:[[0,0],[5,0],[10,0]]}},
   sit:{intent:'sit',from:'stand',to:'sit',loop:false,frames:[{pose:'stand',ticks:2},{pose:'sit',ticks:8}]},
   offer:{intent:'offer',from:'sit',to:'sit',loop:false,frames:[{pose:'sit',ticks:10}]}}};
 const scene={version:1,size:[300,200],actors:[{id:'host',character:'actor',position:[0,100],scale:2,z:0}],furniture:[],foregrounds:[],
  paths:{entrance:{view:'right',points:[[0,100],[60,100]]}},seats:{chair:{position:[60,100],view:'right',activity:'seated'}},interactions:{chair:{position:[60,100],radius:1,intent:'sit'}}};
 return {revision:'revision-1',specs:{actor:spec},project:{version:2,scenes:{one:scene,two:{...structuredClone(scene),actors:[{...scene.actors[0],position:[40,50],scale:1}]}},initial_scene:'one',takes:{},story:{version:1,start:'choose',nodes:{choose:{kind:'choice',choices:[{label:'Yes',set:{accepted:true},next:'end'}]},end:{kind:'end',text:'Done'}}}}};
}
test('save resumes a moving actor and queued action without losing root displacement',()=>{
 const bundle=fixture(),s=new GameSession(bundle);s.dispatch({type:'gesture',actor:'host',intent:'walk'},0);s.dispatch({type:'gesture',actor:'host',intent:'sit'},.3);
 const restored=GameSession.restore(bundle,s.save(.5));
 for(const time of [.7,1.1,2.1]){s.advance(time);restored.advance(time);assert.deepEqual(restored.actors.host.snapshot(time),s.actors.host.snapshot(time));}
 assert.deepEqual(restored.actors.host.placement.position,[20,100]);assert.equal(restored.actors.host.state,'sit');
});
test('path scheduling, interactions and story choices replay deterministically after a large clock jump',()=>{
 const bundle=fixture(),s=new GameSession(bundle);s.dispatch({type:'path',id:'entry',actor:'host',path:'entrance',intent:'walk'},0);
 s.advance(3);assert.deepEqual(s.actors.host.placement.position,[60,100]);
 s.dispatch({type:'interact',actor:'host',target:'chair'},3);s.advance(4);
 s.dispatch({type:'seat',actor:'host',seat:'chair',state:'sit'},4);s.dispatch({type:'choice',index:0},4);
 s.dispatch({type:'gaze',actor:'host',target:'camera'},4);const recording=s.recording(5),replayed=GameSession.fromRecording(bundle,recording);
 assert.deepEqual(replayed.save(5),s.save(5));assert.equal(replayed.conversation.values.accepted,true);
 const middle=GameSession.fromRecording(bundle,recording,1.5);assert.deepEqual(middle.actors.host.snapshot(1.5).layers[0].position,[30,100]);
});
test('scene changes reuse character data and restore a different stage placement',()=>{
 const bundle=fixture(),s=new GameSession(bundle);s.dispatch({type:'scene',scene:'two'},2);
 const restored=GameSession.restore(bundle,s.save(3));assert.equal(restored.sceneId,'two');assert.deepEqual(restored.actors.host.placement.position,[40,50]);
 assert.deepEqual(restored.replay(3).save(3),restored.save(3));
});
test('a saved schedule resumes after the last fired cue without running it twice',()=>{
 const bundle=fixture(),s=new GameSession(bundle);s.dispatch({type:'path',id:'entry',actor:'host',path:'entrance',intent:'walk'},0);
 const save=s.save(1.5),restored=GameSession.restore(bundle,save);s.advance(4);restored.advance(4);
 assert.deepEqual(restored.save(4),s.save(4));assert.deepEqual(restored.actors.host.placement.position,[60,100]);
 save.fired=[];assert.throws(()=>GameSession.restore(bundle,save),/progress/);
});
test('seeking over a sit transition settles the actor before aligning its seat',()=>{
 const bundle=fixture(),s=new GameSession(bundle);s.dispatch({type:'schedule',cues:[
  {id:'sit',at:0,type:'gesture',actor:'host',intent:'sit'},
  {id:'align',at:1.1,type:'seat',actor:'host',seat:'chair',state:'sit'}]},0);
 s.advance(2);assert.deepEqual(s.actors.host.placement.position,[60,100]);
 assert.deepEqual(GameSession.fromRecording(bundle,s.recording(2)).save(2),s.save(2));
});
test('unsupported path lengths, distant interactions, stale saves and broken logs fail loudly',()=>{
 const b=fixture(),s=new GameSession(b);
 assert.throws(()=>planPath(s.actors.host,{view:'right',points:[[0,100],[25,100]]},'walk',0),/authored steps/);
 assert.throws(()=>s.dispatch({type:'interact',actor:'host',target:'chair'},0),/range/);
 let data=s.save(0);assert.throws(()=>GameSession.restore({...b,revision:'different'},data),/revision/);
 data.actors.host.pending='absent';assert.throws(()=>GameSession.restore(b,data),/queued/);
 const log=s.recording(0);log.events=[{at:0,sequence:0,event:{type:'unknown'}}];assert.throws(()=>GameSession.fromRecording(b,log),/sequence/);
});
test('contact review distinguishes a planted foot from a sliding foot; restore cannot overwrite spec',()=>{
 const b=fixture(),spec=b.specs.actor;const issues=contactDrift(spec,'walk');assert.equal(issues.length,1);assert.equal(issues[0].frame,2);
 spec.poses.step.contacts[0].point=[-3,0];assert.equal(contactDrift(spec,'walk').length,2);
 const a=new Actor(spec,b.project.scenes.one.actors[0]),data=a.save(0);data.spec={};const restored=Actor.restore(spec,data,0);assert.equal(restored.spec,spec);
});
test('path planner combines a stride, short stop and an authored turn without stretching',()=>{
 const b=fixture(),s=b.specs.actor;
 s.activities.standing.views.push('front');s.states.front={pose:'step',idle:'front-idle',activity:'standing',view:'front'};
 s.actions['front-idle']={from:'front',to:'front',loop:true,frames:[{pose:'step',ticks:10}]};
 s.actions.short={intent:'short-step',navigation:{family:'walk',kind:'stop'},from:'stand',to:'stand',loop:false,frames:[{pose:'stand',ticks:2},{pose:'step',ticks:2},{pose:'stand',ticks:2}],motion:{displacement:[3,0],roots:[[0,0],[1,0],[3,0]]}};
 s.actions.turn={intent:'turn',navigation:{family:'walk',kind:'turn'},from:'stand',to:'front',loop:false,frames:[{pose:'stand',ticks:2},{pose:'step',ticks:2}]};
 const actor=new Actor(s,b.project.scenes.one.actors[0]);const cues=planPath(actor,{view:'right',points:[[0,100],[26,100]],end_state:'front'},'walk',0);
 assert.deepEqual(cues.map(c=>c.action),['walk','short','turn']);
 const session=new GameSession(b);session.dispatch({type:'schedule',cues:cues.map(c=>({...c,actor:'host'}))},0);session.advance(3);
 assert.deepEqual(session.actors.host.placement.position,[26,100]);assert.equal(session.actors.host.state,'front');
});
test('speech starts, interruptions, seeks and captions replay on the same timeline',()=>{
 const b=fixture();b.project.takes.line={actor:'host',duration:5,captions:[{start:0,end:2,text:'First phrase'},{start:2,end:5,text:'Second phrase'}]};
 const s=new GameSession(b);s.dispatch({type:'speech_start',take:'line',offset:0,rehearsal:true},1);
 s.dispatch({type:'gaze',actor:'host',target:'camera'},1.5);s.dispatch({type:'speech_seek',offset:3},2);
 const save=s.save(2.5),restored=GameSession.restore(b,save);assert.equal(restored.speechSample().at,3.5);assert.equal(restored.speechSample().caption,'Second phrase');
 s.dispatch({type:'speech_stop'},3);s.dispatch({type:'caption',text:'Interrupted'},3);
 const recording=s.recording(4);assert.equal(GameSession.fromRecording(b,recording,1.25).speechSample().at,.25);
 assert.equal(GameSession.fromRecording(b,recording,2.5).speechSample().at,3.5);
 assert.equal(GameSession.fromRecording(b,recording).speechSample(),null);assert.equal(GameSession.fromRecording(b,recording).caption,'Interrupted');
});
test('a scheduled path expands into movement cues without dropping later speech or scene cues',()=>{
 const b=fixture(),s=new GameSession(b);
 s.dispatch({type:'schedule',cues:[{id:'path',at:1,type:'path',actor:'host',path:'entrance',intent:'walk'},{id:'caption',at:4.2,type:'caption',text:'Arrived'}]},0);
 s.advance(5);assert.deepEqual(s.actors.host.placement.position,[60,100]);assert.equal(s.caption,'Arrived');
 const replay=GameSession.fromRecording(b,s.recording(5));assert.deepEqual(replay.save(5),s.save(5));
});
test('scene placements select an authored initial posture and reject missing states',()=>{
 const b=fixture();b.project.scenes.one.actors[0].state='sit';assert.equal(new GameSession(b).actors.host.state,'sit');
 b.project.scenes.one.actors[0].state='missing';assert.throws(()=>new GameSession(b),/initial placement state/);
});
