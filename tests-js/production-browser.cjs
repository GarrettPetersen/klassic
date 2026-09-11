// Integration checks for exported atlases, review controls and session persistence.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
  console.log('Opening next page');await page.goto('http://127.0.0.1:8765/web/review/');await page.waitForFunction(()=>window.workbench,null,{timeout:60000});
  assert.equal(await page.locator('#error').isVisible(),false);
  await page.selectOption('#clip','uncross-seated');await page.click('#next');assert.equal(await page.evaluate(()=>window.workbench.tick),1);
  await page.check('#anchors');await page.check('#contacts');await page.click('#pin');assert(await page.locator('#baseline-figure').isVisible());
  await page.selectOption('#background','checker');await page.check('#silhouette');await page.screenshot({path:'build/seated-production/workbench-guides.png',fullPage:true});
  await page.selectOption('#background','scene');await page.uncheck('#silhouette');await page.uncheck('#anchors');await page.uncheck('#contacts');await page.click('#unpin');
  await page.fill('#reviewer','Integration test');await page.fill('#notes','Test-only needs-changes record. This is not an art approval.');await page.click('#changes');
  assert.equal(await page.evaluate(()=>window.workbench.reviews.size),1);
  const downloaded=page.waitForEvent('download');await page.click('#export-reviews');const download=await downloaded;const bundle=JSON.parse(await fs.readFile(await download.path(),'utf8'));assert.equal(bundle.reviews[0].decision,'changes');assert(bundle.reviews[0].proof.startsWith('data:image/png;base64,'));
  await page.screenshot({path:'build/seated-production/workbench-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:'build/seated-production/workbench-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  console.log('Opening next page');await page.goto('http://127.0.0.1:8765/web/player/?project=../../build/seated-production/project.json');await page.waitForFunction(()=>window.mvp,null,{timeout:60000});
  await page.locator('#choices button').first().click();await page.waitForFunction(()=>document.getElementById('voice').currentTime>.1);await page.click('#pause');
  // Saving is independent of rehearsal and preserves the current spoken line.
  await page.locator('.session-tools summary').click();await page.click('#save-session');console.log('Saved audio');
  const original=await page.evaluate(()=>({id:window.mvp.conversation.id,audio:document.getElementById('voice').currentTime}));
  await page.click('#skip');await page.click('#load-session');
  await page.waitForFunction(()=>document.getElementById('session-status').textContent.startsWith('Restored'));
  assert.equal(await page.evaluate(()=>window.mvp.conversation.id),original.id);assert(Math.abs(await page.evaluate(()=>document.getElementById('voice').currentTime)-original.audio)<.05);
  console.log('Opening next page');await page.goto('http://127.0.0.1:8765/web/player/?project=../../build/arrival/project.json');await page.waitForFunction(()=>window.mvp,null,{timeout:60000});
  await page.locator('.session-tools summary').click();await page.click('#run-scene');
  await page.waitForFunction(()=>window.mvp.clock>8.5);await page.screenshot({path:'build/arrival/seated-study.png',fullPage:true});
  await page.waitForFunction(()=>window.mvp.clock>20.1);assert.equal(await page.locator('#error').isVisible(),false);
  assert.equal(await page.evaluate(()=>window.mvp.actors.host.state),'front');assert(await page.evaluate(()=>Math.hypot(...window.mvp.actors.host.placement.position.map((v,i)=>v-[1266,890][i]))<1e-6));
  console.log('Arrival completed');const recordingDownload=page.waitForEvent('download');await page.click('#recording-export');const recording=await recordingDownload;
  await page.setInputFiles('#recording-import',await recording.path());await page.waitForFunction(()=>document.getElementById('session-status').textContent.startsWith('Performance recording loaded'));
  assert(await page.evaluate(()=>window.mvp.clock<.1));await page.click('#pause');await page.waitForFunction(()=>window.mvp.clock>1.5);
  assert(await page.evaluate(()=>window.mvp.actors.host.snapshot(window.mvp.clock).anchors.root[0]>18));
  console.log('Opening next page');await page.goto('http://127.0.0.1:8765/web/review/?project=../../build/arrival/project.json');await page.waitForFunction(()=>window.workbench,null,{timeout:60000});
  await page.selectOption('#activity','walking');assert.equal(await page.locator('#clip').inputValue(),'stride');await page.click('#play');await page.waitForTimeout(300);await page.click('#play');
  await page.screenshot({path:'build/arrival/walking-review.png',fullPage:true});assert.deepEqual(errors,[]);
  console.log('Production browser checks passed: atlas loading, frame controls, guides, proof export, mobile, saved audio, arrival performance and walking capability.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
