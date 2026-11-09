// Service worker: makes the site installable and lets it open offline.
// Served from /sw.js (api/main.py) so it controls the whole site, not just /static/.
//
// Strategy, chosen so a new deploy is never hidden behind a stale cache:
//   the page, our own CSS/JS and /api/* : network first, cache as fallback
//     (offline, the board shows the last readings it saw, with their times)
//   third-party libraries and fonts     : cache first (versioned URLs)
//   map tiles                           : not cached (too many, change often)
const CACHE = "delhi-air-v1";
const SHELL = ["/", "/static/style.css", "/static/theme.js", "/static/live.js", "/static/gl_base.js",
               "/static/icons/icon-192.png", "/manifest.webmanifest"];
const CDN = ["cdn.plot.ly", "unpkg.com", "fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: request.mode === "navigate" });
    if (cached) return cached;
    if (request.mode === "navigate") return cache.match("/");
    throw err;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok || response.type === "opaque") cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin === self.location.origin) {
    event.respondWith(networkFirst(request));
  } else if (CDN.includes(url.hostname)) {
    event.respondWith(cacheFirst(request));
  }
  // anything else (map tiles, news links) goes straight to the network
});
