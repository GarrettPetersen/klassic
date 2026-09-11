const {chromium}=require('playwright');const fs=require('fs/promises');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{const p=await b.newPage();await p.goto('http://127.0.0.1:8765/web/player/');await p.waitForFunction(()=>window.mvp);const results=await p.evaluate(async()=>{
const {loadProject}=await import('./assets.js');const {Actor}=await import('./runtime.js');const {DrawingRenderer}=await import('./renderer.js');const bundle=await loadProject('../../build/seated-mvp/project.json');const canvas=document.createElement('canvas');const renderer=new DrawingRenderer(canvas,bundle.project.scene,bundle.images);const results={};const keys=['X','A','B','C','D','E','F','G','H'];
for(const state of ['seated','seated_uncrossed','reclined_crossed','reclined_uncrossed','leaning_uncrossed']){
const actors=bundle.project.scene.actors.map(a=>new Actor({...bundle.specs[a.character],initial_state:state==='leaning_uncrossed'?'seated_uncrossed':state},a));
const at=state==='leaning_uncrossed'?4/24:0;if(at)actors.forEach(a=>a.requestIntent('lean_back',0));
const gallery=document.createElement('canvas');gallery.width=900;gallery.height=1260;const ctx=gallery.getContext('2d');ctx.fillStyle='#aaa';ctx.fillRect(0,0,900,1260);
for(let i=0;i<keys.length;i++){
renderer.render(actors.map(a=>a.snapshot(at,{mouth:keys[i],eyes:'partner-open'})),0,{smoke:false});
if(i===0)results['boundary-'+state]=canvas.toDataURL();
for(const [n,x] of [[0,170],[1,1020]]){ctx.drawImage(canvas,x,310,300,180,(i%3)*300,Math.floor(i/3)*420+n*210,300,180);ctx.fillStyle='#000';ctx.fillText(keys[i]+' '+(n?'Fromm':'Krusty'),(i%3)*300+5,Math.floor(i/3)*420+n*210+199);}
}
results['collars-'+state]=gallery.toDataURL();}
return results;});for(const[n,data]of Object.entries(results))await fs.writeFile('build/seated-mvp/'+n+'.png',Buffer.from(data.split(',')[1],'base64'));}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
