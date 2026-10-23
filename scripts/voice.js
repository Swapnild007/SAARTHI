(() => {
  'use strict';
  const KEY='saarthi.voice.v1';
  let prefs={language:'en-IN',muted:false}, recognition=null, generation=0;
  try{const saved=JSON.parse(localStorage.getItem(KEY)||'{}');if(['en-IN','hi-IN','mr-IN'].includes(saved.language))prefs.language=saved.language;prefs.muted=saved.muted===true;}catch{}
  const status=document.createElement('p');status.className='voice-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  document.querySelector('#conversationComposer')?.append(status);
  function announce(text){status.textContent=text;}
  function stop(){generation++;if(recognition){recognition.abort();recognition=null;}window.speechSynthesis?.cancel();if(window.SaarthiDevice?.native)void window.SaarthiDevice.execute('stopSpeech');window.SaarthiApp&&(window.SaarthiApp.voiceTurn=false);document.getElementById('voiceCommand')?.setAttribute('aria-pressed','false');announce('Voice stopped.');}
  function configure(values){stop();if(['en-IN','hi-IN','mr-IN'].includes(values.language))prefs.language=values.language;if(typeof values.muted==='boolean')prefs.muted=values.muted;localStorage.setItem(KEY,JSON.stringify(prefs));announce(prefs.muted?'Spoken replies muted.':'Voice preferences saved.');}
  async function speak(text){
    window.speechSynthesis?.cancel();
    if(prefs.muted||!text)return;
    const cleaned=String(text).replace(/[#*_`]/g,'').slice(0,3500);
    if(window.SaarthiDevice?.native){const result=await window.SaarthiDevice.execute('speak',{text:cleaned,language:prefs.language});if(!result.ok)announce(result.message);return;}
    if(!window.speechSynthesis){announce('Spoken replies are unavailable in this browser.');return;}
    const utterance=new SpeechSynthesisUtterance(cleaned);utterance.lang=prefs.language;utterance.rate=.98;
    utterance.onerror=e=>{if(!['interrupted','canceled'].includes(e.error))announce('Speech output failed. Your response is available in chat.');};
    window.speechSynthesis.speak(utterance);
  }
  async function start(){
    if(recognition){stop();return;}
    stop();const token=++generation;
    const input=document.getElementById('saarthiCommand');
    const deliver=text=>{if(token!==generation||!text.trim())return;window.SaarthiApp.voiceTurn=true;window.SaarthiApp.ask(text.trim());announce('Transcript: '+text.trim());window.SaarthiApp.submit();};
    document.getElementById('voiceCommand')?.setAttribute('aria-pressed','true');
    if(window.SaarthiDevice?.native){announce('Opening Android speech input…');const result=await window.SaarthiDevice.execute('listen',{language:prefs.language});document.getElementById('voiceCommand')?.setAttribute('aria-pressed','false');if(token!==generation)return;if(result.ok)deliver(result.data.transcript);else announce(result.message);return;}
    const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!Recognition){announce('Speech input is unavailable here. Type your request or use native Android speech.');input?.focus();return;}
    recognition=new Recognition();recognition.lang=prefs.language;recognition.interimResults=true;recognition.maxAlternatives=1;
    recognition.onstart=()=>announce('Listening… Tap the microphone or Stop voice to cancel.');
    recognition.onresult=event=>{
      if(token!==generation)return;
      let final='',interim='';for(let i=event.resultIndex;i<event.results.length;i++){if(event.results[i].isFinal)final+=event.results[i][0].transcript;else interim+=event.results[i][0].transcript;}
      if(input)input.value=final||interim;
      if(final){recognition?.stop();deliver(final);}
    };
    recognition.onerror=event=>{if(token===generation)announce(event.error==='not-allowed'?'Microphone permission denied. Enable it in browser settings and try again.':event.error==='no-speech'?'No speech detected. Try the microphone again.':'Speech recognition failed. Check your connection or type your request.');};
    recognition.onend=()=>{recognition=null;document.getElementById('voiceCommand')?.setAttribute('aria-pressed','false');};
    try{recognition.start();}catch{recognition=null;announce('Microphone is busy. Try again.');}
  }
  addEventListener('pagehide',stop);
  window.SaarthiVoice={start,stop,speak,configure,preferences:()=>({...prefs})};
})();
