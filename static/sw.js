const READ_CACHE = 'shiny-read-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname === '/api/read') {
    e.respondWith(
      caches.open(READ_CACHE).then(async cache => {
        const cached = await cache.match(e.request);
        try {
          const fresh = await fetch(e.request);
          if (fresh.ok) cache.put(e.request, fresh.clone());
          return fresh;
        } catch {
          return cached || new Response(JSON.stringify({ error: 'Offline — article not cached yet.' }), {
            headers: { 'Content-Type': 'application/json' },
          });
        }
      })
    );
  }
});

// Called from the page to pre-cache a saved article's content
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'CACHE_ARTICLE' && e.data.url) {
    caches.open(READ_CACHE).then(cache =>
      fetch('/api/read?url=' + encodeURIComponent(e.data.url))
        .then(r => { if (r.ok) cache.put('/api/read?url=' + encodeURIComponent(e.data.url), r); })
        .catch(() => {})
    );
  }
});
