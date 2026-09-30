const SaarthiApp = (() => {
  const $ = (s, root = document) => root.querySelector(s);
  const activity = $('#activityStream');
  const command = $('#saarthiCommand');
  const status = $('#presenceText');

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