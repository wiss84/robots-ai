const CACHE_NAME = 'agent-app-cache-v4';

// Base paths for different image types
const IMAGE_PATHS = {
  avatars: '/avatars/',
  assets: '/assets/'
};

// Known agent folders (can be extended)
const KNOWN_AGENTS = [
  'games_agent',
  'coding_agent', 
  'finance_agent',
  'image_agent',
  'news_agent',
  'realestate_agent',
  'travel_agent',
  'shopping_agent'
];

// Standard pose names that all agents should have
const STANDARD_POSES = [
  'greeting_pose.webp',
  'typing_pose.webp',
  'typing_pose.png', // Some agents use PNG
  'thinking_pose.webp',
  'arms_crossing_pose.webp',
  'wondering_pose.webp',
  'standing_pose.webp'
];

// Assets that should always be cached
const ASSET_IMAGES = [
  'homepage.webp',
  'image-not-found.png',
  'left.webp',
  'right.webp'
];

// Generate cache list dynamically
function generateCacheList() {
  const imagesToCache = [];
  
  // Add all agent poses
  KNOWN_AGENTS.forEach(agent => {
    STANDARD_POSES.forEach(pose => {
      imagesToCache.push(`${IMAGE_PATHS.avatars}${agent}/${pose}`);
    });
    // Add agent's main avatar
    imagesToCache.push(`${IMAGE_PATHS.avatars}${agent}/${agent.replace('_agent', '')}.webp`);
  });
  
  // Add assets
  ASSET_IMAGES.forEach(asset => {
    imagesToCache.push(`${IMAGE_PATHS.assets}${asset}`);
  });
  
  return imagesToCache;
}

const IMAGES_TO_CACHE = generateCacheList();

self.addEventListener('install', (event) => {
  console.log('Service Worker installing and pre-caching images...');
  console.log('Cache list:', IMAGES_TO_CACHE);
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Pre-caching all images...');
      return cache.addAll(IMAGES_TO_CACHE).then(() => {
        console.log('All images pre-cached successfully!');
      }).catch((error) => {
        console.error('Error pre-caching images:', error);
        // Continue even if some images fail to cache
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Check if this is an image request
  if (request.method === 'GET' && 
      (url.pathname.includes('/avatars/') || url.pathname.includes('/assets/')) &&
      (url.pathname.endsWith('.webp') || url.pathname.endsWith('.png') || url.pathname.endsWith('.jpg') || url.pathname.endsWith('.jpeg') || url.pathname.endsWith('.gif'))) {
    
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log('Serving from cache:', url.pathname);
            return cachedResponse;
          }
          // If not in cache, fetch and cache it
          return fetch(request).then((networkResponse) => {
            if (networkResponse.ok) {
              console.log('Caching new image:', url.pathname);
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          }).catch((error) => {
            console.error('Service worker fetch error:', error);
            return new Response('', { status: 404, statusText: 'Not Found' });
          });
        })
      ).catch((error) => {
        console.error('Service worker cache error:', error);
        return fetch(request).catch((fetchError) => {
          console.error('Service worker network error:', fetchError);
          return new Response('', { status: 404, statusText: 'Not Found' });
        });
      })
    );
  }
}); 