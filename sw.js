// 每日彙整快報 PWA - Service Worker
// 快取「應用外殼」(HTML/CSS/JS/圖示)，讓使用者離線時仍能開啟畫面。
// /api/ 開頭的資料請求一律走網路，不做快取（資料本來就需要每次即時抓取）。

const CACHE_VERSION = "v1";
const CACHE_NAME = `daily-digest-shell-${CACHE_VERSION}`;

const APP_SHELL = [
  "/",
  "/manifest.json",
  "/static/css/style.css",
  "/static/js/app.js",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/favicon.ico",
];

// 安裝階段：預先快取應用外殼
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
          .filter((key) => key.startsWith("daily-digest-shell-") && key !== CACHE_NAME)
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

  // 非 GET 請求（例如 POST /api/fetch, /api/send）一律直接透過網路，不快取
  if (request.method !== "GET") {
    return;
  }

  // API 資料一律走網路優先，失敗時不回退快取（避免顯示過期新聞）
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(request));
    return;
  }

  // 應用外殼：快取優先，找不到再打網路，並且把新的結果補進快取
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);
    })
  );
});
