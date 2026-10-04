const SaarthiApp = (() => {
  const $ = (s, root = document) => root.querySelector(s);
  const activity = $('#activityStream');
  const command = $('#saarthiCommand');
  const status = $('#presenceText');
  const liveDay = $('#liveDay');
  const topClock = $('#topClock');
  const greeting = $('#greeting'), coreStatus = $('.core-status');
  const intelligenceFlow = $('#intelligenceFlow');
  const intelligenceFlowTitle = $('#intelligenceFlowTitle');
  const intelligenceFlowState = $('#intelligenceFlowState');
  const intelligenceContext = $('#intelligenceContext');
  const responseCard = $('#assistantResponse'), responseBody = $('#assistantResponseBody'), responseMeta = $('#assistantResponseMeta');
  // Safe visual default: a fresh load is always the home surface. Conversation mode must be explicitly activated.
  document.body.classList.add('home-active');
  document.body.classList.remove('chat-active');
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
  const MAX_ATTACHMENT_BYTES=2*1024*1024;
  const MAX_ATTACHMENT_TOTAL_BYTES=3*1024*1024;
  let sendInFlight=false;
  const attachmentsByAssistant=Object.create(null);
  const conversations=Object.create(null);
  const currentThreads=Object.create(null);
  const historyState={assistants:Object.create(null)};
  const INDUSTRIES=Object.freeze({
    '':'General','travel':'Travel & Tourism','financial_services':'Financial Services','healthcare':'Healthcare & Life Sciences',
    'retail':'Retail & E-commerce','logistics':'Logistics & Supply Chain','manufacturing':'Manufacturing'
  });
  let currentIndustry='';
  const setAutonomousContext=(label,status='AUTO')=>{
    const el=document.getElementById('autonomousContextLabel');
    const st=document.getElementById('autonomousContextStatus');
    if(el)el.textContent=label;
    if(st)st.textContent=status;
  };

  const uid=()=>Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8);
  const assistantInfo=id=>ASSISTANTS.find(x=>x.id===id)||ASSISTANTS[0];
  const titleFromMessage=value=>{
    const clean=String(value||'').replace(/\s+/g,' ').trim();
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
        const thread={id:uid(),title:titleFromMessage(first?.content),createdAt:first?.at||new Date().toISOString(),updatedAt:new Date().toISOString(),messages:legacy.slice()};
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
  // Loading a conversation is an explicit action. A page refresh must not silently
  // reopen the last thread and put the home surface into chat mode.
  const loadConversation=(assistant,resumeLatest=false)=>{
    const id=assistantInfo(assistant).id;
    if(!resumeLatest){
      currentThreads[id]=null;
      conversations[id]=[];
      return conversations[id];
    }
    const thread=ensureThread(id,false);
    conversations[id]=thread?thread.messages:[];
    return conversations[id];
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
  const currentConversation=()=>conversations[currentAssistant]||[];

  const MENUS = Object.freeze({
    assistants:{label:'Ways I can help',capabilities:['saarthi','coding','research','create','data_analyst','analyze','plan']},
    control:{label:'Saarthi settings',capabilities:['ai','usage','memory','voice','tools','connections','security','notifications','appearance','privacy']}
  });
  const ASSISTANTS = Object.freeze([
    {
      id:'saarthi',icon:'✦',name:'Saarthi',description:'Your all-round companion',
      environment:'Saarthi',headline:'Think clearly.<br><em>Move deliberately.</em>',
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
      id:'coding',icon:'⌘',name:'Build',description:'Build, fix, explain and improve code',
      environment:'Build',headline:'Build precisely.<br><em>Ship with confidence.</em>',
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
      id:'research',icon:'◎',name:'Research',description:'Find, compare and make sense of evidence',
      environment:'Research',headline:'Go deeper.<br><em>Know what matters.</em>',
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
      id:'create',icon:'◇',name:'Create',description:'Write, shape and refine ideas',
      environment:'Create',headline:'Make it distinct.<br><em>Give ideas a shape.</em>',
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
      id:'data_analyst',icon:'▥',name:'Numbers',description:'Work with numbers, patterns and charts',
      environment:'Numbers',headline:'Find the signal.<br><em>Show the evidence.</em>',
      descriptionText:'Work with spreadsheets and datasets, calculate what matters, surface patterns and create charts or diagrams when they improve the answer.',
      placeholder:'Upload data or ask a data question…',
      quick:[
        ['▥','Analyze','Analyze this dataset.'],
        ['◫','Chart','Create the right chart for this data.'],
        ['◈','Find patterns','Find the important patterns.'],
        ['◎','Explain','Explain what the numbers mean.']
      ]
    },
    {
      id:'analyze',icon:'◈',name:'Understand',description:'Find patterns, risks and meaning',
      environment:'Understand',headline:'See the signal.<br><em>Separate fact from noise.</em>',
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
      id:'plan',icon:'◷',name:'Plan',description:'Turn intentions into practical steps',
      environment:'Plan',headline:'Turn intent into action.<br><em>Know the next move.</em>',
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
    {id:'ai',icon:'✦',name:'How I think',description:'Choose how Saarthi works for you'},
    {id:'usage',icon:'◉',name:'Your activity',description:'See requests and usage'},
    {id:'memory',icon:'◌',name:'Memory',description:'Manage what Saarthi remembers'},
    {id:'voice',icon:'⌁',name:'Voice',description:'Voice input and speech settings'},
    {id:'tools',icon:'⚙',name:'Things I can use',description:'Services and capabilities available to Saarthi'},
    {id:'connections',icon:'↗',name:'Connected services',description:'Services you have connected'},
    {id:'security',icon:'◈',name:'Security',description:'Sessions, permissions and API safety'},
    {id:'notifications',icon:'•',name:'Reminders',description:'Reminders and useful alerts'},
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
  const CANONICAL_API_BASE='https://saarthi-nine-chi.vercel.app';
  let API_BASE=CANONICAL_API_BASE;
  let API_BASES=[CANONICAL_API_BASE];
  const loadRuntimeConfig=async()=>{
    try{
      const response=await fetch('./config/runtime.json?ts='+Date.now(),{cache:'no-store'});
      if(response.ok){
        const config=await response.json();
        const configured=[
          config.api_base_url,
          ...(Array.isArray(config.fallback_api_base_urls)?config.fallback_api_base_urls:[])
        ]
          .map(value=>String(value||'').replace(/\/$/,''))
          .filter(Boolean);
        const sameOrigin=String(window.location.origin||'').replace(/\/$/,'');
        const sameOriginConfigured=configured.includes(sameOrigin);
        const approved=[CANONICAL_API_BASE,...configured.filter(value=>value===CANONICAL_API_BASE)];
        API_BASES=[...new Set(approved.filter(Boolean))];
        API_BASE=CANONICAL_API_BASE;
      }
    }catch{}
  };
  const ensureApiBase=async()=>{
    if(!API_BASES.length)await loadRuntimeConfig();
    if(!API_BASES.length){
      API_BASE=CANONICAL_API_BASE;
      API_BASES=[CANONICAL_API_BASE];
    }
    return API_BASE;
  };
  const apiUrl=(path,base=API_BASE)=>base+(path.startsWith('/')?path:'/'+path);
  const checkRuntimeHealth=async(base)=>{
    const controller=new AbortController();
    const timeout=window.setTimeout(()=>controller.abort(),5000);
    try{
      const response=await fetch(apiUrl('/api/health',base),{
        method:'GET',
        cache:'no-store',
        signal:controller.signal
      });
      if(!response.ok)throw new Error('Runtime health '+response.status);
      const data=await response.json();
      if(data?.ok!==true)throw new Error('Runtime health check failed');
      return data;
    }finally{
      window.clearTimeout(timeout);
    }
  };

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

  const updateIntelligenceFlow=(state='idle',result=null)=>{
    if(!intelligenceFlow)return;
    const labels={idle:'Ready to reason',running:'Working the objective',complete:'Decision-ready result'};
    if(intelligenceFlowTitle)intelligenceFlowTitle.textContent=labels[state]||labels.idle;
    if(intelligenceFlowState)intelligenceFlowState.textContent=state.toUpperCase();
    const stages=[...intelligenceFlow.querySelectorAll('.intelligence-stage')];
    const active=result?.orchestration?.stages||['understand','contextualize','reason','execute','verify','deliver'];
    const activeCapability=result?.orchestration?.active_capability||assistantInfo(currentAssistant).name;
    const industry=result?.orchestration?.industry||INDUSTRIES[currentIndustry]||'General';
    const workflowList=Array.isArray(result?.orchestration?.workflow)?result.orchestration.workflow:[];
    const frameworkList=Array.isArray(result?.orchestration?.decision_frameworks)?result.orchestration.decision_frameworks:[];
    const workflow=workflowList.join(' · ');
    const decisionLens=frameworkList.join(' · ');
    stages.forEach((el,index)=>el.classList.toggle('active',state==='running'?index<4:state==='complete'?index<active.length:index===0));
    if(intelligenceContext){
      if(state==='complete'&&result?.orchestration){
        intelligenceContext.textContent=industry && industry!=='General'
          ? industry
          : 'Saarthi selected the operating path.';
      }else{
        intelligenceContext.textContent=state==='running'
          ? 'SAARTHI is contextualizing the objective, selecting the right capability and validating the path.'
          : 'SAARTHI is ready to turn an objective into a decision-ready result.';
      }
    }
    const wf=document.getElementById('activeWorkflow');
    const exec=document.getElementById('executionStatus');
    const contextLabel=result?.orchestration?.industry
      ? result.orchestration.industry
      : 'Saarthi selected the operating path.';
    setAutonomousContext(state==='running'
      ? 'Saarthi is deciding the right operating path…'
      : state==='complete'
        ? contextLabel
        : 'Saarthi will determine the right operating path from your objective.',
      state==='running'?'DECIDING':state==='complete'?'READY':'AUTO');
    if(wf)wf.textContent=state==='complete'?(industry && industry!=='General'?industry:'Saarthi'):'Saarthi';
    if(exec)exec.textContent=state==='running'?'WORKING':state==='complete'?'READY':'READY';
  };

  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const inlineMarkdown=value=>escapeHtml(value)
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/__([^_]+)__/g,'<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g,'<em>$1</em>')
    .replace(/_([^_]+)_/g,'<em>$1</em>');

  const renderMarkdown=markdown=>{
    const source=String(markdown||'').replace(new RegExp('<toolcall>[\\s\\S]*?</toolcall>','gi'),'').trim();
    const lines=source.replace(/\r/g,'').split('\n');
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


  const currentAttachments=()=>attachmentsByAssistant[currentAssistant]||[];
  const fileAsDataUrl=file=>new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(String(reader.result||''));
    reader.onerror=()=>reject(reader.error||new Error('Could not read file'));
    reader.readAsDataURL(file);
  });
  const attachmentIcon=mime=>mime.startsWith('image/')?'▧':mime.includes('sheet')||mime.includes('csv')?'▥':mime.includes('pdf')?'▤':'◫';
  const renderAttachmentTray=()=>{
    let tray=$('#attachmentTray');
    if(!tray){
      const composer=document.querySelector('.conversation-composer');
      if(!composer)return;
      tray=document.createElement('div');tray.id='attachmentTray';tray.className='attachment-tray';
      composer.parentElement?.insertBefore(tray,composer);
    }
    const items=currentAttachments();
    tray.innerHTML=items.map((item,index)=>'<div class="attachment-chip"><span class="attachment-chip-icon">'+attachmentIcon(item.type)+'</span><span class="attachment-chip-name" title="'+escapeHtml(item.name)+'">'+escapeHtml(item.name)+'</span><button type="button" data-remove-attachment="'+index+'" aria-label="Remove '+escapeHtml(item.name)+'">×</button></div>').join('');
    tray.hidden=!items.length;
    tray.querySelectorAll('[data-remove-attachment]').forEach(button=>button.addEventListener('click',()=>{
      currentAttachments().splice(Number(button.dataset.removeAttachment),1);renderAttachmentTray();
    }));
  };
  const ensureAttachmentControls=()=>{
    if($('#saarthiFileInput'))return;
    const composer=$('.conversation-composer');
    if(!composer)return;
    const input=document.createElement('input');
    input.type='file';input.id='saarthiFileInput';input.multiple=true;
    input.accept='image/*,.pdf,.txt,.md,.csv,.tsv,.json,.xlsx,.xlsm';
    input.hidden=true;
    composer.appendChild(input);
    const button=document.createElement('button');
    button.type='button';button.id='attachCommand';button.className='attach-button';
    button.setAttribute('aria-label','Attach files or images');button.title='Attach files or images';button.textContent='＋';
    composer.insertBefore(button,composer.firstChild);
    button.addEventListener('click',()=>input.click());
    input.addEventListener('change',async()=>{
      const files=[...input.files||[]];
      let total=currentAttachments().reduce((sum,item)=>sum+Number(item.size||0),0);
      for(const file of files){
        if(file.size>MAX_ATTACHMENT_BYTES){addActivity('Attachment rejected',file.name+' · maximum 2 MB');continue;}
        if(total+file.size>MAX_ATTACHMENT_TOTAL_BYTES){addActivity('Attachment rejected',file.name+' · attachment batch limit reached');continue;}
        try{
          const data=await fileAsDataUrl(file);
          currentAttachments().push({name:file.name,type:file.type||'application/octet-stream',size:file.size,data});
          total+=file.size;
        }catch{addActivity('Attachment failed',file.name+' could not be read.');}
      }
      input.value='';renderAttachmentTray();
    });
    renderAttachmentTray();
  };


  const normalizeLegacyToolVisual=(raw)=>{
    let text=String(raw||'');
    text=text.replace(/\\r?\\n/g,'\n');
    const toolPattern=/<\|toolcall(?:_start)?\|>[\s\S]*?python\(code=([\s\S]*?)\)\s*<\|toolcall(?:_end)?\|>/gi;

    const parseArrayLiteral=(literal)=>{
      try{return JSON.parse(String(literal).replace(/'/g,'"').replace(/\bNone\b/g,'null').replace(/\bTrue\b/g,'true').replace(/\bFalse\b/g,'false'));}catch{return null;}
    };
    const extractAssignedArray=(source,name)=>{
      const m=source.match(new RegExp('\\b'+name+'\\s*=\\s*(?:np\\.array\\s*)?(\\[[\\s\\S]*?\\])','i'));
      return m?parseArrayLiteral(m[1]):null;
    };

    const parseTool=(rawCode)=>{
      let source=String(rawCode||'').trim();
      if((source.startsWith('"')&&source.endsWith('"'))||(source.startsWith("'")&&source.endsWith("'")))source=source.slice(1,-1);
      source=source.replace(/\\n/g,'\n').replace(/\\t/g,'\t').replace(/\\'/g,"'").replace(/\\"/g,'"');

      const hasHeatmap=/\b(?:sns\.)?heatmap\s*\(/i.test(source)||/\bplt\.imshow\s*\(/i.test(source);
      const chartType=hasHeatmap?'heatmap':/\bplt\.pie\s*\(/i.test(source)?'pie':/\bplt\.bar\s*\(/i.test(source)?'bar':'line';
      const arrays={};
      const names=[...source.matchAll(/\b([A-Za-z_]\w*)\s*=\s*(?:np\.array\s*)?(\[[\s\S]*?\])/g)].map(m=>m[1]);
      [...new Set(names)].forEach(name=>{const value=extractAssignedArray(source,name);if(value!==null)arrays[name]=value;});

      if(chartType==='heatmap'){
        const matrix=arrays.data||arrays.values||arrays.matrix||Object.values(arrays).find(v=>Array.isArray(v)&&Array.isArray(v[0]));
        if(Array.isArray(matrix)&&Array.isArray(matrix[0]))return '<saarthi-chart>'+JSON.stringify({chartType:'heatmap',meta:{title:'Generated heat map'},data:matrix.map((row,i)=>({row:String((arrays.labels?.[i]??i+1)),values:row.map(Number)})),rowLabels:Array.isArray(arrays.labels)?arrays.labels.map(String):[],colLabels:Array.isArray(arrays.columns)?arrays.columns.map(String):[]})+'</saarthi-chart>';
      }
      const pieCall=source.match(/plt\.pie\s*\(\s*([A-Za-z_]\w*)/i);
      if(chartType==='pie'&&pieCall&&Array.isArray(arrays[pieCall[1]])){
        const values=arrays[pieCall[1]],labels=arrays.categories||arrays.labels||values.map((_,i)=>String(i+1));
        return '<saarthi-chart>'+JSON.stringify({chartType:'pie',meta:{title:'Generated chart'},nameKey:'category',valueKey:'value',data:values.map((v,i)=>({category:String(labels[i]??i+1),value:Number(v)}))})+'</saarthi-chart>';
      }
      const barCall=source.match(/plt\.bar\s*\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)/i);
      if(chartType==='bar'&&barCall&&Array.isArray(arrays[barCall[1]])&&Array.isArray(arrays[barCall[2]])){
        const labels=arrays[barCall[1]],values=arrays[barCall[2]];
        return '<saarthi-chart>'+JSON.stringify({chartType:'bar',meta:{title:'Generated chart'},xKey:'category',series:[{dataKey:'value',label:'Value'}],data:values.map((v,i)=>({category:String(labels[i]??i+1),value:Number(v)}))})+'</saarthi-chart>';
      }
      const plotCalls=[...source.matchAll(/plt\.plot\s*\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)[^\n]*?(?:label\s*=\s*['"]([^'"]+)['"])?/gi)];
      if(plotCalls.length){
        const xKey=plotCalls[0][1],series=[],data=[],xValues=arrays[xKey]||[];
        plotCalls.forEach((call,i)=>{const key=call[2];if(Array.isArray(arrays[key]))series.push({dataKey:'s'+i,label:call[3]||key});});
        data.push(...xValues.map((x,i)=>{const row={category:String(x)};plotCalls.forEach((call,j)=>row['s'+j]=Number(arrays[call[2]]?.[i]));return row;}));
        if(series.length&&data.length)return '<saarthi-chart>'+JSON.stringify({chartType:'line',meta:{title:'Generated chart'},xKey:'category',series,data})+'</saarthi-chart>';
      }
      return '';
    };
    return text.replace(toolPattern,(_,code)=>parseTool(code));
  };

  const visualizationHtml=(type,json)=>{
    try{
      const spec=JSON.parse(json); const meta=spec.meta&&typeof spec.meta==='object'?spec.meta:{}; const chartTitle=spec.title||meta.title||'Visualization';
      if(type==='chart'){
        const data=Array.isArray(spec.data)?spec.data:[];const series=Array.isArray(spec.series)?spec.series:[];
        if(!data.length)return ''; if(spec.chartType!=='pie'&&spec.chartType!=='donut'&&spec.chartType!=='heatmap'&&!series.length)return '';
        const w=720,h=340,pad=42;
        const values=series.flatMap(se=>data.map(row=>Number(row[se.dataKey]))).filter(Number.isFinite);
        const max=Math.max(...values,1),min=Math.min(0,...values);
        const sx=i=>pad+i*Math.max(1,(w-pad*2)/Math.max(1,data.length-1));
        const sy=v=>h-pad-((v-min)/Math.max(1,max-min))*(h-pad*2);
        const palette=['#6f8fa8','#a38b6a','#6d927a','#8b7ba8'];
        let svg='<svg class="saarthi-chart-svg" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="'+escapeHtml(chartTitle)+'">'+(spec.chartType==='pie'||spec.chartType==='heatmap'?'':'<line x1="'+pad+'" y1="'+(h-pad)+'" x2="'+(w-pad)+'" y2="'+(h-pad)+'" class="chart-axis"/>');
        if(spec.chartType==='pie'||spec.chartType==='donut'){
          const numericKey = spec.valueKey || Object.keys(data[0]||{}).find(key=>data.some(row=>Number.isFinite(Number(row[key])))) || 'value';
          const labelKey = spec.nameKey || Object.keys(data[0]||{}).find(key=>!Number.isFinite(Number(data[0]?.[key]))) || 'category';
          const pieValue = row => Math.max(0, Number(row?.[numericKey]));
          const total=data.reduce((a,row)=>a+pieValue(row),0);
          const cx=190,cy=154,r=104,inner=spec.chartType==='donut'?62:0; let angle=-Math.PI/2;
          data.forEach((row,i)=>{
            const val=pieValue(row),a=total?val/total*Math.PI*2:0;
            const x1=cx+r*Math.cos(angle),y1=cy+r*Math.sin(angle),x2=cx+r*Math.cos(angle+a),y2=cy+r*Math.sin(angle+a);
            const ix1=cx+inner*Math.cos(angle),iy1=cy+inner*Math.sin(angle),ix2=cx+inner*Math.cos(angle+a),iy2=cy+inner*Math.sin(angle+a);
            const large=a>Math.PI?1:0;
            svg+='<path d="M '+x1+' '+y1+' A '+r+' '+r+' 0 '+large+' 1 '+x2+' '+y2+' L '+ix2+' '+iy2+' A '+inner+' '+inner+' 0 '+large+' 0 '+ix1+' '+iy1+' Z" fill="'+palette[i%palette.length]+'" stroke="rgba(255,255,255,.92)" stroke-width="2"/>';
            angle+=a;
          });
          svg+='<text x="'+cx+'" y="'+(cy-2)+'" text-anchor="middle" class="chart-center-total">'+escapeHtml(String(total))+'</text><text x="'+cx+'" y="'+(cy+18)+'" text-anchor="middle" class="chart-center-label">Total</text>';
          data.forEach((row,i)=>{
            const label=String(row[labelKey]??row.category??('Item '+(i+1)));
            const value=pieValue(row);
            const pct=total?(value/total*100):0;
            const y=48+i*40;
            svg+='<rect x="386" y="'+(y-10)+'" width="12" height="12" rx="4" fill="'+palette[i%palette.length]+'"/>';
            svg+='<text x="406" y="'+y+'" class="chart-legend-label">'+escapeHtml(label.slice(0,20))+'</text>';
            svg+='<text x="694" y="'+y+'" text-anchor="end" class="chart-legend-value">'+escapeHtml(Number.isInteger(value)?String(value):value.toFixed(1))+' · '+pct.toFixed(0)+'%</text>';
          });
        }else if(spec.chartType==='heatmap'){
          const rows=data.map(r=>Array.isArray(r.values)?r.values.map(Number):[]).filter(r=>r.length);
          const cols=Math.max(0,...rows.map(r=>r.length)); const gridW=Math.min(520,Math.max(260,cols*104));
          const cellW=gridW/Math.max(1,cols),cellH=52,left=(w-gridW)/2+18,top=58;
          const rowLabels=Array.isArray(spec.rowLabels)?spec.rowLabels:[],colLabels=Array.isArray(spec.colLabels)?spec.colLabels:[];
          const values=rows.flat().filter(Number.isFinite); const lo=Math.min(...values,0),hi=Math.max(...values,1);
          const cellColor=(v)=>{const t=(v-lo)/Math.max(1,hi-lo);const a=Math.round(35+175*t);return 'rgb('+a+','+(232-Math.round(105*t))+','+(244-Math.round(25*t))+')';};
          for(let ci=0;ci<cols;ci++){
            const x=left+ci*cellW+(cellW/2);
            svg+='<text x="'+x+'" y="'+(top-16)+'" text-anchor="middle" class="chart-label">'+escapeHtml(String(colLabels[ci]??('Q'+(ci+1))))+'</text>';
          }
          rows.forEach((row,ri)=>{
            const y=top+ri*cellH;
            svg+='<text x="'+(left-14)+'" y="'+(y+30)+'" text-anchor="end" class="chart-label">'+escapeHtml(String(rowLabels[ri]??('R'+(ri+1))))+'</text>';
            row.forEach((v,ci)=>{
              const x=left+ci*cellW;
              svg+='<rect x="'+x+'" y="'+y+'" width="'+Math.max(4,cellW-7)+'" height="'+(cellH-7)+'" rx="9" fill="'+cellColor(v)+'"/>';
              svg+='<text x="'+(x+(cellW-7)/2)+'" y="'+(y+29)+'" text-anchor="middle" class="chart-heat-value">'+escapeHtml(Number.isInteger(v)?String(v):v.toFixed(1))+'</text>';
            });
          });
        }else if(spec.chartType==='bar'||spec.chartType==='stacked_bar'||spec.chartType==='histogram'){
          const bw=Math.max(10,(w-pad*2)/Math.max(1,data.length*series.length)-6);
          data.forEach((row,i)=>series.forEach((se,j)=>{const v=Number(row[se.dataKey]);if(!Number.isFinite(v))return;const x=pad+i*((w-pad*2)/Math.max(1,data.length))+j*bw,y=sy(v),height=h-pad-y;svg+='<rect x="'+x+'" y="'+y+'" width="'+Math.max(4,bw-3)+'" height="'+Math.max(1,height)+'" rx="5" fill="'+palette[j%palette.length]+'"/>';}));
        }else if(spec.chartType==='scatter'||spec.chartType==='bubble'){
          const xValues=data.map(row=>Number(row[spec.xKey])); const yKey=series[0]?.dataKey;
          const finiteX=xValues.filter(Number.isFinite); const xMin=Math.min(...finiteX,0),xMax=Math.max(...finiteX,1);
          const sxv=v=>pad+((v-xMin)/Math.max(1,xMax-xMin))*(w-pad*2);
          data.forEach((row,i)=>{const x=Number(row[spec.xKey]),y=Number(row[yKey]);if(!Number.isFinite(x)||!Number.isFinite(y))return;const radius=spec.chartType==='bubble'?Math.max(5,Math.min(24,Number(row[spec.sizeKey]||8)/4)):7;svg+='<circle cx="'+sxv(x)+'" cy="'+sy(y)+'" r="'+radius+'" fill="'+palette[i%palette.length]+'" fill-opacity=".78"/>';});
        }else if(spec.chartType==='area'){
          series.forEach((se,j)=>{const pts=data.map((row,i)=>{const v=Number(row[se.dataKey]);return Number.isFinite(v)?sx(i)+','+sy(v):null;}).filter(Boolean);if(pts.length){const first=pts[0].split(',')[0],last=pts[pts.length-1].split(',')[0];svg+='<polygon points="'+first+','+(h-pad)+' '+pts.join(' ')+' '+last+','+(h-pad)+'" fill="'+palette[j%palette.length]+'" fill-opacity=".18"/><polyline points="'+pts.join(' ')+'" fill="none" stroke="'+palette[j%palette.length]+'" stroke-width="3"/>';}}); 
        }else if(spec.chartType==='funnel'){
          const values=data.map(r=>Number(r[spec.valueKey||'value'])).filter(Number.isFinite);const labels=data.map(r=>String(r[spec.nameKey||'stage']||''));const maxV=Math.max(...values,1);values.forEach((v,i)=>{const width=460*(v/maxV);const x=(w-width)/2,y=40+i*48;svg+='<rect x="'+x+'" y="'+y+'" width="'+width+'" height="36" rx="8" fill="'+palette[i%palette.length]+'"/><text x="'+(w/2)+'" y="'+(y+23)+'" text-anchor="middle" class="chart-label">'+escapeHtml(labels[i])+' · '+escapeHtml(String(v))+'</text>';});
        }else if(spec.chartType==='gauge'){
          const value=Number(data[0]?.value??data[0]?.actual??0),target=Number(data[0]?.target??100),ratio=Math.max(0,Math.min(1,value/Math.max(target,1)));const cx=360,cy=270,r=150;svg+='<path d="M '+(cx-r)+' '+cy+' A '+r+' '+r+' 0 0 1 '+(cx+r)+' '+cy+'" fill="none" stroke="rgba(111,143,168,.2)" stroke-width="28"/><path d="M '+(cx-r)+' '+cy+' A '+r+' '+r+' 0 0 1 '+(cx-r+2*r*ratio)+' '+(cy-Math.sqrt(Math.max(0,r*r-(r*(2*ratio-1))**2)))+'" fill="none" stroke="'+palette[0]+'" stroke-width="28" stroke-linecap="round"/><text x="'+cx+'" y="'+(cy-20)+'" text-anchor="middle" class="chart-center-total">'+escapeHtml(String(value))+'</text><text x="'+cx+'" y="'+(cy+10)+'" text-anchor="middle" class="chart-center-label">Target '+escapeHtml(String(target))+'</text>';
        }else if(spec.chartType==='radar'){
          const centerX=360,centerY=170,radius=115,labels=data.map(r=>String(r.category??r.label??'')),vals=series[0]?data.map(r=>Number(r[series[0].dataKey])):[],maxV=Math.max(...vals.filter(Number.isFinite),1);const pts=vals.map((v,i)=>{const a=-Math.PI/2+i*(Math.PI*2/Math.max(1,vals.length));const rr=radius*Math.max(0,v/maxV);return (centerX+rr*Math.cos(a))+','+(centerY+rr*Math.sin(a));});svg+='<polygon points="'+pts.join(' ')+'" fill="'+palette[0]+'" fill-opacity=".2" stroke="'+palette[0]+'" stroke-width="3"/>'+labels.map((l,i)=>{const a=-Math.PI/2+i*(Math.PI*2/Math.max(1,labels.length));return '<text x="'+(centerX+(radius+22)*Math.cos(a))+'" y="'+(centerY+(radius+22)*Math.sin(a))+'" text-anchor="middle" class="chart-label">'+escapeHtml(l.slice(0,16))+'</text>';}).join('');
        }else if(spec.chartType==='waterfall'){
          let running=0;const maxAbs=Math.max(...data.map(r=>Math.abs(Number(r.value)||0)),1);data.forEach((row,i)=>{const v=Number(row.value)||0;const x=pad+i*((w-pad*2)/Math.max(1,data.length));const y=v>=0?sy(running+v):sy(running);const h=Math.abs(sy(running)-sy(running+v));svg+='<rect x="'+x+'" y="'+Math.min(y,sy(running))+'" width="'+Math.max(12,(w-pad*2)/Math.max(1,data.length)-8)+'" height="'+Math.max(2,h)+'" rx="4" fill="'+palette[(v>=0?0:1)]+'"/>';running+=v;});
        }else if(spec.chartType==='box'){
          const groups=Array.isArray(spec.groups)?spec.groups:data.map(r=>r.values).filter(Array.isArray);const boxW=Math.min(80,(w-pad*2)/Math.max(1,groups.length)-12);groups.forEach((vals,i)=>{const n=vals.map(Number).filter(Number.isFinite).sort((a,b)=>a-b);if(n.length<2)return;const q=p=>n[Math.floor((n.length-1)*p)],x=pad+i*((w-pad*2)/Math.max(1,groups.length))+boxW/2;const y1=sy(q(.25)),y2=sy(q(.75));svg+='<line x1="'+x+'" y1="'+sy(q(0))+'" x2="'+x+'" y2="'+sy(q(1))+'" stroke="'+palette[i%palette.length]+'" stroke-width="3"/><rect x="'+(x-boxW/2)+'" y="'+y2+'" width="'+boxW+'" height="'+Math.max(2,y1-y2)+'" rx="6" fill="'+palette[i%palette.length]+'" fill-opacity=".35" stroke="'+palette[i%palette.length]+'"/><line x1="'+(x-boxW/2)+'" y1="'+sy(q(.5))+'" x2="'+(x+boxW/2)+'" y2="'+sy(q(.5))+'" stroke="'+palette[i%palette.length]+'" stroke-width="3"/>';});
        }else{
          series.forEach((se,j)=>{const pts=data.map((row,i)=>{const v=Number(row[se.dataKey]);return Number.isFinite(v)?sx(i)+','+sy(v):null;}).filter(Boolean).join(' ');svg+='<polyline points="'+pts+'" fill="none" stroke="'+palette[j%palette.length]+'" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>';});
        }
        if(spec.chartType!=='pie'&&spec.chartType!=='donut'&&spec.chartType!=='heatmap'&&spec.chartType!=='funnel'&&spec.chartType!=='gauge'&&spec.chartType!=='radar'&&spec.chartType!=='waterfall'&&spec.chartType!=='box'){
          data.forEach((row,i)=>{const label=String(row[spec.xKey]??'');svg+='<text x="'+sx(i)+'" y="'+(h-15)+'" text-anchor="middle" class="chart-label">'+escapeHtml(label.slice(0,14))+'</text>';});
        }
        svg+='</svg>';
        return '<div class="saarthi-visual"><div class="visual-title">'+escapeHtml(chartTitle)+'</div>'+svg+'</div>';
      }
      if(type==='heatmap'){
        const rows=Array.isArray(spec.data)?spec.data:[];
        if(!rows.length||!Array.isArray(rows[0]))return '';
        const flat=rows.flat().map(Number).filter(Number.isFinite);
        if(!flat.length)return '';
        const min=Math.min(...flat),max=Math.max(...flat),range=Math.max(1e-9,max-min);
        const rowLabels=Array.isArray(spec.rowLabels)?spec.rowLabels:[];
        const colLabels=Array.isArray(spec.colLabels)?spec.colLabels:[];
        const cells=rows.map((row,r)=>'<div class="heatmap-row">'+row.map((v,c)=>{
          const n=Number(v); const ratio=Number.isFinite(n)?(n-min)/range:0;
          const alpha=(0.14+ratio*0.70).toFixed(2);
          const label=Number.isFinite(n)?(Number.isInteger(n)?n:n.toFixed(2)):'';
          return '<div class="heatmap-cell" style="--heat-alpha:'+alpha+'" title="'+escapeHtml(String(label))+'">'+escapeHtml(String(label))+'</div>';
        }).join('')+'</div>').join('');
        const cols=rows[0].map((_,i)=>'<span>'+escapeHtml(String(colLabels[i]??i+1))+'</span>').join('');
        return '<div class="saarthi-visual"><div class="visual-title">'+escapeHtml(chartTitle)+'</div><div class="heatmap-wrap"><div class="heatmap-col-labels">'+cols+'</div>'+rows.map((_,r)=>'<div class="heatmap-labeled-row"><span class="heatmap-row-label">'+escapeHtml(String(rowLabels[r]??r+1))+'</span>'+cells.split('</div><div class="heatmap-row">')[r]+'</div>').join('')+'</div></div>';
      }
      if(type==='diagram'){
        const nodes=Array.isArray(spec.nodes)?spec.nodes:[],edges=Array.isArray(spec.edges)?spec.edges:[];
        return '<div class="saarthi-visual"><div class="visual-title">'+escapeHtml(spec.title||'Diagram')+'</div><div class="diagram-flow">'+nodes.map((n,i)=>'<div class="diagram-node"><span>'+escapeHtml(String(n.label||n.id||i+1))+'</span></div>').join('<div class="diagram-arrow">→</div>')+'</div>'+ (edges.length?'<div class="diagram-edges">'+edges.map(e=>escapeHtml(String(e.from||''))+' → '+escapeHtml(String(e.to||''))).join(' · ')+'</div>':'')+'</div>';
      }
    }catch{}
    return '';
  };

  const renderConversation=()=>{
    if(!responseCard||!responseBody)return;
    const item=ASSISTANTS.find(x=>x.id===currentAssistant)||ASSISTANTS[0];
    const messages=conversations[currentAssistant]||[];
    const hasMessages=messages.length>0;
    document.body.classList.toggle('chat-active',hasMessages);
    document.body.classList.toggle('home-active',!hasMessages);
    // Keep the home surface authoritative whenever no thread is actively open.
    if(!hasMessages) document.body.classList.remove('intelligence-expanded');
    if(!hasMessages){responseCard.hidden=true;return;}
    responseBody.innerHTML=messages.map(message=>{
      const role=message.role==='user'?'You':'Saarthi';
      const klass=message.role==='user'?'conversation-message user':'conversation-message assistant';
      let raw=normalizeLegacyToolVisual(String(message.content||''));
      raw=raw.replace(/^\s*(?:User Safety|Response Safety)\s*:\s*(?:safe|unsafe|blocked)\s*$/gim,'').trim();
      const visuals=[];
      raw=raw.replace(/<saarthi-chart>([\s\S]*?)<\/saarthi-chart>/gi,(_,json)=>{
        const index=visuals.length;
        visuals.push(visualizationHtml('chart',json));
        return 'SAARTHIVISUAL'+index+'TOKEN';
      });
      raw=raw.replace(/<saarthi-diagram>([\s\S]*?)<\/saarthi-diagram>/gi,(_,json)=>{
        const index=visuals.length;
        visuals.push(visualizationHtml('diagram',json));
        return 'SAARTHIVISUAL'+index+'TOKEN';
      });
      let html=renderMarkdown(raw);
      visuals.forEach((visual,index)=>{
        const token='SAARTHIVISUAL'+index+'TOKEN';
        html=html.replaceAll(token,visual||'');
      });
      const wp=message.workProduct&&typeof message.workProduct==='object'?message.workProduct:null;
      const isVisualization=/<saarthi-(?:chart|diagram)>/i.test(String(message.content||''));
      // Work-product metadata stays available to the runtime/history, but it is not shown after every reply.\n      // The conversation should feel like a human exchange; execution detail appears only when explicitly requested.\n      const workProductHtml='';
      return '<div class="'+klass+'"><div class="conversation-role">'+escapeHtml(role)+'</div><div class="conversation-content">'+html+workProductHtml+'</div></div>';
    }).join('');
    const lastAssistant=[...messages].reverse().find(m=>m.role==='assistant');
    const expanded=Boolean(lastAssistant?.showIntelligence);
    document.body.classList.toggle('intelligence-expanded',expanded);
    ['intelligenceFlow','autonomousContext','intelligenceCommandbar'].forEach(id=>{
      const el=document.getElementById(id);if(el)el.hidden=!expanded;
    });
    const eyebrow=$('#assistantResponseEyebrow');
    const title=$('#assistantResponseTitle');
    if(eyebrow) eyebrow.textContent=item.name.toUpperCase()+' • CONVERSATION';
    if(title) title.textContent='Conversation';
    if(responseMeta)responseMeta.textContent='SAARTHI · AUTONOMOUS INTELLIGENCE · ORCHESTRATED WORKSPACE';
    responseCard.dataset.assistant=item.id;
    responseCard.hidden=false;
    requestAnimationFrame(()=>{
      responseBody?.lastElementChild?.scrollIntoView({behavior:'smooth',block:'nearest'});
      $('#conversationComposer')?.scrollIntoView({behavior:'smooth',block:'nearest'});
    });
  };
  const renderWorkProduct=wp=>{
 const actions=Array.isArray(wp.actions_taken)?wp.actions_taken:[];
 const evidence=Array.isArray(wp.evidence)?wp.evidence:[];
 const next=Array.isArray(wp.next_actions)?wp.next_actions:[];
 const verification=wp.verification&&typeof wp.verification==='object'?wp.verification:{};
 const listHtml=(items)=>items.map((x)=>'<li>'+escapeHtml(String(x))+'</li>').join('');
 const evidenceHtml=evidence.map((x)=>'<li><b>'+escapeHtml(x.source||'runtime')+'</b> · '+escapeHtml(x.summary||'execution result available')+'</li>').join('');
 const industry=wp.industry&&wp.industry!=='General'?'<span><small>INDUSTRY</small><b>'+escapeHtml(wp.industry)+'</b></span>':'';
 const deliverable=wp.deliverable_type?'<span><small>DELIVERABLE</small><b>'+escapeHtml(String(wp.deliverable_type).replace(/_/g,' '))+'</b></span>':'';
 const journey=wp.journey?'<span><small>JOURNEY</small><b>'+escapeHtml(String(wp.journey).replace(/_/g,' '))+'</b></span>':'';
 const details=[];
 if(industry||deliverable||journey)details.push('<div class="work-product-meta">'+industry+deliverable+journey+'</div>');
 if(actions.length)details.push('<div class="work-product-section"><small>ACTIONS TAKEN</small><ul>'+listHtml(actions)+'</ul></div>');
 if(evidence.length)details.push('<div class="work-product-section"><small>EVIDENCE / EXECUTION</small><ul>'+evidenceHtml+'</ul></div>');
 if(next.length)details.push('<div class="work-product-section"><small>NEXT ACTIONS</small><ul>'+listHtml(next)+'</ul></div>');
 if(Array.isArray(wp.coverage)&&wp.coverage.length)details.push('<div class="work-product-section"><small>DOMAIN COVERAGE</small><div class="work-product-tags">'+wp.coverage.map((x)=>'<span>'+escapeHtml(String(x).replace(/_/g,' '))+'</span>').join('')+'</div></div>');
 if(verification.scope)details.push('<div class="work-product-foot">'+escapeHtml(String(verification.scope))+'</div>');
 const primary=wp.deliverable_type?'<div class="work-product-primary"><small>DELIVERABLE</small><strong>'+escapeHtml(String(wp.deliverable_type).replace(/_/g,' '))+'</strong></div>':'';
 const panel=details.length?'<details class="work-product-details"><summary>Execution details</summary>'+details.join('')+'</details>':'';
 const status=escapeHtml(String(verification.status||'runtime_verified').replace(/_/g,' '));
 return '<section class="work-product"><div class="work-product-head"><div><small>WORK PRODUCT</small><strong>Decision-ready delivery</strong></div><span class="work-product-status">'+status+'</span></div>'+primary+panel+'</section>';
};

const appendConversation=(role,content,workProduct=null,showIntelligence=false)=>{
    if(!content)return;
    const thread=ensureThread(currentAssistant,true);
    const messages=thread.messages||[];
    const message={role,content:String(content),at:new Date().toISOString()};
    if(role==='assistant'&&workProduct&&typeof workProduct==='object')message.workProduct=workProduct;
    if(role==='assistant'){
      messages.forEach(existing=>{if(existing.role==='assistant')existing.showIntelligence=false;});
      message.showIntelligence=Boolean(showIntelligence);
    }
    messages.push(message);
    conversations[currentAssistant]=messages.slice(-MAX_CONTEXT_MESSAGES);
    if(role==='user'&&(!thread.title||thread.title==='New conversation'))thread.title=titleFromMessage(content);
    thread.updatedAt=new Date().toISOString();
    saveConversation(currentAssistant);
    renderConversation();
  };
  const clearRecoveredRuntimeErrors=()=>{
    const thread=ensureThread(currentAssistant,true);
    const messages=Array.isArray(thread.messages)?thread.messages:[];
    const filtered=messages.filter(message=>!(
      message?.role==='assistant' &&
      /^###\\s*Connection issue\\b/i.test(String(message.content||'')) &&
      /could not reach the cloud runtime/i.test(String(message.content||''))
    ));
    if(filtered.length!==messages.length){
      thread.messages=filtered;
      conversations[currentAssistant]=filtered.slice(-MAX_CONTEXT_MESSAGES);
      thread.updatedAt=new Date().toISOString();
      saveConversation(currentAssistant);
    }
  };
  const showResponse=(reply,result)=>{
    const text=String(reply||'');
    const orchestration=result?.orchestration||{};
    const workProduct=result?.work_product||null;
    const intent=String(result?.intent?.name||'');
    const complex=Boolean(
      text.length>900 ||
      orchestration.industry ||
      (Array.isArray(orchestration.workflow)&&orchestration.workflow.length>1) ||
      (Array.isArray(orchestration.stages)&&orchestration.stages.length>=6) ||
      ['plan','research','analyze','data_analysis','coding','create'].some(x=>intent.toLowerCase().includes(x))
    );
    appendConversation('assistant',text,workProduct,complex);
    document.body.classList.toggle('intelligence-expanded',complex);
    if(!complex){
      const flow=document.getElementById('intelligenceFlow');
      const context=document.getElementById('autonomousContext');
      const bar=document.getElementById('intelligenceCommandbar');
      if(flow)flow.hidden=true;
      if(context)context.hidden=true;
      if(bar)bar.hidden=true;
    }else{
      const flow=document.getElementById('intelligenceFlow');
      const context=document.getElementById('autonomousContext');
      const bar=document.getElementById('intelligenceCommandbar');
      if(flow)flow.hidden=false;
      if(context)context.hidden=false;
      if(bar)bar.hidden=false;
    }
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
    attachmentsByAssistant[id]=[];
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
    mobile.innerHTML='<div class="mobile-history-backdrop" data-close-history="true"></div><aside class="mobile-history-panel"><div class="mobile-history-top"><div><b>Conversation history</b><small>'+escapeHtml(assistantInfo(currentAssistant).name)+'</small></div><div class="mobile-history-actions"><button type="button" class="mobile-new-chat" aria-label="New conversation">＋</button><button type="button" data-close-history="true" aria-label="Close">×</button></div></div><div class="mobile-history-content"></div></aside>';
    const content=mobile.querySelector('.mobile-history-content');bind(content);
    content.querySelector('.history-head')?.remove();
    mobile.querySelector('.mobile-new-chat')?.addEventListener('click',()=>{startNewConversation();mobile.hidden=true;});
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

  const renderControlCenter=async()=>{
    const target=$('#menuPicker');if(!target)return;
    closePickers();
    const savedMotion=localStorage.getItem('saarthi.reduceMotion')==='1';
    const adaptive=localStorage.getItem('saarthi.adaptiveUI')!=='0';
    target.innerHTML='<div class="picker-panel control-center-panel">'+
      '<div class="picker-head"><div><div class="eyebrow">SAARTHI</div><h3>Control Center</h3><small>Configure the workspace without changing how Saarthi reasons.</small></div><button class="picker-close" aria-label="Close">×</button></div>'+
      '<div class="control-grid">'+
        '<section class="control-card control-runtime"><div class="control-card-head"><span class="control-icon">◉</span><div><b>Runtime</b><small id="controlRuntimeState">Checking…</small></div></div><div class="control-status-list" id="controlRuntimeDetails"><span>Cloud runtime</span><b>Checking…</b></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">✦</span><div><b>AI & Models</b><small>Provider routing</small></div></div><div class="control-status-list"><span>Provider</span><b id="controlProvider">Checking…</b><span>Active route</span><b id="controlRoute">Checking…</b><span>API key</span><b>Server-side</b></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">◌</span><div><b>Memory</b><small>Conversation context</small></div></div><div class="control-status-list"><span>Local threads</span><b>'+Object.values(historyState.assistants).reduce((n,v)=>n+(Array.isArray(v)?v.length:0),0)+'</b><span>Context window</span><b>'+MAX_CONTEXT_MESSAGES+' messages</b></div><div class="control-actions"><button data-control-action="history">History</button><button data-control-action="clear-current">Clear current</button></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">⌁</span><div><b>Voice</b><small>Browser voice capabilities</small></div></div><div class="control-status-list"><span>Input</span><b>'+(window.SpeechRecognition||window.webkitSpeechRecognition?'Available':'Unavailable')+'</b><span>Speech</span><b>'+('speechSynthesis' in window?'Available':'Unavailable')+'</b></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">⚙</span><div><b>Tools</b><small>Runtime capabilities</small></div></div><div class="control-status-list" id="controlTools"><span>Tools</span><b>Checking…</b></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">↗</span><div><b>Connections</b><small>External services</small></div></div><div class="control-status-list"><span>SAARTHI API</span><b id="controlConnection">Checking…</b><span>External connectors</span><b>Not connected</b></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">◈</span><div><b>Security</b><small>Session safety</small></div></div><div class="control-status-list"><span>Transport</span><b>'+((location.protocol==='https:')?'HTTPS':'Browser connection')+'</b><span>Credentials</span><b>Not exposed</b><span>Execution</span><b>Server runtime</b></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">•</span><div><b>Notifications</b><small>Proactive alerts</small></div></div><div class="control-status-list"><span>Browser permission</span><b id="notificationState">'+('Notification' in window?Notification.permission:'Unavailable')+'</b></div><div class="control-actions"><button data-control-action="notifications">Enable notifications</button></div></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">○</span><div><b>Appearance</b><small>Adaptive workspace</small></div></div><label class="control-toggle"><span>Adaptive intelligence UI</span><input id="adaptiveUIToggle" type="checkbox" '+(adaptive?'checked':'')+'><i></i></label><label class="control-toggle"><span>Reduce motion</span><input id="reduceMotionToggle" type="checkbox" '+(savedMotion?'checked':'')+'><i></i></label></section>'+
        '<section class="control-card"><div class="control-card-head"><span class="control-icon">◇</span><div><b>Privacy</b><small>Browser-stored workspace data</small></div></div><div class="control-status-list"><span>Conversation history</span><b>Stored locally</b><span>Provider key</span><b>Server-side</b></div><div class="control-actions"><button data-control-action="clear-history">Clear local history</button></div></section>'+
      '</div>'+
      '<div class="control-foot">SAARTHI keeps capability routing automatic. Controls change the workspace, not the intelligence architecture.</div>'+
    '</div>';
    target.hidden=false;
    target.querySelector('.picker-close')?.addEventListener('click',closePickers);
    target.querySelector('#adaptiveUIToggle')?.addEventListener('change',e=>{localStorage.setItem('saarthi.adaptiveUI',e.target.checked?'1':'0');document.documentElement.dataset.adaptiveUi=e.target.checked?'on':'off';addActivity('Appearance updated',e.target.checked?'Adaptive intelligence UI on':'Adaptive intelligence UI off');});
    target.querySelector('#reduceMotionToggle')?.addEventListener('change',e=>{localStorage.setItem('saarthi.reduceMotion',e.target.checked?'1':'0');document.documentElement.classList.toggle('reduce-motion',e.target.checked);addActivity('Appearance updated',e.target.checked?'Reduced motion on':'Reduced motion off');});
    target.querySelectorAll('[data-control-action]').forEach(btn=>btn.addEventListener('click',async()=>{
      const action=btn.dataset.controlAction;
      if(action==='history'){closePickers();openHistory();return;}
      if(action==='clear-current'){if(confirm('Clear the current conversation?'))window.SaarthiApp.clearConversation();renderControlCenter();return;}
      if(action==='clear-history'){if(confirm('Clear all locally stored SAARTHI conversation history?')){localStorage.removeItem(HISTORY_KEY);historyState.assistants=Object.create(null);Object.keys(conversations).forEach(k=>{conversations[k]=[];currentThreads[k]=null;});document.body.classList.remove('chat-active');renderConversation();renderHistory();renderControlCenter();}return;}
      if(action==='notifications'){if('Notification' in window){try{await Notification.requestPermission();}catch{}renderControlCenter();}}
    }));
    try{
      const response=await fetch(apiUrl('/api/health'));const data=await response.json();
      const runtime=target.querySelector('#controlRuntimeState'),provider=target.querySelector('#controlProvider'),route=target.querySelector('#controlRoute'),conn=target.querySelector('#controlConnection'),tools=target.querySelector('#controlTools');
      if(runtime)runtime.textContent=data?.ok?'Online':'Unavailable';
      if(provider)provider.textContent=data?.provider_configured?'Configured':'Not configured';
      if(route)route.textContent=data?.ai_gateway_active_route||'—';
      if(conn)conn.textContent=data?.ok?'Connected':'Unavailable';
      if(tools)tools.innerHTML=Array.isArray(data?.tools)?'<span>Available tools</span><b>'+data.tools.length+'</b><div class="control-tool-tags">'+data.tools.map(x=>'<span>'+escapeHtml(String(x))+'</span>').join('')+'</div>':'<span>Tools</span><b>Unavailable</b>';
      const details=target.querySelector('#controlRuntimeDetails');if(details)details.innerHTML='<span>Engine</span><b>'+escapeHtml(data?.engine||'—')+'</b><span>Architecture</span><b>'+escapeHtml(data?.architecture||'—')+'</b>';
    }catch{const runtime=target.querySelector('#controlRuntimeState');if(runtime)runtime.textContent='Unavailable';const conn=target.querySelector('#controlConnection');if(conn)conn.textContent='Unavailable';}
  };

  const renderMenuRoot=()=>{
    const target=$('#menuPicker');if(!target)return;
    target.innerHTML='<div class="picker-panel menu-panel"><div class="picker-head"><div><div class="eyebrow">SAARTHI</div><h3>Menu</h3></div><button class="picker-close" aria-label="Close">×</button></div><div class="menu-options">'+
      '<button class="menu-option" data-new-root="true"><span class="menu-option-icon">＋</span><span><b>New conversation</b><small>Start with a clean Saarthi workspace.</small></span><span class="menu-option-arrow">›</span></button>'+
      '<button class="menu-option" data-history-root="true"><span class="menu-option-icon">☷</span><span><b>Conversation history</b><small>Search and reopen previous conversations.</small></span><span class="menu-option-arrow">›</span></button>'+
      '<button class="menu-option menu-option-featured" data-root-usage="true"><span class="menu-option-icon">◉</span><span><b>AI Usage</b><small>Live session tokens, requests and provider usage.</small></span><span class="menu-option-arrow">›</span></button>'+
      '<button class="menu-option" data-root-control="true"><span class="menu-option-icon">⌘</span><span><b>Control Center</b><small>Runtime, memory, voice, tools, security, privacy and appearance.</small></span><span class="menu-option-arrow">›</span></button>'+
    '</div></div>';
    closePickers();target.hidden=false;
    target.querySelector('.picker-close')?.addEventListener('click',closePickers);
    target.querySelector('[data-new-root]')?.addEventListener('click',startNewConversation);
    target.querySelector('[data-history-root]')?.addEventListener('click',()=>{closePickers();openHistory();});
    target.querySelector('[data-root-usage]')?.addEventListener('click',()=>{addActivity('AI Usage opened','Session telemetry');renderUsagePanel();});
    target.querySelector('[data-root-control]')?.addEventListener('click',renderControlCenter);
  };
  const renderPicker=(type)=>{
    const target=$(type==='assistants'?'#assistantPicker':'#controlPicker');if(!target)return;
    const items=type==='assistants'?ASSISTANTS:CONTROLS;
    target.innerHTML='<div class="picker-panel"><div class="picker-head"><div><div class="eyebrow">SAARTHI</div><h3>'+(type==='assistants'?'Choose capability':'Control Saarthi')+'</h3></div><button class="picker-close" aria-label="Close">×</button></div><div class="picker-grid">'+items.map(item=>'<button class="picker-item" data-picker-id="'+item.id+'"><span class="picker-icon">'+item.icon+'</span><span><b>'+item.name+'</b><small>'+item.description+'</small></span></button>').join('')+'</div></div>';
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
        else showResponse('### '+(CONTROLS.find(x=>x.id===id)?.name||'Control')+'\\n\\nThis control is available from the Saarthi Control Center.',{intent:{name:id},provider:'Saarthi'});
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
    if(id==='control') renderControlCenter();
    else renderPicker(id);
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
    attachmentsByAssistant[id]=attachmentsByAssistant[id]||[];
    const item=ASSISTANTS.find(x=>x.id===id)||ASSISTANTS[0];
    if(!item) return;

    currentAssistant=item.id;
    if($('#assistantName')) $('#assistantName').textContent=item.name;
    if($('#assistantSelectorIcon')) $('#assistantSelectorIcon').textContent=item.icon;
    if($('#coreAssistantLabel')) $('#coreAssistantLabel').textContent=item.name;

    applyAssistantEnvironment(item);
    attachmentsByAssistant[item.id]=attachmentsByAssistant[item.id]||[];
    loadConversation(item.id,true);
    ensureAttachmentControls();renderAttachmentTray();
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
      industry:null,
      conversation:currentConversation().map(({role,content})=>({role,content})),
      attachments:currentAttachments().map(({name,type,size,data})=>({name,type,size,data}))
    };
    let lastError=null;
    for(const base of API_BASES){
      try{
        await checkRuntimeHealth(base);
        const controller=new AbortController();
        const timeout=window.setTimeout(()=>controller.abort(),25000);
        let response;
        try{
          const payload=JSON.stringify({message:value,mode,assistant:currentAssistant,context});
        const target=new URL('/api/command',base);
        const crossOrigin=target.origin!==window.location.origin;
        const endpoint=crossOrigin?'/api/command/plain':'/api/command';
        response=await fetch(apiUrl(endpoint,base),{
            method:'POST',
            headers:{'Content-Type':crossOrigin?'text/plain':'application/json'},
            body:payload,
            signal:controller.signal
          });
        }finally{
          window.clearTimeout(timeout);
        }
        if(response.ok){
          API_BASE=base;
          return response.json();
        }
        lastError=new Error('API '+response.status+' from '+base);
      }catch(error){
        lastError=error;
      }
    }
    throw lastError||new Error('No cloud runtime configured');
  };

  const runCommand=async(value,mode)=>{
    updateIntelligenceFlow('running');
    setStatus('Routing…');setCoreState('routing','Request received.');await new Promise(r=>setTimeout(r,90));
    setStatus('Understanding…');setCoreState('understanding','Separating intent from noise.');
    const request=apiCommand(value,mode);await new Promise(r=>setTimeout(r,120));
    setStatus('Planning…');setCoreState('planning','Building an execution path.');
    const result=await request;if(!result?.ok)throw new Error('SAARTHI runtime rejected the command');
    clearRecoveredRuntimeErrors();
    const intent=result?.intent?.name||mode;setStatus('Verifying…');setCoreState('verifying','Checking the execution result.');
    await new Promise(r=>setTimeout(r,120));
    runs.unshift({id:result.run_id,intent,provider:result.provider,at:new Date().toISOString(),message:value});runs.splice(20);
    setStatus('Ready');setCoreState('ready','Saarthi has a response.');
    updateIntelligenceFlow('complete',result);
    addActivity('Run completed',result.run_id+' · '+intent+' · '+result.provider);
    showResponse(result.reply,result);
    return result;
  };

  const submit=async()=>{
    const value=command?.value.trim();
    if(!value||sendInFlight)return;
    sendInFlight=true;
    const sendButton=$('#sendCommand');
    if(sendButton){
      sendButton.disabled=true;
      sendButton.setAttribute('aria-busy','true');
      sendButton.textContent='…';
    }
    const mode=parseCommand(value);
    addActivity('Command received',currentAssistant+' · '+mode+' · '+value.replace(/^\/\w+\s*/,''));
    appendConversation('user',value);
    try{
      const result=await runCommand(value,mode);
      if(mode==='voice'||window.SaarthiApp.voiceTurn)speak(result.reply);
    }catch(error){
      updateIntelligenceFlow('idle');
      const detail=String(error?.message||'Cloud runtime unavailable.');
      const isHealthFailure=/Runtime health|Failed to fetch|NetworkError|aborted|AbortError/i.test(detail);
      setStatus(isHealthFailure?'Cloud unavailable':'Connection issue');
      setCoreState('offline',isHealthFailure?'Cloud runtime is unreachable.':'Cloud runtime request failed.');
      addActivity('Run failed',detail);
      showResponse(isHealthFailure
        ? '### Cloud runtime unavailable\n\nSAARTHI could not reach the cloud runtime. The message was not lost. Please try again when the connection is available.'
        : '### Connection issue\n\nSAARTHI could not complete this request. Please try again.',{intent:{name:'runtime'},provider:'unavailable'});
    }finally{
      window.SaarthiApp.voiceTurn=false;
      if(command)command.value='';
      if(sendButton){
        sendButton.disabled=false;
        sendButton.removeAttribute('aria-busy');
        sendButton.textContent='➤';
      }
      sendInFlight=false;
      setTimeout(()=>setStatus('Saarthi is present'),1200);
    }
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

  setAutonomousContext('Saarthi will determine the capability, industry and workflow from your objective.','AUTO');
  updateIntelligenceFlow('idle');
  loadHistory();
  // Always start on the clean home surface. Previous threads remain available
  // through Conversation history and are opened explicitly by the user.
  currentThreads.saarthi=null;
  conversations.saarthi=[];
  attachmentsByAssistant.saarthi=[];
  applyAssistantEnvironment(ASSISTANTS[0]);
  renderConversation();
  renderHistory();
  // Final startup guard: the home surface must be visible on a fresh session.
  const enforceFreshHomeSurface=()=>{
    const hasMessages=(conversations[currentAssistant]||[]).length>0;
    if(!hasMessages){
      document.body.classList.add('home-active');
      document.body.classList.remove('chat-active');
      if(responseCard) responseCard.hidden=true;
    }
  };
  enforceFreshHomeSurface();
  requestAnimationFrame(enforceFreshHomeSurface);
  window.setTimeout(enforceFreshHomeSurface,250);

  updateClock();setInterval(updateClock,1000);loadRuntimeConfig();ensureAttachmentControls();
  document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>ask(button.dataset.command)));
  document.querySelectorAll('[data-assistant-shortcut]').forEach(button=>button.addEventListener('click',()=>{
    const id=button.dataset.assistantShortcut;
    selectAssistant(id);
    addActivity('Capability selected',id);
  }));
  document.querySelectorAll('[data-menu]').forEach(button=>button.addEventListener('click',()=>selectMenu(button.dataset.menu)));
  $('#settingsButton')?.addEventListener('click',()=>renderMenuRoot());
  $('#mobileControlButton')?.addEventListener('click',()=>renderControlCenter());
  $('#sidebarNewConversation')?.addEventListener('click',startNewConversation);
  if(!document.querySelector('#historyTrigger')){
    const trigger=document.createElement('button');trigger.id='historyTrigger';trigger.className='history-trigger';trigger.type='button';trigger.setAttribute('aria-label','Conversation history');trigger.textContent='☷';
    document.querySelector('.top-actions')?.insertBefore(trigger,document.querySelector('#settingsButton'));
    trigger.addEventListener('click',openHistory);
  }
  $('#assistantSelector')?.addEventListener('click',()=>renderPicker('assistants'));
  document.addEventListener('click',event=>{if(!event.target.closest('.menu-picker,.assistant-picker,.control-picker,[data-menu],#settingsButton,#mobileControlButton,#assistantSelector'))closePickers();});
  const composerForm=$('#conversationComposer');
  composerForm?.addEventListener('submit',event=>{
    event.preventDefault();
    event.stopPropagation();
    submit();
  });
  $('#sendCommand')?.addEventListener('click',event=>{
    event.preventDefault();
    event.stopPropagation();
    submit();
  });
  $('#voiceCommand')?.addEventListener('click',event=>{event.preventDefault();voice();});
  window.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();selectMenu('command');command?.focus();}});

  window.SaarthiApp={menus:MENUS,assistants:ASSISTANTS,controls:CONTROLS,runs,ask,submit,voice,selectMenu,selectAssistant,getCurrentAssistant:()=>currentAssistant,clearConversation:assistant=>{const id=assistant||currentAssistant;const list=ensureAssistantHistory(id);attachmentsByAssistant[id]=[];const tid=currentThreads[id];const index=list.findIndex(t=>t.id===tid);if(index>=0)list.splice(index,1);currentThreads[id]=null;conversations[id]=[];saveHistory();if(id===currentAssistant){document.body.classList.remove('chat-active');renderConversation();renderHistory();}},startNewConversation,voiceTurn:false};
  return window.SaarthiApp;
})()
