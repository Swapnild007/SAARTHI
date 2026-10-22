'use strict';
const CACHE='saarthi-shell-v1';
const SHELL=['/','/styles/app.css','/styles/workspace.css','/scripts/app.js?v=20261012-01','/scripts/boot.js?v=20261005-22','/scripts/workspace.js','/scripts/utilities.js','/config/runtime.json','/manifest.webmanifest','/assets/icon-192.png','/assets/icon-512.png','/appforge','/appforge/app.css','/appforge/app.js'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('saarthi-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url);
 if(e.request.method!=='GET'||u.origin!==location.origin||u.pathname.startsWith('/api/'))return;
 if(e.request.mode==='navigate'){
   e.respondWith(fetch(e.request).catch(()=>caches.match(u.pathname==='/appforge' ? '/appforge':'/')));return;
 }
 // Only the explicit public shell allowlist is cached; never documents or arbitrary responses.
 if(SHELL.includes(u.pathname+u.search)||SHELL.includes(u.pathname))e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(cached=>cached||fetch(e.request)));
});
