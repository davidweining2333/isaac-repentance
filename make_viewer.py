#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成单文件网页查看器 viewer.html（数据内嵌，可离线双击打开）。"""
import json, os, html

ROOT = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(ROOT, "json", "isaac_repentance_all.json"), encoding="utf-8"))

payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>以撒的结合：忏悔 全资料</title>
<style>
  :root { --bg:#14161c; --panel:#1c1f28; --panel2:#232733; --line:#2c313d;
          --fg:#e6e8ee; --dim:#9aa2b2; --acc:#e0a458; --acc2:#7aa2f7; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif; }
  header { position:sticky; top:0; z-index:20; background:#101218;
           border-bottom:1px solid var(--line); padding:12px 18px; }
  h1 { margin:0 0 8px; font-size:18px; font-weight:650; }
  h1 small { color:var(--dim); font-weight:400; font-size:12px; margin-left:8px; }
  .tabs { display:flex; flex-wrap:wrap; gap:6px; }
  .tab { padding:5px 12px; border:1px solid var(--line); border-radius:999px;
         background:var(--panel); color:var(--dim); cursor:pointer; font-size:13px;
         user-select:none; }
  .tab:hover { color:var(--fg); border-color:#3a4150; }
  .tab.on { background:var(--acc); border-color:var(--acc); color:#20160a; font-weight:600; }
  .bar { display:flex; gap:10px; margin:14px 18px 0; align-items:center; flex-wrap:wrap; }
  input[type=search] { flex:1; min-width:200px; padding:9px 13px; border-radius:9px;
    border:1px solid var(--line); background:var(--panel); color:var(--fg); font-size:14px; }
  input[type=search]:focus { outline:none; border-color:var(--acc2); }
  .cnt { color:var(--dim); font-size:12px; }
  main { padding:14px 18px 60px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:12px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:12px;
          padding:13px 15px; cursor:pointer; transition:.12s; }
  .card:hover { border-color:#3a4150; background:var(--panel2); }
  .card.open { border-color:var(--acc); }
  .ttl { font-weight:650; font-size:15px; }
  .zh { color:var(--acc); margin-left:6px; font-weight:600; }
  .id { float:right; color:var(--dim); font-size:12px; }
  .meta { color:var(--dim); font-size:12px; margin:3px 0 6px; }
  .desc { color:#c8cdd8; font-size:13px; white-space:pre-wrap; }
  .chead { display:flex; gap:11px; align-items:flex-start; }
  .cbody { flex:1; min-width:0; }
  .thumb { width:56px; height:56px; object-fit:contain; border-radius:9px;
           background:#262b37; flex:none; image-rendering:auto; }
  .thumb.noimg { opacity:.25; }
  .thumb.sm { width:32px; height:32px; border-radius:6px; }
  .card .id { float:none; display:block; }
  .more { display:none; margin-top:10px; padding-top:10px; border-top:1px dashed var(--line);
          font-size:12.5px; }
  .card.open .more { display:block; }
  .kv { margin:3px 0; }
  .kv b { color:var(--dim); font-weight:500; margin-right:6px; }
  .chip { display:inline-block; background:#2a3040; color:#b7c0d0; border-radius:6px;
          padding:1px 7px; font-size:11px; margin:2px 3px 0 0; }
  .q { display:inline-block; width:20px; height:20px; line-height:20px; text-align:center;
       border-radius:5px; font-size:11px; font-weight:700; margin-right:7px; }
  .q0{background:#4b5266;color:#fff}.q1{background:#5b8c3a;color:#fff}
  .q2{background:#3a7bb0;color:#fff}.q3{background:#8a5bb0;color:#fff}
  .q4{background:#c08b2e;color:#fff}.qn{background:#3a4150;color:#aaa}
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }
  th { color:var(--dim); font-weight:600; position:sticky; top:0; background:var(--panel2); }
  tr:hover td { background:var(--panel2); }
  .wrap { overflow:auto; border:1px solid var(--line); border-radius:12px; background:var(--panel); }
  .ttl-line { margin:0 18px 8px; color:var(--dim); font-size:13px; }
  .empty { color:var(--dim); padding:40px; text-align:center; }
</style>
</head>
<body>
<header>
  <h1>以撒的结合：忏悔 / 忏悔+ <small>全资料数据集 · 内嵌离线查看</small></h1>
  <div class="tabs" id="tabs"></div>
</header>
<div class="bar">
  <input type="search" id="q" placeholder="搜索名称 / 中文名 / 描述 / ID …">
  <span class="cnt" id="cnt"></span>
</div>
<div class="ttl-line" id="sub"></div>
<main id="main"></main>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);

// 每个标签页：标题、数据、卡片 or 表格、字段映射
const TABS = [
  {k:'items',   t:'道具',   view:'card', n:()=>D.items.length},
  {k:'trinkets',t:'饰品',   view:'card', n:()=>D.trinkets.length},
  {k:'cards',   t:'卡牌',   view:'card', n:()=>D.cards.length},
  {k:'pills',   t:'药丸',   view:'card', n:()=>D.pills.length},
  {k:'item_pools', t:'道具池', view:'pool', n:()=>D.item_pools.length},
  {k:'characters', t:'角色', view:'table', n:()=>D.characters.length,
   cols:['id','name','damage','tears','speed','range','unlocked_by','added_in'],
   head:['ID','名称','伤害','射速','移速','射程','解锁','引入']},
  {k:'transformations', t:'变形', view:'table', n:()=>D.transformations.length,
   cols:['id','name','items'], head:['ID','名称','所需道具ID']},
  {k:'achievements', t:'成就', view:'card', n:()=>D.achievements.length},
  {k:'challenges', t:'挑战', view:'card', n:()=>D.challenges.length},
  {k:'entities', t:'怪物', view:'table', n:()=>D.entities.length,
   cols:['id','variant','subtype','name','type','added_in'],
   head:['ID','变体','子类','名称','类型','引入']},
  {k:'floors', t:'楼层', view:'table', n:()=>D.floors.length,
   cols:['name','chapter','stage','bosses','unlocked_by'],
   head:['名称','章节','代号','Boss','解锁']},
  {k:'room_types', t:'房间类型', view:'table', n:()=>D.room_types.length,
   cols:['name','type','stage_name','id_range'], head:['名称','类型','所属楼层','ID区间']},
  {k:'room_guides', t:'房间机制', view:'text', n:()=>Object.keys(D.room_guides).length},
];

let cur = 'items';
let query = '';

function esc(s){ return (s==null?'':String(s)).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

function img(o, cls){
  const c = cls||'thumb';
  const src = o.image || o.image_url || '';
  if(!src) return `<div class="${c} noimg"></div>`;
  return `<img class="${c}" src="${src}" data-fb="${o.image_url||''}" loading="lazy" onerror="imgFail(this)">`;
}
function imgFail(el){
  const fb = el.getAttribute('data-fb');
  if(fb && el.getAttribute('src')!==fb){ el.setAttribute('data-fb',''); el.src=fb; return; }
  el.classList.add('noimg'); el.removeAttribute('src');
}

function renderTabs(){
  $('#tabs').innerHTML = TABS.map(x=>
    `<div class="tab ${x.k===cur?'on':''}" data-k="${x.k}">${x.t} <b style="opacity:.7">${x.n()}</b></div>`
  ).join('');
  document.querySelectorAll('.tab').forEach(el=>el.onclick=()=>{ cur=el.dataset.k; renderTabs(); render(); });
}

function match(o){
  if(!query) return true;
  return JSON.stringify(o).toLowerCase().includes(query);
}

function render(){
  const tab = TABS.find(x=>x.k===cur);
  $('#sub').textContent = '';
  if(tab.view==='text'){
    const entries = Object.entries(D.room_guides).filter(([k,v])=> !query || (k+v).toLowerCase().includes(query));
    $('#cnt').textContent = entries.length+' 篇';
    $('#main').innerHTML = entries.map(([k,v])=>`
      <div class="card"><div class="ttl">${esc(k)}</div>
      <div class="desc">${esc(v.slice(0,600))}${v.length>600?' …':''}</div></div>`).join('')
      || '<div class="empty">无匹配</div>';
    return;
  }
  const rows = D[cur].filter(match);
  $('#cnt').textContent = rows.length+' 条';

  if(tab.view==='card'){
    $('#main').innerHTML = '<div class="grid">'+rows.map((o,i)=>{
      const zh = o.name_zh? `<span class="zh">${esc(o.name_zh)}</span>`:'';
      const q = o.quality!=null? `<span class="q q${o.quality}">${o.quality}</span>`
                               : `<span class="q qn">–</span>`;
      const title = o.name || o.description || o.wiki_page || ('#'+(o.id??i));
      const sub = [o.quote, o.type, o.added_in, o.goal].filter(Boolean).map(esc).join(' · ');
      const desc = o.description_zh || o.description_en || o.requirements || o.description || '';
      let more = '';
      for(const [k,v] of Object.entries(o)){
        if(['name','name_zh','description_zh','description_en'].includes(k)) continue;
        if(v===''||v==null||(Array.isArray(v)&&!v.length)) continue;
        const val = Array.isArray(v)? v.map(x=>`<span class="chip">${esc(x)}</span>`).join('') : esc(v);
        more += `<div class="kv"><b>${k}</b>${val}</div>`;
      }
      return `<div class="card" onclick="this.classList.toggle('open')">
        <div class="chead">
          ${img(o)}
          <div class="cbody">
            <div class="ttl">${q}${esc(title)}${zh}</div>
            <div class="meta">#${o.id??o.number??''}${sub?' · '+sub:''}</div>
          </div>
        </div>
        <div class="desc">${esc(desc).slice(0,180)}</div>
        <div class="more">${more}</div>
      </div>`;
    }).join('')+'</div>' || '<div class="empty">无匹配</div>';
    return;
  }

  if(tab.view==='pool'){
    $('#main').innerHTML = rows.map(p=>`
      <div class="card"><div class="chead">${img(p)}<div class="cbody">
        <div class="ttl">${esc(p.name)}${p.is_greed?' <span class="chip">贪婪</span>':''}</div>
        <div class="meta">${p.items.length} 个道具 · ${esc(p.price_type||'')}</div>
      </div></div>
      <div>${p.items.map(x=>`<span class="chip">${esc(x.name)} ×${x.weight}</span>`).join('')}</div>
      </div>`).join('') || '<div class="empty">无匹配</div>';
    return;
  }

  // table
  const cols = tab.cols, head = tab.head;
  const hasImg = rows.some(o=>o.image);
  const th = (hasImg?'<th></th>':'') + head.map(h=>`<th>${h}</th>`).join('');
  const td = o => (hasImg?`<td>${o.image?img(o,'thumb sm'):''}</td>`:'')
    + cols.map(c=>{ let v=o[c]; if(Array.isArray(v)) v=v.join(', '); return `<td>${esc(v)}</td>`; }).join('');
  $('#main').innerHTML = `<div class="wrap"><table><thead><tr>${th}</tr></thead>
    <tbody>${rows.map(o=>`<tr>${td(o)}</tr>`).join('')}</tbody></table></div>`
    || '<div class="empty">无匹配</div>';
}

$('#q').addEventListener('input', e=>{ query = e.target.value.trim().toLowerCase(); render(); });
renderTabs(); render();
</script>
</body>
</html>
"""

out = HTML.replace("__DATA__", payload)
path = os.path.join(ROOT, "viewer.html")
with open(path, "w", encoding="utf-8") as f:
    f.write(out)
print("已生成 viewer.html:", round(os.path.getsize(path)/1024/1024, 2), "MB")
