import {Actor,Conversation,requireValue} from './runtime.js';
import {validateScene,alignSeat,planPath} from './staging.js';

// Story choices, authored performance cues and scene placement have independent
// owners. This session joins them through timestamped, serializable events.
export class GameSession {
  constructor(bundle) {
    this.bundle=bundle;this.project=bundle.project;this.revision=bundle.revision;
    this.conversation=new Conversation(this.project.story);this.events=[];this.gaze={};this.schedule=[];this.fired=[];this.caption='';this.speech=null;this.time=0;
    this.enterScene(this.project.initial_scene);
  }
  enterScene(id) {
    const scene=this.project.scenes[id];requireValue(scene,`Unknown scene ${id}`);validateScene(scene,this.bundle.specs);
    this.sceneId=id;this.scene=scene;
    this.actors=Object.fromEntries(scene.actors.map(a=>[a.id,new Actor(this.bundle.specs[a.character],a)]));
    for(const actor of Object.values(this.actors)){actor.started=this.time;actor.lastTime=this.time;}
    this.gaze={};this.speech=null;
  }
  advance(at) {
    requireValue(Number.isFinite(at)&&at>=this.time,'Session clock must be monotonic');
    let cue;
    while((cue=this.schedule.find(c=>!this.fired.includes(c.id)&&c.at<=at))){
      this.time=cue.at;this.fired.push(cue.id);this.apply(cue);
    }
    this.time=at;for(const actor of Object.values(this.actors))actor.advance(at);
  }
  dispatch(event,at) {
    this.advance(at);const clean=structuredClone(event);this.apply(clean);
    this.events.push({at,sequence:this.events.length,event:clean});
  }
  apply(event) {
    const actor=this.actors[event.actor];
    switch(event.type) {
      case 'action':requireValue(actor,'Unknown performer');actor.request(event.action,this.time);break;
      case 'gesture':requireValue(actor,'Unknown performer');actor.requestIntent(event.intent,this.time);break;
      case 'gaze':requireValue(actor&&['partner','camera'].includes(event.target),'Invalid gaze');this.gaze[event.actor]=event.target;break;
      case 'choice':this.conversation.choose(event.index);break;
      case 'finish_line':this.conversation.finishLine(this.conversation.revision);break;
      case 'settle':for(const a of Object.values(this.actors))a.settle(this.time);break;
      case 'scene':this.enterScene(event.scene);break;
      case 'seat':requireValue(actor&&this.scene.seats[event.seat],'Missing actor/seat');alignSeat(actor,this.scene.seats[event.seat],event.state,this.time);break;
      case 'interact':{
        const target=this.scene.interactions[event.target];requireValue(actor&&target,'Missing actor/interaction');
        actor.advance(this.time);
        requireValue(Math.hypot(...actor.placement.position.map((v,i)=>v-target.position[i]))<=target.radius,'Actor is outside interaction range');
        actor.requestIntent(target.intent,this.time);break;
      }
      case 'caption':requireValue(typeof event.text==='string','Invalid caption');this.caption=event.text;break;
      case 'speech_start':{
        const take=this.project.takes[event.take];requireValue(take&&this.actors[take.actor]&&Number.isFinite(event.offset)&&event.offset>=0&&event.offset<=take.duration&&typeof event.rehearsal==='boolean','Invalid speech start');
        this.speech={take:event.take,actor:take.actor,offset:event.offset,started:this.time,rehearsal:event.rehearsal};break;
      }
      case 'speech_seek':requireValue(this.speech&&Number.isFinite(event.offset)&&event.offset>=0&&event.offset<=this.project.takes[this.speech.take].duration,'Invalid speech seek');this.speech={...this.speech,offset:event.offset,started:this.time};break;
      case 'speech_stop':this.speech=null;break;
      case 'schedule':this.setSchedule(event.cues);break;
      case 'path':{
        requireValue(actor&&this.scene.paths[event.path],'Missing actor/path');
        const cues=planPath(actor,this.scene.paths[event.path],event.intent,this.time).map(c=>({...c,id:`${event.id}-${c.id}`,actor:event.actor}));
        this.setSchedule([...this.schedule.filter(c=>!this.fired.includes(c.id)),...cues]);break;
      }
      default:throw new Error(`Unknown performance event ${event.type}`);
    }
  }
  setSchedule(cues) {
    requireValue(Array.isArray(cues)&&new Set(cues.map(c=>c.id)).size===cues.length,'Cue IDs must be unique');
    for(const c of cues){requireValue(typeof c.id==='string'&&c.id&&Number.isFinite(c.at)&&c.at>=this.time&&['gesture','gaze','scene','seat','caption','speech_start','speech_seek','speech_stop','action','path','interact'].includes(c.type),'Invalid scheduled cue');}
    this.schedule=structuredClone(cues).sort((a,b)=>a.at-b.at);this.fired=[];
  }
  speechSample(at=this.time){
    if(!this.speech)return null;const take=this.project.takes[this.speech.take],position=this.speech.offset+at-this.speech.started;
    if(position>=take.duration)return null;
    return {...this.speech,at:position,caption:take.captions.find(c=>c.start<=position&&position<c.end)?.text??''};
  }
  save(at) {
    this.advance(at);return {version:2,project_revision:this.revision,scene:this.sceneId,time:at,
      actors:Object.fromEntries(Object.entries(this.actors).map(([id,a])=>[id,a.save(at)])),
      story:this.conversation.save(),gaze:structuredClone(this.gaze),schedule:structuredClone(this.schedule),fired:[...this.fired],caption:this.caption,
      events:structuredClone(this.events),speech:structuredClone(this.speech)};
  }
  static restore(bundle,data) {
    requireValue(data.version===2&&data.project_revision===bundle.revision,'Save belongs to a different project revision');
    requireValue(Number.isFinite(data.time)&&data.time>=0,'Invalid save clock');
    const session=new GameSession(bundle);session.time=data.time;session.enterScene(data.scene);
    requireValue(Object.keys(data.actors).sort().join()===Object.keys(session.actors).sort().join(),'Saved scene cast mismatch');
    for(const [id,state] of Object.entries(data.actors))session.actors[id]=Actor.restore(session.actors[id].spec,state,data.time);
    session.conversation.restore(data.story);
    requireValue(data.gaze&&Object.entries(data.gaze).every(([id,g])=>session.actors[id]&&['partner','camera'].includes(g)),'Invalid saved gaze');
    requireValue(Array.isArray(data.schedule)&&Array.isArray(data.fired)&&new Set(data.fired).size===data.fired.length,'Invalid saved cues');
    // Validate the full schedule at its original origin, then restore progress.
    session.time=0;session.setSchedule(data.schedule);session.time=data.time;
    requireValue(data.fired.every(id=>data.schedule.some(c=>c.id===id&&c.at<=data.time))&&data.schedule.every(c=>c.at>data.time||data.fired.includes(c.id)),'Saved cue progress mismatch');
    requireValue(typeof data.caption==='string','Invalid saved caption');
    session.gaze=structuredClone(data.gaze);session.fired=[...data.fired];session.caption=data.caption;session.events=validateEvents(data.events,data.time);
    requireValue(data.speech===null||data.speech&&Number.isFinite(data.speech.started)&&data.speech.started>=0&&data.speech.started<=data.time,'Invalid saved speech clock');
    if(data.speech){const p=data.speech;session.time=p.started;session.apply({type:'speech_start',take:p.take,offset:p.offset,rehearsal:p.rehearsal});session.time=data.time;requireValue(session.speech.actor===p.actor,'Saved speech actor mismatch');}
    return session;
  }
  replay(at) {
    const session=new GameSession(this.bundle);
    for(const entry of validateEvents(this.events,this.time))if(entry.at<=at)session.dispatch(entry.event,entry.at);
    session.advance(at);return session;
  }
  recording(at) {this.advance(at);return {version:2,project_revision:this.revision,duration:at,events:structuredClone(this.events)};}
  static fromRecording(bundle,recording,at=recording.duration) {
    requireValue(recording.version===2&&recording.project_revision===bundle.revision,'Recording belongs to a different project revision');
    requireValue(Number.isFinite(recording.duration)&&recording.duration>=0&&Number.isFinite(at)&&at>=0&&at<=recording.duration,'Invalid replay position');
    const s=new GameSession(bundle);s.events=validateEvents(recording.events,recording.duration);s.time=recording.duration;return s.replay(at);
  }
}
function validateEvents(events,duration) {
  requireValue(Array.isArray(events),'Invalid event log');let previous=0;
  events.forEach((e,i)=>{requireValue(Number.isFinite(e.at)&&e.at>=previous&&e.at<=duration&&e.sequence===i&&e.event&&['gesture','gaze','choice','finish_line','settle','scene','seat','caption','schedule','path','interact','speech_start','speech_seek','speech_stop','action'].includes(e.event.type),'Invalid event sequence');previous=e.at;});
  return structuredClone(events);
}
