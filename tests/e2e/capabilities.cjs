// Controlled browser fixtures validate app behavior, not vendor speech or physical Android.
const {chromium}=require('playwright');const {spawn}=require('node:child_process');const assert=require('node:assert/strict');
const AxeBuilder=require('@axe-core/playwright').default;const fs=require('node:fs');
const base='http://127.0.0.1:8768';
const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8768'],{env:{...process.env,SAARTHI_RATE_LIMIT_PER_MINUTE:'2000'},stdio:'pipe'});
server.stderr.on('data',()=>{});
(async()=>{let browser;try{
  for(let n=0;n<60;n++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
  browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']}:{} )});
  const context=await browser.newContext({viewport:{width:393,height:852},isMobile:true,hasTouch:true});
  await context.addInitScript(()=>{
    window.SpeechRecognition=class{constructor(){window.recognitionFixture=this;}start(){this.onstart?.();}stop(){this.onend?.();}abort(){this.onend?.();}};
  });
  const page=await context.newPage(),errors=[],scans=[];page.on('pageerror',e=>errors.push(e.message));
  async function load(){await page.goto(base);await page.waitForFunction(()=>window.SaarthiWorkspace&&window.SaarthiVoice);await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});}
  async function scan(screen){const r=await new AxeBuilder({page}).include('#workspaceDialog').analyze();const serious=r.violations.filter(v=>['serious','critical'].includes(v.impact));assert.deepEqual(serious.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})),[],screen);scans.push({screen,serious:serious.length});}
  await load();await page.evaluate(()=>SaarthiWorkspace.open('device'));
  await page.locator('[name=language]').selectOption('mr-IN');await page.locator('[name=muted]').check();await page.getByRole('button',{name:'Save voice preferences',exact:true}).click();
  await page.getByRole('button',{name:'Get foreground location',exact:true}).click();await page.locator('#deviceResult').filter({hasText:'UNSUPPORTED'}).waitFor();await scan('voice-device-light');
  await page.getByRole('button',{name:'Close dialog'}).click();
  await page.locator('#voiceCommand').click();assert.equal(await page.evaluate(()=>recognitionFixture.lang),'mr-IN');
  // Stop while recognition is pending, then ensure a late result never submits.
  await page.evaluate(()=>{const old=recognitionFixture;SaarthiVoice.stop();const r=[{transcript:'open youtube'}];r.isFinal=true;old.onresult({resultIndex:0,results:[r]});});
  assert.equal(await page.locator('#saarthiCommand').inputValue(),'');
  await page.locator('#voiceCommand').click();await page.evaluate(()=>{const r=[{transcript:'calculate 7 * 8'}];r.isFinal=true;recognitionFixture.onresult({resultIndex:0,results:[r]});});
  await page.waitForFunction(()=>document.getElementById('assistantResponseBody').textContent.includes('56'));
  await page.getByRole('button',{name:'Open Settings',exact:true}).click();await page.locator('#memorySettings').click();
  await page.locator('[name=note]').fill('My project astronomy is Astro Lens.');await page.getByRole('button',{name:'Save memory',exact:true}).click();
  assert.equal(await page.evaluate(()=>SaarthiWorkspace.retrieve('astronomy').length),0,'memory needs explicit sharing');
  await page.locator('#memoryConsent').check();assert.equal(await page.evaluate(()=>SaarthiWorkspace.retrieve('astronomy')[0].content),'My project astronomy is Astro Lens.');
  await scan('memory-light');await page.screenshot({path:'docs/evidence/memory-mobile.png'});
  await page.getByRole('button',{name:'Close dialog'}).click();await load();assert.equal(await page.evaluate(()=>SaarthiVoice.preferences().language),'mr-IN');
  await page.evaluate(()=>SaarthiWorkspace.open('automation'));await page.locator('[name=text]').fill('Review expenses');
  await page.getByRole('button',{name:'Schedule reminder',exact:true}).click();await page.locator('#automationTasks').getByText('Review expenses',{exact:true}).waitFor();await scan('automation-light');await page.screenshot({path:'docs/evidence/automation-mobile.png'});
  await page.getByRole('button',{name:'Close dialog'}).click();await load();
  const at=await page.evaluate(async()=>{const tasks=await SaarthiAutomation.list();await SaarthiAutomation.tick(tasks[0].at+1);await SaarthiAutomation.tick(tasks[0].at+1);return tasks[0].at;});
  assert.equal(await page.locator('.reminder-banner').count(),1);await page.getByRole('button',{name:'Dismiss',exact:true}).click();
  await page.reload();await page.waitForFunction(()=>window.SaarthiAutomation);await page.evaluate(at=>SaarthiAutomation.tick(at+1),at);assert.equal(await page.locator('.reminder-banner').count(),0);
  await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');SaarthiWorkspace.open('automation');});
  await page.locator('#automationTasks').getByText(/delivered/).waitFor();await page.getByRole('button',{name:'Remove',exact:true}).click();await page.getByText('No reminders scheduled.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Close dialog'}).click();await page.evaluate(()=>SaarthiWorkspace.open('settings'));await page.locator('[name=theme]').selectOption('dark');await page.getByRole('button',{name:'Save preferences',exact:true}).click();
  for(const screen of ['device','automation']){await page.evaluate(screen=>SaarthiWorkspace.open(screen),screen);await scan(screen+'-dark');}
  await page.getByRole('button',{name:'Close dialog'}).click();await page.evaluate(()=>SaarthiWorkspace.open('settings'));await page.locator('#memorySettings').click();await scan('memory-dark');
  page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Delete memory',exact:true}).click();assert.equal(await page.evaluate(()=>SaarthiWorkspace.retrieve('astronomy').length),0);
  assert.deepEqual(errors,[]);fs.writeFileSync('docs/evidence/capabilities.json',JSON.stringify({fixture:true,physicalAndroidVerified:false,speechServiceVerified:false,scans,checks:['voice locale','mute persisted','late transcript cancellation','voice calculator routing','unsupported device result','memory consent and deletion','reminder persistence/deduplication/removal']},null,2)+'\n');
  console.log('PASS: controlled voice routing/cancellation, memory consent/delete, persistent reminder deduplication, unsupported device results and six accessibility scans.');
}finally{await browser?.close();server.kill('SIGTERM');}})().catch(error=>{console.error(error);process.exitCode=1;});
