const CACHE = 'fst-v8';
const SHELL = [
  'index.html', 'manifest.json', 'icon.svg', 'assets/hud.css',
  'tools/parts.html', 'tools/dtc.html',
  'vehicles/focus-st/index.html', 'vehicles/zzr600/index.html',
  'vehicles/rz350/index.html', 'vehicles/tz250/index.html', 'vehicles/toyota-pickup/index.html'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('api.github.com')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
