const SaarthiApp = (() => {
  const $ = (s, root = document) => root.querySelector(s);
  const activity = $('#activityStream');
  const command = $('#saarthiCommand');
  const status = $('#presenceText');
  const liveDate = $('#liveDate');
  const liveDay = $('#liveDay');
  const liveTime = $('#liveTime');
  const liveLocation = $('#liveLocation');
  const liveWeather = $('#liveWeather');
  const liveTemp = $('#liveTemp');
  const greeting = $('#greeting');

  // Menu architecture is intentionally separated from presentation.
  // The visible navigation remains unchanged; these IDs define capabilities.
  const MENUS = Object.freeze({
    command: {
      label: 'Command',
      capabilities: ['chat', 'voice', 'tasks', 'actions']
    },
    home: {
      label: 'Home',
      capabilities: ['briefing', 'status', 'context']
    },
    insights: {
      label: 'Insights',
      capabilities: ['research', 'search', 'analyze', 'web']
    },
    journey: {
      label: 'Journey',
      capabilities: ['tasks', 'reminders', 'workflows', 'progress']
    },
    memory: {
      label: 'Memory',
      capabilities: ['remember', 'recall', 'knowledge']
    },
    settings: {
      label: 'Settings',
      capabilities: ['model', 'voice', 'privacy', 'connections']
    }
  });

  const COMMANDS = Object.freeze({
    '/help': 'help',
    '/research': 'research',
    '/search': 'search',
    '/analyze': 'analyze',
    '/remember': 'remember',
    '/recall': 'recall',
    '/tasks': 'tasks',
    '/remind': 'remind',
    '/workflows': 'workflows',
    '/briefing': 'briefing',
    '/system': 'system',
    '/settings': 'settings',
    '/voice': 'voice'
  });


  const WEATHER_URL = 'https://api.open-meteo.com/v1/forecast';

  const weatherDescription = code => {
    const map = {
      0: 'Clear sky',
      1: 'Mainly clear',
      2: 'Partly cloudy',
      3: 'Overcast',
      45: 'Fog',
      48: 'Rime fog',
      51: 'Light drizzle',
      53: 'Drizzle',
      55: 'Heavy drizzle',
      56: 'Freezing drizzle',
      57: 'Heavy freezing drizzle',
      61: 'Light rain',
      63: 'Rain',
      65: 'Heavy rain',
      66: 'Freezing rain',
      67: 'Heavy freezing rain',
      71: 'Light snow',
      73: 'Snow',
      75: 'Heavy snow',
      77: 'Snow grains',
      80: 'Light showers',
      81: 'Showers',
      82: 'Heavy showers',
      85: 'Snow showers',
      86: 'Heavy snow showers',
      95: 'Thunderstorm',
      96: 'Thunderstorm with hail',
      99: 'Thunderstorm with heavy hail'
    };
    return map[code] || 'Weather available';
  };

  const updateClock = () => {
    const now = new Date();
    const time = new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).format(now);
    const date = new Intl.DateTimeFormat('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric'
    }).format(now);
    const day = new Intl.DateTimeFormat('en-IN', { weekday: 'long' }).format(now);
    const hour = now.getHours();

    if (liveTime) liveTime.textContent = time;
    if (liveDate) liveDate.textContent = date;
    if (liveDay) liveDay.textContent = day + ' · local time';
    if (greeting) {
      const part = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : hour < 21 ? 'evening' : 'night';
      greeting.textContent = 'Good ' + part + ', Swapnil';
    }
  };

  const formatLocation = location => {
    const parts = [
      location?.city,
      location?.locality,
      location?.principalSubdivision
    ].filter(Boolean);
    const unique = [...new Set(parts)];
    return unique.slice(0, 2).join(', ') || 'Current location';
  };

  const fetchWeather = async (latitude, longitude) => {
    const url = new URL(WEATHER_URL);
    url.searchParams.set('latitude', latitude.toFixed(5));
    url.searchParams.set('longitude', longitude.toFixed(5));
    url.searchParams.set('timezone', 'auto');
    url.searchParams.set('current', [
      'temperature_2m',
      'relative_humidity_2m',
      'apparent_temperature',
      'weather_code',
      'wind_speed_10m'
    ].join(','));
    url.searchParams.set('hourly', 'precipitation_probability');
    url.searchParams.set('forecast_days', '1');

    const response = await fetch(url.toString(), { cache: 'no-store' });
    if (!response.ok) throw new Error('Weather API ' + response.status);
    return response.json();
  };

  const reverseGeocode = async (latitude, longitude) => {
    try {
      const url = new URL('https://api.bigdatacloud.net/data/reverse-geocode-client');
      url.searchParams.set('latitude', latitude);
      url.searchParams.set('longitude', longitude);
      url.searchParams.set('localityLanguage', 'en');
      const response = await fetch(url.toString(), { cache: 'no-store' });
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  };

  const renderLiveContext = async (latitude, longitude, source = 'device') => {
    try {
      const [weather, location] = await Promise.all([
        fetchWeather(latitude, longitude),
        reverseGeocode(latitude, longitude)
      ]);

      const current = weather.current || {};
      const humidity = current.relative_humidity_2m;
      const apparent = current.apparent_temperature;
      const condition = weatherDescription(current.weather_code);
      const wind = current.wind_speed_10m;
      const hourly = weather.hourly?.precipitation_probability || [];
      const currentHour = new Date().getHours();
      const rainChance = Number.isFinite(hourly[currentHour]) ? hourly[currentHour] : null;

      if (liveLocation) {
        const label = formatLocation(location);
        liveLocation.textContent = source === 'ip' ? label + ' · approximate' : label;
      }
      if (liveTemp) liveTemp.textContent = Number.isFinite(current.temperature_2m) ? Math.round(current.temperature_2m) + '°' : '--°';
      if (liveWeather) {
        const details = [
          condition,
          Number.isFinite(apparent) ? 'feels ' + Math.round(apparent) + '°' : null,
          Number.isFinite(humidity) ? humidity + '% humidity' : null,
          Number.isFinite(wind) ? Math.round(wind) + ' km/h wind' : null,
          Number.isFinite(rainChance) ? rainChance + '% rain' : null
        ].filter(Boolean);
        liveWeather.textContent = details.join(' · ');
      }
      return true;
    } catch {
      return false;
    }
  };

  const loadApproximateContext = async () => {
    try {
      const response = await fetch('https://ipapi.co/json/', { cache: 'no-store' });
      if (!response.ok) throw new Error('IP geolocation ' + response.status);
      const data = await response.json();
      const latitude = Number(data.latitude);
      const longitude = Number(data.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) throw new Error('Invalid coordinates');

      const rendered = await renderLiveContext(latitude, longitude, 'ip');
      if (!rendered) throw new Error('Weather unavailable');
    } catch {
      if (liveLocation) liveLocation.textContent = 'Location unavailable';
      if (liveWeather) liveWeather.textContent = 'Local weather unavailable.';
      if (liveTemp) liveTemp.textContent = '--°';
    }
  };

  const loadLiveContext = async () => {
    if (!navigator.geolocation) {
      await loadApproximateContext();
      return;
    }

    navigator.geolocation.getCurrentPosition(async position => {
      const rendered = await renderLiveContext(position.coords.latitude, position.coords.longitude, 'device');
      if (!rendered) await loadApproximateContext();
    }, async () => {
      // Graceful fallback: do not block the Home context when precise browser
      // location is unavailable or denied. Weather is based on approximate IP location.
      await loadApproximateContext();
    }, {
      enableHighAccuracy: false,
      maximumAge: 300000,
      timeout: 10000
    });
  };

  updateClock();
  setInterval(updateClock, 1000);
  loadLiveContext();
  setInterval(loadLiveContext, 15 * 60 * 1000);

  const addActivity = (title, detail) => {
    if (!activity) return;
    const item = document.createElement('div');
    item.className = 'signal';
    item.innerHTML = '<i></i><div><b></b><span></span></div><time>now</time>';
    item.querySelector('b').textContent = title;
    item.querySelector('span').textContent = detail;
    activity.prepend(item);
  };

  const setStatus = value => {
    if (status) status.textContent = value;
  };

  const selectMenu = menuId => {
    const id = MENUS[menuId] ? menuId : 'command';
    document.querySelectorAll('[data-nav]').forEach(button => {
      button.classList.toggle('active', button.dataset.nav === id);
    });
    const menu = MENUS[id];
    addActivity('Menu selected', menu.label + ' · ' + menu.capabilities.join(' · '));
    return menu;
  };

  const ask = value => {
    if (!command) return;
    command.value = value;
    command.focus();
    document.querySelector('.core-panel')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const parseCommand = value => {
    const token = value.trim().split(/\s+/)[0].toLowerCase();
    return COMMANDS[token] || 'chat';
  };

  const apiCommand = async (value, mode) => {
    try {
      const response = await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value, mode })
      });
      if (!response.ok) throw new Error('API ' + response.status);
      return await response.json();
    } catch {
      return null;
    }
  };

  const submit = async () => {
    const value = command?.value.trim();
    if (!value) return;

    const mode = parseCommand(value);
    addActivity('Command received', mode + ' · ' + value.replace(/^\/\w+\s*/, ''));
    setStatus('Saarthi is thinking');
    command.disabled = true;

    const result = await apiCommand(value, mode);

    if (result?.reply) {
      addActivity('Saarthi response', result.reply);
    } else {
      addActivity('Cloud adapter ready', 'Command routed to ' + mode + '. Connect the cloud provider adapter for execution.');
    }

    command.value = '';
    command.disabled = false;
    setStatus('Saarthi is present');
  };

  const voice = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      addActivity('Voice unavailable', 'This browser does not expose speech recognition.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setStatus('Listening…');
    recognition.onresult = e => {
      ask(e.results[0][0].transcript);
      setStatus('Command ready');
    };
    recognition.onerror = () => setStatus('Saarthi is present');
    recognition.onend = () => {
      if (status && status.textContent === 'Listening…') setStatus('Saarthi is present');
    };
    recognition.start();
  };

  document.querySelectorAll('[data-command]').forEach(button => {
    button.addEventListener('click', () => ask(button.dataset.command));
  });

  document.querySelectorAll('[data-nav]').forEach(button => {
    button.addEventListener('click', () => selectMenu(button.dataset.nav));
  });

  $('#settingsButton')?.addEventListener('click', () => selectMenu('settings'));
  $('#sendCommand')?.addEventListener('click', submit);
  $('#voiceCommand')?.addEventListener('click', voice);
  command?.addEventListener('keydown', event => {
    if (event.key === 'Enter') submit();
  });

  // JARVIS-style command discovery without changing the visual UI.
  window.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      selectMenu('command');
      command?.focus();
    }
  });

  window.SaarthiApp = {
    menus: MENUS,
    commands: COMMANDS,
    ask,
    submit,
    voice,
    selectMenu
  };

  return window.SaarthiApp;
})();