const SaarthiApp = (() => {
  const $ = (s, root = document) => root.querySelector(s);
  const activity = $('#activityStream');
  const command = $('#saarthiCommand');
  const status = $('#presenceText');
  const liveDay = $('#liveDay'), liveLow = $('#liveLow'), liveHigh = $('#liveHigh');
  const weatherSymbol = $('#weatherSymbol'), topClock = $('#topClock');
  const liveLocation = $('#liveLocation'), liveWeather = $('#liveWeather'), liveTemp = $('#liveTemp');
  const greeting = $('#greeting'), coreStatus = $('.core-status');
  const responseCard = $('#assistantResponse'), responseBody = $('#assistantResponseBody'), responseMeta = $('#assistantResponseMeta');
  const runs = [];

  const MENUS = Object.freeze({
    command:{label:'Command',capabilities:['chat','voice','tasks','actions','runs']},
    home:{label:'Home',capabilities:['briefing','status','context']},
    insights:{label:'Insights',capabilities:['research','search','analyze','web','sources']},
    journey:{label:'Journey',capabilities:['tasks','reminders','workflows','progress']},
    memory:{label:'Memory',capabilities:['remember','recall','knowledge','preferences']},
    settings:{label:'Settings',capabilities:['model','voice','privacy','connections','permissions']}
  });
  const COMMANDS = Object.freeze({
    '/help':'help','/research':'research','/search':'search','/analyze':'analyze','/plan':'plan',
    '/remember':'remember','/recall':'recall','/tasks':'tasks','/task':'task','/remind':'remind',
    '/workflow':'workflow','/workflows':'workflows','/briefing':'briefing','/system':'system',
    '/settings':'settings','/voice':'voice'
  });
  const WEATHER_URL='https://api.open-meteo.com/v1/forecast';
  let API_BASE='';
  const loadRuntimeConfig=async()=>{
    try{
      const response=await fetch('./config/runtime.json?ts='+Date.now(),{cache:'no-store'});
      if(response.ok){
        const config=await response.json();
        API_BASE=String(config.api_base_url||'').replace(/\\/$/,'');
      }
    }catch{}
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
    if(topClock)topClock.textContent=new Intl.DateTimeFormat('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(now);
    if(liveDay)liveDay.textContent=new Intl.DateTimeFormat('en-IN',{weekday:'long'}).format(now)+' · local time';
    if(greeting){const h=now.getHours();const p=h<12?'morning':h<17?'afternoon':h<21?'evening':'night';greeting.textContent='Good '+p+', Swapnil';}
  };

  const formatLocation=location=>{
    const parts=[location?.city,location?.locality,location?.principalSubdivision].filter(Boolean);
    return [...new Set(parts)].slice(0,2).join(', ')||'Current location';
  };

  const fetchWeather=async(latitude,longitude)=>{
    const url=new URL(WEATHER_URL);
    url.searchParams.set('latitude',latitude.toFixed(5));url.searchParams.set('longitude',longitude.toFixed(5));
    url.searchParams.set('timezone','auto');
    url.searchParams.set('current','temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m');
    url.searchParams.set('hourly','precipitation_probability');url.searchParams.set('daily','temperature_2m_max,temperature_2m_min');
    url.searchParams.set('forecast_days','1');
    const response=await fetch(url.toString(),{cache:'no-store'});if(!response.ok)throw new Error('Weather API '+response.status);return response.json();
  };

  const reverseGeocode=async(latitude,longitude)=>{
    try{const url=new URL('https://api.bigdatacloud.net/data/reverse-geocode-client');url.searchParams.set('latitude',latitude);url.searchParams.set('longitude',longitude);url.searchParams.set('localityLanguage','en');const response=await fetch(url.toString(),{cache:'no-store'});return response.ok?await response.json():null;}catch{return null;}
  };

  const renderLiveContext=async(latitude,longitude,source='device',explicitLocation=null)=>{
    try{
      const [weather,location]=await Promise.all([fetchWeather(latitude,longitude),source==='device'?reverseGeocode(latitude,longitude):Promise.resolve(null)]);
      const current=weather.current||{},daily=weather.daily||{},apparent=current.apparent_temperature;
      if(liveLocation)liveLocation.textContent=source==='ip'?(explicitLocation||'Approximate location')+' · approximate':(explicitLocation||formatLocation(location));
      if(liveTemp)liveTemp.textContent=Number.isFinite(current.temperature_2m)?Math.round(current.temperature_2m)+'°':'--°';
      if(liveLow)liveLow.textContent=Number.isFinite(daily.temperature_2m_min?.[0])?Math.round(daily.temperature_2m_min[0])+'°':'--°';
      if(liveHigh)liveHigh.textContent=Number.isFinite(daily.temperature_2m_max?.[0])?Math.round(daily.temperature_2m_max[0])+'°':'--°';
      if(weatherSymbol)weatherSymbol.textContent=weatherIcon(current.weather_code);
      if(liveWeather)liveWeather.textContent=weatherDescription(current.weather_code)+(Number.isFinite(apparent)?' · feels '+Math.round(apparent)+'°':'');
      return true;
    }catch{return false;}
  };

  const loadApproximateContext=async()=>{
    try{
      const response=await fetch('https://ipwho.is/',{cache:'no-store'});if(!response.ok)throw new Error('IP geolocation '+response.status);
      const data=await response.json();if(!data.success)throw new Error(data.message||'IP geolocation failed');
      const latitude=Number(data.latitude),longitude=Number(data.longitude);
      if(!Number.isFinite(latitude)||!Number.isFinite(longitude))throw new Error('Invalid coordinates');
      const label=[String(data.city||'').trim(),String(data.region||data.region_code||'').trim()].filter(Boolean).join(', ')||String(data.country||'').trim()||'Approximate location';
      if(!await renderLiveContext(latitude,longitude,'ip',label))throw new Error('Weather unavailable');
    }catch{if(liveLocation)liveLocation.textContent='Approximate location unavailable';if(liveWeather)liveWeather.textContent='Local weather unavailable.';if(liveTemp)liveTemp.textContent='--°';}
  };

  const loadLiveContext=async()=>{
    if(!navigator.geolocation)return loadApproximateContext();
    navigator.geolocation.getCurrentPosition(async position=>{
      if(!await renderLiveContext(position.coords.latitude,position.coords.longitude,'device'))await loadApproximateContext();
    },loadApproximateContext,{enableHighAccuracy:true,maximumAge:0,timeout:15000});
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

  const showResponse=(reply,result)=>{
    if(!responseCard||!responseBody)return;
    responseBody.innerHTML=renderMarkdown(reply||'Command completed.');
    if(responseMeta){
      const intent=result?.intent?.name||'chat';
      const provider=result?.provider||'runtime';
      responseMeta.textContent='SAARTHI RESPONSE · '+intent.toUpperCase()+' · '+provider;
    }
    responseCard.hidden=false;
    responseCard.scrollIntoView({behavior:'smooth',block:'nearest'});
  };

  const speak=text=>{
    if(!window.speechSynthesis||!text)return;window.speechSynthesis.cancel();
    const utterance=new SpeechSynthesisUtterance(text.replace(/[#*_]/g,''));
    utterance.lang='en-IN';utterance.rate=.98;utterance.pitch=.92;window.speechSynthesis.speak(utterance);
  };

  const selectMenu=menuId=>{
    const id=MENUS[menuId]?menuId:'command';
    document.querySelectorAll('[data-nav]').forEach(button=>button.classList.toggle('active',button.dataset.nav===id));
    const menu=MENUS[id];addActivity('Menu selected',menu.label+' · '+menu.capabilities.join(' · '));return menu;
  };

  const ask=value=>{
    if(!command)return;command.value=value;command.focus();
    document.querySelector('.core-panel')?.scrollIntoView({behavior:'smooth',block:'center'});
  };

  const parseCommand=value=>{const token=value.trim().split(/\s+/)[0].toLowerCase();return COMMANDS[token]||'chat';};

  const apiCommand=async(value,mode)=>{
    const context={client_time:new Date().toISOString(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Kolkata',locale:navigator.language||'en-IN'};
    const response=await fetch(apiUrl('/api/command'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:value,mode,context})});
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
    const mode=parseCommand(value);addActivity('Command received',mode+' · '+value.replace(/^\/\w+\s*/,''));
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

  updateClock();setInterval(updateClock,1000);loadRuntimeConfig().then(loadLiveContext);setInterval(loadLiveContext,15*60*1000);
  document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>ask(button.dataset.command)));
  document.querySelectorAll('[data-nav]').forEach(button=>button.addEventListener('click',()=>selectMenu(button.dataset.nav)));
  $('#settingsButton')?.addEventListener('click',()=>selectMenu('settings'));$('#sendCommand')?.addEventListener('click',submit);$('#voiceCommand')?.addEventListener('click',voice);
  command?.addEventListener('keydown',event=>{if(event.key==='Enter')submit();});
  window.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();selectMenu('command');command?.focus();}});

  window.SaarthiApp={menus:MENUS,commands:COMMANDS,runs,ask,submit,voice,selectMenu,voiceTurn:false};
  return window.SaarthiApp;
})();