/* Unified workspace. Credentials remain in this closure for the current tab only. */
(() => {
  'use strict';
  const PREFS='saarthi.preferences.v1', LIBRARY='saarthi.knowledge.v1';
  let prefs={provider:'server',model:'',theme:'system',reducedMotion:false,knowledge:false,mcp:false};
  try { Object.assign(prefs,JSON.parse(localStorage.getItem(PREFS)||'{}')); } catch {}
  let key='', access='', admin='', lastFocus;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const save=()=>{localStorage.setItem(PREFS,JSON.stringify(prefs));apply();};
  function apply(){
    document.documentElement.dataset.theme=prefs.theme;
    const dark=prefs.theme==='dark'||(prefs.theme==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark-theme',dark);
    document.documentElement.classList.toggle('reduce-motion',prefs.reducedMotion);
  }
  apply();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',apply);
  const dialog=document.createElement('dialog');dialog.id='workspaceDialog';dialog.setAttribute('aria-labelledby','workspaceTitle');document.body.append(dialog);
  dialog.addEventListener('close',()=>lastFocus?.focus());
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  const nav=document.createElement('nav');nav.className='workspace-nav';nav.setAttribute('aria-label','Workspace');
  nav.innerHTML='<button data-screen="chat" aria-label="Chat">✦<span>Chat</span></button><button data-screen="history" aria-label="History">☷<span>History</span></button><a href="/appforge" aria-label="AppForge">⌘<span>Build</span></a><button data-screen="knowledge" aria-label="Knowledge">▤<span>Knowledge</span></button><button data-screen="settings" aria-label="Settings">⚙<span>Settings</span></button>';
  document.body.append(nav);
  nav.querySelector('a').onclick=e=>{e.preventDefault();open('appforge');};
  nav.addEventListener('click',e=>{const b=e.target.closest('[data-screen]');if(!b)return;if(b.dataset.screen==='chat'){dialog.close();document.getElementById('saarthiCommand')?.focus();}else if(b.dataset.screen==='history'){dialog.close();document.getElementById('historyTrigger')?.click();}else open(b.dataset.screen);});
  document.getElementById('settingsButton')?.setAttribute('aria-label','Open Settings');
  const menuLabel=document.querySelector('#settingsButton span');if(menuLabel)menuLabel.textContent='Settings';
  function announce(text){const el=dialog.querySelector('[role="status"]');if(el)el.textContent=text;}
  function shell(title,body){
    lastFocus=document.activeElement;
    dialog.innerHTML='<header class="workspace-head"><div><small>सारथी · YOUR WORKSPACE</small><h2 id="workspaceTitle">'+title+'</h2></div><button class="dialog-close" aria-label="Close dialog">×</button></header>'+body+'<p class="workspace-status" role="status" aria-live="polite"></p>';
    dialog.querySelector('.dialog-close').onclick=()=>dialog.close();
    if(!dialog.open)dialog.showModal();
  }
  function providerSelection(){return {provider:prefs.provider,model:prefs.model,api_key:key,allow_fallback:!!prefs.fallback};}
  function headers(){return access?{'X-SAARTHI-Access':access}:{};}
  async function request(path,options={}){
    const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',...headers(),...options.headers},signal:options.signal||AbortSignal.timeout(15000)});
    const value=await response.json();
    if(!response.ok)throw new Error(typeof value.detail==='string'?value.detail:'Request rejected ('+response.status+').');
    return value;
  }
  function settings(){
    shell('Settings','<form id="preferencesForm" class="workspace-form"><section><h3>AI provider</h3><label>Provider<select name="provider"><option value="server">Deployment default</option><option value="gemini">Google Gemini</option><option value="openrouter">OpenRouter</option><option value="groq">Groq</option><option value="mistral">Mistral</option><option value="openai">OpenAI</option></select></label><label>Model ID<input name="model" maxlength="160" placeholder="Exact model ID from your provider" value="'+esc(prefs.model)+'"></label><label>API key · current tab only<input name="key" type="password" autocomplete="off" value="'+esc(key)+'" placeholder="Never saved to browser storage"></label><p>Requests go through this deployment to the selected provider. Free tiers depend on the provider. Calculator, time, history and local knowledge work without a paid provider.</p><label class="check"><input name="fallback" type="checkbox" '+(prefs.fallback?'checked':'')+'> Allow fallback to the deployment provider if my provider fails</label><button type="button" id="validateProvider">Validate key and model</button></section><section><h3>Appearance</h3><label>Theme<select name="theme"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label><label class="check"><input name="motion" type="checkbox" '+(prefs.reducedMotion?'checked':'')+'> Reduce motion</label></section><section><h3>Privacy & permissions</h3><label class="check"><input name="knowledge" type="checkbox" '+(prefs.knowledge?'checked':'')+'> Include matching local knowledge excerpts in AI requests</label><label class="check"><input name="mcp" type="checkbox" '+(prefs.mcp?'checked':'')+'> Allow approved read-only remote tools during chat</label><label>Private deployment access token · current tab only<input name="access" type="password" autocomplete="off" value="'+esc(access)+'"></label><p>History and documents stay in this browser. Sending a message shares its recent context and selected excerpts with your configured provider. Clearing site data removes local work.</p><div class="workspace-actions"><button type="button" id="manageTools">Tools & MCP</button><button type="button" id="clearHistory">Clear conversations</button><button type="button" id="exportHistory">Export conversations</button><button type="button" id="forgetKey">Forget credentials</button></div></section><button class="primary" type="submit">Save preferences</button></form>');
    const form=dialog.querySelector('form');form.elements.provider.value=prefs.provider;form.elements.theme.value=prefs.theme;
    function read(){prefs.provider=form.elements.provider.value;prefs.model=form.elements.model.value.trim();prefs.fallback=form.elements.fallback.checked;prefs.theme=form.elements.theme.value;prefs.reducedMotion=form.elements.motion.checked;prefs.knowledge=form.elements.knowledge.checked;prefs.mcp=form.elements.mcp.checked;key=form.elements.key.value.trim();access=form.elements.access.value.trim();}
    form.onsubmit=e=>{e.preventDefault();read();save();announce('Preferences saved. Credentials remain in this tab only.');};
    dialog.querySelector('#validateProvider').onclick=async e=>{read();e.target.disabled=true;announce('Validating…');try{const r=await request('/api/providers/validate',{method:'POST',body:JSON.stringify(providerSelection())});announce(r.detail);}catch(error){announce(error.message);}finally{e.target.disabled=false;}};
    dialog.querySelector('#forgetKey').onclick=()=>{key='';access='';admin='';form.elements.key.value='';form.elements.access.value='';announce('Credentials forgotten.');};
    dialog.querySelector('#manageTools').onclick=tools;
    dialog.querySelector('#clearHistory').onclick=()=>{if(confirm('Delete all local conversation history? Documents and preferences will be preserved.')){localStorage.removeItem('saarthi.history.v2');Object.keys(localStorage).filter(k=>k.startsWith('saarthi.conversation.v1.')).forEach(k=>localStorage.removeItem(k));location.reload();}};
    dialog.querySelector('#exportHistory').onclick=()=>download('saarthi-conversations.json',localStorage.getItem('saarthi.history.v2')||'{}');
  }
  function download(name,data){const u=URL.createObjectURL(new Blob([data],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
  function documents(){try{const docs=JSON.parse(localStorage.getItem(LIBRARY)||'[]');return Array.isArray(docs)?docs:[];}catch{return [];}}
  function retrieve(query){
    if(!prefs.knowledge)return [];
    const terms=[...new Set(query.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu)||[])];
    return documents().flatMap(doc=>{const chunks=[];for(let i=0;i<doc.text.length;i+=1200){const content=doc.text.slice(i,i+1450);const score=terms.filter(t=>content.toLowerCase().includes(t)).length;if(score)chunks.push({title:doc.title,source:'local:'+doc.id,content,chunk_index:i/1200,score});}return chunks;}).sort((a,b)=>b.score-a.score).slice(0,4);
  }
  function knowledge(){
    const docs=documents();shell('Knowledge library','<p>Your personal documents stay in this browser. Retrieval uses lexical matching; it does not claim semantic embeddings. PDF extraction needs the backend. AI answers need a configured model.</p><label class="upload-label">Add TXT, Markdown, CSV, JSON or PDF<input id="knowledgeUpload" type="file" accept=".txt,.md,.csv,.json,.pdf"></label><label>Search local knowledge<input id="knowledgeSearch" type="search" placeholder="Search your documents"></label><div id="knowledgeResults"></div><div class="document-list">'+docs.map(d=>'<article><div><strong>'+esc(d.title)+'</strong><small>'+d.text.length.toLocaleString()+' characters · browser storage</small></div><button data-delete="'+esc(d.id)+'" aria-label="Delete '+esc(d.title)+'">Delete</button></article>').join('')+'</div>'+(docs.length?'':'<p class="empty-state">Add your first document to build personal context.</p>'));
    dialog.querySelector('#knowledgeUpload').onchange=async e=>{
      const file=e.target.files[0];if(!file)return;
      if(file.size>500000){announce('Use a document smaller than 500 KB.');return;}
      announce('Extracting document…');
      try{
        let text;
        if(/\.pdf$/i.test(file.name)){
          const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
          const result=await request('/api/knowledge/extract',{method:'POST',body:JSON.stringify({name:file.name,type:file.type,data})});text=result.text;
        }else text=await file.text();
        if(!text.trim())throw new Error('No extractable text found. Scanned PDFs need OCR, which is not available.');
        const current=documents();if(current.length>=20||text.length+current.reduce((n,d)=>n+d.text.length,0)>1500000)throw new Error('Library limit reached. Export or remove an older document first.');
        current.push({id:crypto.randomUUID(),title:file.name,text:text.slice(0,100000)});localStorage.setItem(LIBRARY,JSON.stringify(current));knowledge();announce('Document indexed locally. Enable knowledge sharing in Settings to use excerpts in chat.');
      }catch(error){announce(error.message);}
    };
    dialog.querySelector('#knowledgeSearch').oninput=e=>{const q=e.target.value.toLowerCase().trim();dialog.querySelector('#knowledgeResults').textContent=q?docs.filter(d=>(d.title+' '+d.text).toLowerCase().includes(q)).map(d=>d.title+': '+d.text.slice(Math.max(0,d.text.toLowerCase().indexOf(q)-80),Math.max(0,d.text.toLowerCase().indexOf(q)-80)+400)).join('\n\n'):'';};
    dialog.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>{if(confirm('Delete this local document?')){localStorage.setItem(LIBRARY,JSON.stringify(documents().filter(d=>d.id!==b.dataset.delete)));knowledge();announce('Document deleted.');}});
  }
  async function tools(){
    shell('Tools & MCP','<p>Calculator, time and date run without an AI provider. Remote MCP servers are configured on the backend. Chat can use only explicitly approved read-only tools when you enable permission in Settings. Sensitive tools require a separate confirmed invocation.</p><label>Knowledge / MCP admin token · current tab only<input id="adminToken" type="password" autocomplete="off" value="'+esc(admin)+'"></label><button id="discoverTools">Discover remote tools</button><pre id="toolDetails">Remote integration has not been verified on this deployment.</pre><form id="invokeTool" class="workspace-form"><label>Exact discovered tool name<input name="tool" required maxlength="64"></label><label>Arguments as JSON<textarea name="arguments" rows="4">{}</textarea></label><button type="submit">Review & invoke tool</button></form>');
    dialog.querySelector('#invokeTool').onsubmit=async e=>{e.preventDefault();admin=dialog.querySelector('#adminToken').value;try{const name=e.target.elements.tool.value.trim(),args=JSON.parse(e.target.elements.arguments.value);if(!confirm('Invoke '+name+' with these arguments?\n'+JSON.stringify(args).slice(0,800)))return;const result=await request('/api/mcp/invoke',{method:'POST',headers:{Authorization:'Bearer '+admin},body:JSON.stringify({name,arguments:args,confirmed:true})});dialog.querySelector('#toolDetails').textContent=JSON.stringify(result,null,2);announce('Remote tool returned a response. Review its output.');}catch(error){announce(error.message);}};
    dialog.querySelector('#discoverTools').onclick=async e=>{admin=dialog.querySelector('#adminToken').value;e.target.disabled=true;try{const r=await request('/api/mcp/tools',{headers:{Authorization:'Bearer '+admin}});const root=dialog.querySelector('#toolDetails');root.textContent=JSON.stringify(r,null,2);announce(r.unavailable_servers?.length?'Some servers are unavailable.':'Discovery completed. Invocation is a separate check.');}catch(error){announce(error.message);}finally{e.target.disabled=false;}};
  }
  function open(screen){if(screen==='appforge'){shell('AppForge','<iframe class="appforge-workspace" title="AppForge workspace" src="/appforge"></iframe>');dialog.classList.add('wide');}else{dialog.classList.remove('wide');if(screen==='knowledge')knowledge();else if(screen==='tools')tools();else settings();}}
  async function openProject(requirements){
    open('appforge');const frame=dialog.querySelector('iframe');
    frame.addEventListener('load',async()=>{
      const doc=frame.contentDocument,input=doc.getElementById('prompt');if(input)input.value=requirements;
      try{const ready=prefs.provider==='server'?(await request('/api/health')).provider_configured:!!(key&&prefs.model);if(ready)doc.getElementById('generate')?.click();else announce('Requirements transferred. Configure an AI provider in Settings, then generate your project.');}catch(error){announce(error.message);}
    },{once:true});
  }
  window.SaarthiWorkspace={open,openProject,providerSelection,headers,retrieve,permissions:()=>({mcp:prefs.mcp})};
  // Do not cache API responses, credentials or uploads in the service worker.
  if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
  const online=()=>{nav.dataset.offline=String(!navigator.onLine);nav.setAttribute('aria-label',navigator.onLine?'Workspace':'Workspace · offline');};
  addEventListener('online',online);addEventListener('offline',online);online();
})();
