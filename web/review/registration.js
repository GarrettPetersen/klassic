import {requireValue,transformPoint} from '../player/runtime.js';

export function canvasPoint(event,canvas){
 const r=canvas.getBoundingClientRect(),scale=Math.min(r.width/canvas.width,r.height/canvas.height);
 const x=(event.clientX-r.left-(r.width-canvas.width*scale)/2)/scale;
 const y=(event.clientY-r.top-(r.height-canvas.height*scale)/2)/scale;
 return [x,y];
}
export function localPoint(world,placement,origin,root=[0,0]){
 return world.map((v,i)=>(v-placement.position[i])/placement.scale+origin[i]-root[i]);
}
export class RegistrationEditor{
 constructor(spec){this.spec=spec;this.original=structuredClone(spec.poses);this.undoStack=[];this.redoStack=[];}
 get dirty(){return JSON.stringify(this.spec.poses)!==JSON.stringify(this.original);}
 targets(pose){const p=this.spec.poses[pose];return [
  ...Object.keys(p.anchors).map(name=>({type:'anchor',name,label:name,point:p.anchors[name]})),
  ...p.contacts.map(c=>({type:'contact',name:c.id,label:c.id+' contact',point:c.point})),
  ...Object.entries(p.attachments).map(([name,point])=>({type:'attachment',name,label:name+' attachment',point})),
  ...p.layers.map((l,i)=>({type:'layer',name:String(i),label:l.drawing,point:transformPoint(this.spec.drawings[l.drawing].position,l.transform)}))];}
 begin(pose){this.transaction={pose,before:structuredClone(this.spec.poses[pose])};}
 move(pose,type,name,point){
  requireValue(point.length===2&&point.every(Number.isFinite),'Invalid registration point');const p=this.spec.poses[pose];point=point.map(v=>Math.round(v*10)/10);
  if(type==='contact'){const c=p.contacts.find(c=>c.id===name);requireValue(c,'Unknown contact');c.point=point;return;}
  if(type==='attachment'){requireValue(p.attachments[name],'Unknown attachment');p.attachments[name]=point;return;}
  const moveLayer=(i,delta)=>{const l=p.layers[i];requireValue(l,'Missing bound layer');const t=l.transform??{origin:[0,0],position:[0,0],degrees:0};l.transform={...t,position:t.position.map((v,j)=>v+delta[j])};};
  if(type==='layer'){const i=Number(name),current=transformPoint(this.spec.drawings[p.layers[i].drawing].position,p.layers[i].transform);moveLayer(i,point.map((v,j)=>v-current[j]));return;}
  requireValue(type==='anchor'&&p.anchors[name],'Unknown registration anchor');const delta=point.map((v,i)=>v-p.anchors[name][i]);p.anchors[name]=point;
  // Bindings are authored data: moving a shoulder moves its whole arm and prop.
  const binding=p.anchor_bindings?.[name];if(!binding)return;
  for(const i of binding.layers)moveLayer(i,delta);
  for(const overlay of binding.overlays)p.overlay_offsets[overlay]=p.overlay_offsets[overlay].map((v,i)=>v+delta[i]);
  for(const attachment of binding.attachments)p.attachments[attachment]=p.attachments[attachment].map((v,i)=>v+delta[i]);
 }
 commit(){requireValue(this.transaction,'No registration edit in progress');const {pose,before}=this.transaction,after=structuredClone(this.spec.poses[pose]);this.transaction=null;if(JSON.stringify(before)!==JSON.stringify(after)){this.undoStack.push({pose,before,after});this.redoStack=[];}}
 undo(){const edit=this.undoStack.pop();if(edit){this.spec.poses[edit.pose]=structuredClone(edit.before);this.redoStack.push(edit);}}
 redo(){const edit=this.redoStack.pop();if(edit){this.spec.poses[edit.pose]=structuredClone(edit.after);this.undoStack.push(edit);}}
 patch(){return {version:1,character:this.spec.id,base_signature:this.spec.production.source_signature,changes:Object.entries(this.spec.poses).filter(([name,p])=>JSON.stringify(p)!==JSON.stringify(this.original[name])).map(([pose,after])=>({pose,before:this.original[pose],after:structuredClone(after)}))};}
}
