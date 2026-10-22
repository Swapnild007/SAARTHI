const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const assert=require('node:assert/strict');
const base='http://127.0.0.1:8767';
const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','backend.app:app','--port','8767'],{stdio:'ignore'});
(async()=>{let browser;try{
 for(let n=0;n<60;n++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
 browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--disable-gpu']}: {})});
 const context=await browser.newContext();const page=await context.newPage();await page.goto(base);await page.evaluate(async()=>{await navigator.serviceWorker.ready;});await page.reload();await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
 const cdp=await context.newCDPSession(page);const manifest=await cdp.send('Page.getAppManifest');assert.equal(manifest.errors.length,0);
 const installability=await cdp.send('Page.getInstallabilityErrors');assert.deepEqual(installability.installabilityErrors,[]);
 const data=JSON.parse(manifest.data);assert.equal(data.display,'standalone');assert(data.icons.some(i=>i.sizes.includes('512')));
 const report={browser:browser.version(),manifestValid:true,serviceWorkerControlled:true,installabilityErrors:installability.installabilityErrors,installation:'Not attempted',physicalAndroid:'Not available'};
 // Only an ephemeral test browser profile is affected. Unsupported headless domains are recorded, not passed.
 const browserCdp=await browser.newBrowserCDPSession();let installed=false;const manifestId=new URL(data.id||data.start_url,base).href;
 try{await browserCdp.send('PWA.install',{manifestId,installUrlOrBundleUrl:base});installed=true;const launch=await browserCdp.send('PWA.launch',{manifestId});assert(launch.targetId);report.installation='Installed and launched in ephemeral Chromium profile';}
 catch(error){report.installation='Blocked: '+error.message;}
 finally{if(installed)await browserCdp.send('PWA.uninstall',{manifestId});}
 fs.writeFileSync('docs/evidence/pwa.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 }finally{if(browser)await browser.close();server.kill('SIGTERM');}})().catch(e=>{console.error(e);process.exitCode=1;});
