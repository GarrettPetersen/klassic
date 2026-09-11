// Reference composition invariants. Screenshots are evidence, not automatic art approvals.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await b.newPage({viewport:{width:1440,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765/web/review/?project=../../build/adrian-seated/project.json');await page.waitForFunction(()=>window.workbench);
 assert.equal(await page.inputValue('#activity'),'seated');await page.selectOption('#clip','offer');
 const samples=[];for(const tick of [0,4,8,32,37]){await page.locator('#frame').evaluate((e,t)=>{e.value=t;e.dispatchEvent(new Event('input'))},tick);samples.push(await page.evaluate(()=>{const v=window.workbench.draw();return {contacts:v.contacts,body:v.layers.find(l=>l.image.endsWith('/seated-base'))};}));await page.locator('#stage').screenshot({path:`build/adrian-seated/reference-${tick}.png`});}
 assert(samples[0].body);for(const sample of samples){assert.deepEqual(sample.body,samples[0].body);assert.deepEqual(sample.contacts,samples[0].contacts);}
 await page.locator('#frame').evaluate(e=>{e.value=0;e.dispatchEvent(new Event('input'))});await page.uncheck('#loop');await page.click('#play');await page.waitForFunction(()=>document.getElementById('play').textContent==='Play');assert.match(await page.textContent('#drift'),/12 adjacent planted contacts remain fixed/);
 await page.goto('http://127.0.0.1:8765/web/player/?project=../../build/adrian-seated/project.json');await page.waitForFunction(()=>window.mvp);assert.equal(await page.evaluate(()=>window.mvp.actors.host.state),'seated');await page.locator('.session-tools summary').click();await page.click('#run-scene');await page.waitForFunction(()=>window.mvp.clock>4.1);assert.equal(await page.locator('#error').isVisible(),false);await page.screenshot({path:'build/adrian-seated/player-reference.png',fullPage:true});assert.deepEqual(errors,[]);
 console.log('Reference checks passed: initial seated placement, fixed body, 3 planted contacts, normal-speed gesture, scene performance.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});
