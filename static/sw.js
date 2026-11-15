/* JARVIS service worker - makes the dashboard installable and usable offline.
 *
 * Strategy: network-first for everything on our own origin, so a running server
 * is always preferred (fresh market data / AI replies) and the cached app shell
 * is only used when the phone is offline or on a flaky network.
 */

const CACHE = "jarvis-shell-v1";
const SHELL = ["/", "/static/icon.svg", "/static/icon-192.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) =>
        Promise.all(
          SHELL.map((url) => cache.add(url).catch(() => undefined))
        )
      )
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Live data endpoints must never be served from cache.
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname === "/chat" ||
    url.pathname === "/health" ||
    url.pathname === "/sw.js"
  ) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => undefined);
        }
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => cached || caches.match("/"))
      )
  );
});
