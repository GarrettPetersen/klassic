import {Actor, requireValue} from './runtime.js';
const point=p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite);
export function validateScene(scene,specs) {
  requireValue(scene.version===1&&scene.size.length===2&&scene.size.every(n=>Number.isInteger(n)&&n>0),'Invalid scene');
  const ids=scene.actors.map(a=>a.id);requireValue(ids.length&&new Set(ids).size===ids.length,'Duplicate or missing scene actors');
  for(const a of scene.actors) {requireValue(specs[a.character],`Missing character ${a.character}`);new Actor(specs[a.character],a);}
  requireValue(scene.paths&&scene.seats&&scene.interactions,'Scene needs explicit paths, seats and interactions');
  for(const [id,path] of Object.entries(scene.paths))requireValue(typeof path.view==='string'&&path.points.length>=2&&path.points.every(point)&&(path.end_state===undefined||typeof path.end_state==='string'),`Invalid path ${id}`);
  for(const [id,seat] of Object.entries(scene.seats))requireValue(point(seat.position)&&typeof seat.view==='string'&&typeof seat.activity==='string',`Invalid seat ${id}`);
  for(const [id,target] of Object.entries(scene.interactions))requireValue(point(target.position)&&Number.isFinite(target.radius)&&target.radius>=0&&typeof target.intent==='string',`Invalid interaction ${id}`);
  for(const chair of scene.furniture)requireValue(scene.seats[chair.seat],`Unknown furniture seat ${chair.seat}`);
  return scene;
}
export function alignSeat(actor,seat,state,now) {
  actor.advance(now);
  const target=actor.spec.states[state];requireValue(target&&target.activity===seat.activity&&target.view===seat.view,'Character cannot use this seat in that state/view');
  requireValue(actor.state===state&&actor.spec.actions[actor.current].loop,'Seat alignment requires a settled seated pose');
  const contacts=actor.snapshot(now).contacts.filter(c=>c.kind==='seat');requireValue(contacts.length===1,'Seated drawing needs one seat contact');
  actor.placement.position=actor.placement.position.map((v,i)=>v+seat.position[i]-contacts[0].point[i]);
}
export function planPath(actor,path,family,at) {
  actor.advance(at);
  requireValue(actor.spec.actions[actor.current].loop,'Navigation must start from a settled state');
  requireValue(actor.spec.states[actor.state].view===path.view,'Path requires a different authored view');
  requireValue(Math.hypot(...path.points[0].map((v,i)=>v-actor.placement.position[i]))<.01,'Actor is not at path entry');
  requireValue(path.end_state===undefined||actor.spec.states[path.end_state],'Unknown path destination state');
  const candidates=Object.entries(actor.spec.actions).filter(([,a])=>!a.loop&&a.navigation?.family===family);
  requireValue(candidates.length,'No authored movement options for this path');
  const cues=[];let state=actor.state,time=at;
  for(let segment=1;segment<path.points.length;segment++){
    const delta=path.points[segment].map((v,i)=>(v-path.points[segment-1][i])/actor.placement.scale);
    const end=segment===path.points.length-1?(path.end_state??actor.state):null;
    const actions=movementPlan(actor.spec,candidates,state,delta,end);
    for(const name of actions){const clip=actor.spec.actions[name];cues.push({id:`path-${segment}-${cues.length}`,at:time,type:'action',action:name});time+=clip.frames.reduce((n,f)=>n+f.ticks,0)/actor.spec.fps;state=clip.to;}
  }
  return cues;
}
// Dijkstra over authored displacement/state combinations. No stretched stride,
// foot sliding correction, sprite mirroring or implicit snap to the destination.
export function movementPlan(spec,candidates,start,delta,end){
  const length=Math.hypot(...delta),direction=length?delta.map(v=>v/length):[1,0];
  let queue=[{state:start,distance:0,cost:0,actions:[]}];const best=new Map();let expanded=0;
  while(queue.length){
    queue.sort((a,b)=>a.cost-b.cost||a.actions.length-b.actions.length);const node=queue.shift();
    if(Math.abs(node.distance-length)<.01&&(!end||node.state===end))return node.actions;
    const key=node.state+':'+Math.round(node.distance*1000);if((best.get(key)??Infinity)<=node.cost)continue;best.set(key,node.cost);
    requireValue(++expanded<50000,'Path exceeds the authored movement search budget; divide it into waypoints');
    for(const [name,clip]of candidates.filter(([,a])=>a.from===node.state)){
      const d=clip.motion?.displacement??[0,0],along=d[0]*direction[0]+d[1]*direction[1],across=Math.abs(d[0]*direction[1]-d[1]*direction[0]);
      if(across>.01||along<-.01||node.distance+along>length+.01)continue;
      if(['stop','approach'].includes(clip.navigation.kind)&&Math.abs(node.distance+along-length)>.01)continue;
      queue.push({state:clip.to,distance:node.distance+along,cost:node.cost+clip.frames.reduce((n,f)=>n+f.ticks,0)/spec.fps,actions:[...node.actions,name]});
    }
  }
  throw new Error('No authored steps/turns can reach this destination and final state. Add a short or stopping step, change the waypoint, or author the missing view.');
}
export function contactReport(spec,actionName,tolerance=1) {
  const clip=spec.actions[actionName];requireValue(clip,'Unknown contact-review action');
  const roots=clip.motion?.roots??clip.frames.map(()=>[0,0]);const findings=[];let previous=new Map(),checks=0;
  clip.frames.forEach((frame,i)=> {
    const current=new Map();for(const c of spec.poses[frame.pose].contacts.filter(c=>c.locked)) {
      const position=c.point.map((v,j)=>v+roots[i][j]);current.set(c.id,position);
      if(previous.has(c.id)){checks++;const distance=Math.hypot(...position.map((v,j)=>v-previous.get(c.id)[j]));if(distance>tolerance)findings.push({frame:i,contact:c.id,distance});}
    }previous=current;
  });
  if(clip.loop){for(const c of spec.poses[clip.frames[0].pose].contacts.filter(c=>c.locked&&previous.has(c.id))){checks++;const position=c.point.map((v,j)=>v+(clip.motion?.displacement[j]??0)),distance=Math.hypot(...position.map((v,j)=>v-previous.get(c.id)[j]));if(distance>tolerance)findings.push({frame:0,contact:c.id,distance});}}
  return {findings,checks};
}
export const contactDrift=(spec,action,tolerance=1)=>contactReport(spec,action,tolerance).findings;
