(() => {
  'use strict';
  const KEY='saarthi.tasks.v1',eventName='saarthi-reminder';
  const read=()=>{try{const tasks=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(tasks)?tasks:[];}catch{return [];}};
  const write=tasks=>localStorage.setItem(KEY,JSON.stringify(tasks));
  const native=()=>window.SaarthiDevice?.native;
  async function list(){if(!native())return read();const r=await window.SaarthiDevice.execute('tasks');if(!r.ok)throw Error(r.message);return r.data.tasks;}
  async function create({text,at,repeat='once'}){
    text=String(text||'').trim();at=Number(at);
    if(!text||text.length>500||!Number.isFinite(at)||at<=Date.now()||at-Date.now()>366*86400000||!['once','daily'].includes(repeat))throw Error('Choose a future time within one year, reminder text under 500 characters, and a supported repeat.');
    const task={id:crypto.randomUUID(),text,at,repeat,status:'scheduled'};
    if(native()){
      const notifications=window.SaarthiDevice.plugin('LocalNotifications');
      if((await notifications.requestPermissions()).display!=='granted')throw Error('Notification permission denied. No reminder was scheduled.');
      const result=await window.SaarthiDevice.execute('schedule',task);if(!result.ok)throw Error(result.message);return result.data.task;
    }
    const tasks=read();if(tasks.length>=200)throw Error('Remove an older reminder before adding more.');tasks.push(task);write(tasks);return task;
  }
  async function cancel(id){
    if(native()){const result=await window.SaarthiDevice.execute('cancelTask',{id});if(!result.ok)throw Error(result.message);}
    else write(read().filter(t=>t.id!==id));
  }
  async function tick(now=Date.now()){
    if(native()||!navigator.locks)return;
    await navigator.locks.request('saarthi-reminder-delivery',{ifAvailable:true},async lock=>{
      if(!lock)return;
      const tasks=read(),due=tasks.filter(t=>t.status==='scheduled'&&t.at<=now);
      if(!due.length)return;
      for(const task of due){task.lastDeliveredAt=now;if(task.repeat==='daily'){task.at+= (Math.floor((now-task.at)/86400000)+1)*86400000;}else task.status='delivered';}
      // Persist the claim before side effects. No repeat on reload or a second tab.
      // A process crash here can miss delivery; we do not claim exactly-once notification.
      write(tasks);
      for(const task of due){
        dispatchEvent(new CustomEvent(eventName,{detail:{...task}}));
        if('Notification' in window&&Notification.permission==='granted')try{new Notification('SAARTHI reminder',{body:task.text,tag:'saarthi-'+task.id});}catch{}
      }
    });
  }
  async function permission(){if(native())return (await window.SaarthiDevice.plugin('LocalNotifications').requestPermissions()).display;if(!('Notification'in window))return 'unsupported';return Notification.requestPermission();}
  function parse(text){
    const match=/^remind me in (\d+)\s*(seconds?|minutes?|hours?|days?) to (.{1,500})$/i.exec(text.trim());
    if(!match)return null;
    const factor={s:1000,m:60000,h:3600000,d:86400000}[match[2][0].toLowerCase()];
    return {text:match[3],at:Date.now()+Number(match[1])*factor,repeat:'once'};
  }
  setInterval(()=>tick().catch(()=>{}),15000);addEventListener('focus',()=>tick().catch(()=>{}));addEventListener('online',()=>tick().catch(()=>{}));
  window.SaarthiAutomation={list,create,cancel,tick,permission,parse};
})();
