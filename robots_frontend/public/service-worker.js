const CACHE_NAME = 'agent-app-cache-v1';
const IMAGE_CACHE_PATTERN = /\/avatars\/.*\.(webp|png|jpg|jpeg|gif)$|\/assets\/.*\.(webp|png|jpg|jpeg|gif)$/;

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only cache GET requests for images in /avatars/ or /assets/
  if (
    request.method === 'GET' &&
    IMAGE_CACHE_PATTERN.test(url.pathname)
  ) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          return fetch(request).then((networkResponse) => {
            if (networkResponse.ok) {
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          });
        })
      )
    );
  }
});
