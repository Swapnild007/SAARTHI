/* Bounded, deterministic offline utilities. No eval or generated code execution. */
(function(root){
  function calculate(source){
    let value=source.replace(/^.*?\b(?:calculate|calculator|compute|what is)\b/i,'').trim().replace(/[?:]$/,'');
    value=value.replace(/(-?\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+(-?\d+(?:\.\d+)?)/i,'($1 / 100 * $2)').replace(/[×x]/g,'*').replace(/÷/g,'/');
    if(value.length>200||!/^[\d\s.+*/%()\-]+$/.test(value))throw Error('Enter arithmetic such as (12 + 8) * 3 or 15% of 200.');
    const tokens=value.match(/\d+(?:\.\d*)?|\.\d+|[()+*/%\-]/g)||[];let at=0,steps=0;
    const safe=n=>{if(!Number.isFinite(n)||Math.abs(n)>1e100)throw Error('Calculation is undefined or too large.');return n;};
    function atom(){if(++steps>80)throw Error('Calculation is too complex.');const token=tokens[at++];if(token==='+'||token==='-')return atom()*(token==='-'?-1:1);if(token==='('){const n=expr();if(tokens[at++]!==')')throw Error('Unbalanced parentheses.');return n;}if(!token||!/^\d|^\.\d/.test(token))throw Error('Invalid expression.');return safe(Number(token));}
    function term(){let n=atom();while(['*','/','%'].includes(tokens[at])){const op=tokens[at++],b=atom();n=safe(op==='*'?n*b:op==='/'?n/b:n%b);}return n;}
    function expr(){let n=term();while(['+','-'].includes(tokens[at])){const op=tokens[at++],b=term();n=safe(op==='+'?n+b:n-b);}return n;}
    const result=expr();if(at!==tokens.length)throw Error('Invalid expression.');return {expression:value,value:result};
  }
  function run(message){
    const result={ok:true,run_id:'offline-'+Date.now(),provider:'browser-local',execution:'completed',tool_results:{},intent:{name:'chat'}};
    if(/\b(calculate|calculator|compute)\b|\d\s*[+*/×-]\s*\d|\d\s*%\s*of/i.test(message)){
      result.intent.name='calculate';try{const c=calculate(message);result.tool_results['system.calculate']=c;result.reply=c.expression+' = '+c.value;}catch(error){result.reply=error.message;result.execution='invalid-input';}return result;
    }
    if(/^(?:what(?:'s| is)? (?:the )?(?:current )?time(?: is it)?|time now|tell me the time)[?.!]?$/i.test(message.trim())){result.intent.name='time';result.reply='Your device time is '+new Date().toLocaleTimeString()+' ('+Intl.DateTimeFormat().resolvedOptions().timeZone+').';return result;}
    if(/^(?:what(?:'s| is)? (?:today(?:'s)? )?date|what day is today)[?.!]?$/i.test(message.trim())){result.intent.name='date';result.reply='Your device date is '+new Date().toLocaleDateString()+'.';return result;}
    result.execution='offline-unavailable';result.reply='You are offline. Your message is saved locally. AI chat requires a connection and a configured provider; history, knowledge search, calculator, time and date remain available.';return result;
  }
  root.SaarthiOffline={calculate,run};
})(typeof window==='undefined'?globalThis:window);
