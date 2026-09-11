import {loadProject} from '../player/assets.js';
import {Actor,requireValue} from '../player/runtime.js';
import {DrawingRenderer} from '../player/renderer.js';
import {contactReport} from '../player/staging.js';
import {RegistrationEditor,canvasPoint,localPoint} from './registration.js';
import {subjectId,faceSubject,subjectFor,statusFor} from './acceptance.js';
const el=id=>document.getElementById(id);
let bundle,renderer,baselineBundle=null,pinned=null,playing=false,tick=0,last=null;
const reviews=new Map(),editors=new Map(),watched=new Set();let watchedRun=null;
const editor=()=>editors.get(spec().id);
const guarded=fn=>async(...args)=>{try{await fn(...args);el('error').hidden=true;}catch(e){playing=false;el('play').textContent='Play';el('error').hidden=false;el('error').textContent=e.message;console.error(e);}};
const select=(id,entries,value)=>{el(id).replaceChildren(...entries.map(([key,label])=>new Option(label,key)));if(value!==undefined&&entries.some(([key])=>key===value))el(id).value=value;};
const scene=()=>bundle.project.scenes[el('scene').value];
const placement=()=>scene().actors.find(a=>a.id===el('actor').value);
const spec=()=>bundle.specs[placement().character];
const clip=()=>spec().actions[el('clip').value];
const duration=()=>clip().frames.reduce((n,f)=>n+f.ticks,0);
const selectedOverlays=s=>Object.fromEntries(['mouth','eyes'].filter(k=>s.overlays[k]).map(k=>[k,el(k).value]));
function clipsForSelection(){return Object.entries(spec().actions).filter(([,a])=>{const state=a.capability??spec().states[a.from];return state.activity===el('activity').value&&state.view===el('view').value;});}
function populateActors(){select('actor',scene().actors.map(a=>[a.id,bundle.specs[a.character].name]));populateActivities();}
function populateActivities(){select('activity',Object.entries(spec().activities).map(([id,a])=>[id,a.label]),spec().states[placement().state??spec().initial_state].activity);populateViews();}
function populateViews(){select('view',spec().activities[el('activity').value].views.map(v=>[v,v]));populateClips();}
function populateClips(){const faceOption=el('review-scope').querySelector('[value=face]');faceOption.disabled=!Object.keys(spec().overlays).length;if(faceOption.disabled&&el('review-scope').value==='face')el('review-scope').value='pose';select('clip',clipsForSelection().map(([id,a])=>[id,a.label??id]));for(const key of ['mouth','eyes']){const keys=Object.keys(spec().overlays[key]?.drawings??{});select(key,keys.length?keys.map(k=>[k,k]):[['','None']],key==='mouth'?'X':'partner-open');el(key).disabled=!keys.length;}resetClip();}
function resetClip(){watchedRun=null;tick=0;playing=false;el('play').textContent='Play';el('frame').max=duration()-1;makeStrip();draw();makeMatrix();}
function makeStrip(){let at=0;el('strip').replaceChildren(...clip().frames.map((f,i)=>{const start=at;at+=f.ticks;const b=document.createElement('button');b.dataset.frame=i;b.textContent=`${i+1}. ${f.pose} · ${f.ticks} ticks`;b.onclick=()=>{tick=start;playing=false;el('play').textContent='Play';draw();};return b;}));}
function viewsFor(source){
 const s=source.project.scenes[el('scene').value];requireValue(s,'Comparison project is missing this scene');
 return s.actors.map(a=>{
  const character=source.specs[a.character];let initial=a.state??character.initial_state;
  const selected=a.id===el('actor').value;const action=selected?character.actions[el('clip').value]:null;
  if(selected){requireValue(action,'Comparison project is missing this clip');initial=action.from;}
  const actor=new Actor(character,{...a,state:initial});
  if(selected&&!action.loop)actor.request(el('clip').value,0);
  else if(selected){actor.current=el('clip').value;actor.started=0;}
  const overlays=selected?selectedOverlays(character):Object.fromEntries(Object.entries(character.overlays).map(([name,o])=>[name,name==='mouth'?'X':'partner-open']));
  return actor.snapshot(selected?Math.floor(tick)/character.fps:0,overlays);
 });
}
function draw(){
 if(!bundle)return;const views=viewsFor(bundle);renderer.scene=scene();
 const options={smoke:false,background:el('background').value,silhouette:el('silhouette').checked,anchors:el('anchors').checked,contacts:el('contacts').checked};
 renderer.render(views,Math.floor(tick)/spec().fps,options);
 const selected=views[scene().actors.indexOf(placement())];el('frame').value=Math.floor(tick);
 el('status').textContent=`Frame ${Math.floor(tick)+1} / ${duration()} · ${selected.pose} · ${el('activity').value} / ${el('view').value}`;
 el('current-caption').textContent=`${spec().name} — ${selected.pose}`;
 for(const button of el('strip').children)button.classList.toggle('active',Number(button.dataset.frame)===selected.frame);
 const {findings,checks}=contactReport(spec(),el('clip').value);el('drift').textContent=findings.length?`Contact check: ${findings.map(f=>`${f.contact} moves ${f.distance.toFixed(1)} px at drawing ${f.frame+1}`).join('; ')}`:checks?`Contact check: ${checks} adjacent planted contacts remain fixed.`:'No adjacent planted contacts registered. Inspect the feet visually; this is not a contact-check pass.';
 if(baselineBundle){const other=new DrawingRenderer(el('baseline'),baselineBundle.project.scenes[el('scene').value],baselineBundle.images);other.render(viewsFor(baselineBundle),Math.floor(tick)/spec().fps,options);}
 else if(pinned){const ctx=el('baseline').getContext('2d');el('baseline').width=pinned.width;el('baseline').height=pinned.height;ctx.drawImage(pinned,0,0);}
 updateRegistration(selected);updateSubject(selected);
 return selected;
}
function matrix(){return Object.entries(spec().actions).map(([name,a])=>({scene:el('scene').value,character:spec().id,state:a.from,activity:(a.capability??spec().states[a.from]).activity,view:(a.capability??spec().states[a.from]).view,clip:name,poses:[...new Set(a.frames.map(f=>f.pose))],mouths:Object.keys(spec().overlays.mouth?.drawings??{}),eyes:Object.keys(spec().overlays.eyes?.drawings??{})}));}
function projectMatrix(){
 const cases=[];
 for(const [scene,stage] of Object.entries(bundle.project.scenes))for(const actor of stage.actors){
  const s=bundle.specs[actor.character],mouths=Object.keys(s.overlays.mouth?.drawings??{}),eyes=Object.keys(s.overlays.eyes?.drawings??{});
  for(const [clip,a] of Object.entries(s.actions))for(const pose of new Set(a.frames.map(f=>f.pose)))for(const mouth of mouths.length?mouths:[''])for(const eye of eyes.length?eyes:['']){
   const {activity,view}=a.capability??s.states[a.from];cases.push({scene,actor:actor.id,character:s.id,activity,view,clip,pose,mouth,eyes:eye});
  }
 }return cases;
}
function makeMatrix(){el('matrix').replaceChildren(...matrix().map(row=>{
 const s=spec(),state=id=>editor().dirty?'stale':statusFor(s.production,reviews,s.id,id);
 const poses=row.poses.filter(p=>state(subjectId('pose',p))==='approved').length;
 const faces=Object.entries(s.production?.review_manifest??{}).filter(([,m])=>m.kind==='face'&&row.poses.includes(m.pose));
 const approved=faces.filter(([id])=>state(id)==='approved').length;
 const tr=document.createElement('tr');const data=[row.state,row.clip,row.poses.length,`${row.mouths.length||0} mouths × ${row.eyes.length||0} eyes`,`${poses}/${row.poses.length} poses · ${approved}/${faces.length} faces · timing: ${state(subjectId('clip',row.clip))}`];
 data.forEach((value,i)=>{const td=document.createElement('td');if(i===1){const b=document.createElement('button');b.textContent=value;b.onclick=()=>{el('activity').value=row.activity;populateViews();el('view').value=row.view;populateClips();el('clip').value=row.clip;resetClip();};td.append(b);}else td.textContent=value;tr.append(td);});return tr;
}));}
function currentSubject(current){const kind=el('review-scope').value;return {kind,owner:kind==='scene'?'@project':spec().id,id:subjectFor(kind,{pose:current.pose,overlays:selectedOverlays(spec()),clip:el('clip').value,drawing:el('review-drawing').value,scene:el('scene').value})};}
function updateSubject(current){
 const existing=el('review-drawing').value,names=[...new Set([...spec().poses[current.pose].layers.map(l=>l.drawing),...Object.entries(selectedOverlays(spec())).map(([o,k])=>spec().overlays[o].drawings[k])])];
 select('review-drawing',names.map(n=>[n,n]),existing);el('review-drawing').disabled=el('review-scope').value!=='drawing';
 const subject=currentSubject(current),production=subject.owner==='@project'?bundle.project.production:spec().production;
 el('review-subject').textContent=`${subject.id} · ${editor().dirty?'unexported registration edits':statusFor(production,reviews,subject.owner,subject.id)}`;
}
function updateRegistration(current){
 const targets=editor().targets(current.pose),existing=el('registration-target').value;
 select('registration-target',targets.map(t=>[t.type+':'+t.name,t.label]),existing);
 const target=targets.find(t=>t.type+':'+t.name===el('registration-target').value);
 el('registration-x').value=target.point[0];el('registration-y').value=target.point[1];
 el('registration-status').textContent=editor().dirty?'Unexported edits. Export/apply the patch and rebuild before recording approvals.':'Drag the selected marker with Edit registration enabled. Shoulder/neck bindings move their associated drawings.';
 if(el('edit-registration').checked){const root=clip().motion?.roots[current.frame]??[0,0],p=target.point.map((v,i)=>placement().position[i]+(v+root[i]-spec().origin[i])*placement().scale),ctx=el('stage').getContext('2d');ctx.save();ctx.strokeStyle='#f4a321';ctx.lineWidth=4;ctx.beginPath();ctx.arc(...p,12,0,2*Math.PI);ctx.stroke();ctx.restore();}
}
function installRegistration(){
 const canvas=el('stage');let drag=null;
 el('edit-registration').onchange=()=>{el('error').hidden=true;playing=false;el('play').textContent='Play';el('play').disabled=el('edit-registration').checked;draw();};
 el('registration-target').onchange=draw;
 canvas.onpointerdown=guarded(event=>{if(!el('edit-registration').checked)return;const current=draw(),[type,name]=el('registration-target').value.split(':');const point=localPoint(canvasPoint(event,canvas),placement(),spec().origin,clip().motion?.roots[current.frame]??[0,0]),target=editor().targets(current.pose).find(t=>t.type===type&&t.name===name);if(Math.hypot(...point.map((v,i)=>v-target.point[i]))*placement().scale>24)return;editor().begin(current.pose);drag={pose:current.pose,type,name,root:clip().motion?.roots[current.frame]??[0,0]};canvas.setPointerCapture(event.pointerId);});
 canvas.onpointermove=event=>{if(!drag)return;guarded(()=>{editor().move(drag.pose,drag.type,drag.name,localPoint(canvasPoint(event,canvas),placement(),spec().origin,drag.root));draw();})();};
 const finish=()=>{if(drag){editor().commit();drag=null;watched.clear();makeMatrix();draw();}};canvas.onpointerup=finish;canvas.onpointercancel=finish;
 el('registration-apply').onclick=guarded(()=>{const current=viewsFor(bundle)[scene().actors.indexOf(placement())],[type,name]=el('registration-target').value.split(':');editor().begin(current.pose);editor().move(current.pose,type,name,[Number(el('registration-x').value),Number(el('registration-y').value)]);editor().commit();watched.clear();draw();makeMatrix();});
 for(const op of ['undo','redo'])el('registration-'+op).onclick=()=>{editor()[op]();watched.clear();draw();makeMatrix();};
 el('registration-export').onclick=guarded(()=>{requireValue(editor().dirty,'No registration changes');download(spec().id+'-registration.json',editor().patch());});
}

