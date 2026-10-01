const SaarthiApp = (() => {
  const $ = (s, root = document) => root.querySelector(s);
  const activity = $('#activityStream');
  const command = $('#saarthiCommand');
  const status = $('#presenceText');
  const liveDay = $('#liveDay');
  const topClock = $('#topClock');
  const greeting = $('#greeting'), coreStatus = $('.core-status');
  const responseCard = $('#assistantResponse'), responseBody = $('#assistantResponseBody'), responseMeta = $('#assistantResponseMeta');
  const runs = [];
  const usageTotals = {
    requests: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    reasoning_tokens: 0,
    cached_tokens: 0,
    total_tokens: 0,
    cost: 0
  };
  const HISTORY_KEY='saarthi.history.v2';
  const MAX_CONTEXT_MESSAGES=20;
  const MAX_THREADS_PER_ASSISTANT=100;
  const conversations=Object.create(null);
  const currentThreads=Object.create(null);
  const historyState={assistants:Object.create(null)};

  const uid=()=>Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8);
  const assistantInfo=id=>ASSISTANTS.find(x=>x.id===id)||ASSISTANTS[0];
  const titleFromMessage=value=>{
    const clean=String(value||'').replace(/\\s+/g,' ').trim();
    if(!clean)return 'New conversation';
    return clean.length>48?clean.slice(0,47).trimEnd()+'…':clean;
  };
  const loadHistory=()=>{
    try{
      const parsed=JSON.parse(localStorage.getItem(HISTORY_KEY)||'{}');
      historyState.assistants=parsed&&parsed.assistants&&typeof parsed.assistants==='object'?parsed.assistants:Object.create(null);
    }catch{historyState.assistants=Object.create(null);}
    return historyState.assistants;
  };
  const saveHistory=()=>{
    try{localStorage.setItem(HISTORY_KEY,JSON.stringify(historyState));}catch{}
  };
  const ensureAssistantHistory=assistant=>{
    const id=assistantInfo(assistant).id;
    if(!Array.isArray(historyState.assistants[id]))historyState.assistants[id]=[];
    historyState.assistants[id]=historyState.assistants[id].filter(t=>t&&t.id&&Array.isArray(t.messages)).slice(-MAX_THREADS_PER_ASSISTANT);
    return historyState.assistants[id];
  };
  const migrateLegacyConversation=assistant=>{
    const list=ensureAssistantHistory(assistant);
    if(list.length)return list;
    try{
      const legacy=JSON.parse(localStorage.getItem('saarthi.conversation.v1.'+assistant)||'[]');
      if(Array.isArray(legacy)&&legacy.length){
        const first=legacy.find(m=>m.role==='user');
        const thread={id:uid(),title:titleFromMessage(first?.content),createdAt:first?.at||new Date().toISOString(),updatedAt:new Date().toISOString(),messages:legacy.slice(-MAX_CONTEXT_MESSAGES)};
        list.push(thread);saveHistory();return list;
      }
    }catch{}
    return list;
  };
  const ensureThread=(assistant=currentAssistant,create=true)=>{
    const list=migrateLegacyConversation(assistant);
    let thread=list.find(t=>t.id===currentThreads[assistant]);
    if(!thread&&list.length){thread=list[list.length-1];currentThreads[assistant]=thread.id;}
    if(!thread&&create){
      thread={id:uid(),title:'New conversation',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),messages:[]};
      list.push(thread);currentThreads[assistant]=thread.id;saveHistory();
    }
    return thread;
  };
  const loadConversation=assistant=>{
    const thread=ensureThread(assistant,false);
    conversations[assistant]=thread?thread.messages:[];
    return conversations[assistant];
  };
  const saveConversation=assistant=>{
    const thread=ensureThread(assistant,false);
    if(!thread)return;
    thread.messages=(conversations[assistant]||[]).slice(-MAX_CONTEXT_MESSAGES);
    const firstUser=thread.messages.find(m=>m.role==='user');
    if(firstUser&&(!thread.title||thread.title==='New conversation'))thread.title=titleFromMessage(firstUser.content);
    thread.updatedAt=new Date().toISOString();
    const list=ensureAssistantHistory(assistant);
    const index=list.findIndex(t=>t.id===thread.id);
    if(index>=0)list.splice(index,1);
    list.push(thread);
    saveHistory();
    renderHistory();
  };
  const currentConversation=()=>loadConversation(currentAssistant);

  const MENUS = Object.freeze({
    assistants:{label:'Assistants',capabilities:['saarthi','coding','research','create','analyze','plan']},
    control:{label:'Control',capabilities:['ai','usage','memory','voice','tools','connections','security','notifications','appearance','privacy']}
  });
  const ASSISTANTS = Object.freeze([
    {
      id:'saarthi',icon:'✦',name:'Saarthi',description:'General personal intelligence',
      environment:'Saarthi environment',headline:'Think clearly.<br><em>Move deliberately.</em>',
      descriptionText:'Bring a problem, plan, question, or decision. Saarthi keeps the context together and helps you work it through.',
      placeholder:'Give Saarthi a direction…',
      quick:[
        ['✦','Decision','Help me make a decision.'],
        ['◷','Plan','Plan my day around what matters most.'],
        ['◌','Learn','Teach me this from first principles.'],
        ['◈','Understand','Break this situation into facts and assumptions.']
      ]
    },
    {
      id:'coding',icon:'⌘',name:'AI Coding',description:'Build, debug, explain and refactor code',
      environment:'Coding environment',headline:'Build precisely.<br><em>Ship with confidence.</em>',
      descriptionText:'Write, debug, review and improve software. Bring code, an error, or an idea and turn it into a runnable solution.',
      placeholder:'Describe what you want to build…',
      quick:[
        ['⌘','Build','Build a complete solution for me.'],
        ['◈','Debug','Help me debug this code.'],
        ['◎','Review','Review this code for issues.'],
        ['◇','Explain','Explain this code simply.']
      ]
    },
    {
      id:'research',icon:'◎',name:'Research',description:'Research, compare and synthesize',
      environment:'Research environment',headline:'Go deeper.<br><em>Know what matters.</em>',
      descriptionText:'Structure a question, compare evidence, expose uncertainty and turn information into a clear synthesis.',
      placeholder:'What should I investigate…',
      quick:[
        ['◎','Investigate','Investigate this topic.'],
        ['◈','Compare','Compare these options objectively.'],
        ['✦','Explain','Explain the evidence behind this.'],
        ['◇','Synthesize','Synthesize what matters most.']
      ]
    },
    {
      id:'create',icon:'◇',name:'Create',description:'Writing, ideas and creative generation',
      environment:'Create environment',headline:'Make it distinct.<br><em>Give ideas a shape.</em>',
      descriptionText:'Turn rough ideas into polished writing, concepts, prompts, structures and creative directions.',
      placeholder:'What should we create…',
      quick:[
        ['◇','Draft','Draft this from my idea.'],
        ['✦','Ideate','Give me strong ideas for this.'],
        ['◈','Rewrite','Rewrite this with more impact.'],
        ['◎','Refine','Refine this into a polished version.']
      ]
    },
    {
      id:'analyze',icon:'◈',name:'Analyze',description:'Data, documents and visual analysis',
      environment:'Analysis environment',headline:'See the signal.<br><em>Separate fact from noise.</em>',
      descriptionText:'Break complex material into evidence, patterns, assumptions, risks and useful conclusions.',
      placeholder:'What should I analyze…',
      quick:[
        ['◈','Analyze','Analyze this carefully.'],
        ['◎','Find patterns','Find the important patterns.'],
        ['✦','Explain','Explain what the data means.'],
        ['◇','Challenge','Challenge the assumptions.']
      ]
    },
    {
      id:'plan',icon:'◷',name:'Plan',description:'Planning, decisions and automation',
      environment:'Planning environment',headline:'Turn intent into action.<br><em>Know the next move.</em>',
      descriptionText:'Convert goals into practical steps, dependencies, checkpoints and decisions without losing the bigger picture.',
      placeholder:'What are we trying to accomplish…',
      quick:[
        ['◷','Plan','Build a practical plan.'],
        ['✦','Prioritize','Help me prioritize this.'],
        ['◈','Map','Map the steps and dependencies.'],
        ['◇','Decide','Help me choose the next move.']
      ]
    }
  ]);
  const CONTROLS = Object.freeze([
    {id:'ai',icon:'✦',name:'AI & Models',description:'Choose the intelligence behind Saarthi'},
    {id:'usage',icon:'◉',name:'AI Usage',description:'Tokens, requests and estimated cost'},
    {id:'memory',icon:'◌',name:'Memory',description:'Manage what Saarthi remembers'},
    {id:'voice',icon:'⌁',name:'Voice',description:'Voice input and speech settings'},
    {id:'tools',icon:'⚙',name:'Tools',description:'Capabilities available to assistants'},
    {id:'connections',icon:'↗',name:'Connections',description:'Connected services and APIs'},
    {id:'security',icon:'◈',name:'Security',description:'Sessions, permissions and API safety'},
    {id:'notifications',icon:'•',name:'Notifications',description:'Reminders and proactive alerts'},
    {id:'appearance',icon:'○',name:'Appearance',description:'Visual and interaction preferences'},
    {id:'privacy',icon:'◇',name:'Privacy',description:'Data and privacy controls'}
  ]);
  let currentAssistant='saarthi';
  const COMMANDS = Object.freeze({
    '/help':'help','/research':'research','/search':'search','/analyze':'analyze','/plan':'plan',
    '/remember':'remember','/recall':'recall','/tasks':'tasks','/task':'task','/remind':'remind',
    '/workflow':'workflow','/workflows':'workflows','/briefing':'briefing','/system':'system',
    '/settings':'settings','/voice':'voice'
  });
  let API_BASE='';
  const loadRuntimeConfig=async()=>{
    try{
      const response=await fetch('./config/runtime.json?ts='+Date.now(),{cache:'no-store'});
      if(response.ok){
        const config=await response.json();
        API_BASE=String(config.api_base_url||'').replace(/\/$/,'');
      }
    }catch{}
  };
  const ensureApiBase=async()=>{
    if(!API_BASE)await loadRuntimeConfig();
    if(!API_BASE)API_BASE='https://saarthi-nine-chi.vercel.app';
    return API_BASE;
  };
  const apiUrl=path=>API_BASE+(path.startsWith('/')?path:'/'+path);

  const weatherDescription=code=>({
    0:'Clear sky',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Rime fog',
    51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',56:'Freezing drizzle',57:'Heavy freezing drizzle',
    61:'Light rain',63:'Rain',65:'Heavy rain',66:'Freezing rain',67:'Heavy freezing rain',
    71:'Light snow',73:'Snow',75:'Heavy snow',77:'Snow grains',80:'Light showers',81:'Showers',
    82:'Heavy showers',85:'Snow showers',86:'Heavy snow showers',95:'Thunderstorm',
    96:'Thunderstorm with hail',99:'Thunderstorm with heavy hail'
  }[code]||'Weather available');

  const weatherIcon=code=>{
    if(code===0)return '☀︎'; if([1,2].includes(code))return '⛅'; if([3,45,48].includes(code))return '☁︎';
    if([51,53,55,56,57].includes(code))return '☂︎'; if([61,63,65,66,67,80,81,82].includes(code))return '☔';
    if([71,73,75,77,85,86].includes(code))return '❄︎'; if([95,96,99].includes(code))return '⚡'; return '☁︎';
  };

  const updateClock=()=>{
    const now=new Date();
    if(topClock)topClock.textContent=new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(now);
    if(liveDay)liveDay.textContent=new Intl.DateTimeFormat('en-IN',{weekday:'long'}).format(now)+' · local time';
    if(greeting){const h=Number(new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',hour:'2-digit',hour12:false}).format(now));const p=h>=5&&h<12?'morning':h>=12&&h<17?'afternoon':h>=17&&h<21?'evening':'night';greeting.textContent='Good '+p+', Swapnil';}
  };

  const addActivity=(title,detail)=>{
    if(!activity)return;const item=document.createElement('div');item.className='signal';
    item.innerHTML='<i></i><div><b></b><span></span></div><time>now</time>';
    item.querySelector('b').textContent=title;item.querySelector('span').textContent=detail;activity.prepend(item);
  };
  const setStatus=value=>{if(status)status.textContent=value;};
  const setCoreState=(value)=>{
    if(coreStatus)coreStatus.innerHTML='<b>सारथी CORE</b> · '+value;
  };

  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const inlineMarkdown=value=>escapeHtml(value)
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/__([^_]+)__/g,'<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g,'<em>$1</em>')
    .replace(/_([^_]+)_/g,'<em>$1</em>');

  const renderMarkdown=markdown=>{
    const lines=String(markdown||'').replace(/\r/g,'').split('\n');
    const out=[];let inCode=false,code=[];let listType=null,tableMode=false;
    const closeList=()=>{if(listType){out.push('</'+listType+'>');listType=null;}};
    const closeTable=()=>{if(tableMode){out.push('</tbody></table>');tableMode=false;}};
    for(let i=0;i<lines.length;i++){
      const raw=lines[i], line=raw.trim();
      if(line.startsWith('```')){closeList();closeTable();if(inCode){out.push('<pre><code>'+escapeHtml(code.join('\n'))+'</code></pre>');code=[];inCode=false;}else inCode=true;continue;}
      if(inCode){code.push(raw);continue;}
      if(!line){closeList();closeTable();continue;}
      if(/^\|.*\|$/.test(line)){
        const cells=line.slice(1,-1).split('|').map(x=>x.trim());
        if(cells.every(x=>/^:?-{3,}:?$/.test(x))){continue;}
        closeList();
        if(!tableMode){tableMode=true;out.push('<table><thead><tr>'+cells.map(x=>'<th>'+inlineMarkdown(x)+'</th>').join('')+'</tr></thead><tbody>');}
        else out.push('<tr>'+cells.map(x=>'<td>'+inlineMarkdown(x)+'</td>').join('')+'</tr>');
        continue;
      }
      closeTable();
      const heading=line.match(/^(#{1,3})\s+(.+)$/);
      if(heading){closeList();const level=heading[1].length;out.push('<h'+level+'>'+inlineMarkdown(heading[2])+'</h'+level+'>');continue;}
      const bullet=line.match(/^[-*•]\s+(.+)$/);
      if(bullet){if(listType!=='ul'){closeList();listType='ul';out.push('<ul>');}out.push('<li>'+inlineMarkdown(bullet[1])+'</li>');continue;}
      const numbered=line.match(/^\d+[.)]\s+(.+)$/);
      if(numbered){if(listType!=='ol'){closeList();listType='ol';out.push('<ol>');}out.push('<li>'+inlineMarkdown(numbered[1])+'</li>');continue;}
      if(/^>\s?/.test(line)){closeList();out.push('<blockquote>'+inlineMarkdown(line.replace(/^>\s?/,''))+'</blockquote>');continue;}
      if(/^---+$/.test(line)){closeList();out.push('<hr>');continue;}
      closeList();out.push('<p>'+inlineMarkdown(line)+'</p>');
    }
    if(inCode)out.push('<pre><code>'+escapeHtml(code.join('\n'))+'</code></pre>');
    closeList();closeTable();
    return out.join('');
  };

  const renderConversation=()=>{
    if(!responseCard||!responseBody)return;
    const item=ASSISTANTS.find(x=>x.id===currentAssistant)||ASSISTANTS[0];
    const messages=currentConversation();
    document.body.classList.toggle('chat-active',messages.length>0);
    if(!messages.length){responseCard.hidden=true;return;}
    responseBody.innerHTML=messages.map(message=>{
      const role=message.role==='user'?'You':item.name;
      const klass=message.role==='user'?'conversation-message user':'conversation-message assistant';
      return '<div class="'+klass+'"><div class="conversation-role">'+escapeHtml(role)+'</div><div class="conversation-content">'+renderMarkdown(message.content)+'</div></div>';
    }).join('');
    const eyebrow=$('#assistantResponseEyebrow');
    const title=$('#assistantResponseTitle');
    if(eyebrow) eyebrow.textContent=item.name.toUpperCase()+' • CONVERSATION';
    if(title) title.textContent='Conversation';
    if(responseMeta)responseMeta.textContent=item.name.toUpperCase()+' · ISOLATED CONVERSATION';
    responseCard.dataset.assistant=item.id;
    responseCard.hidden=false;
    requestAnimationFrame(()=>{
      responseBody?.lastElementChild?.scrollIntoView({behavior:'smooth',block:'nearest'});
      $('#conversationComposer')?.scrollIntoView({behavior:'smooth',block:'nearest'});
    });
  };
  const appendConversation=(role,content)=>{
    if(!content)return;
    const thread=ensureThread(currentAssistant,true);
    const messages=thread.messages||[];
    messages.push({role,content:String(content),at:new Date().toISOString()});
    conversations[currentAssistant]=messages.slice(-MAX_CONTEXT_MESSAGES);
    if(role==='user'&&(!thread.title||thread.title==='New conversation'))thread.title=titleFromMessage(content);
    thread.updatedAt=new Date().toISOString();
    saveConversation(currentAssistant);
    renderConversation();
  };
  const showResponse=(reply,result)=>{
    appendConversation('assistant',reply||'Command completed.');
    responseCard?.scrollIntoView({behavior:'smooth',block:'nearest'});
  };

  const speak=text=>{
    if(!window.speechSynthesis||!text)return;window.speechSynthesis.cancel();
    const utterance=new SpeechSynthesisUtterance(text.replace(/[#*_]/g,''));
    utterance.lang='en-IN';utterance.rate=.98;utterance.pitch=.92;window.speechSynthesis.speak(utterance);
  };

  const closePickers=()=>{['menuPicker','assistantPicker','controlPicker'].forEach(id=>{const el=$('#'+id);if(el)el.hidden=true;});};
  const renderUsagePanel=async()=>{
    const target=$('#menuPicker');if(!target)return;
    closePickers();
    target.innerHTML='<div class="picker-panel usage-panel"><div class="picker-head"><div><div class="eyebrow">SAARTHI</div><h3>AI Usage</h3><small class="usage-live-state">Loading…</small></div><button class="picker-close" aria-label="Close">×</button></div><div class="usage-summary"><div class="usage-card"><small>SESSION REQUESTS</small><strong>'+usageTotals.requests+'</strong></div><div class="usage-card"><small>SESSION TOKENS</small><strong>'+usageTotals.total_tokens.toLocaleString('en-IN')+'</strong></div><div class="usage-card"><small>SESSION COST</small><strong>$'+Number(usageTotals.cost||0).toFixed(6)+'</strong></div></div><div class="usage-details" id="liveUsageDetails"><div><span>OpenRouter</span><b>Loading…</b></div></div><div class="usage-models"><div class="usage-section-title">Models · last 30 days</div><div class="usage-model-list"><div class="usage-empty">Loading…</div></div></div><div class="usage-foot">Usage is loaded through the Saarthi server.</div></div>';
    target.hidden=false;
    target.querySelector('.picker-close')?.addEventListener('click',closePickers);
    try{
      const response=await fetch(apiUrl('/api/usage'));
      const data=await response.json();
      const key=data?.key?.data||data?.key||{};
      const details=target.querySelector('#liveUsageDetails');
      if(details) details.innerHTML='<div><span>Current usage</span><b>$'+Number(key.usage||0).toFixed(6)+'</b></div><div><span>Today</span><b>$'+Number(key.usage_daily||0).toFixed(6)+'</b></div><div><span>This week</span><b>$'+Number(key.usage_weekly||0).toFixed(6)+'</b></div><div><span>This month</span><b>$'+Number(key.usage_monthly||0).toFixed(6)+'</b></div><div><span>Limit remaining</span><b>'+((key.limit_remaining==null)?'—':'$'+Number(key.limit_remaining).toFixed(6))+'</b></div>';
      const models=data?.analytics_by_model_30d?.data||data?.analytics_by_model_30d?.results||[];
      const modelBox=target.querySelector('.usage-model-list');
      if(modelBox) modelBox.innerHTML=Array.isArray(models)&&models.length?models.slice(0,6).map(row=>'<div class="usage-model-row"><span>'+String(row.model||'Unknown')+'</span><b>$'+Number(row.total_usage||0).toFixed(6)+'</b></div>').join(''):'<div class="usage-empty">'+(data?.analytics_configured?'No model data returned.':'30-day model analytics is not connected yet.')+'</div>';
      const state=target.querySelector('.usage-live-state');
      if(state) state.textContent=data?.analytics_configured?'LIVE · OPENROUTER ANALYTICS':(data?.key_error?'OPENROUTER KEY ERROR':'LIVE · OPENROUTER KEY');
      if(data?.key_error){const details=target.querySelector('#liveUsageDetails');if(details)details.insertAdjacentHTML('beforeend','<div><span>Status</span><b>'+String(data.key_error).slice(0,140)+'</b></div>');}
    }catch(error){
      const state=target.querySelector('.usage-live-state');
      if(state) state.textContent='Usage unavailable';
    }
  };

  const startNewConversation=()=>{
    const id=currentAssistant;
    const list=ensureAssistantHistory(id);
    const thread={id:uid(),title:'New conversation',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),messages:[]};
    list.push(thread);
    currentThreads[id]=thread.id;
    conversations[id]=[];
    saveHistory();
    document.body.classList.remove('chat-active');
    renderConversation();
    renderHistory();
    closePickers();
    command?.focus();
    addActivity('New conversation started',id);
  };

  const renderHistory=()=>{
    const list=ensureAssistantHistory(currentAssistant);
    const active=currentThreads[currentAssistant];
    const rows=list.slice().sort((a,b)=>new Date(b.updatedAt)-new Date(a.updatedAt)).map(t=>
      '<button class="history-thread '+(t.id===active?'active':'')+'" data-thread-id="'+escapeHtml(t.id)+'"><span class="history-thread-icon">'+escapeHtml(assistantInfo(currentAssistant).icon)+'</span><span><b>'+escapeHtml(t.title||'New conversation')+'</b><small>'+new Date(t.updatedAt).toLocaleDateString('en-IN',{day:'numeric',month:'short'})+'</small></span></button>'
    ).join('');
    const markup='<div class="history-head"><div><small>CONVERSATIONS</small><b>'+escapeHtml(assistantInfo(currentAssistant).name)+'</b></div><button type="button" class="history-new" aria-label="New conversation">＋</button></div><div class="history-search"><span>⌕</span><input type="search" placeholder="Search conversations…" aria-label="Search conversations"></div><div class="history-list">'+(rows||'<div class="history-empty">No conversations yet.</div>')+'</div>';
    const bind=box=>{
      box.innerHTML=markup;
      box.querySelector('.history-new')?.addEventListener('click',startNewConversation);
      box.querySelector('.history-search input')?.addEventListener('input',e=>{
        const q=e.target.value.trim().toLowerCase();
        box.querySelectorAll('.history-thread').forEach(row=>{row.hidden=!row.textContent.toLowerCase().includes(q);});
      });
      box.querySelectorAll('.history-thread').forEach(row=>row.addEventListener('click',()=>openConversation(row.dataset.threadId)));
    };
    const nav=document.querySelector('.sidebar .nav');
    if(nav){
      let box=document.querySelector('.assistant-history');
      if(!box){box=document.createElement('section');box.className='assistant-history';nav.insertAdjacentElement('afterend',box);}
      bind(box);
    }
    let mobile=document.querySelector('#mobileHistory');
    if(!mobile){
      mobile=document.createElement('div');mobile.id='mobileHistory';mobile.className='mobile-history';mobile.hidden=true;document.body.appendChild(mobile);
    }
    mobile.innerHTML='<div class="mobile-history-backdrop" data-close-history="true"></div><aside class="mobile-history-panel"><div class="mobile-history-top"><b>Conversation history</b><button type="button" data-close-history="true">×</button></div><div class="mobile-history-agent">'+escapeHtml(assistantInfo(currentAssistant).name)+'</div><div class="mobile-history-content"></div></aside>';
    const content=mobile.querySelector('.mobile-history-content');bind(content);
    content.querySelector('.history-head')?.remove();
    mobile.querySelectorAll('[data-close-history]').forEach(x=>x.addEventListener('click',()=>{mobile.hidden=true;}));
  };
  const openHistory=()=>{renderHistory();const mobile=document.querySelector('#mobileHistory');if(mobile)mobile.hidden=false;};

  const openConversation=threadId=>{
    const list=ensureAssistantHistory(currentAssistant);
    const thread=list.find(t=>t.id===threadId);
    if(!thread)return;
    currentThreads[currentAssistant]=thread.id;
    conversations[currentAssistant]=thread.messages.slice(-MAX_CONTEXT_MESSAGES);
    saveHistory();
    closePickers();
    renderConversation();
    renderHistory();
    window.scrollTo({top:0,behavior:'smooth'});
    command?.focus();
  };

  const renderMenuRoot=()=>{
    const target=$('#menuPicker');if(!target)return;
    target.innerHTML='<div class="picker-panel menu-panel"><div class="picker-head"><div><div class="eyebrow">SAARTHI</div><h3>Menu</h3></div><button class="picker-close" aria-label="Close">×</button></div><div class="menu-options"><button class="menu-option" data-history-root="true"><span class="menu-option-icon">☷</span><span><b>Conversation history</b><small>Open '+(ASSISTANTS.find(x=>x.id===currentAssistant)?.name||'Saarthi')+'\'s conversations.</small></span><span class="menu-option-arrow">›</span></button><button class="menu-option menu-option-new" data-new-conversation="true"><span class="menu-option-icon">＋</span><span><b>New conversation</b><small>Start a clean conversation with '+(ASSISTANTS.find(x=>x.id===currentAssistant)?.name||'Saarthi')+'.</small></span><span class="menu-option-arrow">›</span></button><button class="menu-option" data-root-menu="assistants"><span class="menu-option-icon">✦</span><span><b>Assistants</b><small>Switch between Saarthi, Coding, Research, Create, Analyze and Plan.</small></span><span class="menu-option-arrow">›</span></button><button class="menu-option menu-option-featured" data-root-usage="true"><span class="menu-option-icon">◉</span><span><b>AI Usage</b><small>Live session tokens, requests and estimated OpenRouter cost.</small></span><span class="menu-option-arrow">›</span></button><button class="menu-option" data-root-menu="control"><span class="menu-option-icon">⌘</span><span><b>Control</b><small>Memory, voice, tools, connections, security and privacy.</small></span><span class="menu-option-arrow">›</span></button></div></div>';
    closePickers();
    target.hidden=false;
    target.querySelector('.picker-close')?.addEventListener('click',closePickers);
    target.querySelectorAll('[data-root-menu]').forEach(btn=>btn.addEventListener('click',()=>selectMenu(btn.dataset.rootMenu)));
    target.querySelector('[data-new-conversation]')?.addEventListener('click',startNewConversation);
    target.querySelector('[data-history-root]')?.addEventListener('click',()=>{closePickers();openHistory();});
    target.querySelector('[data-root-usage]')?.addEventListener('click',()=>{
      addActivity('AI Usage opened','Session telemetry');
      renderUsagePanel();
    });
  };
  const renderPicker=(type)=>{
    const target=$(type==='assistants'?'#assistantPicker':'#controlPicker');if(!target)return;
    const items=type==='assistants'?ASSISTANTS:CONTROLS;
    target.innerHTML='<div class="picker-panel"><div class="picker-head"><div><div class="eyebrow">SAARTHI</div><h3>'+(type==='assistants'?'Choose intelligence':'Control Saarthi')+'</h3></div><button class="picker-close" aria-label="Close">×</button></div><div class="picker-grid">'+items.map(item=>'<button class="picker-item" data-picker-id="'+item.id+'"><span class="picker-icon">'+item.icon+'</span><span><b>'+item.name+'</b><small>'+item.description+'</small></span></button>').join('')+'</div></div>';
    closePickers();
    target.hidden=false;
    target.querySelector('.picker-close')?.addEventListener('click',closePickers);
    target.querySelectorAll('.picker-item').forEach(btn=>btn.addEventListener('click',()=>{
      const id=btn.dataset.pickerId;
      if(type==='assistants'){
        selectAssistant(id);
        closePickers();
      }else{
        addActivity('Control opened',id);
        closePickers();
        if(id==='usage') renderUsagePanel();
        else showResponse('### '+(CONTROLS.find(x=>x.id===id)?.name||'Control')+'\\n\\nThis control is ready to become a dedicated Saarthi surface without adding another primary navigation page.',{intent:{name:id},provider:'Saarthi'});
      }
    }));
  };

  const formatUsage=()=>{
    const money=Number(usageTotals.cost||0).toFixed(6);
    return [
      '### AI Usage','',
      '**Session requests:** '+usageTotals.requests.toLocaleString('en-IN'),
      '**Prompt tokens:** '+usageTotals.prompt_tokens.toLocaleString('en-IN'),
      '**Completion tokens:** '+usageTotals.completion_tokens.toLocaleString('en-IN'),
      '**Reasoning tokens:** '+usageTotals.reasoning_tokens.toLocaleString('en-IN'),
      '**Cached tokens:** '+usageTotals.cached_tokens.toLocaleString('en-IN'),
      '**Total tokens:** '+usageTotals.total_tokens.toLocaleString('en-IN'),
      '**Estimated cost:** $'+money,
      '',
      '**Provider:** OpenRouter',
      '**API key:** masked',
      '',
      usageTotals.requests ? 'Usage is measured from OpenRouter runtime responses received in this browser session.' : 'No AI requests have been recorded in this browser session yet.'
    ].join('\n');
  };
  const recordUsage=usage=>{
    if(!usage||typeof usage!=='object')return;
    usageTotals.requests+=1;
    usageTotals.prompt_tokens+=Number(usage.prompt_tokens||0);
    usageTotals.completion_tokens+=Number(usage.completion_tokens||0);
    usageTotals.reasoning_tokens+=Number(usage.reasoning_tokens||0);
    usageTotals.cached_tokens+=Number(usage.cached_tokens||0);
    usageTotals.total_tokens+=Number(usage.total_tokens||0);
    usageTotals.cost+=Number(usage.cost||0);
  };

  const selectMenu=menuId=>{
    const id=MENUS[menuId]?menuId:'assistants';
    closePickers();
    renderPicker(id);
    document.querySelectorAll('[data-menu]').forEach(button=>button.classList.toggle('active',button.dataset.menu===id));
    addActivity('Menu selected',MENUS[id].label);
    return MENUS[id];
  };
  const applyAssistantEnvironment = item => {
    if(!item) return;
    document.documentElement.dataset.assistant = item.id;
    document.body.dataset.assistant = item.id;

    const kicker = $('.core-kicker');
    const headline = $('.core-copy h3');
    const description = $('.core-copy > p');
    const input = $('#saarthiCommand');
    const quickRow = $('.quick-row');

    if(kicker) kicker.innerHTML = '<span class="online-dot"></span> '+item.environment.toUpperCase()+' <span>·</span> CONTEXT AWARE';
    if(headline) headline.innerHTML = item.headline;
    if(description) description.textContent = item.descriptionText;
    if(input) input.placeholder = item.placeholder;

    if(quickRow) {
      quickRow.innerHTML = item.quick.map(([icon,label,value]) =>
        '<button class="quick" data-command="'+value.replace(/"/g,'&quot;')+'"><b>'+icon+'</b>'+label+'</button>'
      ).join('');
      quickRow.querySelectorAll('[data-command]').forEach(button => {
        button.addEventListener('click', () => ask(button.dataset.command));
      });
    }

    if(responseCard) responseCard.dataset.assistant = item.id;
  };

  const selectAssistant=id=>{
    currentAssistant=id;
    const item=ASSISTANTS.find(x=>x.id===id)||ASSISTANTS[0];
    if(!item) return;

    currentAssistant=item.id;
    if($('#assistantName')) $('#assistantName').textContent=item.name;
    if($('#assistantSelectorIcon')) $('#assistantSelectorIcon').textContent=item.icon;
    if($('#coreAssistantLabel')) $('#coreAssistantLabel').textContent=item.name;

    applyAssistantEnvironment(item);
    loadConversation(item.id);
    renderConversation();
    renderHistory();
    setStatus(item.name+' ready');
    setCoreState('ready',item.name+' environment is ready.');
    addActivity('Assistant selected',item.name+' · '+item.environment);
  };

  const ask=value=>{
    if(!command)return;command.value=value;command.focus();
    document.querySelector('.core-panel')?.scrollIntoView({behavior:'smooth',block:'center'});
  };

  const parseCommand=value=>{const token=value.trim().split(/\s+/)[0].toLowerCase();return COMMANDS[token]||'chat';};

  const apiCommand=async(value,mode)=>{
    await ensureApiBase();
    const context={
      client_time:new Date().toISOString(),
      timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Kolkata',
      locale:navigator.language||'en-IN',
      conversation:currentConversation().map(({role,content})=>({role,content}))
    };
    const response=await fetch(apiUrl('/api/command'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:value,mode,assistant:currentAssistant,context})});
    if(!response.ok)throw new Error('API '+response.status);return response.json();
  };

  const runCommand=async(value,mode)=>{
    setStatus('Routing…');setCoreState('routing','Request received.');await new Promise(r=>setTimeout(r,90));
    setStatus('Understanding…');setCoreState('understanding','Separating intent from noise.');
    const request=apiCommand(value,mode);await new Promise(r=>setTimeout(r,120));
    setStatus('Planning…');setCoreState('planning','Building an execution path.');
    const result=await request;if(!result?.ok)throw new Error('SAARTHI runtime rejected the command');
    const intent=result?.intent?.name||mode;setStatus('Verifying…');setCoreState('verifying','Checking the execution result.');
    await new Promise(r=>setTimeout(r,120));
    runs.unshift({id:result.run_id,intent,provider:result.provider,at:new Date().toISOString(),message:value});runs.splice(20);
    setStatus('Ready');setCoreState('ready','Saarthi has a response.');
    addActivity('Run completed',result.run_id+' · '+intent+' · '+result.provider);
    showResponse(result.reply,result);
    return result;
  };

  const submit=async()=>{
    const value=command?.value.trim();if(!value||command.disabled)return;
    const mode=parseCommand(value);addActivity('Command received',currentAssistant+' · '+mode+' · '+value.replace(/^\/\w+\s*/,''));
    appendConversation('user',value);
    command.disabled=true;
    try{const result=await runCommand(value,mode);if(mode==='voice'||window.SaarthiApp.voiceTurn)speak(result.reply);}
    catch(error){
      setStatus('Connection issue');setCoreState('offline','Cloud runtime is unavailable.');
      addActivity('Run failed',error?.message||'Cloud runtime unavailable.');
      showResponse('### Connection issue\n\nSAARTHI could not reach the cloud runtime. Check the backend connection and try again.',{intent:{name:'runtime'},provider:'unavailable'});
    }finally{window.SaarthiApp.voiceTurn=false;command.value='';command.disabled=false;setTimeout(()=>setStatus('Saarthi is present'),1200);}
  };

  const voice=()=>{
    const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SpeechRecognition){addActivity('Voice unavailable','This browser does not expose speech recognition.');return;}
    const recognition=new SpeechRecognition();recognition.lang='en-IN';recognition.interimResults=false;recognition.maxAlternatives=1;
    window.SaarthiApp.voiceTurn=true;recognition.onstart=()=>setStatus('Listening…');
    recognition.onresult=e=>{ask(e.results[0][0].transcript);setStatus('Command ready');submit();};
    recognition.onerror=()=>{window.SaarthiApp.voiceTurn=false;setStatus('Saarthi is present');};
    recognition.onend=()=>{if(status&&status.textContent==='Listening…')setStatus('Saarthi is present');};recognition.start();
  };

  loadHistory();
  loadConversation('saarthi');
  applyAssistantEnvironment(ASSISTANTS[0]);
  renderConversation();
  renderHistory();
  updateClock();setInterval(updateClock,1000);loadRuntimeConfig();
  document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>ask(button.dataset.command)));
  document.querySelectorAll('[data-menu]').forEach(button=>button.addEventListener('click',()=>selectMenu(button.dataset.menu)));
  $('#settingsButton')?.addEventListener('click',()=>renderMenuRoot());
  if(!document.querySelector('#historyTrigger')){
    const trigger=document.createElement('button');trigger.id='historyTrigger';trigger.className='history-trigger';trigger.type='button';trigger.setAttribute('aria-label','Conversation history');trigger.textContent='☷';
    document.querySelector('.top-actions')?.insertBefore(trigger,document.querySelector('#settingsButton'));
    trigger.addEventListener('click',openHistory);
  }
  $('#assistantSelector')?.addEventListener('click',()=>renderPicker('assistants'));
  document.addEventListener('click',event=>{if(!event.target.closest('.menu-picker,.assistant-picker,.control-picker,[data-menu],#settingsButton,#assistantSelector'))closePickers();});
  $('#sendCommand')?.addEventListener('click',submit);$('#voiceCommand')?.addEventListener('click',voice);
  command?.addEventListener('keydown',event=>{if(event.key==='Enter')submit();});
  window.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();selectMenu('command');command?.focus();}});

  window.SaarthiApp={menus:MENUS,assistants:ASSISTANTS,controls:CONTROLS,runs,ask,submit,voice,selectMenu,selectAssistant,getCurrentAssistant:()=>currentAssistant,clearConversation:assistant=>{const id=assistant||currentAssistant;const list=ensureAssistantHistory(id);const tid=currentThreads[id];const index=list.findIndex(t=>t.id===tid);if(index>=0)list.splice(index,1);currentThreads[id]=null;conversations[id]=[];saveHistory();if(id===currentAssistant){document.body.classList.remove('chat-active');renderConversation();renderHistory();}},startNewConversation,voiceTurn:false};
  return window.SaarthiApp;
})()
