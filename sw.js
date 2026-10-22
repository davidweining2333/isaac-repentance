/* 以撒图鉴 Service Worker
 * 作用域：仓库根目录（图片在 /images/ 下，所以 sw.js 必须放在根目录）。
 * 策略：
 *   - 安装时预缓存应用外壳（HTML/JS/manifest/图标）
 *   - 图标：缓存优先（一旦缓存，断网可用）
 *   - 页面/脚本：网络优先，失败回退缓存
 */
const V = "isaac-guide-v15";     // 应用外壳（随版本更新）
const IMG = "isaac-images-v1";   // 图标（跨版本保留，避免升级后重新下载 4MB）

const CORE = [
  "./",
  "./index.html",
  "./manifest.json",
  "./app/web/index.html",
  "./app/web/app.js",
  "./app/web/guide.js",
  "./app/web/recognition.js",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
  "./icons/favicon.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(V)
      /* cache:"reload" 绕过 HTTP 缓存，确保升级时拿到新脚本而不是旧副本 */
      .then((c) => c.addAll(CORE.map((u) => new Request(u, { cache: "reload" }))))
      .catch(() => {})
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== V && k !== IMG).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  let url;
  try { url = new URL(req.url); } catch { return; }
  if (url.origin !== location.origin) return;

  const isImage = /\.(png|jpe?g|webp|gif|svg|ico)$/i.test(url.pathname);
  const isDoc = /\.(js|css|json)$/i.test(url.pathname) || req.mode === "navigate";

  /* 图标：缓存优先（跨版本保留） */
  if (isImage) {
    e.respondWith((async () => {
      const c = await caches.open(IMG);
      const hit = await c.match(req);
      if (hit) return hit;
      try {
        const res = await fetch(req);
        if (res && res.ok) c.put(req, res.clone());
        return res;
      } catch {
        return new Response("", { status: 404, statusText: "offline" });
      }
    })());
    return;
  }

  /* 页面/脚本/数据：网络优先（强制回源校验，避免更新后仍读旧缓存） */
  if (isDoc) {
    e.respondWith((async () => {
      const c = await caches.open(V);
      try {
        const res = await fetch(req, { cache: "no-cache" });
        if (res && res.ok) c.put(req, res.clone());
        return res;
      } catch {
        const hit = await c.match(req);
        return hit || new Response(
          `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
           <title>离线</title>
           <body style="margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;
                        background:#12141a;color:#e9ebf1;font:15px/1.8 -apple-system,'PingFang SC',sans-serif;text-align:center;padding:24px">
             <div style="font-size:40px">📴</div>
             <h2 style="margin:12px 0 6px">当前处于离线状态</h2>
             <p style="color:#98a0b0;margin:0">这个页面还没有缓存过。<br>请联网打开一次后再试。</p>
           </body>`,
          { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
        );
      }
    })());
  }
});
