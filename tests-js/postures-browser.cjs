/* Run after export, with the local server active; requires Playwright/Chrome. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  await page.goto('http://127.0.0.1:8765/web/player/');await page.waitForFunction(()=>window.mvp,{timeout:30000});
  await page.getByRole('button',{name:'Rehearsal room',exact:true}).click();
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  const step=async n=>{await page.evaluate(n=>{for(let i=0;i<n;i++)document.getElementById('step').click()},n);await page.waitForTimeout(20)};
  const audit=[];
  for(const actor of ['interviewer','analyst']) {
   await page.locator('#performer').selectOption(actor);
   for(const [action,state] of [[null,'seated'],['Uncross legs','seated_uncrossed'],['Lean back','reclined_uncrossed'],['Cross legs','reclined_crossed'],['Sit upright','seated']]) {
    if(action){await page.getByRole('button',{name:action,exact:true}).click();await step(24)}
    assert.equal(await page.evaluate(id=>window.mvp.actors[id].state,actor),state);
    for(const gesture of ['Offer','Concede','Qualify']) {
     await page.getByRole('button',{name:gesture,exact:true}).click();await step(9);
     const view=await page.evaluate(id=>window.mvp.actors[id].snapshot(window.mvp.clock),actor);
     assert(view.layers.some(l=>l.id.startsWith('free-')));assert(view.layers.some(l=>l.id.startsWith('cigarette-')));
     assert(!view.layers.some(l=>/posture.*arm/.test(l.id)),'Postures must reuse original arm sprites');
     if(state.startsWith('reclined'))assert(view.layers.some(l=>l.degrees!==0),'Reclined arms use rigid placements');
     const bodies=view.layers.filter(l=>l.id.startsWith('posture-body-'));
     assert.equal(bodies.length,1,'Every posture uses one complete torso-and-leg drawing');
     assert(bodies[0].z<30,'The seated body belongs behind the chair front');
     assert(view.layers.find(l=>l.id.startsWith('posture-legs-front-')).z>30,'Front legs overlap the cushion edge');
     assert(!view.layers.some(l=>/posture-(pelvis|thighs|torso)|lap-front/.test(l.id)),'No stitched torso/hip/leg pieces remain');
     if(state.startsWith('reclined'))assert(view.layers.find(l=>l.id.startsWith('posture-collar-')).z>view.layers.find(l=>l.id==='posture-head').z,'Front collar overlaps the neck base');
     await step(30);assert.equal(await page.evaluate(id=>window.mvp.actors[id].state,actor),state);
    }
    audit.push({actor,state,gestures:3});
   }
   await page.getByRole('button',{name:'Lean back',exact:true}).click();await step(24);
   await page.getByRole('button',{name:'Play speech sample',exact:true}).click();
   await page.waitForFunction(()=>document.getElementById('voice').currentTime>.15);
   const view=await page.evaluate(id=>window.mvp.snapshot().find(v=>v.layers.some(l=>l.image.startsWith(window.mvp.actors[id].spec.id+'/'))),actor);
   const mouth=view.layers.find(l=>l.id.startsWith('mouth-'));
   const expected=await page.evaluate(({id,drawing})=>{
    const a=window.mvp.actors[id],p=a.spec.poses[a.snapshot(window.mvp.clock).pose];
    return a.spec.drawings[drawing].position.map((v,i)=>a.placement.position[i]+(v+p.overlay_offsets.mouth[i]-a.spec.origin[i])*a.placement.scale);
   },{id:actor,drawing:mouth.id});assert.deepEqual(mouth.position,expected);
   await page.getByRole('button',{name:'Step one frame',exact:true}).click();
   const at=await page.evaluate(()=>document.getElementById('voice').currentTime);await page.waitForTimeout(120);
   assert.equal(await page.evaluate(()=>document.getElementById('voice').currentTime),at,'Frame stepping pauses the sample audio');
   await page.getByRole('button',{name:'Look at camera',exact:true}).click();await step(1);
   await page.screenshot({path:`build/seated-mvp/${actor}-reclined-speech.png`,fullPage:true});
   await page.getByRole('button',{name:'Skip line',exact:true}).click();
   await page.getByRole('button',{name:'Sit upright',exact:true}).click();await step(24);
  }
  // Both changes coexist, and the table remains above the legs in scene data.
  for(const actor of ['interviewer','analyst']) {
   await page.locator('#performer').selectOption(actor);
   await page.getByRole('button',{name:'Uncross legs',exact:true}).click();await step(24);
   await page.getByRole('button',{name:'Lean back',exact:true}).click();await step(24);
  }
  await page.locator('canvas').screenshot({path:'build/seated-mvp/reclined-uncrossed-preview.png'});
  assert(await page.evaluate(()=>window.mvp.project.scenes[window.mvp.project.initial_scene].foregrounds.some(f=>f.file.includes('table')&&f.z>40)));
  await page.getByRole('button',{name:'Start over',exact:true}).click();
  assert(await page.evaluate(()=>Object.values(window.mvp.actors).every(a=>a.state==='seated')));
  await page.getByRole('button',{name:'Rehearsal room',exact:true}).click();
  await page.getByRole('button',{name:'Uncross legs',exact:true}).click();await step(24);
  assert.equal(await page.evaluate(()=>window.mvp.actors[document.getElementById('performer').value].state),'seated_uncrossed','Controls bind to reset actors');
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  await fs.writeFile('build/seated-mvp/posture-verification.json',JSON.stringify({passed:true,audit,errors,checked_at:new Date().toISOString()},null,2)+'\n');
  console.log('Posture browser checks passed: both actors, four postures, reused arms, gestures, face anchors, speech/step pause, reverse actions, reset and mobile.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
