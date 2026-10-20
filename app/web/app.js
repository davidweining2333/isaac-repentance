/* 以撒图鉴前端：模糊搜索 + 无模型拍照识别。纯 JS，无依赖、无 AI 模型。 */
(function () {
  const G = window.GUIDE, R = window.RECOG || [];
  const IMG = (r) => r.image ? "../../" + r.image : (r.image_url || "");
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  /* ---------- 顶部标签切换 ---------- */
  $$(".tabs .tab[data-view]").forEach(t => t.onclick = () => {
    $$(".tabs .tab[data-view]").forEach(x => x.classList.remove("on"));
    t.classList.add("on");
    ["search", "recognize", "about"].forEach(v => $("#view-" + v).style.display = (v === t.dataset.view ? "" : "none"));
  });

  /* ---------- 模糊搜索 ---------- */
  let kind = "items", query = "";
  $$("#kindTabs .tab").forEach(t => t.onclick = () => {
    $$("#kindTabs .tab").forEach(x => x.classList.remove("on"));
    t.classList.add("on"); kind = t.dataset.kind; render();
  });
  $("#q").addEventListener("input", e => { query = e.target.value.trim().toLowerCase(); render(); });

  function score(rec, q) {
    if (!q) return 1;
    let s = 0;
    const zh = (rec.name_zh || "").toLowerCase(), en = (rec.name || "").toLowerCase();
    if (zh === q || en === q) s += 100;
    if (zh.includes(q)) s += 45;
    if (en.includes(q)) s += 40;
    for (const n of rec.nick || []) { const v = n.toLowerCase(); if (v === q) s += 90; else if (v.includes(q)) s += 50; }
    for (const l of rec.look || []) if (l.toLowerCase().includes(q)) s += 30;
    for (const p of rec.pinyin || []) if (p.includes(q.replace(/\s/g, ""))) s += 35;
    if ((rec.search || "").includes(q)) s += 12;
    return s;
  }

  function cardHTML(r, i) {
    const q = r.quality != null ? `<span class="quality q${r.quality}">${r.quality}</span>` : "";
    const tags = [...(r.nick || []).slice(0, 3), ...(r.look || []).slice(0, 3)]
      .map((t, k) => `<span class="ctag${k >= (r.nick || []).slice(0, 3).length ? " look" : ""}">${t}</span>`).join("");
    const thumb = (r.image || r.image_url)
      ? `<img class="thumb" src="${IMG(r)}" onerror="this.classList.add('noimg');this.src='${r.image_url || ""}'">`
      : `<div class="thumb ph">💊</div>`;
    return `<div class="card" data-idx="${i}" data-kind="${kind}">
      ${q}${thumb}
      <div class="cname"><span class="czh">${r.name_zh || r.name}</span></div>
      <div class="cname" style="color:#8b93a3;font-size:11.5px">${r.name || ""}</div>
      ${tags}</div>`;
  }

  const KIND_LABEL = { items: "道具", trinkets: "饰品", cards: "卡牌", pills: "药丸" };
  let lastList = [];

  function render() {
    lastList = (G[kind] || []).map(r => ({ r, s: score(r, query) }))
      .filter(x => x.s > 0).sort((a, b) => b.s - a.s)
      .slice(0, query ? 80 : 40).map(x => x.r);
    $("#searchCnt").textContent = `${lastList.length} 条` + (query ? ` · “${query}”` : "");
    $("#results").innerHTML = lastList.map((r, i) => cardHTML(r, i)).join("") || `<div class="empty">没找到，换个俗称/拼音/长相试试</div>`;
  }

  /* 卡片详情弹层 */
  function openDetail(r) {
    const q = r.quality != null ? `品质 ${r.quality}` : "";
    const head = (r.image || r.image_url)
      ? `<img src="${IMG(r)}" onerror="this.style.display='none'">`
      : `<div class="mph">💊</div>`;
    const tags = [...(r.nick || []), ...(r.look || [])];
    $("#modal .mbody").innerHTML = `
      <div class="mhead">${head}
        <div><div class="mtitle">${r.name_zh || r.name}</div>
        <div class="msub">${r.name || ""}${q ? " · " + q : ""}${r.type ? " · " + r.type : ""}</div></div>
      </div>
      ${r.quote ? `<div class="mquote">“${r.quote}”</div>` : ""}
      <div class="mdesc">${(r.desc_zh || "（暂无效果描述）").replace(/</g, "&lt;")}</div>
      ${tags.length ? `<div class="mtags">${tags.map(t => `<span class="ctag">${t}</span>`).join("")}</div>` : ""}
      <div class="msub" style="margin-top:10px">${KIND_LABEL[kind] || ""}${r.id != null ? " · ID " + r.id : ""}</div>`;
    $("#modal").classList.add("on");
  }
  $("#results").addEventListener("click", e => {
    const c = e.target.closest(".card");
    if (c) openDetail(lastList[+c.dataset.idx]);
  });
  $("#modal").addEventListener("click", e => {
    if (e.target.id === "modal" || e.target.closest(".mclose")) $("#modal").classList.remove("on");
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") $("#modal").classList.remove("on"); });

  render();

  /* ---------- 无模型识别：感知哈希 + 主色 ---------- */
  const cv = $("#cv"), ctx = cv.getContext("2d");
  let img = null, sel = null, dragging = false, start = null;

  $("#drop").onclick = () => $("#file").click();
  $("#file").onchange = e => loadFile(e.target.files[0]);
  ["dragover", "drop"].forEach(ev => $("#drop").addEventListener(ev, e => {
    e.preventDefault();
    if (ev === "drop") loadFile(e.dataTransfer.files[0]);
  }));
  function loadFile(f) {
    if (!f) return;
    const fr = new FileReader();
    fr.onload = () => { const im = new Image(); im.onload = () => draw(im); im.src = fr.result; };
    fr.readAsDataURL(f);
  }
  function draw(im) {
    img = im; sel = null;
    const maxW = 640, sc = Math.min(1, maxW / im.width);
    cv.width = im.width * sc; cv.height = im.height * sc;
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cv.width, cv.height); // 白底，避免透明被当黑色
    ctx.drawImage(im, 0, 0, cv.width, cv.height);
    $("#recCnt").textContent = "已加载图片，可拖动框选道具。";
    $("#recResults").innerHTML = "";
  }
  function pos(e) {
    const b = cv.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - b.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - b.top;
    return { x: x * cv.width / b.width, y: y * cv.height / b.height };
  }
  cv.addEventListener("mousedown", e => { dragging = true; start = pos(e); });
  cv.addEventListener("touchstart", e => { dragging = true; start = pos(e); e.preventDefault(); }, { passive: false });
  ["mousemove", "touchmove"].forEach(ev => cv.addEventListener(ev, e => {
    if (!dragging) return; e.preventDefault();
    const p = pos(e);
    sel = { x: Math.min(start.x, p.x), y: Math.min(start.y, p.y), w: Math.abs(p.x - start.x), h: Math.abs(p.y - start.y) };
    redraw();
  }, { passive: false }));
  ["mouseup", "touchend"].forEach(ev => cv.addEventListener(ev, () => dragging = false));
  function redraw() {
    if (!img) return;
    ctx.drawImage(img, 0, 0, cv.width, cv.height);
    if (sel) { ctx.strokeStyle = "#e0a458"; ctx.lineWidth = 2; ctx.strokeRect(sel.x, sel.y, sel.w, sel.h); }
  }

  // ---- 无模型识别：16×16 彩色模板 + alpha 掩码 + 多尺度/平移搜索 ----
  const META = window.RECOG_META || { S: 16, scale: 40 };
  let MODEL = [], modelName = "内置图标库";
  const b64ToBytes = s => {
    const bin = atob(s), a = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
    return a;
  };
  function decodeModel(list) {
    const out = [];
    for (const e of list) {
      if (!e.v || !e.m) continue;
      const vb = b64ToBytes(e.v), mb = b64ToBytes(e.m);
      const v = new Float32Array(vb.length);
      for (let i = 0; i < vb.length; i++) {
        const x = vb[i] > 127 ? vb[i] - 256 : vb[i];
        v[i] = x / META.scale;
      }
      const idx = [];
      for (let p = 0; p < 256; p++) {
        if ((mb[p >> 3] >> (7 - (p & 7))) & 1) idx.push(p * 3, p * 3 + 1, p * 3 + 2);
      }
      let sum = 0, sum2 = 0;
      for (let i = 0; i < v.length; i++) { sum += v[i]; sum2 += v[i] * v[i]; }
      out.push({ ...e, v, idx: Int32Array.from(idx), mv: sum / v.length, mvv: sum2 / v.length });
    }
    return out;
  }
  MODEL = decodeModel(R);

  function candidates(region) {
    const src = region || { x: 0, y: 0, w: cv.width, h: cv.height };
    const S = META.S, out = [];
    for (const sc of [0.92, 1, 1.08]) {
      const cw = Math.max(8, Math.round(src.w * sc)), ch = Math.max(8, Math.round(src.h * sc));
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        let x0 = Math.round(src.x + (src.w - cw) / 2 + dx);
        let y0 = Math.round(src.y + (src.h - ch) / 2 + dy);
        x0 = Math.max(src.x, Math.min(x0, src.x + src.w - cw));
        y0 = Math.max(src.y, Math.min(y0, src.y + src.h - ch));
        const c = document.createElement("canvas"); c.width = S; c.height = S;
        const cc = c.getContext("2d", { willReadFrequently: true });
        cc.drawImage(cv, x0, y0, cw, ch, 0, 0, S, S);
        const d = cc.getImageData(0, 0, S, S).data;
        const f = new Float32Array(S * S * 3);
        for (let i = 0, j = 0; i < S * S; i++) {
          f[j++] = d[i * 4] / 255; f[j++] = d[i * 4 + 1] / 255; f[j++] = d[i * 4 + 2] / 255;
        }
        out.push(f);
      }
    }
    return out;
  }

  function recognize(region) {
    if (!img) { $("#recCnt").textContent = "请先上传/拍照。"; return; }
    if (!MODEL.length) { $("#recCnt").textContent = "模型未加载。"; return; }
    const C = candidates(region), t0 = performance.now();
    const best = new Float32Array(MODEL.length);
    for (let k = 0; k < MODEL.length; k++) {
      const m = MODEL[k], idx = m.idx, n = idx.length;
      let bd = Infinity;
      for (let ci = 0; ci < C.length; ci++) {
        const q = C[ci];
        let sq = 0, sq2 = 0, dot = 0;
        for (let i = 0; i < n; i++) {
          const x = q[idx[i]];
          sq += x; sq2 += x * x; dot += m.v[i] * x;
        }
        const mean = sq / n;
        const sd = Math.sqrt(Math.max(sq2 / n - mean * mean, 1e-9));
        const d = m.mvv + 1 - 2 * (dot / n - m.mv * mean) / sd;
        if (d < bd) bd = d;
      }
      best[k] = bd;
    }
    const order = Array.from(MODEL.keys()).sort((a, b) => best[a] - best[b]).slice(0, 8);
    const ms = Math.round(performance.now() - t0);
    $("#recCnt").textContent = `识别结果（无模型·像素模板 · ${C.length} 候选 · ${ms}ms）`;
    $("#recResults").innerHTML = order.map((k, rank) => {
      const e = MODEL[k];
      const conf = Math.max(0, Math.min(100, Math.round((1 - best[k] / 1.5) * 100)));
      return `
      <div class="result">
        <img src="${e.image ? "../../" + e.image : (e.image_url || "")}" onerror="this.src='${e.image_url || ""}'">
        <div>
          <div class="cname"><span class="czh">${e.name_zh || e.name}</span><span class="badge">${e.kind}</span>${rank === 0 ? '<span class="badge" style="background:#2e6b46">最佳</span>' : ""}</div>
          <div style="color:#8b93a3;font-size:11.5px">${e.name || ""}</div>
          <div class="score">匹配度 ${conf}%</div>
        </div>
      </div>`;
    }).join("");
  }
  $("#recBtn").onclick = () => recognize(sel && sel.w > 4 ? sel : null);
  $("#recAll").onclick = () => recognize(null);

  // ---- 识别后端切换：① 内置无模型；②③ 加载自定义模型（JSON，格式同 recognition.js） ----
  $("#backend").onchange = () => {
    if ($("#backend").value === "builtin") {
      MODEL = decodeModel(R); modelName = "内置图标库";
      $("#backendHint").textContent = `当前：内置 ${MODEL.length} 个图标模板（无模型·像素模板）。`;
      $("#recCnt").textContent = "";
    } else {
      $("#modelFile").click();
    }
  };
  $("#modelFile").onchange = ev => {
    const f = ev.target.files[0]; if (!f) return;
    const fr = new FileReader();
    fr.onload = () => {
      try {
        const data = JSON.parse(fr.result);
        const list = Array.isArray(data) ? data : (data.recog || data.icons || []);
        const m = decodeModel(list);
        if (!m.length) throw new Error("没有可用条目（需要 v / m 字段）");
        MODEL = m; modelName = f.name;
        $("#backendHint").textContent = `当前：${f.name}，共 ${m.length} 条。`;
        $("#recCnt").textContent = `已加载模型：${m.length} 条`;
      } catch (err) {
        $("#recCnt").textContent = "模型加载失败：" + err.message;
        $("#backend").value = "builtin";
        MODEL = decodeModel(R);
      }
    };
    fr.readAsText(f);
  };
  $("#reset").onclick = () => { if (img) draw(img); $("#recResults").innerHTML = ""; $("#recCnt").textContent = ""; };

  /* ---------- PWA：Service Worker + 一键离线缓存 ---------- */
  const httpMode = location.protocol.startsWith("http");
  if ("serviceWorker" in navigator && httpMode) {
    navigator.serviceWorker.register("../../sw.js", { scope: "../../" }).catch(() => {});
  }
  const cacheBtn = $("#cacheBtn");
  if (cacheBtn) {
    if (!httpMode) {
      cacheBtn.disabled = true;
      $("#cacheInfo").textContent = "本地文件模式不支持离线缓存；部署到网页后即可一键缓存。";
    } else cacheBtn.onclick = async () => {
      const el = $("#cacheInfo");
      let done = 0, total = 0;
      try {
        /* 等 Service Worker 就绪并接管本页，确保图标写进 Cache Storage */
        if ("serviceWorker" in navigator) {
          await navigator.serviceWorker.ready;
          if (!navigator.serviceWorker.controller) {
            await new Promise(r => {
              const t = setTimeout(r, 3000);
              navigator.serviceWorker.addEventListener("controllerchange", () => { clearTimeout(t); r(); }, { once: true });
            });
          }
        }
        const list = await (await fetch("images.json")).json();
        total = list.length;
        el.textContent = `缓存中… 0 / ${total}`;
        for (let i = 0; i < list.length; i += 8) {
          await Promise.all(list.slice(i, i + 8).map(p => fetch("../../" + p).catch(() => {})));
          done = Math.min(i + 8, total);
          el.textContent = `缓存中… ${done} / ${total}`;
        }
        el.textContent = `✅ 已缓存 ${done} 张图标，断网也能用。`;
      } catch (e) {
        el.textContent = "缓存失败：" + e.message;
      }
    };
  }
})();
