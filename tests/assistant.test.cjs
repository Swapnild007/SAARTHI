const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const {webcrypto}=require('node:crypto');
function environment(native=false,origin=''){
  const storage=new Map(),events=[],requests=[];
  const c={URL,Request,Blob,btoa:value=>Buffer.from(value,'binary').toString('base64'),crypto:webcrypto,Date,JSON,console,location:{href:'https://localhost/',origin:'https://localhost'},
    navigator:{locks:{request:async(name,options,callback)=>callback({name})}},
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
    setInterval:()=>0,addEventListener:()=>{},dispatchEvent:e=>events.push(e),CustomEvent:class{constructor(type,options){this.type=type;this.detail=options.detail;}},
    fetch:async(...args)=>{requests.push(args);return {ok:true};},SaarthiNativeConfig:{apiOrigin:origin},
    Capacitor:{isNativePlatform:()=>native,registerPlugin:()=>({execute:async()=>({ok:true,message:'fixture'})})}};
  c.window=c;c.parent=c;vm.createContext(c);
  const load=name=>vm.runInContext(fs.readFileSync('scripts/'+name,'utf8'),c);
  load('native-runtime.js');load('automation.js');return {c,storage,events,requests};
}
test('browser device actions report unsupported without calling a backend',async()=>{
  const {c,requests}=environment();const result=await c.SaarthiDevice.execute('launch',{app:'whatsapp'});
  assert.equal(result.ok,false);assert.equal(result.code,'UNSUPPORTED');assert.equal(requests.length,0);
});
test('packaged Android routes only own API paths to configured HTTPS origin',async()=>{
  const {c,requests}=environment(true,'https://assistant.example');
  await c.fetch('/api/health');await c.fetch('/styles/app.css');await c.fetch('https://other.example/api/x');
  assert.equal(requests[0][0],'https://assistant.example/api/health');assert.equal(requests[1][0],'/styles/app.css');assert.equal(requests[2][0],'https://other.example/api/x');
});
test('unconfigured Android backend rejects cloud requests instead of using an implicit deployment',async()=>{
  const {c,requests}=environment(true);await assert.rejects(c.fetch('/api/command'),/not configured/);assert.equal(requests.length,0);
});
test('failed native operation cannot become a successful structured result',async()=>{
  const {c}=environment(true);c.Capacitor.registerPlugin=()=>({execute:async()=>({ok:false,code:'PERMISSION_DENIED',message:'Denied'})});
  const result=await c.SaarthiDevice.execute('launch',{app:'whatsapp'});assert.equal(result.ok,false);assert.equal(result.action,'launch');assert.equal(result.code,'PERMISSION_DENIED');
});
test('native bridge works with Android generated proxies without a core JS bundle',async()=>{
  const {c}=environment(true);delete c.Capacitor.registerPlugin;
  c.Capacitor.Plugins={SaarthiDevice:{execute:async()=>({ok:true,message:'Opened'})}};
  const result=await c.SaarthiDevice.execute('launch',{app:'maps'});assert.equal(result.ok,true);assert.equal(result.data.message,'Opened');
});
test('native export preserves bytes and reports a cancelled document selection',async()=>{
  const {c}=environment(true);let received;
  c.Capacitor.registerPlugin=()=>({execute:async args=>{received=args;return {ok:false,code:'CANCELLED',message:'Export cancelled.'};}});
  const source=new Blob(['मराठी export'],{type:'application/json'});
  await assert.rejects(c.SaarthiDevice.saveBlob(source,'notes.json'),/cancelled/);
  assert.equal(received.action,'saveDocument');assert.equal(received.mime,'application/json');assert.equal(Buffer.from(received.data,'base64').toString(),'मराठी export');
});
test('oversized native export never invokes a device operation',async()=>{
  const {c}=environment(true);c.Capacitor.registerPlugin=()=>{throw Error('Must not invoke');};
  await assert.rejects(c.SaarthiDevice.saveBlob(new Blob(['x'.repeat(1000001)]),'large.zip'),/1 MB/);
});
test('reminder persisted before dispatch, reload and duplicate ticks do not redeliver',async()=>{
  const {c,events,storage}=environment();
  const task=await c.SaarthiAutomation.create({text:'Read a report',at:Date.now()+10000});
  await c.SaarthiAutomation.tick(task.at+1);await c.SaarthiAutomation.tick(task.at+1);
  assert.equal(events.length,1);assert.equal(JSON.parse(storage.get('saarthi.tasks.v1'))[0].status,'delivered');
  vm.runInContext(fs.readFileSync('scripts/automation.js','utf8'),c);await c.SaarthiAutomation.tick(task.at+100);assert.equal(events.length,1);
});
test('daily recovery skips missed occurrences and preserves a future next occurrence',async()=>{
  const {c,events}=environment();const task=await c.SaarthiAutomation.create({text:'Daily briefing',at:Date.now()+10000,repeat:'daily'});
  const now=task.at+4*86400000+1000;await c.SaarthiAutomation.tick(now);await c.SaarthiAutomation.tick(now);
  assert.equal(events.length,1);const tasks=await c.SaarthiAutomation.list();assert.equal(tasks[0].status,'scheduled');assert(tasks[0].at>now);
});
test('cancelled reminders do not execute and invalid schedules do not persist',async()=>{
  const {c,events}=environment();
  for(const input of [{text:'x',at:0},{text:'',at:Date.now()+1000},{text:'x',at:Date.now()+1000,repeat:'minute'},{text:'x',at:Infinity}])await assert.rejects(c.SaarthiAutomation.create(input));
  const task=await c.SaarthiAutomation.create({text:'Cancel me',at:Date.now()+1000});await c.SaarthiAutomation.cancel(task.id);await c.SaarthiAutomation.tick(task.at+1);assert.equal(events.length,0);
});
test('natural-language reminder produces a review draft rather than silently scheduling',async()=>{
  const {c}=environment();assert.equal(c.SaarthiAutomation.parse('remind me in 5 minutes to Review expenses').text,'Review expenses');assert.equal((await c.SaarthiAutomation.list()).length,0);assert.equal(c.SaarthiAutomation.parse('research reminders'),null);
});
