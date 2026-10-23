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
  assert.match(await page.locator('#workspaceDialog [role=status]').innerText(),/Preferences saved/);
  assert(!await page.evaluate(()=>JSON.stringify({...localStorage}).includes('test-session-secret')),'key persisted');
  await page.locator('[name=provider]').selectOption('server');await page.locator('[name=theme]').selectOption('light');await page.getByRole('button',{name:'Forget credentials'}).click();await page.getByRole('button',{name:'Save preferences',exact:true}).click();
  const historyDownload=page.waitForEvent('download');await page.locator('#exportHistory').click();assert.equal((await historyDownload).suggestedFilename(),'saarthi-conversations.json');
  await page.locator('#manageTools').click();await page.locator('#discoverTools').click();await page.getByText('MCP tool discovery is not authorized.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Close dialog'}).click();await page.getByRole('button',{name:'Open Settings',exact:true}).click();
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
  page.once('dialog',dialog=>dialog.dismiss());await page.getByRole('button',{name:'Delete policy.txt',exact:true}).click();assert.equal(await page.locator('.document-list article').count(),1);
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Delete policy.txt',exact:true}).click();await page.getByText('Document deleted.',{exact:true}).waitFor();assert.equal(await page.locator('.document-list article').count(),0);
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.locator('.workspace-nav a').click();await page.frameLocator('.appforge-workspace').locator('#prompt').waitFor();
  // Browser fixture checks generated-code editing and isolation; vendor inference is tested separately.
  const files={'index.html':'<!doctype html><html><head><link rel="stylesheet" href="styles.css"></head><body><button id="counter">0</button><script src="app.js"></script></body></html>','styles.css':'body{background:#eff8f5;font:20px system-ui;padding:24px}button{padding:20px;border-radius:12px;color:teal}','app.js':'document.getElementById("counter").onclick=e=>e.target.textContent=Number(e.target.textContent)+1;'};
  await page.route('**/api/appforge/generate',route=>route.fulfill({json:{ok:true,files,html:files['index.html'],mode:'ai-generated',note:'Controlled test project'}}));
  const appforge=page.frameLocator('.appforge-workspace');await appforge.locator('#generate').click();
  const preview=appforge.frameLocator('#preview');await preview.locator('#counter').click();assert.equal(await preview.locator('#counter').innerText(),'1');
  assert.equal(await appforge.locator('#preview').getAttribute('sandbox'),'allow-scripts');
  await appforge.getByRole('button',{name:'Code',exact:true}).click();await appforge.locator('#filePicker').selectOption('app.js');assert.match(await appforge.locator('#codeEditor').inputValue(),/onclick/);
  await appforge.locator('#codeEditor').fill('document.getElementById("counter").onclick=e=>e.target.textContent="edited";');
  await appforge.locator('#applyCode').click();await appforge.getByRole('button',{name:'Preview',exact:true}).click();
  await preview.locator('#counter').click();assert.equal(await preview.locator('#counter').innerText(),'edited');
  await appforge.locator('#restoreVersion').click();await preview.locator('#counter').click();assert.equal(await preview.locator('#counter').innerText(),'1');
  const downloadPromise=page.waitForEvent('download');await appforge.locator('#downloadProject').click();const download=await downloadPromise;
  assert.match(download.suggestedFilename(),/\.zip$/);const zipPath=await download.path();
  require('node:child_process').execFileSync(process.env.PYTHON||'python',['-c','import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); assert set(z.namelist())=={"index.html","styles.css","app.js"}; assert b"onclick" in z.read("app.js")',zipPath]);
  assert(await appforge.locator('#cloudBuild').isDisabled(),'unconfigured build must be disabled');
  await page.screenshot({path:'docs/evidence/android-appforge.png'});
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.evaluate(async()=>{await navigator.serviceWorker.ready;});
  await page.reload();await page.waitForFunction(()=>navigator.serviceWorker.controller);
  await context.setOffline(true);await page.reload();await page.waitForFunction(()=>!!window.SaarthiWorkspace);
  await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});
  // Deliberately stale browser connectivity hint reproduces the Chromium CI failure.
  await page.evaluate(()=>Object.defineProperty(navigator,'onLine',{get:()=>true,configurable:true}));
  await page.locator('#saarthiCommand').fill('calculate 15% of 200');await page.locator('#sendCommand').click();await page.waitForFunction(()=>document.getElementById('assistantResponseBody').textContent.includes('30'));
  assert.match(await page.locator('#assistantResponseBody').innerText(),/30/);
  await context.setOffline(false);
  await page.evaluate(()=>delete navigator.onLine);
  await page.setViewportSize({width:393,height:450});
  const composer=await page.locator('#conversationComposer').boundingBox();assert(composer.y>=0&&composer.y+composer.height<=450,'composer outside reduced keyboard viewport');
  for(const width of [360,412,768,1440]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'overflow '+width);}
  await page.screenshot({path:'docs/evidence/desktop-chat.png'});
  await page.evaluate(()=>{const state=JSON.parse(localStorage.getItem('saarthi.history.v2'));const thread=state.assistants.saarthi[0];thread.messages=Array.from({length:30},(_,i)=>({role:i%2?'assistant':'user',content:'Archived message '+i}));thread.updatedAt=new Date(Date.now()+1000).toISOString();localStorage.setItem('saarthi.history.v2',JSON.stringify(state));});
  await page.reload();await page.waitForFunction(()=>!!window.SaarthiWorkspace);await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});
  await page.locator('.workspace-nav [data-screen=history]').click();await page.locator('#mobileHistory .history-thread').first().click();await page.locator('#saarthiCommand').fill('calculate 2 + 2');await page.locator('#sendCommand').click();await page.waitForFunction(()=>Object.values(JSON.parse(localStorage.getItem('saarthi.history.v2')).assistants).flat().some(t=>t.messages.length===32));
  await page.evaluate(()=>{const key='saarthi.appforge.projects.v1',projects=JSON.parse(localStorage.getItem(key));for(let i=0;i<31;i++)projects.push({id:crypto.randomUUID(),name:'Archived project '+i,prompt:'Archive fixture',files:{'index.html':'<html><body>Archive</body></html>'},versions:[],updatedAt:new Date().toISOString()});localStorage.setItem(key,JSON.stringify(projects));});
  await page.locator('.workspace-nav a').click();await page.frameLocator('.appforge-workspace').locator('#projectPicker option').nth(31).waitFor({state:'attached'});assert.equal(await page.frameLocator('.appforge-workspace').locator('#projectPicker option').count(),32);
  const archiveWorkspace=page.frameLocator('.appforge-workspace');await archiveWorkspace.locator('#newProject').click();assert.equal(await archiveWorkspace.locator('#projectPicker option').count(),33);
  for(const width of [360,393,412]){await page.setViewportSize({width,height:852});assert(await archiveWorkspace.locator('html').evaluate(el=>el.scrollWidth<=innerWidth),'AppForge overflow '+width);}

  await archiveWorkspace.getByRole('link',{name:'Back to SAARTHI'}).click();assert(!await page.locator('#workspaceDialog').isVisible(),'AppForge back should close workspace, not nest the home page');
  assert.deepEqual(errors,[]);
  console.log('PASS: settings, provider preferences, secret non-persistence, calculator routing, history, knowledge upload/search, embedded AppForge, offline shell/utilities, responsive widths 360/393/412/768/1440, no page errors');
 }finally{if(browser)await browser.close();server.kill('SIGTERM');}
})().catch(error=>{console.error(error);process.exitCode=1;});
