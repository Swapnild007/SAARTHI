const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base='http://127.0.0.1:8765';
const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8765'],{env:{...process.env,SAARTHI_RATE_LIMIT_PER_MINUTE:'2000'},stdio:'pipe'});
server.stderr.on('data',()=>{});
(async()=>{
 let browser;
 try{
  for(let n=0;n<60;n++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
  browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--disable-gpu']}:{} )});
  const context=await browser.newContext({viewport:{width:393,height:852},isMobile:true,hasTouch:true});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error('PAGE ERROR',e.message);});page.on('console',e=>{if(e.type()==='error')console.error('BROWSER',e.text().slice(0,400));});
  await page.goto(base);await page.waitForFunction(()=>!!window.SaarthiApp&&!!window.SaarthiWorkspace);
  await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile overflow');
  await page.getByRole('button',{name:'Open Settings',exact:true}).click();
  await page.locator('[name=provider]').selectOption('groq');await page.locator('[name=model]').fill('test-model');await page.locator('[name=key]').fill('test-session-secret');
  await page.locator('[name=theme]').selectOption('dark');await page.getByRole('button',{name:'Save preferences',exact:true}).click();
  assert.match(await page.locator('[role=status]').innerText(),/Preferences saved/);
  assert(!await page.evaluate(()=>JSON.stringify({...localStorage}).includes('test-session-secret')),'key persisted');
  await page.locator('[name=provider]').selectOption('server');await page.locator('[name=theme]').selectOption('light');await page.getByRole('button',{name:'Forget credentials'}).click();await page.getByRole('button',{name:'Save preferences',exact:true}).click();
  await page.locator('#workspaceDialog').evaluate(el=>el.scrollTop=0);
  await page.screenshot({path:'docs/evidence/android-settings.png'});
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.locator('#saarthiCommand').fill('Calculate (12 + 8) * 3');await page.locator('#sendCommand').click();
  await page.waitForFunction(()=>document.getElementById('assistantResponseBody').textContent.includes('60'),null,{timeout:12000}).catch(async e=>{console.log('BODY',await page.locator('#assistantResponseBody').innerText());throw e;});
  assert.match(await page.locator('#assistantResponseBody').innerText(),/60/);
  assert.equal(await page.evaluate(()=>Object.values(JSON.parse(localStorage.getItem('saarthi.history.v2')).assistants).flat()[0].messages.length),2);
  await page.screenshot({path:'docs/evidence/android-chat.png'});
  await page.reload();await page.waitForFunction(()=>!!window.SaarthiWorkspace);await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});
  await page.locator('.workspace-nav [data-screen=history]').click();await page.locator('#mobileHistory .history-thread').first().click();assert.match(await page.locator('#assistantResponseBody').innerText(),/60/);
  await page.locator('.workspace-nav [data-screen=knowledge]').click();
  await page.locator('#knowledgeUpload').setInputFiles({name:'policy.txt',mimeType:'text/plain',buffer:Buffer.from('The escalation threshold for CountyCare is ninety percent. Contact the duty manager if the queue is red.')});
  await page.getByText('Document indexed locally.',{exact:false}).waitFor();
  await page.locator('#knowledgeSearch').fill('escalation');assert.match(await page.locator('#knowledgeResults').innerText(),/ninety percent/);
  await page.screenshot({path:'docs/evidence/android-knowledge.png'});
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.locator('.workspace-nav a').click();await page.frameLocator('.appforge-workspace').locator('#prompt').waitFor();
  await page.screenshot({path:'docs/evidence/android-appforge.png'});
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.evaluate(async()=>{await navigator.serviceWorker.ready;});
  await page.reload();await page.waitForFunction(()=>navigator.serviceWorker.controller);
  await context.setOffline(true);await page.reload();await page.waitForFunction(()=>!!window.SaarthiWorkspace);
  await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});
  await page.locator('#saarthiCommand').fill('calculate 15% of 200');await page.locator('#sendCommand').click();await page.waitForFunction(()=>document.getElementById('assistantResponseBody').textContent.includes('30'));
  assert.match(await page.locator('#assistantResponseBody').innerText(),/30/);
  await context.setOffline(false);
  for(const width of [360,412,768,1440]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'overflow '+width);}
  await page.screenshot({path:'docs/evidence/desktop-chat.png'});
  assert.deepEqual(errors,[]);
  console.log('PASS: settings, provider preferences, secret non-persistence, calculator routing, history, knowledge upload/search, embedded AppForge, offline shell/utilities, responsive widths 360/393/412/768/1440, no page errors');
 }finally{if(browser)await browser.close();server.kill('SIGTERM');}
})().catch(error=>{console.error(error);process.exitCode=1;});
