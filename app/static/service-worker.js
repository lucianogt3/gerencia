const CACHE_NAME = 'nurse-portal-v1';
const urlsToCache = [
  '/',
  '/static/css/app.css',
  '/auth/login'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});