function download(name,data,type='application/json'){const blob=typeof data==='string'?new Blob([data],{type}):new Blob([JSON.stringify(data,null,2)],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function captureProof(){const clean=document.createElement('canvas');new DrawingRenderer(clean,scene(),bundle.images).render(viewsFor(bundle),tick/spec().fps,{smoke:false});return clean.toDataURL('image/png');}
function decide(decision){
 const current=draw(),s=spec(),subject=currentSubject(current),production=subject.owner==='@project'?bundle.project.production:s.production,signature=production?.review_manifest[subject.id]?.signature;
 requireValue(signature,'This review subject is not supported by the current export.');
 requireValue(![...editors.values()].some(e=>e.dirty),'Apply/export registration edits before reviewing their new revision.');
 requireValue(el('reviewer').value.trim()&&el('notes').value.trim(),'Enter the reviewer and visual observations.');
 requireValue(el('background').value==='scene','Review the subject in its scene.');
 if(decision==='approved'&&subject.kind==='clip')requireValue(watched.has(s.id+'/'+el('clip').value),'Play the complete clip at normal speed before accepting its timing.');
 const record={subject:subject.id,signature,decision,reviewer:el('reviewer').value.trim(),notes:el('notes').value.trim(),proof:captureProof(),context:{scene:el('scene').value,clip:el('clip').value,tick:Math.floor(tick),overlays:selectedOverlays(s),played:watched.has(s.id+'/'+el('clip').value)}};
 reviews.set(subject.owner+'/'+subject.id,record);el('review-status').textContent=`${subject.id}: ${decision}. Export the review bundle to save it in the repository.`;makeMatrix();updateSubject(current);
}

async function main(){
 const url=new URLSearchParams(location.search).get('project')??'../../build/seated-production/project.json';
 bundle=await loadProject(url,(n,total)=>el('message').textContent=`Loading drawings ${n} / ${total}`);
 for(const s of Object.values(bundle.specs))editors.set(s.id,new RegistrationEditor(s));
 renderer=new DrawingRenderer(el('stage'),bundle.project.scenes[bundle.project.initial_scene],bundle.images);
 const player=new URL('../player/',location.href);player.searchParams.set('project',new URL(url,location.href));el('player-link').href=player;
 select('scene',Object.entries(bundle.project.scenes).map(([id,s])=>[id,s.title??id]),bundle.project.initial_scene);populateActors();
 el('message').textContent=`${bundle.project.title}. Source revision ${bundle.revision.slice(0,12)}. Review decisions remain local until exported.`;
 el('scene').onchange=guarded(populateActors);el('actor').onchange=guarded(populateActivities);el('activity').onchange=guarded(populateViews);el('view').onchange=guarded(populateClips);el('clip').onchange=guarded(resetClip);
 for(const id of ['mouth','eyes','background','silhouette','anchors','contacts'])el(id).onchange=guarded(draw);
 el('frame').oninput=guarded(()=>{playing=false;watchedRun=null;el('play').textContent='Play';tick=Number(el('frame').value);draw();});
 el('previous').onclick=guarded(()=>{playing=false;tick=Math.max(0,Math.floor(tick)-1);el('play').textContent='Play';draw();});
 el('next').onclick=guarded(()=>{playing=false;tick=Math.min(duration()-1,Math.floor(tick)+1);el('play').textContent='Play';draw();});
 el('speed').onchange=()=>{watchedRun=null;};
 el('play').onclick=()=>{playing=!playing;last=null;watchedRun=playing&&tick===0&&Number(el('speed').value)===1?spec().id+'/'+el('clip').value:null;el('play').textContent=playing?'Pause':'Play';};
 el('pin').onclick=guarded(async()=>{baselineBundle=null;pinned=await createImageBitmap(el('stage'));el('baseline-figure').hidden=false;el('viewers').classList.add('comparing');el('unpin').disabled=false;el('baseline-caption').textContent='Pinned: '+el('current-caption').textContent;draw();});
 el('unpin').onclick=()=>{baselineBundle=null;pinned?.close();pinned=null;el('baseline-figure').hidden=true;el('viewers').classList.remove('comparing');el('unpin').disabled=true;};
 el('load-baseline').onclick=guarded(async()=>{const url=el('baseline-url').value;requireValue(url,'Enter a project URL');const candidate=await loadProject(url);viewsFor(candidate);baselineBundle=candidate;pinned?.close();pinned=null;el('baseline-figure').hidden=false;el('viewers').classList.add('comparing');el('unpin').disabled=false;el('baseline-caption').textContent='Earlier export: '+candidate.revision.slice(0,12);draw();});
 el('proof').onclick=()=>{const a=document.createElement('a');a.href=captureProof();a.download=draw().pose+'.png';a.click();};
 installRegistration();el('review-scope').onchange=draw;el('review-drawing').onchange=draw;
 el('accept').onclick=guarded(()=>decide('approved'));el('changes').onclick=guarded(()=>decide('changes'));
 el('export-reviews').onclick=guarded(()=>{const owner=el('review-scope').value==='scene'?'@project':spec().id,entries=[...reviews.entries()].filter(([key])=>key.startsWith(owner+'/')).map(([,r])=>r);requireValue(entries.length,'No recorded decisions for this scope');download(owner==='@project'?'project-reviews.json':owner+'-reviews.json',{version:2,...(owner==='@project'?{}:{character:owner}),reviews:entries});});
 el('export-matrix').onclick=()=>download('project-review-matrix.json',{version:1,project_revision:bundle.revision,subjects:[...Object.values(bundle.specs).flatMap(s=>Object.entries(s.production.review_manifest).map(([id,m])=>({character:s.id,subject:id,...m,status:editors.get(s.id).dirty?'stale':statusFor(s.production,reviews,s.id,id)}))),...Object.entries(bundle.project.production.review_manifest).map(([id,m])=>({subject:id,...m,status:[...editors.values()].some(e=>e.dirty)?'stale':statusFor(bundle.project.production,reviews,'@project',id)}))],cases:projectMatrix()});
 window.workbench={get bundle(){return bundle;},draw,matrix,editors,get tick(){return tick;},get reviews(){return reviews;}};
 function animate(now){try{if(playing&&last!==null){tick+=(now-last)/1000*spec().fps*Number(el('speed').value);if(tick>=duration()){if(watchedRun&&Number(el('speed').value)===1)watched.add(watchedRun);watchedRun=null;if(el('loop').checked)tick%=duration();else{tick=duration()-1;playing=false;el('play').textContent='Play';}}draw();}last=now;requestAnimationFrame(animate);}catch(e){el('error').hidden=false;el('error').textContent=e.message;playing=false;}}
 requestAnimationFrame(animate);
}
guarded(main)();
