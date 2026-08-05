const CACHE_NAME = "areses-articles-v1";
const MAX_CACHED_ARTICLES = 50;

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

async function trimCache() {
  const cache = await caches.open(CACHE_NAME);
  const keys = await cache.keys();
  if (keys.length > MAX_CACHED_ARTICLES) {
    const toDelete = keys.slice(0, keys.length - MAX_CACHED_ARTICLES);
    await Promise.all(toDelete.map((key) => cache.delete(key)));
  }
}

self.addEventListener("push", (event) => {
  let payload = { title: "ARESES", body: "New article", url: "/" };
  try {
    if (event.data) payload = { ...payload, ...event.data.json() };
  } catch {
    /* fall back to defaults if payload isn't JSON */
  }
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      data: { url: payload.url },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(targetUrl);
    })
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isArticleDetail = /\/api\/articles\/\d+$/.test(url.pathname);

  if (!isArticleDetail || event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, clone);
          trimCache();
        });
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
