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
    window.scrollTo(0, 0);
  });

  /* ---------- 模糊搜索：默认全类型 ---------- */
  const KIND_LABEL = { items: "道具", trinkets: "饰品", cards: "卡牌", pills: "药丸" };
  const SEARCH_KINDS = [
    { key: "items", label: KIND_LABEL.items },
    { key: "trinkets", label: KIND_LABEL.trinkets },
    { key: "cards", label: KIND_LABEL.cards },
    { key: "pills", label: KIND_LABEL.pills }
  ];
  let kind = "all", query = "";

  function setKind(k) {
    kind = k;
    $$("#kindTabs .tab").forEach(x => x.classList.toggle("on", x.dataset.kind === k));
    render();
  }
  $$("#kindTabs .tab").forEach(t => t.onclick = () => setKind(t.dataset.kind));
  $("#q").addEventListener("input", e => {
    const had = !!query;
    query = e.target.value.trim().toLowerCase();
    /* 开始一次新搜索时自动回到「全部」，不被上次选中的分类限制 */
    if (query && !had && kind !== "all") setKind("all");
    else render();
  });

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

  function cardHTML(r, i, groupKey) {
    const q = r.quality != null ? `<span class="quality q${r.quality}">${r.quality}</span>` : "";
    const tags = [...(r.nick || []).slice(0, 3), ...(r.look || []).slice(0, 3)]
      .map((t, k) => `<span class="ctag${k >= (r.nick || []).slice(0, 3).length ? " look" : ""}">${t}</span>`).join("");
    const thumb = (r.image || r.image_url)
      ? `<img class="thumb" src="${IMG(r)}" onerror="this.classList.add('noimg');this.src='${r.image_url || ""}'">`
      : `<div class="thumb ph">💊</div>`;
    const kindTag = kind === "all" ? `<span class="kindtag">${KIND_LABEL[groupKey] || ""}</span>` : "";
    return `<div class="card" data-idx="${i}" data-kind="${groupKey}">
      ${q}${thumb}
      <div class="cname">${kindTag}<span class="czh">${r.name_zh || r.name}</span></div>
      <div class="cname" style="color:#8b93a3;font-size:11.5px">${r.name || ""}</div>
      ${tags}</div>`;
  }

  let lastList = [];

  function render() {
    const groups = kind === "all" ? SEARCH_KINDS : SEARCH_KINDS.filter(g => g.key === kind);
    const buckets = [];
    let matched = 0;

    for (const g of groups) {
      const all = G[g.key] || [];
      let rows = all.map(r => ({ r, k: g.key, s: score(r, query) }))
        .filter(x => x.s > 0)
        .sort((a, b) => b.s - a.s);
      matched += rows.length;
      /* 不搜索时按分类浏览：全部类型各展示 12 条，单分类保持原数量 */
      if (!query) rows = rows.slice(0, kind === "all" ? 12 : (g.key === "pills" ? 60 : 40));
      buckets.push(rows);
    }

    const picked = [];
    if (!query && kind === "all") {
      /* 「全部」浏览时四类交替出现，避免第一屏看起来仍然只有道具 */
      const max = Math.max(0, ...buckets.map(b => b.length));
      for (let i = 0; i < max; i++) {
        for (const b of buckets) if (b[i]) picked.push(b[i]);
      }
    } else {
      for (const b of buckets) picked.push(...b);
    }
    if (query) picked.sort((a, b) => b.s - a.s);
    lastList = picked.slice(0, query ? 80 : 200);

    const shown = lastList.length;
    let txt = `${shown} 条`;
    if (shown < matched) txt += query ? ` / 命中 ${matched} 条` : ` / 共 ${matched} 条`;
    if (query) txt += ` · “${query}”`;
    else if (kind === "all") txt += " · 全部类型";
    $("#searchCnt").textContent = txt;
    $("#results").innerHTML = lastList.map((x, i) => cardHTML(x.r, i, x.k)).join("") || `<div class="empty">没找到，换个俗称/拼音/长相试试</div>`;
  }

  /* 卡片详情弹层 */
  function openDetail(r, kindKey) {
    const quality = r.quality != null ? `<span class="mq q${r.quality}">品质 ${r.quality}</span>` : "";
    const head = (r.image || r.image_url)
      ? `<img src="${IMG(r)}" onerror="this.style.display='none'">`
      : `<div class="mph">💊</div>`;
    const tags = [...(r.nick || []), ...(r.look || [])];
    $("#modal .mbody").innerHTML = `
      <div class="mhead">${head}
        <div><div class="mtitle">${r.name_zh || r.name}</div>
        <div class="msub">${r.name || ""}${r.type ? " · " + r.type : ""}</div>
        ${quality}</div>
      </div>
      ${r.quote ? `<div class="mquote">“${r.quote}”</div>` : ""}
      <div class="mdesc">${(r.desc_zh || "（暂无效果描述）").replace(/</g, "&lt;")}</div>
      ${tags.length ? `<div class="mtags">${tags.map(t => `<span class="ctag">${t}</span>`).join("")}</div>` : ""}
      <div class="msub" style="margin-top:10px">${KIND_LABEL[kindKey] || ""}${r.id != null ? " · ID " + r.id : ""}</div>`;
    $("#modal").classList.add("on");
  }
  $("#results").addEventListener("click", e => {
    const c = e.target.closest(".card");
    if (!c) return;
    const item = lastList[+c.dataset.idx];
    if (item) openDetail(item.r, item.k);
  });
  $("#modal").addEventListener("click", e => {
    if (e.target.id === "modal" || e.target.closest(".mclose")) $("#modal").classList.remove("on");
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") $("#modal").classList.remove("on"); });

  render();

  /* ---------- 拍照识别：内置像素模板 / 可选自定义模型 ---------- */
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
    ["recBtn", "recAll", "reset"].forEach(id => $("#" + id).disabled = false);
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

  // ---- 无模型识别：24×24 彩色模板 + alpha 掩码 + 原图高分辨率裁切 + 自动前景框 + 多尺度/平移/旋转搜索 ----
  const META = window.RECOG_META || { S: 24, scale: 40 };
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
      const total = META.S * META.S;
      for (let p = 0; p < total; p++) {
        if ((mb[p >> 3] >> (7 - (p & 7))) & 1) idx.push(p * 3, p * 3 + 1, p * 3 + 2);
      }
      let sum = 0, sum2 = 0;
      for (let i = 0; i < v.length; i++) { sum += v[i]; sum2 += v[i] * v[i]; }
      out.push({ ...e, v, idx: Int32Array.from(idx), mv: sum / v.length, mvv: sum2 / v.length });
    }
    return out;
  }
  MODEL = decodeModel(R);

  /* 识别时不要用屏幕上缩小后的 640px 画布，而是从原图重新裁切。
     手机照片里道具可能只有几十像素，直接缩到 640 会先丢掉细节。 */
  function sourceFor(region) {
    const c = document.createElement("canvas");
    const cc = c.getContext("2d", { willReadFrequently: true });
    const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
    let sx = 0, sy = 0, sw = iw, sh = ih;
    if (region) {
      const kx = iw / cv.width, ky = ih / cv.height;
      sx = region.x * kx; sy = region.y * ky;
      sw = region.w * kx; sh = region.h * ky;
      /* 选框稍微往外扩一点：手机上容易把图标边缘切掉，留出兜底空间 */
      const padX = sw * 0.18, padY = sh * 0.18;
      sx = Math.max(0, sx - padX); sy = Math.max(0, sy - padY);
      sw = Math.min(iw - sx, sw + padX * 2);
      sh = Math.min(ih - sy, sh + padY * 2);
    }
    const max = region ? 1024 : 1280;
    const sc = Math.min(1, max / Math.max(sw, sh));
    c.width = Math.max(8, Math.round(sw * sc));
    c.height = Math.max(8, Math.round(sh * sc));
    cc.fillStyle = "#fff"; cc.fillRect(0, 0, c.width, c.height);
    cc.drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height);
    return c;
  }

  /* 从选框里找“最像物体”的区域。手机上框大了、道具偏在一边时，
     只靠等比例缩小很难对齐；先估一个前景框，再围绕它多尺度裁切。 */
  function autoBox(src) {
    const N = 80;
    const c = document.createElement("canvas"); c.width = N; c.height = N;
    const cc = c.getContext("2d", { willReadFrequently: true });
    cc.fillStyle = "#fff"; cc.fillRect(0, 0, N, N);
    cc.drawImage(src, 0, 0, src.width, src.height, 0, 0, N, N);
    const d = cc.getImageData(0, 0, N, N).data;
    const rs = [], gs = [], bs = [], gray = new Float32Array(N * N);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const i = (y * N + x) * 4;
      gray[y * N + x] = (d[i] * .299 + d[i + 1] * .587 + d[i + 2] * .114) / 255;
      if (x < 6 || x >= N - 6 || y < 6 || y >= N - 6) {
        rs.push(d[i]); gs.push(d[i + 1]); bs.push(d[i + 2]);
      }
    }
    const med = a => { a.sort((u, v) => u - v); return a[a.length >> 1]; };
    const br = med(rs) / 255, bg = med(gs) / 255, bb = med(bs) / 255;
    const scores = new Float32Array(N * N);
    for (let y = 4; y < N - 4; y++) for (let x = 4; x < N - 4; x++) {
      const p = y * N + x, i = p * 4;
      const r = d[i] / 255, g = d[i + 1] / 255, b = d[i + 2] / 255;
      const cd = Math.hypot(r - br, g - bg, b - bb);
      const gx = (gray[p + 1] - gray[p - 1]) * .5;
      const gy = (gray[p + N] - gray[p - N]) * .5;
      const gm = Math.hypot(gx, gy);
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
      const sat = (mx - mn) / (mx + 1e-6);
      const dx = (x - (N - 1) / 2) / (N / 2), dy = (y - (N - 1) / 2) / (N / 2);
      const center = Math.max(0, Math.min(1, 1.25 - 0.55 * Math.hypot(dx, dy)));
      scores[p] = (cd + gm * 0.9 + sat * 0.25 + (r + g + b) / 3 * 0.08) * center;
    }
    const sorted = Array.from(scores).sort((a, b) => a - b);
    /* 取高响应点；太低会把阴影/地面算进去，太高中小物体只剩一块高光 */
    const th = sorted[Math.floor(N * N * 0.85)];
    let x0 = N, y0 = N, x1 = 0, y1 = 0, count = 0;
    for (let y = 4; y < N - 4; y++) for (let x = 4; x < N - 4; x++) {
      if (scores[y * N + x] > th) {
        count++; if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
    }
    if (count < 20) return null;
    /* 百分位框通常会略小于物体，向外扩 7% */
    let bx = x0 / N * src.width, by = y0 / N * src.height;
    let bw = (x1 - x0 + 1) / N * src.width, bh = (y1 - y0 + 1) / N * src.height;
    const padX = bw * 0.07, padY = bh * 0.07;
    bx -= padX; by -= padY; bw += padX * 2; bh += padY * 2;
    bx = Math.max(0, bx); by = Math.max(0, by);
    bw = Math.min(src.width - bx, bw); bh = Math.min(src.height - by, bh);
    if (bw < 12 || bh < 12) return null;
    if (bw * bh > src.width * src.height * 0.92) return null;
    return { x: bx, y: by, w: bw, h: bh };
  }

  function candidates(src) {
    const S = META.S, out = [];
    const ANGLES = [-14, -7, 0, 7, 14];
    const SHIFTS = [-0.18, 0, 0.18];
    const bases = [];
    /* 用户原选框：适合框得比较准的情况 */
    for (const margin of [0, 0.08, 0.18, 0.30, 0.42]) {
      bases.push({
        x: src.width * margin / 2, y: src.height * margin / 2,
        w: src.width * (1 - margin), h: src.height * (1 - margin)
      });
    }
    /* 自动前景框：框大了、道具只占一小块时用 */
    const auto = autoBox(src);
    if (auto) {
      for (const margin of [0, 0.12, 0.25, 0.40, 0.52]) {
        bases.push({
          x: auto.x + auto.w * margin / 2, y: auto.y + auto.h * margin / 2,
          w: auto.w * (1 - margin), h: auto.h * (1 - margin)
        });
      }
    }
    const c = document.createElement("canvas"); c.width = S; c.height = S;
    const cc = c.getContext("2d", { willReadFrequently: true });
    const seen = new Set();
    for (const b of bases) {
      const bw = Math.max(8, b.w), bh = Math.max(8, b.h);
      for (const fx of SHIFTS) for (const fy of SHIFTS) {
        const cw = Math.min(src.width, Math.max(8, Math.round(bw)));
        const ch = Math.min(src.height, Math.max(8, Math.round(bh)));
        let x0 = Math.round(b.x + bw * fx);
        let y0 = Math.round(b.y + bh * fy);
        x0 = Math.max(0, Math.min(x0, src.width - cw));
        y0 = Math.max(0, Math.min(y0, src.height - ch));
        const key = x0 + "," + y0 + "," + cw + "," + ch;
        if (seen.has(key)) continue;
        seen.add(key);
        for (const ang of ANGLES) {
          cc.clearRect(0, 0, S, S);
          cc.save();
          cc.translate(S / 2, S / 2);
          cc.rotate(ang * Math.PI / 180);
          cc.drawImage(src, x0, y0, cw, ch, -S / 2, -S / 2, S, S);
          cc.restore();
          const d = cc.getImageData(0, 0, S, S).data;
          const f = new Float32Array(S * S * 3);
          for (let i = 0, j = 0; i < S * S; i++) {
            f[j++] = d[i * 4] / 255; f[j++] = d[i * 4 + 1] / 255; f[j++] = d[i * 4 + 2] / 255;
          }
          /* 轻微偏好大一点的裁切：避免从图标内部的一小块高光/图案匹配到别的道具 */
          const prior = 0.10 * (1 - Math.min(1, (cw * ch) / (src.width * src.height)));
          out.push({ f, prior });
        }
      }
    }
    return out;
  }

  function recognize(region) {
    if (!img) { $("#recCnt").textContent = "请先上传/拍照。"; return; }
    if (!MODEL.length) { $("#recCnt").textContent = "模型未加载。"; return; }
    const src = sourceFor(region);
    const C = candidates(src), t0 = performance.now();
    const best = new Float32Array(MODEL.length);
    for (let k = 0; k < MODEL.length; k++) {
      const m = MODEL[k], idx = m.idx, n = idx.length;
      let bd = Infinity;
      for (let ci = 0; ci < C.length; ci++) {
        const cand = C[ci], q = cand.f;
        let sq = 0, sq2 = 0, dot = 0;
        for (let i = 0; i < n; i++) {
          const x = q[idx[i]];
          sq += x; sq2 += x * x; dot += m.v[i] * x;
        }
        const mean = sq / n;
        const sd = Math.sqrt(Math.max(sq2 / n - mean * mean, 1e-9));
        const d = m.mvv + 1 - 2 * (dot / n - m.mv * mean) / sd + cand.prior;
        if (d < bd) bd = d;
      }
      best[k] = bd;
    }
    const order = Array.from(MODEL.keys()).sort((a, b) => best[a] - best[b]).slice(0, 8);
    const ms = Math.round(performance.now() - t0);
    const gap = order.length > 1 ? best[order[1]] - best[order[0]] : 1;
    const near = gap < 0.025;
    const low = best[order[0]] > 0.72;
    const note = near ? " · 候选很接近，请点开确认" : (low ? " · 匹配度偏低，请确认" : "");
    $("#recCnt").textContent = `识别结果（无模型·像素模板 · ${C.length} 候选 · ${ms}ms）${note} · 点击查看详情`;
    $("#recResults").innerHTML = order.map((k, rank) => {
      const e = MODEL[k];
      const conf = Math.max(0, Math.min(100, Math.round((1 - best[k] / 1.5) * 100)));
      const badge = rank === 0 ? `<span class="badge" style="background:${near ? "#8a5a24" : "#2e6b46"}">${near ? "最接近" : "最佳"}</span>` : "";
      return `
      <div class="result" data-k="${k}">
        <img src="${e.image ? "../../" + e.image : (e.image_url || "")}" onerror="this.src='${e.image_url || ""}'">
        <div>
          <div class="cname"><span class="czh">${e.name_zh || e.name}</span><span class="badge">${KIND_LABEL[e.kind + "s"] || e.kind}</span>${badge}</div>
          <div style="color:#8b93a3;font-size:11.5px">${e.name || ""}</div>
          <div class="score">匹配度 ${conf}%</div>
        </div>
      </div>`;
    }).join("");
    /* 手机端操作栏固定在底部，识别完成后把结果滚进视野 */
    if (window.matchMedia("(max-width:640px)").matches) {
      requestAnimationFrame(() => $("#recCnt").scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }
  $("#recBtn").onclick = () => recognize(sel && sel.w > 4 ? sel : null);
  $("#recAll").onclick = () => recognize(null);
  $("#recResults").addEventListener("click", e => {
    const el = e.target.closest(".result");
    if (!el) return;
    const rec = MODEL[+el.dataset.k];
    if (!rec) return;
    const kindKey = rec.kind === "trinket" ? "trinkets" : rec.kind === "card" ? "cards" : "items";
    const arr = G[kindKey] || [];
    const full = arr.find(x => x.name === rec.name) || arr.find(x => x.id === rec.id) || rec;
    openDetail(full, kindKey);
  });

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
