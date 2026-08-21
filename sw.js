/**
 * sw.js — Service Worker
 * ------------------------------------------------------------
 * 策略：
 *   - App Shell（HTML / CSS / JS / manifest / icons）：Cache First，
 *     並在背景更新快取（stale-while-revalidate）。
 *   - /api/ 開頭的動態資料請求：Network First，離線時才退回快取。
 * ------------------------------------------------------------
 */

const CACHE_VERSION = "v1";
const CACHE_NAME = `daily-news-pwa-${CACHE_VERSION}`;

const APP_SHELL = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/manifest.json",
  "/icons/icon-72.png",
  "/icons/icon-96.png",
  "/icons/icon-128.png",
  "/icons/icon-144.png",
  "/icons/icon-152.png",
  "/icons/icon-192.png",
  "/icons/icon-384.png",
  "/icons/icon-512.png",
];

// 安裝階段：預先快取 App Shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// 啟用階段：清除舊版本快取
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("daily-news-pwa-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// 攔截請求
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    // POST（例如 /api/fetch、/api/send）一律走網路，不做快取
    return;
  }

  // 動態 API：Network First
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // App Shell 與靜態資源：Cache First + 背景更新
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
