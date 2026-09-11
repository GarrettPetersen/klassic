/* Run with the local server active. Requires Playwright and installed Chrome. */
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const OUT=path.resolve('build/seated-mvp');
const URL='http://127.0.0.1:8765/web/player/';
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
    page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
    await page.goto(URL);await page.waitForFunction(()=>window.mvp,{timeout:30000});
    await page.waitForTimeout(300);
    assert.equal(await page.locator('#choices button').count(),2);
    await page.screenshot({path:path.join(OUT,'conversation-desktop.png'),fullPage:true});
    await page.getByRole('button',{name:'What makes this a good society?'}).click();
    await page.waitForFunction(()=>document.getElementById('voice').currentTime>.1);
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    const before=await page.evaluate(()=>[window.mvp.clock,document.getElementById('voice').currentTime]);
    await page.waitForTimeout(300);
    const after=await page.evaluate(()=>[window.mvp.clock,document.getElementById('voice').currentTime]);
    assert.deepEqual(after,before,'Pause must stop both clocks');
    await page.getByRole('button',{name:'Resume',exact:true}).click();
    await page.waitForTimeout(350);
    assert((await page.evaluate(()=>document.getElementById('voice').currentTime))>after[1]);
    // A stale media completion event must not skip the current line.
    await page.evaluate(()=>document.getElementById('voice').dispatchEvent(new Event('ended')));
    assert.equal(await page.evaluate(()=>window.mvp.conversation.id),'society_question');
    await page.evaluate(()=>{const a=document.getElementById('voice');a.currentTime=a.duration-.06});
    await page.waitForFunction(()=>window.mvp.conversation.id==='society_answer');
    await page.waitForFunction(()=>document.getElementById('voice').currentTime>.1);
    await page.getByRole('button',{name:'Skip line',exact:true}).click();
    await page.getByRole('button',{name:'Turn the conversation to work.'}).click();
    await page.waitForFunction(()=>window.mvp.conversation.id==='work_question');
    await page.getByRole('button',{name:'Skip line',exact:true}).click();
    await page.waitForFunction(()=>window.mvp.conversation.id==='work_answer');
    await page.waitForTimeout(850);
    assert.equal(await page.locator('#heading').textContent(),'Erich Fromm');
    assert((await page.locator('#caption').textContent()).length>0);
    await page.screenshot({path:path.join(OUT,'conversation-response.png'),fullPage:true});
    await page.getByRole('button',{name:'Skip line',exact:true}).click();
    assert.equal(await page.getByRole('button',{name:'Press him on what meaningful work actually means.'}).count(),1);
    assert.equal(await page.getByRole('button',{name:'Turn the conversation to work.'}).count(),0);
    await page.getByRole('button',{name:'Press him on what meaningful work actually means.'}).click();
    await page.waitForFunction(()=>window.mvp.conversation.id==='meaning_question');
    await page.getByRole('button',{name:'Skip line',exact:true}).click();
    await page.waitForFunction(()=>window.mvp.conversation.id==='meaning_answer');
    await page.getByRole('button',{name:'Skip line',exact:true}).click();
    await page.getByRole('button',{name:'Begin another interview'}).click();
    assert.equal(await page.locator('#choices button').count(),2);
    await page.getByRole('button',{name:'Surely earning a living gives work meaning?'}).click();
    await page.waitForFunction(()=>window.mvp.conversation.id==='work_question');
    await page.getByRole('button',{name:'Rehearsal room'}).click();
    assert.equal(await page.evaluate(()=>window.mvp.active),null);
    assert(await page.evaluate(()=>window.mvp.snapshot().every(s=>s.layers.some(l=>l.id==='mouth-X'))));
    await page.waitForTimeout(1450);
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    const audit={};
    for(const actor of ['interviewer','analyst']) {
      await page.locator('#performer').selectOption(actor);
      for(const action of ['offer','concede','qualify']) {
        await page.getByRole('button',{name:action[0].toUpperCase()+action.slice(1),exact:true}).click();
        const poses=await page.evaluate(async({actor})=>{
          const observed=[];
          for(let i=0;i<35;i++) {
            document.getElementById('step').click();await new Promise(r=>setTimeout(r,0));
            observed.push(window.mvp.actors[actor].snapshot(window.mvp.clock).pose);
          }
          return [...new Set(observed)];
        },{actor});
        const neutral=await page.evaluate(id=>{const a=window.mvp.actors[id];return a.spec.states[a.state].pose},actor);
        assert(poses.includes(neutral)&&poses.length===3,`${actor}/${action}: ${poses}`);
        audit[`${actor}/${action}`]=poses;
      }
      await page.getByRole('button',{name:'Look at camera',exact:true}).click();
      await page.getByRole('button',{name:'Step one frame'}).click();
      await page.screenshot({path:path.join(OUT,`${actor}-rehearsal.png`),fullPage:true});
    }
    const frozen=await page.evaluate(()=>window.mvp.clock);
    await page.getByRole('button',{name:'Step one frame'}).click();
    assert(Math.abs((await page.evaluate(()=>window.mvp.clock))-frozen-1/24)<1e-8);
    await page.getByRole('button',{name:'Start over',exact:true}).click();
    assert(await page.locator('#lab').isHidden());
    assert.equal(await page.locator('#choices button').count(),2);
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(OUT,'conversation-mobile.png'),fullPage:true});
    assert.equal(await page.locator('#error').isHidden(),true);
    assert.deepEqual(errors,[]);
    // Corrupt an asset deliberately: the player must show the actual failure.
    const assetFile=await page.evaluate(()=>Object.values(Object.values(window.mvp.actors)[0].spec.drawings)[0].file);
    const broken=await browser.newPage();
    await broken.route('**/krusty-study/'+assetFile,route=>route.fulfill({status:200,contentType:'image/png',body:'corrupt'}));
    await broken.goto(URL);
    await broken.waitForFunction(()=>!document.getElementById('error').hidden);
    assert.match(await broken.locator('#error').textContent(),/Asset changed after export/);
    await broken.close();
    await fs.writeFile(path.join(OUT,'browser-verification.json'),JSON.stringify({passed:true,
      conversation_branches:['society','work','meaning'],checks:['audio completion','pause/resume clocks','skip','restart','stale ended event','conditional follow-up','rehearsal interruption','neutral recovery','frame stepping','camera gaze','mobile overflow','asset corruption fails visibly'],
      pose_audit:audit,browser_errors:errors,checked_at:new Date().toISOString()},null,2)+'\n');
    console.log('Browser checks passed: both branches, dialogue controls, six gesture clips, chair composition preview, mobile and corrupt-asset failure.');
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
