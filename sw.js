'use strict';
const CACHE = 'saarthi-shell-v2';
const SHELL = ['/', '/styles/app.css', '/styles/workspace.css', '/scripts/app.js?v=20261012-01', '/scripts/boot.js?v=20261005-22', '/scripts/workspace.js', '/scripts/utilities.js', '/config/runtime.json', '/manifest.webmanifest', '/assets/devanagari.woff2', '/assets/icon-192.png', '/assets/icon-512.png', '/appforge', '/appforge/app.css', '/appforge/app.js'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('saarthi-shell-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  // API failures belong to the caller. Never cache API requests, uploads or credentials.
  if (event.request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    if (event.request.mode === 'navigate') {
      try { return await fetch(event.request); }
      catch { return await cache.match(url.pathname.replace(/\/$/, '') === '/appforge' ? '/appforge' : '/') || new Response('Offline shell unavailable. Load SAARTHI online once.', {status: 503}); }
    }
    // Normalize against the public allowlist, including cache-busting query strings.
    const canonical = SHELL.find(path => new URL(path, location.origin).pathname === url.pathname);
    if (canonical) {
      const cached = await cache.match(canonical);
      if (cached) return cached;
    }
    try { return await fetch(event.request); }
    catch { return new Response(null, {status: 503, statusText: 'Resource unavailable offline'}); }
  })());
});
