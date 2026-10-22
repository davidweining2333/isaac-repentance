/* 以撒图鉴前端：模糊搜索 + 拍照识别。默认像素模板；可选 OpenCV ORB / DINOv2。 */
(function () {
  const G = window.GUIDE, R = window.RECOG || [];
  const IMG = (r) => r.image ? "../../" + r.image : (r.image_url || "");
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* 顶部导航是 sticky，搜索栏要吸在它下面；高度由 JS 实测后写入 CSS 变量 */
  const hdr = document.querySelector("header");
  const syncHeaderH = () => document.documentElement.style.setProperty("--header-h", hdr.offsetHeight + "px");
  syncHeaderH();
  window.addEventListener("resize", syncHeaderH);
  if (window.ResizeObserver) new ResizeObserver(syncHeaderH).observe(hdr);

  /* ---------- 顶部标签切换 ---------- */
  $$(".tabs .tab[data-view]").forEach(t => t.onclick = () => {
    $$(".tabs .tab[data-view]").forEach(x => x.classList.remove("on"));
    t.classList.add("on");
    ["search", "recognize", "about"].forEach(v => $("#view-" + v).style.display = (v === t.dataset.view ? "" : "none"));
    window.scrollTo(0, 0);
  });

  /* ---------- 模糊搜索：默认全类型 ---------- */
  const KIND_LABEL = { items: "道具", trinkets: "饰品", cards: "卡牌", pills: "药丸" };
  const TYPE_LABEL = { active: "主动道具", passive: "被动道具" };

  /* 主动道具充能：数字=房间数；Ns=随时间自动充能；其余是特殊值 */
  function chargeInfo(r) {
    if (!r || r.type !== "active") return null;
    const raw = String(r.recharge ?? "").trim();
    const timed = raw.match(/^(\d+(?:\.\d+)?)s$/);
    if (timed) return {
      short: `自动${raw}`, auto: true, value: `${timed[1]} 秒`,
      note: "自动充能（随时间恢复）",
      title: `自动充能 ${timed[1]} 秒（随时间恢复）`
    };
    if (/^\d+(?:\.\d+)?$/.test(raw)) return {
      short: `${raw}房`, auto: false, value: `${raw} 房间`,
      note: "非自动（清房间充能）",
      title: `充能 ${raw} 房间（非自动，清房间充能）`
    };
    const special = {
      unlimited: ["∞", "无限", "无充能条，可无限使用", "充能", "无限使用（无充能条）"],
      "one time": ["1次", "1 次", "一次性使用（使用后消失）", "使用次数", "一次性使用（使用后消失）"],
      variable: ["可变", "可变", "特殊（充能数可变）", "充能", "充能数可变（特殊）"],
      damage: ["伤害", "伤害", "伤害积累（非时间自动）", "充能", "伤害充能（造成伤害时积累）"],
      "1f": ["1层", "每层 1 次", "特殊（每层重置）", "频率", "每层 1 次（特殊）"],
      "": ["—", "无数据", "特殊（未记录充能）", "充能", "特殊（未记录充能）"]
    }[raw];
    if (special) return {
      short: special[0], auto: false, value: special[1],
      note: special[2], label: special[3], title: special[4]
    };
    return { short: raw, auto: false, value: raw, note: "特殊充能", label: "充能", title: `充能 ${raw}` };
  }
  const SEARCH_KINDS = [
    { key: "items", label: KIND_LABEL.items },
    { key: "trinkets", label: KIND_LABEL.trinkets },
    { key: "cards", label: KIND_LABEL.cards },
    { key: "pills", label: KIND_LABEL.pills }
  ];
  /* 「全部」只混合道具/饰品/卡牌；药丸只有切到药丸分类才显示 */
  const ALL_KINDS = SEARCH_KINDS.filter(g => g.key !== "pills");
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
    /* 开始一次新搜索时自动回到「全部」，不被上次选中的分类限制；
       药丸分类除外，否则在药丸页输入会立刻跳到不含药丸的「全部」。 */
    if (query && !had && kind !== "all" && kind !== "pills") setKind("all");
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
    const name = r.name_zh || r.name || "";
    /* 药丸外观随机，没有固定图标；直接展示名称和效果，避免无意义的占位图标 */
    if (groupKey === "pills") {
      const effect = r.desc_zh || "（暂无效果描述）";
      return `<div class="card k-pills pill-card" data-idx="${i}" data-kind="${groupKey}"
        title="${esc(name)}：${esc(effect)}" aria-label="${esc(name)}，${esc(effect)}">
        <div class="pill-name">${esc(name)}</div>
        <div class="pill-desc">${esc(effect)}</div>
      </div>`;
    }
    const thumb = (r.image || r.image_url)
      ? `<img class="thumb" src="${IMG(r)}" alt="${esc(name)}" loading="lazy" onerror="this.classList.add('noimg');this.src='${r.image_url || ""}'">`
      : `<div class="thumb ph" aria-label="${esc(name)}">?</div>`;
    /* 道具卡双层边框：外层金边表示道具，内层颜色表示主动/被动 */
    const typeClass = groupKey === "items" && r.type ? " " + r.type : "";
    const label = groupKey === "items" && TYPE_LABEL[r.type]
      ? `${TYPE_LABEL[r.type]} · ${name}`
      : name;
    const qual = groupKey === "items" && r.quality != null
      ? `<span class="quality q${r.quality}" title="品质 ${r.quality}" aria-label="品质 ${r.quality}">${r.quality}</span>`
      : "";
    const charge = groupKey === "items" ? chargeInfo(r) : null;
    const chargeHTML = charge
      ? `<span class="charge${charge.auto ? " auto" : ""}" title="${esc(charge.title)}" aria-label="${esc(charge.title)}">${esc(charge.short)}</span>`
      : "";
    const fullLabel = charge ? `${label} · ${charge.title}` : label;
    return `<div class="card k-${groupKey}${typeClass}" data-idx="${i}" data-kind="${groupKey}" title="${esc(fullLabel)}" aria-label="${esc(fullLabel)}">${thumb}${qual}${chargeHTML}</div>`;
  }

  let lastList = [];

  function render() {
    const groups = kind === "all" ? ALL_KINDS : SEARCH_KINDS.filter(g => g.key === kind);
    const buckets = [];

    for (const g of groups) {
      const all = G[g.key] || [];
      const rows = all.map(r => ({ r, k: g.key, s: score(r, query) }))
        .filter(x => x.s > 0)
        .sort((a, b) => b.s - a.s);
      buckets.push(rows);
    }

    const picked = [];
    if (!query && kind === "all") {
      /* 「全部」浏览时三类交替出现；药丸只在药丸分类显示 */
      const max = Math.max(0, ...buckets.map(b => b.length));
      for (let i = 0; i < max; i++) {
        for (const b of buckets) if (b[i]) picked.push(b[i]);
      }
    } else {
      for (const b of buckets) picked.push(...b);
    }
    if (query) picked.sort((a, b) => b.s - a.s);

    lastList = picked;

    let txt = `${picked.length} 条`;
    if (query) txt += ` · “${query}”`;
    else if (kind === "all") txt += " · 全部类型（不含药丸）";
    $("#searchCnt").textContent = txt;
    $("#results").innerHTML = lastList.map((x, i) => cardHTML(x.r, i, x.k)).join("") || `<div class="empty">没找到，换个俗称/拼音/长相试试</div>`;
  }

  /* 卡片详情弹层 */
  function openDetail(r, kindKey) {
    const quality = r.quality != null ? `<span class="mq q${r.quality}">品质 ${r.quality}</span>` : "";
    const head = (r.image || r.image_url)
      ? `<img src="${IMG(r)}" onerror="this.style.display='none'">`
      : `<div class="mph pillph">药丸</div>`;
    const tags = [...(r.nick || []), ...(r.look || [])];
    const sub = [r.name || "", TYPE_LABEL[r.type] || ""].filter(Boolean).join(" · ");
    const charge = chargeInfo(r);
    const chargeHTML = charge
      ? `<div class="mcharge${charge.auto ? " auto" : ""}">
          <span class="mcharge-k">${esc(charge.label || "充能")}</span><b>${esc(charge.value)}</b>
          <span class="mcharge-note">${esc(charge.note)}</span>
        </div>`
      : "";
    $("#modal .mbody").innerHTML = `
      <div class="mhead">${head}
        <div><div class="mtitle">${r.name_zh || r.name}</div>
        <div class="msub">${sub}</div>
        ${quality}</div>
      </div>
      ${r.quote ? `<div class="mquote">“${r.quote}”</div>` : ""}
      ${chargeHTML}
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
  const recCanvas = $("#recCanvas"), ctx = recCanvas.getContext("2d");
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
    recCanvas.width = im.width * sc; recCanvas.height = im.height * sc;
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, recCanvas.width, recCanvas.height); // 白底，避免透明被当黑色
    ctx.drawImage(im, 0, 0, recCanvas.width, recCanvas.height);
    ["recBtn", "recAll", "reset"].forEach(id => $("#" + id).disabled = false);
    $("#recCnt").textContent = "已加载图片，可拖动框选道具。";
    $("#recResults").innerHTML = "";
  }
  function pos(e) {
    const b = recCanvas.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - b.left;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - b.top;
    return { x: x * recCanvas.width / b.width, y: y * recCanvas.height / b.height };
  }
  recCanvas.addEventListener("mousedown", e => { dragging = true; start = pos(e); });
  recCanvas.addEventListener("touchstart", e => { dragging = true; start = pos(e); e.preventDefault(); }, { passive: false });
  ["mousemove", "touchmove"].forEach(ev => recCanvas.addEventListener(ev, e => {
    if (!dragging) return; e.preventDefault();
    const p = pos(e);
    sel = { x: Math.min(start.x, p.x), y: Math.min(start.y, p.y), w: Math.abs(p.x - start.x), h: Math.abs(p.y - start.y) };
    redraw();
  }, { passive: false }));
  ["mouseup", "touchend"].forEach(ev => recCanvas.addEventListener(ev, () => dragging = false));
  function redraw() {
    if (!img) return;
    ctx.drawImage(img, 0, 0, recCanvas.width, recCanvas.height);
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
  const BUILTIN_MODEL_BY_KEY = new Map(MODEL.map(e => [e.kind + ":" + e.id, e]));
  const REC_BY_KEY = new Map(R.map(e => [e.kind + ":" + e.id, e]));
  const KIND_TO_GUIDE = { item: "items", trinket: "trinkets", card: "cards" };
  let lastResults = [];
  let activeEngine = "template";

  /* 识别时不要用屏幕上缩小后的 640px 画布，而是从原图重新裁切。
     手机照片里道具可能只有几十像素，直接缩到 640 会先丢掉细节。 */
  function sourceFor(region) {
    const c = document.createElement("canvas");
    const cc = c.getContext("2d", { willReadFrequently: true });
    const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
    let sx = 0, sy = 0, sw = iw, sh = ih;
    if (region) {
      const kx = iw / recCanvas.width, ky = ih / recCanvas.height;
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

  /* ---------- 前景/背景分离 ----------
     手机截图和照片里，道具通常只占选框的一小块，周围是地板、墙、光晕或 UI。
     下面这套做法不依赖模型：先估计选框边缘的背景色，再把与背景相连的低对比像素
     泛洪掉，只留下中央的前景块；最后用前景包围盒裁切，避免背景进入模板/向量。
     对纯白底的图标（32×32 PNG）同样适用：边缘是白色，前景就是彩色像素。 */
  const FG_CACHE = new WeakMap();

  function medianOf(a) {
    if (!a.length) return 0;
    a.sort((x, y) => x - y);
    return a[a.length >> 1];
  }

  function otsuThreshold(hist, total) {
    let sum = 0;
    for (let i = 0; i < hist.length; i++) sum += i * hist[i];
    let sumB = 0, wB = 0, best = 0, bestVar = -1;
    for (let i = 0; i < hist.length; i++) {
      wB += hist[i];
      if (!wB) continue;
      const wF = total - wB;
      if (!wF) break;
      sumB += i * hist[i];
      const mB = sumB / wB, mF = (sum - sumB) / wF;
      const v = wB * wF * (mB - mF) * (mB - mF);
      if (v > bestVar) { bestVar = v; best = i; }
    }
    return best;
  }

  function openMask(mask, N) {
    const e = new Uint8Array(N * N);
    for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) {
      const p = y * N + x;
      if (mask[p] && mask[p - 1] && mask[p + 1] && mask[p - N] && mask[p + N] &&
          mask[p - N - 1] && mask[p - N + 1] && mask[p + N - 1] && mask[p + N + 1]) e[p] = 1;
    }
    const d = new Uint8Array(N * N);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const p = y * N + x;
      if (e[p]) { d[p] = 1; continue; }
      if (x > 0 && e[p - 1]) d[p] = 1;
      else if (x < N - 1 && e[p + 1]) d[p] = 1;
      else if (y > 0 && e[p - N]) d[p] = 1;
      else if (y < N - 1 && e[p + N]) d[p] = 1;
      else if (x > 0 && y > 0 && e[p - N - 1]) d[p] = 1;
      else if (x < N - 1 && y > 0 && e[p - N + 1]) d[p] = 1;
      else if (x > 0 && y < N - 1 && e[p + N - 1]) d[p] = 1;
      else if (x < N - 1 && y < N - 1 && e[p + N + 1]) d[p] = 1;
    }
    return d;
  }

  function dilateMask(mask, N) {
    const out = new Uint8Array(N * N);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const p = y * N + x;
      if (mask[p]) { out[p] = 1; continue; }
      if (x > 0 && mask[p - 1]) out[p] = 1;
      else if (x < N - 1 && mask[p + 1]) out[p] = 1;
      else if (y > 0 && mask[p - N]) out[p] = 1;
      else if (y < N - 1 && mask[p + N]) out[p] = 1;
      else if (x > 0 && y > 0 && mask[p - N - 1]) out[p] = 1;
      else if (x < N - 1 && y > 0 && mask[p - N + 1]) out[p] = 1;
      else if (x > 0 && y < N - 1 && mask[p + N - 1]) out[p] = 1;
      else if (x < N - 1 && y < N - 1 && mask[p + N + 1]) out[p] = 1;
    }
    return out;
  }

  function fillMaskHoles(mask, N) {
    const bg = new Uint8Array(N * N);
    const q = new Int32Array(N * N);
    let qh = 0, qt = 0;
    const push = p => { if (!mask[p] && !bg[p]) { bg[p] = 1; q[qt++] = p; } };
    for (let x = 0; x < N; x++) { push(x); push((N - 1) * N + x); }
    for (let y = 1; y < N - 1; y++) { push(y * N); push(y * N + N - 1); }
    while (qh < qt) {
      const p = q[qh++], x = p % N, y = (p / N) | 0;
      if (x > 0) push(p - 1);
      if (x < N - 1) push(p + 1);
      if (y > 0) push(p - N);
      if (y < N - 1) push(p + N);
    }
    const out = new Uint8Array(mask);
    for (let p = 0; p < N * N; p++) if (!mask[p] && !bg[p]) out[p] = 1;
    return out;
  }

  function segmentForeground(src, N = 96) {
    const c = document.createElement("canvas"); c.width = N; c.height = N;
    const cc = c.getContext("2d", { willReadFrequently: true });
    cc.fillStyle = "#fff"; cc.fillRect(0, 0, N, N);
    cc.drawImage(src, 0, 0, N, N);
    const px = cc.getImageData(0, 0, N, N).data;

    /* 选框最外圈通常是背景。取中位数和 MAD，作为背景色模型。 */
    const bw = Math.max(3, N >> 4);
    const rs = [], gs = [], bs = [];
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      if (x >= bw && x < N - bw && y >= bw && y < N - bw) continue;
      const i = (y * N + x) * 4;
      rs.push(px[i]); gs.push(px[i + 1]); bs.push(px[i + 2]);
    }
    if (rs.length < 16) return null;
    const medR = medianOf(rs), medG = medianOf(gs), medB = medianOf(bs);
    const ar = rs.map(v => Math.abs(v - medR)), ag = gs.map(v => Math.abs(v - medG)), ab = bs.map(v => Math.abs(v - medB));
    const madR = medianOf(ar), madG = medianOf(ag), madB = medianOf(ab);
    const sr = Math.max(8, madR * 3), sg = Math.max(8, madG * 3), sb = Math.max(8, madB * 3);

    const score = new Float32Array(N * N);
    const hist = new Uint32Array(128);
    for (let p = 0; p < N * N; p++) {
      const i = p * 4;
      const dr = (px[i] - medR) / sr, dg = (px[i + 1] - medG) / sg, db = (px[i + 2] - medB) / sb;
      const s = Math.sqrt(dr * dr + dg * dg + db * db);
      score[p] = s;
      hist[Math.min(127, Math.round(s * 16))]++;
    }
    const thBin = otsuThreshold(hist, N * N);
    const threshold = Math.max(0.42, (thBin + 0.5) / 16);

    /* 只把“和边缘背景连通”的低对比区域当作背景。这样图标内部即使有
       和背景相近的颜色，只要被图标轮廓包住，就不会被误删。 */
    const cand = new Uint8Array(N * N);
    for (let p = 0; p < N * N; p++) cand[p] = score[p] < threshold * 1.08 ? 1 : 0;
    const bg = new Uint8Array(N * N);
    const q = new Int32Array(N * N);
    let qh = 0, qt = 0;
    const push = p => { if (cand[p] && !bg[p]) { bg[p] = 1; q[qt++] = p; } };
    for (let x = 0; x < N; x++) { push(x); push((N - 1) * N + x); }
    for (let y = 1; y < N - 1; y++) { push(y * N); push(y * N + N - 1); }
    while (qh < qt) {
      const p = q[qh++], x = p % N, y = (p / N) | 0;
      if (x > 0) push(p - 1);
      if (x < N - 1) push(p + 1);
      if (y > 0) push(p - N);
      if (y < N - 1) push(p + N);
    }
    let fg = new Uint8Array(N * N);
    let fgCount = 0;
    for (let p = 0; p < N * N; p++) if (!bg[p]) { fg[p] = 1; fgCount++; }
    const frac = fgCount / (N * N);
    if (frac < 0.006 || frac > 0.92) return null;

    fg = openMask(fg, N);
    if (!fg.some(v => v)) return null;

    /* 8 连通块：保留靠近中心的主块，以及紧挨着它的碎块（火焰、触须、光点等）。 */
    const labels = new Int32Array(N * N).fill(-1);
    const comps = [];
    for (let start = 0; start < N * N; start++) {
      if (!fg[start] || labels[start] >= 0) continue;
      const ci = comps.length;
      let head = 0, tail = 0, area = 0, sx = 0, sy = 0;
      let x0 = N, y0 = N, x1 = -1, y1 = -1, touch = 0;
      q[tail++] = start; labels[start] = ci;
      while (head < tail) {
        const p = q[head++], x = p % N, y = (p / N) | 0;
        area++; sx += x; sy += y;
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y;
        if (x === 0 || x === N - 1 || y === 0 || y === N - 1) touch = 1;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || nx >= N || ny < 0 || ny >= N) continue;
          const np = ny * N + nx;
          if (fg[np] && labels[np] < 0) { labels[np] = ci; q[tail++] = np; }
        }
      }
      const cx = sx / area, cy = sy / area;
      const dx = (cx - (N - 1) / 2) / (N / 2), dy = (cy - (N - 1) / 2) / (N / 2);
      const center = Math.max(0.18, 1.35 - 0.65 * Math.hypot(dx, dy));
      comps.push({ i: ci, area, x0, y0, x1, y1, cx, cy, score: area * center * (touch && area < N * N * 0.01 ? 0.5 : 1) });
    }
    if (!comps.length) return null;
    comps.sort((a, b) => b.score - a.score);
    const main = comps[0];
    if (main.area < Math.max(8, N * N * 0.0015)) return null;

    const keep = new Uint8Array(N * N);
    const take = new Uint8Array(comps.length);
    take[main.i] = 1;
    const mw = main.x1 - main.x0 + 1, mh = main.y1 - main.y0 + 1;
    const ex = Math.max(6, mw * 0.55), ey = Math.max(6, mh * 0.55);
    for (const c of comps) {
      if (c === main) continue;
      if (c.area < Math.max(4, main.area * 0.006)) continue;
      if (c.cx < main.cx - mw * 0.75 - ex || c.cx > main.cx + mw * 0.75 + ex) continue;
      if (c.cy < main.cy - mh * 0.75 - ey || c.cy > main.cy + mh * 0.75 + ey) continue;
      if (c.x1 < main.x0 - ex || c.x0 > main.x1 + ex) continue;
      if (c.y1 < main.y0 - ey || c.y0 > main.y1 + ey) continue;
      take[c.i] = 1;
    }
    for (let p = 0; p < N * N; p++) if (labels[p] >= 0 && take[labels[p]]) keep[p] = 1;
    const filled = fillMaskHoles(keep, N);
    const mask = dilateMask(filled, N);

    let x0 = N, y0 = N, x1 = -1, y1 = -1, count = 0;
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      if (!mask[y * N + x]) continue;
      count++;
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    if (count < 12) return null;
    const w = x1 - x0 + 1, h = y1 - y0 + 1;
    if (w < 4 || h < 4 || w * h > N * N * 0.94) return null;
    const pad = Math.max(1, Math.round(Math.min(w, h) * 0.04));
    x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad);
    x1 = Math.min(N - 1, x1 + pad); y1 = Math.min(N - 1, y1 + pad);

    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = N; maskCanvas.height = N;
    const mctx = maskCanvas.getContext("2d", { willReadFrequently: true });
    const mi = mctx.createImageData(N, N);
    for (let p = 0; p < N * N; p++) {
      if (!mask[p]) continue;
      const i = p * 4;
      mi.data[i] = 255; mi.data[i + 1] = 255; mi.data[i + 2] = 255; mi.data[i + 3] = 255;
    }
    mctx.putImageData(mi, 0, 0);

    return {
      N, mask, maskCanvas,
      bbox: {
        x: x0 / N * src.width, y: y0 / N * src.height,
        w: (x1 - x0 + 1) / N * src.width,
        h: (y1 - y0 + 1) / N * src.height
      }
    };
  }

  function foregroundFor(src) {
    if (FG_CACHE.has(src)) return FG_CACHE.get(src);
    const fg = segmentForeground(src);
    FG_CACHE.set(src, fg);
    return fg;
  }

  /* 旧版纯启发式前景框，只在分离失败时兜底。 */
  function autoBoxHeuristic(src) {
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

  function autoBox(src) {
    const fg = foregroundFor(src);
    return fg ? fg.bbox : autoBoxHeuristic(src);
  }

  /* 手机照片常见偏色/白平衡漂移：额外生成一份按通道标准化的副本，
     与原图候选一起匹配，避免整张图偏黄/偏蓝时模板直接失效。 */
  function normalizedSource(src) {
    const c = document.createElement("canvas");
    c.width = src.width; c.height = src.height;
    const cc = c.getContext("2d", { willReadFrequently: true });
    cc.drawImage(src, 0, 0);
    const im = cc.getImageData(0, 0, c.width, c.height);
    const d = im.data, n = c.width * c.height;
    let sr = 0, sg = 0, sb = 0, qr = 0, qg = 0, qb = 0;
    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], g = d[i + 1], b = d[i + 2];
      sr += r; sg += g; sb += b; qr += r * r; qg += g * g; qb += b * b;
    }
    const mr = sr / n, mg = sg / n, mb = sb / n;
    const dr = Math.sqrt(Math.max(qr / n - mr * mr, 1e-6)) || 1;
    const dg = Math.sqrt(Math.max(qg / n - mg * mg, 1e-6)) || 1;
    const db = Math.sqrt(Math.max(qb / n - mb * mb, 1e-6)) || 1;
    for (let i = 0; i < d.length; i += 4) {
      d[i] = Math.max(0, Math.min(255, (d[i] - mr) / dr * 48 + 128));
      d[i + 1] = Math.max(0, Math.min(255, (d[i + 1] - mg) / dg * 48 + 128));
      d[i + 2] = Math.max(0, Math.min(255, (d[i + 2] - mb) / db * 48 + 128));
    }
    cc.putImageData(im, 0, 0);
    return c;
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
      /* 前景框通常只包住本体，向外再放一点，给深色描边、火焰/触须留位置 */
      for (const grow of [0.10, 0.24, 0.42]) {
        const gx = auto.w * grow / 2, gy = auto.h * grow / 2;
        const x0 = Math.max(0, auto.x - gx), y0 = Math.max(0, auto.y - gy);
        const x1 = Math.min(src.width, auto.x + auto.w + gx);
        const y1 = Math.min(src.height, auto.y + auto.h + gy);
        bases.push({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
      }
      for (const margin of [0, 0.12, 0.25, 0.40, 0.52]) {
        bases.push({
          x: auto.x + auto.w * margin / 2, y: auto.y + auto.h * margin / 2,
          w: auto.w * (1 - margin), h: auto.h * (1 - margin)
        });
      }
    }
    /* 旧版启发式框仍然有价值：当图标几乎占满画面、边缘背景很窄时，
       泛洪分割可能把一圈边框算进来，而旧框反而更贴合。两套框都作为候选，
       模板距离会自己选更合适的那个，不需要二选一。 */
    const oldAuto = autoBoxHeuristic(src);
    if (oldAuto && (!auto || Math.abs(oldAuto.x - auto.x) > 1 || Math.abs(oldAuto.y - auto.y) > 1 ||
        Math.abs(oldAuto.w - auto.w) > 1 || Math.abs(oldAuto.h - auto.h) > 1)) {
      for (const margin of [0, 0.12, 0.25, 0.40, 0.52]) {
        bases.push({
          x: oldAuto.x + oldAuto.w * margin / 2, y: oldAuto.y + oldAuto.h * margin / 2,
          w: oldAuto.w * (1 - margin), h: oldAuto.h * (1 - margin)
        });
      }
    }
    /* 中心裁切：图标通常位于选框中央；背景纹理/网格会让 autoBox 偏掉时兜底 */
    const side = Math.min(src.width, src.height);
    for (const frac of [0.34, 0.46, 0.60, 0.76]) {
      const s = side * frac;
      bases.push({
        x: (src.width - s) / 2, y: (src.height - s) / 2, w: s, h: s
      });
    }
    const c = document.createElement("canvas"); c.width = S; c.height = S;
    const cc = c.getContext("2d", { willReadFrequently: true });
    const seen = new Set();
    const sources = [src, normalizedSource(src)];
    for (let si = 0; si < sources.length; si++) {
      const source = sources[si];
      for (const b of bases) {
        const bw = Math.max(8, b.w), bh = Math.max(8, b.h);
        for (const fx of SHIFTS) for (const fy of SHIFTS) {
          const cw = Math.min(source.width, Math.max(8, Math.round(bw)));
          const ch = Math.min(source.height, Math.max(8, Math.round(bh)));
          let x0 = Math.round(b.x + bw * fx);
          let y0 = Math.round(b.y + bh * fy);
          x0 = Math.max(0, Math.min(x0, source.width - cw));
          y0 = Math.max(0, Math.min(y0, source.height - ch));
          const key = si + ":" + x0 + "," + y0 + "," + cw + "," + ch;
          if (seen.has(key)) continue;
          seen.add(key);
          for (const ang of ANGLES) {
            cc.clearRect(0, 0, S, S);
            cc.save();
            cc.translate(S / 2, S / 2);
            cc.rotate(ang * Math.PI / 180);
            cc.drawImage(source, x0, y0, cw, ch, -S / 2, -S / 2, S, S);
            cc.restore();
            const d = cc.getImageData(0, 0, S, S).data;
            const f = new Float32Array(S * S * 3);
            for (let i = 0, j = 0; i < S * S; i++) {
              f[j++] = d[i * 4] / 255; f[j++] = d[i * 4 + 1] / 255; f[j++] = d[i * 4 + 2] / 255;
            }
            /* 只保留极轻的大裁切偏好：中心裁切/小图标候选不应因为面积小而吃亏 */
            const prior = 0.012 * (1 - Math.min(1, (cw * ch) / (src.width * src.height)));
            out.push({ f, prior });
          }
        }
      }
    }
    return out;
  }

  function renderRecResults(items, title) {
    lastResults = items;
    $("#recCnt").textContent = title;
    $("#recResults").innerHTML = items.map((e, i) => `
      <div class="result" data-i="${i}">
        <img src="${e.image ? "../../" + e.image : (e.image_url || "")}" onerror="this.src='${e.image_url || ""}'">
        <div>
          <div class="cname"><span class="czh">${e.name_zh || e.name}</span><span class="badge">${KIND_LABEL[e.kind + "s"] || e.kind}</span>${e._badge || ""}</div>
          <div style="color:#8b93a3;font-size:11.5px">${e.name || ""}</div>
          <div class="score">${e._scoreText || ""}</div>
        </div>
      </div>`).join("");
    if (window.matchMedia("(max-width:640px)").matches) {
      requestAnimationFrame(() => $("#recCnt").scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }

  function templateDistance(m, C) {
    const idx = m.idx, n = idx.length;
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
    return bd;
  }

  function recognizeTemplate(region) {
    if (!MODEL.length) { $("#recCnt").textContent = "模型未加载。"; return; }
    const src = sourceFor(region);
    const C = candidates(src), t0 = performance.now();
    const best = new Float32Array(MODEL.length);
    for (let k = 0; k < MODEL.length; k++) best[k] = templateDistance(MODEL[k], C);
    const order = Array.from(MODEL.keys()).sort((a, b) => best[a] - best[b]).slice(0, 8);
    const ms = Math.round(performance.now() - t0);
    const gap = order.length > 1 ? best[order[1]] - best[order[0]] : 1;
    const near = gap < 0.025;
    const low = best[order[0]] > 0.72;
    const note = near ? " · 候选很接近，请点开确认" : (low ? " · 匹配度偏低，请确认" : "");
    const items = order.map((k, rank) => {
      const e = MODEL[k];
      const conf = Math.max(0, Math.min(100, Math.round((1 - best[k] / 1.5) * 100)));
      return { ...e, _badge: rank === 0 ? `<span class="badge" style="background:${near ? "#8a5a24" : "#2e6b46"}">${near ? "最接近" : "最佳"}</span>` : "", _scoreText: `匹配度 ${conf}%` };
    });
    renderRecResults(items, `识别结果（像素模板 · ${C.length} 候选 · ${ms}ms）${note} · 点击查看详情`);
  }

  async function recognize(region) {
    if (!img) { $("#recCnt").textContent = "请先上传/拍照。"; return; }
    if (activeEngine === "template" || activeEngine === "custom") {
      recognizeTemplate(region);
      return;
    }
    try {
      await prepareEngine(activeEngine);
    } catch (e) {
      $("#recCnt").textContent = `引擎加载失败：${e && e.message ? e.message : e}`;
      $("#engineStatus").style.display = "";
      $("#engineStatus").textContent = "可以切回「像素模板」立即识别；ORB / 端侧向量需要联网加载一次资源。";
      return;
    }
    try {
      if (activeEngine === "orb") recognizeOrb(region);
      else if (activeEngine === "embed") await recognizeEmbed(region);
    } catch (e) {
      $("#recCnt").textContent = `识别失败：${e && e.message ? e.message : e}`;
    }
  }
  $("#recBtn").onclick = () => recognize(sel && sel.w > 4 ? sel : null);
  $("#recAll").onclick = () => recognize(null);
  $("#recResults").addEventListener("click", e => {
    const el = e.target.closest(".result");
    if (!el) return;
    const rec = lastResults[+el.dataset.i];
    if (!rec) return;
    const kindKey = KIND_TO_GUIDE[rec.kind] || "items";
    const arr = G[kindKey] || [];
    const full = arr.find(x => x.id === rec.id) || arr.find(x => x.name === rec.name) || rec;
    openDetail(full, kindKey);
  });

  /* ---------- 两个新识别引擎：OpenCV.js ORB / Transformers.js DINOv2 ---------- */
  const engineStatus = $("#engineStatus");
  function setEngineStatus(text) {
    if (!engineStatus) return;
    engineStatus.style.display = text ? "" : "none";
    engineStatus.textContent = text || "";
  }
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error("加载失败：" + src));
      document.head.appendChild(s);
    });
  }

  /* 把选框/自动前景框标准化成正方形白底图。模板库和查询图使用同一套裁切规则。 */
  function canonicalCanvas(src, size = 256, margin = 0.06) {
    const c = document.createElement("canvas");
    c.width = size; c.height = size;
    const g = c.getContext("2d", { willReadFrequently: true });
    g.fillStyle = "#fff"; g.fillRect(0, 0, size, size);
    let sx = 0, sy = 0, sw = src.width, sh = src.height;
    const ab = autoBox(src);
    if (ab && ab.w > 8 && ab.h > 8 && ab.w * ab.h < src.width * src.height * 0.92) {
      const pad = Math.max(2, Math.min(ab.w, ab.h) * margin);
      sx = Math.max(0, ab.x - pad); sy = Math.max(0, ab.y - pad);
      sw = Math.min(src.width - sx, ab.w + pad * 2);
      sh = Math.min(src.height - sy, ab.h + pad * 2);
    } else {
      /* 没找到前景：取中心正方形，避免把整张游戏截图的背景全带进来 */
      const side = Math.min(src.width, src.height) * 0.92;
      sx = (src.width - side) / 2; sy = (src.height - side) / 2; sw = side; sh = side;
    }
    const inner = size * (1 - margin * 2);
    const sc = Math.min(inner / sw, inner / sh);
    const dw = Math.max(1, sw * sc), dh = Math.max(1, sh * sc);
    g.imageSmoothingEnabled = true;
    g.imageSmoothingQuality = "high";
    g.drawImage(src, sx, sy, sw, sh, (size - dw) / 2, (size - dh) / 2, dw, dh);
    return c;
  }

  /* 在 canonicalCanvas 的基础上，把前景以外的背景刷成白色，并返回对齐的
     前景 mask。DINOv2 / ORB 的模板是在白底图标上生成的；查询图也去掉背景后，
     颜色、边缘和特征点才不会把地板、墙壁、UI 算进去。 */
  function canonicalClean(src, size = 256, margin = 0.06) {
    const c = document.createElement("canvas");
    c.width = size; c.height = size;
    const g = c.getContext("2d", { willReadFrequently: true });
    g.fillStyle = "#fff"; g.fillRect(0, 0, size, size);

    const fg = foregroundFor(src);
    let box = fg ? fg.bbox : null;
    let useMask = !!box;
    if (!box || box.w * box.h > src.width * src.height * 0.92) {
      useMask = false;
      const ab = autoBoxHeuristic(src);
      if (ab && ab.w > 8 && ab.h > 8 && ab.w * ab.h < src.width * src.height * 0.92) {
        box = ab;
      } else {
        const side = Math.min(src.width, src.height) * 0.92;
        box = { x: (src.width - side) / 2, y: (src.height - side) / 2, w: side, h: side };
      }
    }

    const inner = size * (1 - margin * 2);
    const sc = Math.min(inner / box.w, inner / box.h);
    const dw = Math.max(1, box.w * sc), dh = Math.max(1, box.h * sc);
    const dx = (size - dw) / 2, dy = (size - dh) / 2;

    let maskOut = null;
    if (useMask && fg) {
      const tmp = document.createElement("canvas");
      tmp.width = size; tmp.height = size;
      const tg = tmp.getContext("2d", { willReadFrequently: true });
      tg.imageSmoothingEnabled = true; tg.imageSmoothingQuality = "high";
      tg.drawImage(src, box.x, box.y, box.w, box.h, dx, dy, dw, dh);

      const mc = document.createElement("canvas");
      mc.width = size; mc.height = size;
      const mg = mc.getContext("2d", { willReadFrequently: true });
      mg.imageSmoothingEnabled = true; mg.imageSmoothingQuality = "high";
      const mx = Math.max(0, box.x / src.width * fg.N);
      const my = Math.max(0, box.y / src.height * fg.N);
      const mw = Math.min(fg.N - mx, box.w / src.width * fg.N);
      const mh = Math.min(fg.N - my, box.h / src.height * fg.N);
      mg.drawImage(fg.maskCanvas, mx, my, mw, mh, dx, dy, dw, dh);

      tg.globalCompositeOperation = "destination-in";
      tg.drawImage(mc, 0, 0);
      tg.globalCompositeOperation = "source-over";
      g.drawImage(tmp, 0, 0);
      maskOut = mc;
    } else {
      g.drawImage(src, box.x, box.y, box.w, box.h, dx, dy, dw, dh);
    }
    return { canvas: c, mask: maskOut };
  }

  function recFor(kind, id) {
    return REC_BY_KEY.get(kind + ":" + id) || null;
  }

  /* ---------- ② OpenCV.js ORB：预计算描述子 + BFMatcher 投票 ---------- */
  const orbState = { ready: false, promise: null, cv: null, entries: null, counts: null, train: null, ids: null, bf: null };

  async function ensureOpenCV() {
    if (window.cv && window.cv.Mat && window.cv.ORB) return true;
    if (!window.__ocvLoadPromise) {
      window.__ocvLoadPromise = loadScript("vendor/opencv.js").catch(e => {
        window.__ocvLoadPromise = null;
        throw e;
      });
    }
    await window.__ocvLoadPromise;
    const t0 = Date.now();
    while (Date.now() - t0 < 120000) {
      const c = window.cv;
      if (c && c.Mat && c.ORB && c.BFMatcher && c.KeyPointVector) return true;
      await new Promise(r => setTimeout(r, 100));
    }
    throw new Error("OpenCV.js 初始化超时");
  }

  async function ensureOrb() {
    if (orbState.ready) return orbState;
    if (orbState.promise) return orbState.promise;
    orbState.promise = (async () => {
      setEngineStatus("正在加载 OpenCV.js（约 11MB，首次较慢）…");
      /* 注意：cv 对象自带 then()，不能从 async 函数直接 return cv，否则会被当成 Promise 递归等待。 */
      await ensureOpenCV();
      const cv = window.cv;
      if (!window.ORB_DB) {
        setEngineStatus("正在加载 ORB 特征库（约 4MB）…");
        await loadScript("recog/orb_db.js");
      }
      const db = window.ORB_DB;
      const entries = db.entries || [];
      const counts = new Array(entries.length);
      const raw = new Array(entries.length);
      let total = 0;
      for (let i = 0; i < entries.length; i++) {
        const b = b64ToBytes(entries[i].d);
        raw[i] = b; counts[i] = b.length / 32; total += counts[i];
      }
      const train = new cv.Mat(total, 32, cv.CV_8U);
      const ids = new Int32Array(total);
      let row = 0;
      for (let i = 0; i < entries.length; i++) {
        train.data.set(raw[i], row * 32);
        for (let j = 0; j < counts[i]; j++) ids[row + j] = i;
        row += counts[i];
      }
      orbState.cv = cv; orbState.entries = entries; orbState.counts = counts;
      orbState.train = train; orbState.ids = ids;
      orbState.bf = new cv.BFMatcher(cv.NORM_HAMMING, false);
      orbState.ready = true;
      setEngineStatus(`ORB 已就绪：${entries.length} 个模板 / ${total} 个特征点。`);
      return orbState;
    })();
    try { return await orbState.promise; }
    catch (e) { orbState.promise = null; throw e; }
  }

  function orbQuery(cv, canvas, maskCanvas) {
    const rgba = cv.imread(canvas);
    const gray = new cv.Mat();
    cv.cvtColor(rgba, gray, cv.COLOR_RGBA2GRAY);
    const orb = new cv.ORB(150, 1.2, 8, 16, 0, 2, cv.ORB_HARRIS_SCORE, 31, 10);
    const kp = new cv.KeyPointVector();
    const desc = new cv.Mat();
    let mask = new cv.Mat();
    let maskRgba = null;
    try {
      if (maskCanvas) {
        maskRgba = cv.imread(maskCanvas);
        mask = new cv.Mat();
        cv.cvtColor(maskRgba, mask, cv.COLOR_RGBA2GRAY);
      }
      orb.detectAndCompute(gray, mask, kp, desc);
      const out = desc.rows ? desc.clone() : null;
      return { desc: out, kps: kp.size() };
    } finally {
      if (maskRgba) maskRgba.delete();
      kp.delete(); desc.delete(); mask.delete(); orb.delete(); gray.delete(); rgba.delete();
    }
  }

  function orbVotes(state, desc) {
    const cv = state.cv;
    const votes = new Map();
    const ratio = Number(state.entries && window.ORB_DB.meta.ratio) || 0.78;
    const maxDist = Number(window.ORB_DB.meta.dist) || 64;
    let matches = null;
    try {
      matches = new cv.DMatchVectorVector();
      state.bf.knnMatch(desc, state.train, matches, 2);
      for (let i = 0; i < matches.size(); i++) {
        const rowm = matches.get(i);
        if (rowm.size() >= 2) {
          const a = rowm.get(0), b = rowm.get(1);
          if (a.distance < ratio * b.distance && a.distance < maxDist) {
            const ti = state.ids[a.trainIdx];
            votes.set(ti, (votes.get(ti) || 0) + 1);
          }
        }
        rowm.delete();
      }
    } catch (e) {
      /* 某些精简版 OpenCV.js 没有 DMatchVectorVector，退回最近邻计数 */
      if (matches) { try { matches.delete(); } catch (_) {} }
      matches = new cv.DMatchVector();
      state.bf.match(desc, state.train, matches);
      for (let i = 0; i < matches.size(); i++) {
        const a = matches.get(i);
        if (a.distance < maxDist) {
          const ti = state.ids[a.trainIdx];
          votes.set(ti, (votes.get(ti) || 0) + 1);
        }
      }
    } finally {
      if (matches) { try { matches.delete(); } catch (_) {} }
    }
    return votes;
  }

  function recognizeOrb(region) {
    const state = orbState;
    if (!state.ready) { $("#recCnt").textContent = "ORB 尚未就绪。"; return; }
    const src = sourceFor(region);
    const clean = canonicalClean(src, 192, 0.06);
    const canvas = clean.canvas;
    const t0 = performance.now();
    let q;
    try { q = orbQuery(state.cv, canvas, clean.mask); }
    catch (e) { $("#recCnt").textContent = "ORB 特征提取失败：" + e.message; return; }
    if (!q || !q.desc || q.desc.rows < 6) {
      if (q && q.desc) q.desc.delete();
      setEngineStatus("ORB 没提取到足够特征点，已回退像素模板。");
      recognizeTemplate(region);
      return;
    }
    const votes = orbVotes(state, q.desc);
    const qn = q.desc.rows;
    q.desc.delete();
    const ms = Math.round(performance.now() - t0);
    const ranked = [...votes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    /* 照片模糊、图标很小的时候 ORB 可能只命中 1–2 个点，这时排序基本是噪声；
       直接回退到像素模板，避免把错误候选强行标成“最佳”。 */
    if (!ranked.length || ranked[0][1] < 3) {
      setEngineStatus(`ORB 匹配点太少（最高 ${ranked.length ? ranked[0][1] : 0} 个），已回退像素模板。`);
      recognizeTemplate(region);
      return;
    }
    const items = [];
    for (const [ti, count] of ranked) {
      const e = state.entries[ti];
      const rec = recFor(e.k, e.id);
      if (!rec) continue;
      items.push({ ...rec, _badge: items.length === 0 ? '<span class="badge" style="background:#2e6b46">最佳</span>' : "", _scoreText: `匹配点 ${count}` });
    }
    if (!items.length) {
      setEngineStatus("ORB 没有命中模板，已回退像素模板。");
      recognizeTemplate(region);
      return;
    }
    const gap = ranked.length > 1 ? ranked[0][1] - ranked[1][1] : 999;
    const note = gap <= 1 ? " · 候选很接近，请点开确认" : "";
    renderRecResults(items, `识别结果（OpenCV ORB · 查询 ${qn} 个特征点 · ${ms}ms）${note} · 点击查看详情`);
  }

  /* ---------- ③ Transformers.js + DINOv2：CLS 向量 + 颜色/边缘/灰度特征 ---------- */
  const embedState = { ready: false, promise: null, pipe: null, rawImage: null, entries: null, meta: null };

  async function ensureEmbed() {
    if (embedState.ready) return embedState;
    if (embedState.promise) return embedState.promise;
    embedState.promise = (async () => {
      setEngineStatus("正在加载端侧向量模型 DINOv2（约 24MB，首次需下载并缓存）…");
      const mod = await import(new URL("vendor/transformers/transformers.min.js", location.href).href);
      const env = mod.env;
      env.allowRemoteModels = false;
      env.localModelPath = new URL("vendor/models/", location.href).href;
      env.backends.onnx.wasm.wasmPaths = new URL("vendor/transformers/", location.href).href;
      env.backends.onnx.wasm.numThreads = 1;
      env.backends.onnx.wasm.simd = true;
      const pipe = await mod.pipeline("image-feature-extraction", "dinov2-small", { quantized: true });
      if (!window.EMBED_DB) {
        setEngineStatus("正在加载向量库（约 2MB）…");
        await loadScript("recog/embed_db.js");
      }
      const db = window.EMBED_DB;
      const entries = (db.entries || []).map(e => {
        const u = b64ToBytes(e.v);
        return { ...e, q: new Int8Array(u.buffer), s: e.s, n: e.n };
      });
      embedState.pipe = pipe; embedState.rawImage = mod.RawImage;
      embedState.entries = entries; embedState.meta = db.meta; embedState.ready = true;
      setEngineStatus(`端侧向量已就绪：DINOv2-small / ${entries.length} 个模板 / 1408 维混合向量。`);
      return embedState;
    })();
    try { return await embedState.promise; }
    catch (e) { embedState.promise = null; throw e; }
  }

  function normalizeFloat(a) {
    let n = 0;
    for (let i = 0; i < a.length; i++) n += a[i] * a[i];
    n = Math.sqrt(n) || 1;
    for (let i = 0; i < a.length; i++) a[i] /= n;
    return a;
  }

  function embedQueryFeatures(canvas, dino, maskCanvas) {
    const g = canvas.getContext("2d", { willReadFrequently: true });
    const d = g.getImageData(0, 0, 256, 256).data;
    let fgMask = null;
    if (maskCanvas) {
      const md = maskCanvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 256, 256).data;
      fgMask = new Uint8Array(256 * 256);
      for (let p = 0; p < fgMask.length; p++) fgMask[p] = md[p * 4 + 3] > 96 ? 1 : 0;
    }
    const hist = new Float32Array(512);
    const gray = new Float32Array(256 * 256);
    for (let i = 0, p = 0; i < d.length; i += 4, p++) {
      const r = d[i], gg = d[i + 1], b = d[i + 2];
      gray[p] = (r * .299 + gg * .587 + b * .114) / 255;
      if ((!fgMask || fgMask[p]) && Math.min(r, gg, b) < 245) hist[(r >> 5) * 64 + (gg >> 5) * 8 + (b >> 5)]++;
    }
    for (let i = 0; i < 512; i++) hist[i] = Math.sqrt(hist[i]);
    normalizeFloat(hist);
    const edge = new Float32Array(256 * 256);
    for (let y = 1; y < 255; y++) for (let x = 1; x < 255; x++) {
      const p = y * 256 + x;
      const gx = -gray[p - 257] + gray[p - 255] - 2 * gray[p - 1] + 2 * gray[p + 1] - gray[p + 255] + gray[p + 257];
      const gy = -gray[p - 257] - 2 * gray[p - 256] - gray[p - 255] + gray[p + 255] + 2 * gray[p + 256] + gray[p + 257];
      edge[p] = Math.hypot(gx, gy) > 0.28 ? 1 : 0;
    }
    const e16 = new Float32Array(256), g16 = new Float32Array(256);
    for (let by = 0; by < 16; by++) for (let bx = 0; bx < 16; bx++) {
      let se = 0, sg = 0;
      for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
        const p = (by * 16 + y) * 256 + bx * 16 + x;
        se += edge[p]; sg += gray[p];
      }
      e16[by * 16 + bx] = se / 256; g16[by * 16 + bx] = sg / 256;
    }
    let me = 0, mg = 0;
    for (let i = 0; i < 256; i++) { me += e16[i]; mg += g16[i]; }
    me /= 256; mg /= 256;
    for (let i = 0; i < 256; i++) { e16[i] -= me; g16[i] -= mg; }
    normalizeFloat(e16); normalizeFloat(g16);
    const dinoN = normalizeFloat(Float32Array.from(dino));
    return [dinoN, hist, e16, g16];
  }

  async function recognizeEmbed(region) {
    const state = embedState;
    if (!state.ready) { $("#recCnt").textContent = "端侧向量模型尚未就绪。"; return; }
    const t0 = performance.now();
    const src = sourceFor(region);
    const clean = canonicalClean(src, 256, 0.06);
    const canvas = clean.canvas;
    let out;
    try {
      /* Transformers.js v2.17 的 RawImage 没有 fromCanvas，直接用 ImageData 构造。 */
      const g = canvas.getContext("2d", { willReadFrequently: true });
      const id = g.getImageData(0, 0, 256, 256);
      const raw = new state.rawImage(id.data, 256, 256, 4);
      out = await state.pipe(raw);
    } catch (e) {
      $("#recCnt").textContent = "端侧模型推理失败：" + (e.message || e);
      return;
    }
    const dims = out.dims || [];
    const dino = dims.length === 3 ? out.data.slice(0, dims[2]) : out.data.slice(0, 384);
    if (out && typeof out.dispose === "function") out.dispose();
    const feats = embedQueryFeatures(canvas, dino, clean.mask);
    const qn = feats.map(a => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * a[i]; return Math.sqrt(s) || 1; });
    const blocks = state.meta.blocks, weights = state.meta.weights;
    const scores = [];
    for (let ei = 0; ei < state.entries.length; ei++) {
      const e = state.entries[ei];
      let off = 0, score = 0;
      for (let b = 0; b < blocks.length; b++) {
        const dim = blocks[b];
        let dot = 0;
        for (let i = 0; i < dim; i++) dot += e.q[off + i] * feats[b][i];
        /* DB 是 int8 分块量化，先乘回每块 scale 再算余弦 */
        score += weights[b] * (dot * (e.s[b] || 1)) / ((e.n[b] || 1) * qn[b]);
        off += dim;
      }
      scores.push([ei, score]);
    }
    scores.sort((a, b) => b[1] - a[1]);
    const maxScore = weights.reduce((a, b) => a + b, 0) || 1;

    /* DINOv2 负责整体语义，像素模板负责局部颜色/轮廓复核。
       向量模型对“粉色肉块”这类形状容易混淆，只靠 CLS 会输给形似的错误图标；
       对前 24 个候选补算一次模板距离，通常几十毫秒，能把明显的错误压下去。 */
    const C = candidates(src);
    const ranked = [];
    for (const [ei, score] of scores.slice(0, 24)) {
      const e = state.entries[ei];
      const rec = recFor(e.k, e.id);
      if (!rec) continue;
      const m = BUILTIN_MODEL_BY_KEY.get(e.k + ":" + e.id);
      const td = m ? templateDistance(m, C) : 1.5;
      const tpl = Math.max(0, Math.min(1, 1 - td / 1.5));
      const emb = score / maxScore;
      ranked.push({ rec, score, tpl, combined: emb * 0.70 + tpl * 0.30 });
    }
    ranked.sort((a, b) => b.combined - a.combined);
    const ms = Math.round(performance.now() - t0);
    const items = ranked.slice(0, 8).map((x, rank) => ({
      ...x.rec,
      _badge: rank === 0 ? '<span class="badge" style="background:#2e6b46">最佳</span>' : "",
      _scoreText: `综合 ${Math.round(x.combined * 100)}% · DINOv2 ${x.score.toFixed(2)} · 模板 ${Math.round(x.tpl * 100)}%`
    }));
    const gap = ranked.length > 1 ? ranked[0].combined - ranked[1].combined : 1;
    const note = gap < 0.025 ? " · 候选很接近，请点开确认" : "";
    renderRecResults(items, `识别结果（DINOv2 + 像素模板复核 · ${ms}ms）${note} · 点击查看详情`);
  }

  async function prepareEngine(name) {
    if (name === "orb") return ensureOrb();
    if (name === "embed") return ensureEmbed();
    return null;
  }

  /* ---------- 识别后端切换 ---------- */
  $("#backend").onchange = () => {
    const v = $("#backend").value;
    activeEngine = v;
    lastResults = [];
    $("#recResults").innerHTML = "";
    $("#recCnt").textContent = "";
    if (v === "template") {
      MODEL = decodeModel(R); modelName = "内置图标库";
      $("#backendHint").textContent = `当前：内置 ${MODEL.length} 个图标模板（像素模板）。`;
      setEngineStatus("");
    } else if (v === "custom") {
      $("#backendHint").textContent = "当前：自定义模板。请选择与 recognition.js 同格式的 JSON。";
      $("#modelFile").click();
    } else if (v === "orb") {
      $("#backendHint").textContent = "当前：OpenCV.js ORB 特征点匹配（道具/饰品/卡牌，不含药丸）。首次使用会加载约 11MB 引擎和 4MB 特征库。";
      prepareEngine("orb").catch(e => setEngineStatus("ORB 加载失败：" + e.message + "。可切回像素模板。"));
    } else if (v === "embed") {
      $("#backendHint").textContent = "当前：端侧 DINOv2 向量匹配（道具/饰品/卡牌，不含药丸）。首次使用会加载约 24MB 模型 + 运行库，之后离线可用。";
      prepareEngine("embed").catch(e => setEngineStatus("端侧模型加载失败：" + e.message + "。可切回像素模板。"));
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
        MODEL = m; modelName = f.name; activeEngine = "custom";
        $("#backendHint").textContent = `当前：${f.name}，共 ${m.length} 条。`;
        $("#recCnt").textContent = `已加载模型：${m.length} 条`;
      } catch (err) {
        $("#recCnt").textContent = "模型加载失败：" + err.message;
        $("#backend").value = "template";
        activeEngine = "template";
        MODEL = decodeModel(R);
      }
    };
    fr.readAsText(f);
  };
  $("#reset").onclick = () => { if (img) draw(img); lastResults = []; $("#recResults").innerHTML = ""; $("#recCnt").textContent = ""; };

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
