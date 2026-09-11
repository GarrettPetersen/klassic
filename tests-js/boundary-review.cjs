const {chromium}=require('playwright');const fs=require('fs/promises');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{const p=await b.newPage();await p.goto('http://127.0.0.1:8765/web/player/');await p.waitForFunction(()=>window.mvp);const results=await p.evaluate(async()=>{
const {loadProject}=await import('./assets.js');const {Actor}=await import('./runtime.js');const {DrawingRenderer}=await import('./renderer.js');const bundle=await loadProject('../../build/seated-mvp/project.json');const canvas=document.createElement('canvas');const renderer=new DrawingRenderer(canvas,bundle.project.scenes[bundle.project.initial_scene],bundle.images);const results={};const keys=['X','A','B','C','D','E','F','G','H'];
for(const state of ['seated','seated_uncrossed','reclined_crossed','reclined_uncrossed','leaning_crossed','leaning_uncrossed','uncrossing_upright','uncrossing_reclined']){
const transitions={leaning_crossed:['seated','lean_back'],leaning_uncrossed:['seated_uncrossed','lean_back'],uncrossing_upright:['seated','uncross'],uncrossing_reclined:['reclined_crossed','uncross']};
const transition=transitions[state];
const actors=bundle.project.scenes[bundle.project.initial_scene].actors.map(a=>new Actor({...bundle.specs[a.character],initial_state:transition?transition[0]:state},a));
const at=transition?4/24:0;if(transition)actors.forEach(a=>a.requestIntent(transition[1],0));
const gallery=document.createElement('canvas');gallery.width=900;gallery.height=1260;const ctx=gallery.getContext('2d');ctx.fillStyle='#aaa';ctx.fillRect(0,0,900,1260);
for(let i=0;i<keys.length;i++){
renderer.render(actors.map(a=>a.snapshot(at,{mouth:keys[i],eyes:'partner-open'})),0,{smoke:false});
if(i===0)results['boundary-'+state]=canvas.toDataURL();
for(const [n,x] of [[0,170],[1,1020]]){ctx.drawImage(canvas,x,310,300,180,(i%3)*300,Math.floor(i/3)*420+n*210,300,180);ctx.fillStyle='#000';ctx.fillText(keys[i]+' '+(n?'Fromm':'Krusty'),(i%3)*300+5,Math.floor(i/3)*420+n*210+199);}
}
results['collars-'+state]=gallery.toDataURL();
if(!transition){
const gestures=document.createElement('canvas');gestures.width=2172;gestures.height=565;const g=gestures.getContext('2d');g.fillStyle='#aaa';g.fillRect(0,0,2172,565);
for(const[i,intent]of ['offer','concede','qualify'].entries()){
const performers=bundle.project.scenes[bundle.project.initial_scene].actors.map(a=>new Actor({...bundle.specs[a.character],initial_state:state},a));performers.forEach(a=>a.requestIntent(intent,0));
renderer.render(performers.map(a=>a.snapshot(9/24,{mouth:'X',eyes:'partner-open'})),0,{smoke:false});g.drawImage(canvas,i*724,0,724,543);g.fillStyle='#000';g.fillText(intent,i*724+10,558);
}results['gestures-'+state]=gestures.toDataURL();}}
return results;});for(const[n,data]of Object.entries(results))await fs.writeFile('build/seated-mvp/'+n+'.png',Buffer.from(data.split(',')[1],'base64'));}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
