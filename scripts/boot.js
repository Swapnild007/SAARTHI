(() => {
  const clock = document.getElementById('topClock');
  const greeting = document.getElementById('greeting');
  const liveDay = document.getElementById('liveDay');
  const liveLow = document.getElementById('liveLow');
  const liveHigh = document.getElementById('liveHigh');
  const liveLocation = document.getElementById('liveLocation');
  const liveWeather = document.getElementById('liveWeather');
  const liveTemp = document.getElementById('liveTemp');
  const weatherSymbol = document.getElementById('weatherSymbol');
  const input = document.getElementById('saarthiCommand');
  const send = document.getElementById('sendCommand');

  const tick = () => {
    const now = new Date();
    if (clock) clock.textContent = new Intl.DateTimeFormat('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(now);
    if (liveDay) liveDay.textContent = new Intl.DateTimeFormat('en-IN',{weekday:'long'}).format(now) + ' · local time';
    if (greeting) {
      const h = now.getHours();
      greeting.textContent = 'Good ' + (h < 12 ? 'morning' : h < 17 ? 'afternoon' : h < 21 ? 'evening' : 'night') + ', Swapnil';
    }
  };
  tick();
  setInterval(tick,1000);

  const icon = code => code === 0 ? '☀︎' : [1,2].includes(code) ? '⛅' : [3,45,48].includes(code) ? '☁︎' : [95,96,99].includes(code) ? '⚡' : [71,73,75,77,85,86].includes(code) ? '❄︎' : '☔';
  const description = code => ({0:'Clear sky',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Rime fog',51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',80:'Light showers',81:'Showers',82:'Heavy showers',95:'Thunderstorm',96:'Thunderstorm with hail',99:'Thunderstorm with heavy hail'}[code] || 'Weather available');

  async function weather(lat,lon,label) {
    const u = new URL('https://api.open-meteo.com/v1/forecast');
    u.searchParams.set('latitude',lat); u.searchParams.set('longitude',lon);
    u.searchParams.set('timezone','auto'); u.searchParams.set('current','temperature_2m,apparent_temperature,weather_code');
    u.searchParams.set('daily','temperature_2m_max,temperature_2m_min'); u.searchParams.set('forecast_days','1');
    const r = await fetch(u,{cache:'no-store'}); if(!r.ok) throw new Error('weather '+r.status);
    const d = await r.json(), c=d.current||{}, day=d.daily||{};
    if(liveLocation) liveLocation.textContent=label;
    if(liveTemp) liveTemp.textContent=Number.isFinite(c.temperature_2m)?Math.round(c.temperature_2m)+'°':'--°';
    if(liveLow) liveLow.textContent=Number.isFinite(day.temperature_2m_min?.[0])?Math.round(day.temperature_2m_min[0])+'°':'--°';
    if(liveHigh) liveHigh.textContent=Number.isFinite(day.temperature_2m_max?.[0])?Math.round(day.temperature_2m_max[0])+'°':'--°';
    if(weatherSymbol) weatherSymbol.textContent=icon(c.weather_code);
    if(liveWeather) liveWeather.textContent=description(c.weather_code)+(Number.isFinite(c.apparent_temperature)?' · feels '+Math.round(c.apparent_temperature)+'°':'');
  }

  async function loadContext() {
    try {
      if (navigator.geolocation) {
        const pos = await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,maximumAge:0,timeout:12000}));
        let label='Current location';
        try {
          const r=await fetch('https://api.bigdatacloud.net/data/reverse-geocode-client?latitude='+encodeURIComponent(pos.coords.latitude)+'&longitude='+encodeURIComponent(pos.coords.longitude)+'&localityLanguage=en',{cache:'no-store'});
          if(r.ok){const d=await r.json(); label=[d.city,d.locality,d.principalSubdivision].filter(Boolean).slice(0,2).join(', ')||label;}
        } catch {}
        await weather(pos.coords.latitude,pos.coords.longitude,label);
        return;
      }
    } catch {}
    const r=await fetch('https://ipwho.is/',{cache:'no-store'}); if(!r.ok) throw new Error('location');
    const d=await r.json(); if(!d.success) throw new Error('location');
    await weather(Number(d.latitude),Number(d.longitude),[d.city,d.region].filter(Boolean).join(', ')+' · approximate');
  }
  loadContext().catch(()=>{ if(liveLocation)liveLocation.textContent='Weather location unavailable'; if(liveWeather)liveWeather.textContent='Local weather unavailable'; });

  const fallbackSend = async () => {
    const value=input?.value.trim(); if(!value) return;
    const cfg=await fetch('./config/runtime.json?ts='+Date.now(),{cache:'no-store'}).then(r=>r.json());
    const base=String(cfg.api_base_url||'').replace(/\/$/,'');
    const mode=(value.match(/^\/([a-z]+)/i)||[])[1]||'chat';
    send.disabled=true;
    try {
      const r=await fetch(base+'/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:value,mode,context:{client_time:new Date().toISOString(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Kolkata'}})});
      if(!r.ok) throw new Error('API '+r.status);
      const data=await r.json();
      const p=document.querySelector('.chat-strip p');
      if(p) p.innerHTML='<b>'+String(data.reply||'Command completed.').replace(/</g,'&lt;')+'</b>';
      input.value='';
    } catch(e) {
      const p=document.querySelector('.chat-strip p');
      if(p) p.innerHTML='<b>SAARTHI cloud connection failed.</b> '+String(e.message||'Please retry.');
    } finally { send.disabled=false; }
  };

  if (send) send.addEventListener('click', () => {
    if (window.SaarthiApp?.submit) window.SaarthiApp.submit();
    else fallbackSend();
  });
  input?.addEventListener('keydown',e=>{if(e.key==='Enter' && !window.SaarthiApp?.submit) fallbackSend();});
})();

  // Splash lifecycle moved here so production CSP can keep script-src self.
  const splash = document.getElementById('sudarshanSplash');
  const splashVideo = document.getElementById('saarthiSplashVideo');
  const fallback = document.getElementById('splashFallbackBrand');
  if (fallback) fallback.style.display = 'none';
  let splashClosed = false;
  const closeSplash = () => {
    if (splashClosed) return;
    splashClosed = true;
    splash?.classList.add('hide');
  };
  const showFallback = (delay = 900) => {
    if (fallback) fallback.style.display = 'grid';
    window.setTimeout(closeSplash, delay);
  };
  splashVideo?.addEventListener('error', () => showFallback());
  splashVideo?.addEventListener('ended', closeSplash);
  if (splashVideo) {
    splashVideo.play?.().catch(() => showFallback());
  } else {
    closeSplash();
  }
  window.setTimeout(closeSplash, 6000);
