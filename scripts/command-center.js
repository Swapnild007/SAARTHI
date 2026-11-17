
(()=>{'use strict';
const $=id=>document.getElementById(id);
const form=$('commandForm'),runButton=$('runButton'),errorBox=$('errorBox'),resultBody=$('resultBody'),resultState=$('resultState'),statusText=$('statusText');
let selectedAgent='saarthi',busy=false;
const agentNames={saarthi:'Saarthi',coding:'Build',research:'Research',create:'Create',data_analyst:'Numbers',analyze:'Understand',plan:'Plan'};
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const loadHistory=()=>{try{return JSON.parse(localStorage.getItem('saarthi.command-center.history')||'[]')}catch{return []}};
const saveHistory=items=>{try{localStorage.setItem('saarthi.command-center.history',JSON.stringify(items.slice(0,8)))}catch{}};
const showError=message=>{errorBox.textContent=message;errorBox.classList.add('show')};
const hideError=()=>{errorBox.textContent='';errorBox.classList.remove('show')};
const renderHistory=()=>{const items=loadHistory(),host=$('historyList');if(!items.length){host.innerHTML='<div class="footnote">No runs saved yet.</div>';return}host.innerHTML=items.map((item,i)=>'<div class="historyitem"><button type="button" data-history="'+i+'"><strong>'+escapeHtml(item.objective)+'</strong><small>'+escapeHtml(agentNames[item.agent]||item.agent)+' · '+escapeHtml(new Date(item.at).toLocaleString())+'</small></button><span class="restore">View</span></div>').join('');host.querySelectorAll('[data-history]').forEach(btn=>btn.addEventListener('click',()=>{const item=items[Number(btn.dataset.history)];if(item){$('objective').value=item.objective;$('context').value=item.context||'';$('constraints').value=item.constraints||'';$('success').value=item.success||'';selectAgent(item.agent);renderResult(item.reply,item)}}))};
const selectAgent=id=>{selectedAgent=agentNames[id]?id:'saarthi';document.querySelectorAll('.agent').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.agent===selectedAgent)))};
const renderResult=(reply,meta={})=>{const text=String(reply||'The runtime returned no reply text.');resultBody.innerHTML='<div class="resultmeta"><span class="chip">'+escapeHtml(agentNames[meta.agent||selectedAgent]||'Saarthi')+'</span><span class="chip">'+escapeHtml(meta.format||$('format').value)+'</span>'+(meta.provider?'<span class="chip">'+escapeHtml(meta.provider)+'</span>':'')+(meta.run_id?'<span class="chip">Run '+escapeHtml(meta.run_id)+'</span>':'')+'</div><div class="reply" id="replyText">'+escapeHtml(text)+'</div><div class="resultactions"><button class="secondary" type="button" id="copyResult">Copy result</button><button class="secondary" type="button" id="downloadResult">Export .txt</button></div>';resultState.textContent='RESULT READY';$('copyResult').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(text);$('copyResult').textContent='Copied'}catch{$('copyResult').textContent='Copy unavailable'}});$('downloadResult').addEventListener('click',()=>{const blob=new Blob([text],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='saarthi-command-result.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})};
document.querySelectorAll('.agent').forEach(btn=>btn.addEventListener('click',()=>selectAgent(btn.dataset.agent)));
$('resetButton').addEventListener('click',()=>{if(busy)return;form.reset();selectAgent('saarthi');hideError();resultState.textContent='WAITING';resultBody.innerHTML='<div class="empty"><div><div class="orb">↗</div><strong>No command processed yet</strong><p>Complete the intake form and run it. The returned result will appear here.</p></div></div>'});
$('clearHistory').addEventListener('click',()=>{saveHistory([]);renderHistory()});
form.addEventListener('submit',async event=>{event.preventDefault();if(busy)return;hideError();const objective=$('objective').value.trim();if(!objective){showError('Add an objective before running this command.');return}
const context=$('context').value.trim(),constraints=$('constraints').value.trim(),success=$('success').value.trim(),depth=$('depth').value,format=$('format').value;
const prompt=[
'You are operating inside SAARTHI Command Center.',
'Selected specialist lens: '+agentNames[selectedAgent]+' ('+selectedAgent+').',
'Processing depth: '+depth+'. Required output format: '+format+'.',
'OBJECTIVE:\n'+objective,
'INPUTS AND CONTEXT:\n'+(context||'(No additional context provided.)'),
'CONSTRAINTS:\n'+(constraints||'(No explicit constraints provided.)'),
'SUCCESS CRITERIA:\n'+(success||'(Derive practical criteria and state them.)'),
'Instructions: Process the supplied inputs rather than merely describing how to process them. Follow the selected specialist lens. Structure the response with a concise outcome, key work/findings, assumptions or missing information, constraint checks, and prioritized next actions as appropriate. Never claim external research, calculations, code execution, file creation, bookings or other actions were performed unless they were actually performed. Distinguish verified facts from assumptions. If essential information is missing, do the useful work possible and state what remains blocked.'
].join('\n\n');
busy=true;runButton.disabled=true;runButton.innerHTML='<span class="spinner"></span>Processing…';statusText.textContent='Processing command';resultState.textContent='RUNNING';resultBody.innerHTML='<div class="empty"><div><div class="orb">⟳</div><strong>SAARTHI is processing your command</strong><p>Sending the structured intake to the cloud runtime. This may take a short while.</p></div></div>';
const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),32000);
try{
const payload={message:prompt,mode:'chat',assistant:'saarthi',conversation_id:null,turn_id:crypto.randomUUID(),context:{client_time:new Date().toISOString(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Kolkata',locale:navigator.language||'en-IN',industry:null,conversation:[],attachments:[]}};
const response=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal,redirect:'error'});
if(response.status===401)throw new Error('Sign in from the SAARTHI home page first.');
if(!response.ok)throw new Error('Cloud runtime returned HTTP '+response.status+'.');
const data=await response.json();if(data?.ok===false)throw new Error(data.reply||'The cloud runtime rejected this command.');
const reply=data.reply||data.result||data.message||'The runtime completed without a reply field.';
renderResult(reply,{agent:selectedAgent,format,provider:data.provider,run_id:data.run_id});
const items=loadHistory();items.unshift({objective,context,constraints,success,agent:selectedAgent,format,reply,at:new Date().toISOString()});saveHistory(items);renderHistory();statusText.textContent='Command complete';
}catch(error){const message=error.name==='AbortError'?'The connection timed out. Check conversation history before retrying.':(error.message||'Request failed.');showError(message);resultState.textContent='NEEDS RETRY';resultBody.innerHTML='<div class="empty"><div><div class="orb">!</div><strong>Command did not complete</strong><p>'+escapeHtml(message)+'</p></div></div>';statusText.textContent='Needs attention'}
finally{clearTimeout(timer);busy=false;runButton.disabled=false;runButton.textContent='▶ Process command'}
});
renderHistory();
})();
