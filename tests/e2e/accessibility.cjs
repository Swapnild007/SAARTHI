const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const {default:AxeBuilder}=require(process.env.AXE_PLAYWRIGHT_PATH||'@axe-core/playwright');
const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','backend.app:app','--port','8766'],{env:{...process.env,SAARTHI_RATE_LIMIT_PER_MINUTE:'1000'},stdio:'ignore'});
(async()=>{let browser;const results=[];try{
 for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:8766/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
 browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--disable-gpu']}: {})});
 const context=await browser.newContext({viewport:{width:393,height:852},isMobile:true,hasTouch:true});const page=await context.newPage();await page.goto('http://127.0.0.1:8766');await page.waitForFunction(()=>!!window.SaarthiWorkspace);await page.evaluate(()=>{document.getElementById('sudarshanSplash')?.remove();document.body.classList.remove('splash-active');});
 async function check(screen){const r=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();results.push({screen,violations:r.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({html:n.html,target:n.target,summary:n.failureSummary}))}))});}
 await check('home-light');
 await page.locator('#settingsButton').click();await check('settings-light');
 await page.locator('[name=theme]').selectOption('dark');await page.getByRole('button',{name:'Save preferences',exact:true}).click();await check('settings-dark');await page.screenshot({path:'docs/evidence/android-dark-settings.png'});await page.getByRole('button',{name:'Close dialog'}).click();await check('home-dark');await page.locator('.workspace-nav a').click();await page.frameLocator('.appforge-workspace').locator('#prompt').waitFor();await page.frameLocator('.appforge-workspace').locator('#generate').hover();await check('appforge-dark');await page.getByRole('button',{name:'Close dialog'}).click();await page.locator('#settingsButton').click();
 await page.locator('[name=theme]').selectOption('light');await page.getByRole('button',{name:'Save preferences',exact:true}).click();await page.getByRole('button',{name:'Tools & MCP',exact:true}).click();await check('tools');await page.getByRole('button',{name:'Close dialog'}).click();
 await page.locator('.workspace-nav [data-screen=knowledge]').click();await check('knowledge');await page.getByRole('button',{name:'Close dialog'}).click();
 await page.locator('#saarthiCommand').fill('calculate 2 + 2');await page.locator('#sendCommand').click();await page.waitForFunction(()=>document.getElementById('assistantResponseBody').textContent.includes('4'));await check('chat');
 await page.locator('.workspace-nav [data-screen=history]').click();await check('history');await page.locator('#mobileHistory [data-close-history]').last().click();
 await page.locator('.workspace-nav a').click();await page.frameLocator('.appforge-workspace').locator('#prompt').waitFor();await check('appforge-embedded');
 fs.writeFileSync('docs/evidence/accessibility.json',JSON.stringify(results,null,2));
 const failures=results.flatMap(r=>r.violations.filter(v=>['critical','serious'].includes(v.impact)).map(v=>({screen:r.screen,...v})));
 console.log(JSON.stringify({screens:results.length,failures},null,2));if(failures.length)process.exitCode=1;
 }finally{if(browser)await browser.close();server.kill('SIGTERM');}})().catch(e=>{console.error(e);process.exitCode=1;});
