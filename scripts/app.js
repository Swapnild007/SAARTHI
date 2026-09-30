const SaarthiApp = (() => {
  const $ = (s,root=document) => root.querySelector(s);
  const messages = $('#activityStream');
  const command = $('#saarthiCommand');
  const status = $('#presenceText');

  const addActivity = (title, detail) => {
    if (!messages) return;
    const item = document.createElement('div');
    item.className = 'signal';
    item.innerHTML = '<i></i><div><b></b><span></span></div><time>now</time>';
    item.querySelector('b').textContent = title;
    item.querySelector('span').textContent = detail;
    messages.prepend(item);
  };

  const ask = (value) => {
    if (!command) return;
    command.value = value;
    command.focus();
    document.querySelector('.core-panel')?.scrollIntoView({behavior:'smooth',block:'center'});
  };

  const submit = () => {
    const value = command?.value.trim();
    if (!value) return;
    addActivity('Command received', value);
    if (status) status.textContent = 'Saarthi is thinking';
    setTimeout(() => {
      addActivity('Saarthi ready', 'Cloud reasoning is ready for the next step.');
      if (status) status.textContent = 'Saarthi is present';
    }, 650);
    command.value = '';
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
    recognition.onstart = () => { if(status) status.textContent='Listening…'; };
    recognition.onresult = e => { ask(e.results[0][0].transcript); if(status) status.textContent='Command ready'; };
    recognition.onerror = () => { if(status) status.textContent='Saarthi is present'; };
    recognition.onend = () => { if(status && status.textContent==='Listening…') status.textContent='Saarthi is present'; };
    recognition.start();
  };

  document.querySelectorAll('[data-command]').forEach(btn => btn.addEventListener('click', () => ask(btn.dataset.command)));
  document.querySelectorAll('[data-nav]').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('[data-nav]').forEach(x => x.classList.remove('active'));
    btn.classList.add('active');
  }));
  $('#sendCommand')?.addEventListener('click', submit);
  $('#voiceCommand')?.addEventListener('click', voice);
  command?.addEventListener('keydown', e => { if(e.key === 'Enter') submit(); });

  window.SaarthiApp = {ask, submit, voice};
  return window.SaarthiApp;
})();