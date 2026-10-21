#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成单文件网页查看器 viewer.html（数据内嵌，可离线双击打开）。

英文原文字段（name / description / requirements 等）始终保留；中文作为
i18n 覆盖层加载。中文缺失时明确显示“中文待补”，不会把英文假装成中文。
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "json", "isaac_repentance_all.json")
ZH_PATH = os.path.join(ROOT, "i18n", "zh.json")

with open(DATA_PATH, encoding="utf-8") as f:
    data = json.load(f)
with open(ZH_PATH, encoding="utf-8") as f:
    ZH = json.load(f)

# Drop stale image references whose local file is missing (e.g. the English
# wiki image host was under maintenance), so the UI can show a proper fallback
# instead of a broken image.
for table in ("items", "trinkets", "cards", "characters", "transformations", "entities", "floors", "item_pools"):
    for rec in data.get(table, []):
        img = rec.get("image")
        if img and not os.path.exists(os.path.join(ROOT, img)):
            rec["image"] = ""
            rec["image_url"] = ""

# ---------------------------------------------------------------- enrichment
def put_zh(rec, **fields):
    for k, v in fields.items():
        if v:
            rec[k] = v


# item / trinket / card / pill translations already live in the main dataset
item_zh_by_name = {x.get("name"): x.get("name_zh", "") for x in data.get("items", []) if x.get("name")}
item_zh_by_id = {x.get("id"): x.get("name_zh", "") for x in data.get("items", []) if x.get("id") is not None}

# Achievements: Chinese wiki table + downloaded achievement sprites.
for a in data.get("achievements", []):
    z = ZH.get("achievements", {}).get(str(a.get("id")), {})
    put_zh(a,
           name_zh=z.get("name_zh"),
           description_zh=z.get("description_zh"),
           requirements_zh=z.get("requirements_zh"),
           reward_zh=z.get("reward_zh"))
    img = z.get("image")
    if img and os.path.exists(os.path.join(ROOT, img)):
        a["image"] = img
        a["image_url"] = ""
    else:
        a["image"] = ""

# Challenges
for c in data.get("challenges", []):
    put_zh(c, name_zh=ZH.get("challenges", {}).get(str(c.get("number")), ""))

# Item pools + item chips
for p in data.get("item_pools", []):
    put_zh(p, name_zh=ZH.get("item_pools", {}).get(p.get("name"), ""))
    for it in p.get("items", []):
        it["name_zh"] = item_zh_by_name.get(it.get("name"), "")

# Characters
char_images = ZH.get("character_images", {})
for c in data.get("characters", []):
    put_zh(c, name_zh=ZH.get("characters", {}).get(c.get("name"), ""))
    img = char_images.get(c.get("name"))
    if img and os.path.exists(os.path.join(ROOT, img)):
        c["image"] = img
        c["image_url"] = ""

# Transformations + readable item names
transformation_images = ZH.get("transformation_images", {})
for t in data.get("transformations", []):
    put_zh(t, name_zh=ZH.get("transformations", {}).get(t.get("name"), ""))
    img = transformation_images.get(t.get("name"))
    if img and os.path.exists(os.path.join(ROOT, img)):
        t["image"] = img
        t["image_url"] = ""
    names = []
    for iid in t.get("items", []):
        if iid in item_zh_by_id:
            names.append(item_zh_by_id[iid] or str(iid))
        else:
            names.append(str(iid))
    if names:
        t["item_names_zh"] = names

# Entities: id.variant.subtype is the exact key used by the Chinese wiki.
entity_images = ZH.get("entity_images", {})
for e in data.get("entities", []):
    key = f'{e.get("id", "") or 0}.{e.get("variant", 0)}.{e.get("subtype", 0)}'
    put_zh(e, name_zh=ZH.get("entities", {}).get(key, ""))
    img = entity_images.get(key)
    if img and os.path.exists(os.path.join(ROOT, img)):
        e["image"] = img
        e["image_url"] = ""

# Floors: the Chinese wiki uses screenshots/icons for each stage.  The main
# dataset already points at local files for most stages; fill in the gaps by
# the conventional slug and let Greed variants reuse their base floor image.
for f in data.get("floors", []):
    put_zh(f, name_zh=ZH.get("floors", {}).get(f.get("name"), ""))
    if not f.get("image"):
        base = (f.get("name") or "").replace(" [Greed]", "")
        slug = base.lower().replace(" ", "_").replace("-", "_")
        for candidate in (f"images/stage/{slug}.png", f"images/stage/{slug}.jpg"):
            if os.path.exists(os.path.join(ROOT, candidate)):
                f["image"] = candidate
                f["image_url"] = ""
                break

# Room types
for r in data.get("room_types", []):
    put_zh(r, name_zh=ZH.get("room_types", {}).get(r.get("name"), ""))

# Room guides: turn the English dict into records while keeping the source text.
guides = []
for key, text in data.get("room_guides", {}).items():
    z = ZH.get("room_guides", {}).get(key, {})
    guides.append({
        "name": key,
        "name_zh": z.get("title_zh", ""),
        "summary_zh": z.get("summary_zh", ""),
        "text_en": text,
    })
data["room_guides"] = guides

# ---------------------------------------------------------------- image fallbacks
# Some rows share a wiki image with another row of the same English name
# (especially entity variants and duplicate character entries).  Only reuse an
# image inside the same table: a pool named "Beggar" must not inherit the
# monster sprite also called "Beggar".
for table in ("items", "trinkets", "cards", "characters", "transformations", "entities", "floors", "item_pools"):
    by_name = {}
    for rec in data.get(table, []):
        name = rec.get("name")
        image = rec.get("image")
        if name and image:
            by_name.setdefault(name, image)
    for rec in data.get(table, []):
        if not rec.get("image"):
            rec["image"] = by_name.get(rec.get("name"), "")
            if rec["image"]:
                rec["image_url"] = ""

# This is only used as a compact offline payload.  Keep the original fields.
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>以撒的结合：忏悔 / 忏悔+ · 全资料</title>
<style>
  :root {
    --bg:#12151c; --panel:#1b1f29; --panel2:#222837; --line:#303747;
    --fg:#e8ebf2; --dim:#98a2b5; --acc:#e0a458; --acc2:#7aa2f7;
    --item:#b58343; --trinket:#5bb97a; --card:#7aa2f7; --pill:#d97a9e;
  }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body { margin:0; background:radial-gradient(1100px 500px at 50% -160px, #202737 0%, var(--bg) 62%);
         color:var(--fg); font:15px/1.55 -apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif; }
  header { position:sticky; top:0; z-index:30; background:rgba(15,18,25,.94);
           backdrop-filter:blur(14px); border-bottom:1px solid var(--line); padding:12px 16px 10px; }
  .headline { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
  h1 { margin:0; font-size:17px; font-weight:700; letter-spacing:.2px; }
  h1 small { color:var(--dim); font-weight:400; font-size:11.5px; margin-left:7px; }
  .lang { display:flex; flex:none; border:1px solid var(--line); border-radius:9px; overflow:hidden; }
  .lang button { border:0; background:transparent; color:var(--dim); padding:4px 8px; font-size:12px; cursor:pointer; }
  .lang button.on { background:var(--acc); color:#20160a; font-weight:700; }
  .tabs { display:flex; gap:6px; overflow-x:auto; padding:10px 0 2px; scrollbar-width:none; }
  .tabs::-webkit-scrollbar { display:none; }
  .tab { flex:none; padding:5px 10px; border:1px solid var(--line); border-radius:999px;
         background:var(--panel); color:var(--dim); cursor:pointer; font-size:12.5px; white-space:nowrap; }
  .tab:hover { color:var(--fg); border-color:#44506a; }
  .tab.on { background:var(--acc); border-color:var(--acc); color:#20160a; font-weight:700; }
  .bar { display:flex; gap:10px; margin:12px 16px 0; align-items:center; flex-wrap:wrap; }
  input[type=search] { flex:1; min-width:190px; padding:9px 13px; border-radius:9px;
    border:1px solid var(--line); background:var(--panel); color:var(--fg); font-size:14px; }
  input[type=search]:focus { outline:none; border-color:var(--acc2); }
  .cnt { color:var(--dim); font-size:12px; white-space:nowrap; }
  main { padding:13px 16px 56px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(310px,1fr)); gap:11px; }
  .card { background:linear-gradient(180deg,var(--panel) 0%,#191d26 100%);
          border:1px solid var(--line); border-radius:12px; padding:12px 13px; cursor:pointer;
          transition:border-color .12s,background .12s; min-width:0; }
  .card:hover { border-color:#46536c; background:var(--panel2); }
  .card.open { border-color:var(--acc); }
  .chead { display:flex; gap:10px; align-items:flex-start; }
  .thumb { width:56px; height:56px; border-radius:9px; background:#262c39; flex:none;
           display:grid; place-items:center; overflow:visible; position:relative; }
  .thumb img { width:100%; height:100%; object-fit:contain; display:block; border-radius:9px; }
  .thumb .ph { width:34px; height:34px; color:#6f7b91; display:grid; place-items:center; }
  .thumb .ph svg { width:34px; height:34px; }
  .cbody { flex:1; min-width:0; }
  .ttl { font-weight:700; font-size:15px; line-height:1.3; overflow-wrap:anywhere; }
  .ttl .zh { color:var(--acc); }
  .orig-name { color:var(--dim); font-size:11.5px; line-height:1.35; margin-top:2px; overflow-wrap:anywhere; }
  .id { color:var(--dim); font-size:11.5px; }
  .meta { color:var(--dim); font-size:12px; margin:3px 0 7px; overflow-wrap:anywhere; }
  .badge { display:inline-block; border-radius:5px; padding:1px 5px; font-size:10.5px;
           background:#3b2d1f; color:#efbd7a; border:1px solid #5d472b; margin-left:5px; }
  .desc { color:#cdd4e1; font-size:13px; white-space:pre-wrap; overflow-wrap:anywhere; }
  .desc.orig { color:#aab4c7; }
  .more { display:none; margin-top:10px; padding-top:9px; border-top:1px dashed var(--line); }
  .card.open .more { display:block; }
  .kv { margin:4px 0; font-size:12.5px; overflow-wrap:anywhere; }
  .kv b { color:var(--dim); font-weight:500; margin-right:5px; }
  .kv .en-orig { display:block; color:#7f8aa0; font-size:11.5px; margin-top:1px; }
  .chip { display:inline-block; background:#2a3142; color:#bdc8dc; border-radius:6px;
          padding:1px 6px; font-size:11px; margin:2px 3px 0 0; }
  .chip a { color:inherit; text-decoration:none; }
  .qbadge { position:absolute; z-index:3; top:-4px; right:-4px; width:18px; height:18px;
            line-height:16px; text-align:center; border-radius:50%; font-size:10.5px;
            font-weight:800; color:#fff; border:2px solid #12151c; box-shadow:0 1px 3px #0008; }
  .q { display:inline-block; width:20px; height:20px; line-height:20px; text-align:center;
       border-radius:5px; font-size:11px; font-weight:700; margin-right:5px; vertical-align:1px; }
  .q0{background:#4b5266;color:#fff}.q1{background:#5b8c3a;color:#fff}
  .q2{background:#3a7bb0;color:#fff}.q3{background:#8a5bb0;color:#fff}
  .q4{background:#c08b2e;color:#fff}.qn{background:#3a4150;color:#aaa}
  .empty { color:var(--dim); padding:44px; text-align:center; grid-column:1/-1; }
  .sub { color:var(--dim); font-size:12px; margin:0 16px 9px; }
  .source { margin:22px 16px 0; padding-top:14px; border-top:1px solid var(--line);
            color:#7b879d; font-size:11.5px; line-height:1.75; }
  .source a { color:#aebbd3; }
  .source details { margin-top:5px; }
  .source summary { cursor:pointer; color:#9ba8bd; }
  details.en-source { margin-top:8px; }
  details.en-source summary { cursor:pointer; color:#8f9bb0; font-size:11.5px; }
  .en-box { color:#9ba6ba; font-size:12px; white-space:pre-wrap; margin-top:4px; line-height:1.55; }
  .pills-note { color:var(--dim); font-size:11.5px; margin-bottom:8px; }
  @media (max-width:460px) {
    h1 { font-size:15.5px; }
    h1 small { display:none; }
    .grid { grid-template-columns:1fr; }
    .bar { margin-left:12px; margin-right:12px; }
    main { padding-left:12px; padding-right:12px; }
    .source { margin-left:12px; margin-right:12px; }
  }
</style>
</head>
<body>
<header>
  <div class="headline">
    <h1>以撒的结合：忏悔 / 忏悔+ <small>全资料 · i18n</small></h1>
    <div class="lang" role="group" aria-label="Language">
      <button type="button" id="langZh" class="on">中文</button>
      <button type="button" id="langEn">EN</button>
    </div>
  </div>
  <div class="tabs" id="tabs"></div>
</header>
<div class="bar">
  <input type="search" id="q" autocomplete="off">
  <span class="cnt" id="cnt"></span>
</div>
<div class="sub" id="sub"></div>
<main id="main"></main>
<footer class="source" id="source"></footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);

const TABS = [
  {k:'items', zh:'道具', en:'Items', kind:'item'},
  {k:'trinkets', zh:'饰品', en:'Trinkets', kind:'trinket'},
  {k:'cards', zh:'卡牌', en:'Cards', kind:'card'},
  {k:'pills', zh:'药丸', en:'Pills', kind:'pill'},
  {k:'item_pools', zh:'道具池', en:'Item Pools', kind:'pool'},
  {k:'characters', zh:'角色', en:'Characters', kind:'character'},
  {k:'transformations', zh:'套装', en:'Transformations', kind:'transformation'},
  {k:'achievements', zh:'成就', en:'Achievements', kind:'achievement'},
  {k:'challenges', zh:'挑战', en:'Challenges', kind:'challenge'},
  {k:'entities', zh:'怪物', en:'Monsters', kind:'entity'},
  {k:'floors', zh:'楼层', en:'Floors', kind:'floor'},
  {k:'room_types', zh:'房间类型', en:'Room Types', kind:'room'},
  {k:'room_guides', zh:'房间机制', en:'Room Mechanics', kind:'guide'},
];

const UI = {
  zh: {
    title:'以撒的结合：忏悔 / 忏悔+', sub:'全资料数据集 · 内嵌离线查看',
    search:'搜索中文 / 英文 / 描述 / ID …', count:n=>n+' 条',
    all:'全部', noMatch:'无匹配',
    zhMissing:'中文待补', enOriginal:'英文原文', sourceTitle:'来源与许可',
    source:'数据来自社区 Wiki。英文名称与描述保留为原文；中文优先使用 EID / 灰机 Wiki 的社区译名。中文 Wiki 文本按 CC BY-NC-SA 3.0 使用，英文 Wiki 文本按 CC BY-SA 4.0 使用；游戏素材版权归 Nicalis / Edmund McMillen，本项目为非官方粉丝图鉴。',
    sourceLinks:'灰机 Wiki · 以撒的结合中文维基', wikiGG:'英文 Wiki（CC BY-SA 4.0）',
    fields:{id:'ID', name:'名称', type:'类型', quality:'品质', quote:'格言', recharge:'充能',
      description:'描述', description_en:'英文描述', description_zh:'中文描述', requirements:'解锁条件',
      requirements_zh:'中文解锁条件', reward_zh:'中文奖励', notes:'备注', added_in:'引入版本',
      unlocked_by:'解锁方式', damage:'伤害', tears:'射速', speed:'移速', range:'射程',
      goal:'目标', character:'使用角色', starting_item:'初始道具', starting_pickup:'初始掉落',
      starting_trinket:'初始饰品', blindfolded:'蒙眼', has_shops:'有商店',
      has_treasure_rooms:'有宝箱房', unlocks:'解锁奖励', wiki_page:'Wiki 页面',
      variant:'变体', subtype:'子类', chapter:'章节', stage:'阶段', stage_name:'所属楼层',
      id_range:'ID 区间', bosses:'头目', items:'包含道具', weight:'权重', price_type:'价格类型',
      decrease:'降权', is_greed:'贪婪模式', tags:'标签', devil_price:'恶魔价格',
      shop_price:'商店价格', item_names_zh:'道具（中文）', summary_zh:'中文摘要',
      text_en:'英文原文', base_game_path:'游戏路径', pattern:'布局模式', show_in_menu:'菜单显示',
    },
    added:{Rebirth:'重生', Afterbirth:'胎衣', 'Afterbirth+':'胎衣†', Repentance:'忏悔', 'Repentance+':'忏悔+'},
    bool:{true:'是', false:'否'}, yes:'是', no:'否',
    sourceHref:'https://isaac.huijiwiki.com/', sourceLabel:'以撒的结合中文维基（灰机 Wiki）',
    fieldsTitle:'字段', original:'英文原名', originalDesc:'英文原描述', originalReq:'英文解锁条件',
  },
  en: {
    title:'The Binding of Isaac: Repentance / Repentance+', sub:'Full data set · offline viewer',
    search:'Search names, descriptions, IDs…', count:n=>n+' entries',
    all:'All', noMatch:'No matches',
    zhMissing:'Chinese missing', enOriginal:'English original', sourceTitle:'Sources & licences',
    source:'Community Wiki data. English names and descriptions are kept as the source text. Chinese uses EID / Huiji Wiki community translations where available. Chinese Wiki text is used under CC BY-NC-SA 3.0; English Wiki text under CC BY-SA 4.0. Game assets remain © Nicalis / Edmund McMillen; this is an unofficial fan reference.',
    sourceLinks:'Huiji Wiki · Chinese Isaac Wiki', wikiGG:'English Wiki (CC BY-SA 4.0)',
    fields:{id:'ID', name:'Name', type:'Type', quality:'Quality', quote:'Quote', recharge:'Recharge',
      description:'Description', description_en:'English description', description_zh:'Chinese description',
      requirements:'Requirements', requirements_zh:'Chinese requirements', reward_zh:'Chinese reward',
      notes:'Notes', added_in:'Added in', unlocked_by:'Unlocked by', damage:'Damage', tears:'Tears',
      speed:'Speed', range:'Range', goal:'Goal', character:'Character', starting_item:'Starting item',
      starting_pickup:'Starting pickup', starting_trinket:'Starting trinket', blindfolded:'Blindfolded',
      has_shops:'Shops', has_treasure_rooms:'Treasure rooms', unlocks:'Unlocks', wiki_page:'Wiki page',
      variant:'Variant', subtype:'Subtype', chapter:'Chapter', stage:'Stage', stage_name:'Floor',
      id_range:'ID range', bosses:'Bosses', items:'Items', weight:'Weight', price_type:'Price type',
      decrease:'Decrease', is_greed:'Greed mode', tags:'Tags', devil_price:'Devil price',
      shop_price:'Shop price', item_names_zh:'Items (Chinese)', summary_zh:'Chinese summary',
      text_en:'English text', base_game_path:'Game path', pattern:'Pattern', show_in_menu:'In menu',
    },
    added:{Rebirth:'Rebirth', Afterbirth:'Afterbirth', 'Afterbirth+':'Afterbirth+', Repentance:'Repentance', 'Repentance+':'Repentance+'},
    bool:{true:'Yes', false:'No'}, yes:'Yes', no:'No',
    sourceHref:'https://isaac.huijiwiki.com/', sourceLabel:'Huiji Wiki · Chinese Isaac Wiki',
    fieldsTitle:'Fields', original:'English name', originalDesc:'English description', originalReq:'English requirements',
  }
};

const ICONS = {
  item:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 15c0-4 3-7 7-7h6a3 3 0 0 1 0 6h-6a3 3 0 0 0 0 6h6"/></svg>',
  trinket:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l2.2 4.5 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L4.8 8.2l5-.7z"/></svg>',
  card:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="6" y="3" width="12" height="18" rx="2"/><path d="M9 7h6M9 11h6M9 15h3"/></svg>',
  pill:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M8.5 16.5l8-8a3.5 3.5 0 0 1 5 5l-8 8a3.5 3.5 0 0 1-5-5z"/><path d="M11 14l4 4"/></svg>',
  pool:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 8h16M6 8v10h12V8M9 8V5h6v3"/><path d="M9 12h6"/></svg>',
  character:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="7" r="3"/><path d="M6 21v-2a6 6 0 0 1 12 0v2"/></svg>',
  transformation:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="7"/></svg>',
  achievement:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M8 4h8v4a4 4 0 0 1-8 0z"/><path d="M8 5H5v2a3 3 0 0 0 3 3M16 5h3v2a3 3 0 0 1-3 3M12 12v5M8 21h8M9 21c0-2 1.5-3 3-3s3 1 3 3"/></svg>',
  challenge:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 4h14v5a7 7 0 0 1-14 0z"/><path d="M5 5H2v2a4 4 0 0 0 4 4M19 5h3v2a4 4 0 0 1-4 4M12 16v5M8 21h8"/></svg>',
  entity:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M7 20v-3a5 5 0 0 1 10 0v3M5 9c0-4 3-6 7-6s7 2 7 6v4a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4z"/><circle cx="9" cy="10" r="1"/><circle cx="15" cy="10" r="1"/></svg>',
  floor:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 20h16M6 20V9l6-5 6 5v11M9 20v-5h6v5"/></svg>',
  room:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16M10 10v10"/></svg>',
  guide:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 5a3 3 0 0 1 3-2h13v18H7a3 3 0 0 1-3-2z"/><path d="M4 19a3 3 0 0 1 3-2h13M8 7h8M8 10h6"/></svg>',
};

let state = {lang: 'zh', cur:'items', query:''};
try { const saved = localStorage.getItem('isaac-viewer-lang'); if (saved === 'en' || saved === 'zh') state.lang = saved; } catch (_) {}
function L(){ return UI[state.lang]; }
function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function isHan(s){ return /[\\u3400-\\u9fff]/.test(String(s||'')); }
function zhFirst(o, keys){
  for (const k of keys) if (o[k]) return o[k];
  return '';
}
function locAdded(v){ return L().added[v] || v || ''; }
function tab(){ return TABS.find(t=>t.k===state.cur) || TABS[0]; }
function label(k){ return L().fields[k] || k; }
function val(v){
  if (v == null) return '';
  if (typeof v === 'boolean') return v ? L().yes : L().no;
  if (Array.isArray(v)) return v.map(x=>typeof x === 'object' ? (x.name_zh && state.lang==='zh' ? x.name_zh : x.name || JSON.stringify(x)) : String(x)).join('、');
  return String(v);
}
function nameZh(o){
  if (state.lang === 'en') return o.name || o.key || '';
  return o.name_zh || o.name || o.key || '';
}
function nameEn(o){ return o.name || o.key || ''; }
function hasZh(o){ return !!(o.name_zh || o.description_zh || o.requirements_zh || o.summary_zh || o.title_zh); }

function thumb(o, kind){
  const src = o.image || '';
  const ph = `<span class="ph">${ICONS[kind] || ICONS.item}</span>`;
  const q = o.quality != null
    ? `<span class="qbadge q${o.quality}" title="${state.lang==='zh'?'品质':'Quality'} ${o.quality}">${o.quality}</span>`
    : '';
  if (!src) return `<div class="thumb">${ph}${q}</div>`;
  return `<div class="thumb"><img src="${esc(src)}" alt="" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='grid'">${ph.replace('class="ph"','class="ph" style="display:none"')}${q}</div>`;
}

function sourceBlock(o){
  if (state.lang !== 'zh' || !hasZh(o)) return '';
  const lines = [];
  if (o.name && o.name !== o.name_zh) lines.push(`<div><b>${L().original}</b> ${esc(o.name)}</div>`);
  const enDesc = o.description_en || o.description || o.text_en || '';
  if (enDesc && (o.description_zh || o.summary_zh)) lines.push(`<div><b>${L().originalDesc}</b> ${esc(enDesc)}</div>`);
  if (o.requirements && o.requirements_zh) lines.push(`<div><b>${L().originalReq}</b> ${esc(o.requirements)}</div>`);
  if (!lines.length) return '';
  return `<details class="en-source"><summary>${L().enOriginal}</summary><div class="en-box">${lines.join('')}</div></details>`;
}

function descFor(o){
  if (state.lang === 'zh') return o.description_zh || o.summary_zh || o.description_en || o.description || o.requirements_zh || o.requirements || '';
  return o.description_en || o.description || o.text_en || o.requirements || o.summary_zh || '';
}

function metaFor(o){
  const bits = [];
  if (o.id != null && o.id !== '') bits.push('#'+o.id);
  else if (o.number != null) bits.push('#'+o.number);
  if (o.type) bits.push(locType(o.type));
  if (o.added_in) bits.push(locAdded(o.added_in));
  if (o.chapter) bits.push((state.lang==='zh'?'第':'Ch. ')+o.chapter+(state.lang==='zh'?'章':''));
  if (o.goal) bits.push((state.lang==='zh'?'目标：':'Goal: ')+o.goal);
  return bits.map(esc).join(' · ');
}
function locType(t){
  if (state.lang==='en') return t;
  return ({active:'主动道具', passive:'被动道具', monster:'怪物', boss:'头目', npc:'NPC'}[t] || t);
}

function fieldRows(o){
  const skip = new Set(['name','name_zh','description','description_en','description_zh','requirements','requirements_zh','requirements_zh','summary_zh','text_en','key','image','image_url','item_names_zh','reward_zh','name_en']);
  const rows = [];
  for (const [k,v] of Object.entries(o)){
    if (skip.has(k) || k.startsWith('_')) continue;
    if (k.endsWith('_zh')) continue;
    if (v === '' || v == null || (Array.isArray(v) && !v.length)) continue;
    const zhKey = k+'_zh';
    let shown = v, en = '';
    if (state.lang==='zh' && o[zhKey]) { shown = o[zhKey]; en = v; }
    if (k==='items' && Array.isArray(v)){
      shown = v.map(x=>{
        if (typeof x !== 'object') return `<span class="chip">${esc(x)}</span>`;
        const n = state.lang==='zh' ? (x.name_zh || x.name) : (x.name || x.name_zh);
        const w = x.weight != null ? ' ×'+x.weight : '';
        return `<span class="chip">${esc(n)}${esc(w)}</span>`;
      }).join('');
    } else if (Array.isArray(v)) {
      shown = v.map(x=>`<span class="chip">${esc(typeof x==='object' ? (state.lang==='zh' && x.name_zh ? x.name_zh : x.name) : x)}</span>`).join('');
    } else if (k==='added_in') {
      shown = locAdded(v);
    } else if (k==='wiki_page') {
      shown = `<a href="https://bindingofisaacrebirth.wiki.gg/wiki/${encodeURIComponent(v).replace(/%20/g,'_')}" target="_blank" rel="noopener">${esc(v)}</a>`;
    } else {
      shown = esc(val(shown));
    }
    if (en) shown += `<span class="en-orig">${esc(val(en))}</span>`;
    rows.push(`<div class="kv"><b>${esc(label(k))}</b>${shown}</div>`);
  }
  return rows.join('');
}

function card(o, kind, idx){
  const title = state.lang==='zh' ? (o.name_zh || o.name || o.key || '#'+(o.id ?? idx)) : (o.name || o.key || '#'+(o.id ?? idx));
  const en = state.lang==='zh' ? (o.name && o.name !== title ? o.name : '') : '';
  const untranslated = state.lang==='zh' && !hasZh(o) ? `<span class="badge">${L().zhMissing}</span>` : '';
  const desc = descFor(o);
  const meta = metaFor(o);
  return `<div class="card" onclick="this.classList.toggle('open')">
    <div class="chead">
      ${thumb(o, kind)}
      <div class="cbody">
        <div class="ttl">${esc(title)}${untranslated}</div>
        ${en?`<div class="orig-name">${esc(en)}</div>`:''}
        ${meta?`<div class="meta">${meta}</div>`:''}
      </div>
    </div>
    ${desc?`<div class="desc">${esc(desc).slice(0,240)}${desc.length>240?' …':''}</div>`:''}
    <div class="more">${fieldRows(o)}${sourceBlock(o)}</div>
  </div>`;
}

function renderTabs(){
  $('#tabs').innerHTML = TABS.map(t=>{
    const n = (D[t.k]||[]).length;
    const on = t.k===state.cur ? ' on':'';
    return `<button class="tab${on}" type="button" data-k="${t.k}">${t[state.lang]} <b style="opacity:.68">${n}</b></button>`;
  }).join('');
  $('#tabs').querySelectorAll('.tab').forEach(el=>el.onclick=()=>{
    state.cur = el.dataset.k; state.query = ''; $('#q').value=''; renderTabs(); render();
  });
}

function match(o){
  if (!state.query) return true;
  const q = state.query.toLowerCase();
  return JSON.stringify(o).toLowerCase().includes(q);
}

function render(){
  const t = tab();
  $('#q').placeholder = L().search;
  const rows = (D[t.k]||[]).filter(match);
  $('#cnt').textContent = L().count(rows.length) + ' · ' + t[state.lang];
  $('#sub').textContent = state.lang==='zh'
    ? `英文原文字段保留 · 中文优先显示官方/社区译名 · 每张卡片可展开全部字段`
    : `English source fields preserved · tap a card to expand all fields`;
  if (!rows.length) {
    $('#main').innerHTML = `<div class="grid"><div class="empty">${L().noMatch}</div></div>`;
  } else {
    const kind = t.kind;
    $('#main').innerHTML = `<div class="grid">${rows.map((o,i)=>card(o, kind, i)).join('')}</div>`;
  }
  $('#source').innerHTML = `<b>${L().sourceTitle}</b><br>${L().source}<br>
    <a href="${L().sourceHref}" target="_blank" rel="noopener">${L().sourceLinks}</a> ·
    <a href="https://bindingofisaacrebirth.wiki.gg/" target="_blank" rel="noopener">${L().wikiGG}</a>
    <details><summary>字段说明 / Fields</summary><div class="en-box">
      ${Object.entries(L().fields).map(([k,v])=>`<b>${k}</b>: ${esc(v)}`).join(' · ')}
    </div></details>`;
}

function setLang(lang){
  state.lang = lang === 'en' ? 'en' : 'zh';
  document.documentElement.lang = state.lang === 'en' ? 'en' : 'zh-CN';
  $('#langZh').classList.toggle('on', state.lang==='zh');
  $('#langEn').classList.toggle('on', state.lang==='en');
  try { localStorage.setItem('isaac-viewer-lang', state.lang); } catch (_) {}
  renderTabs(); render();
}

$('#q').addEventListener('input', e=>{ state.query = e.target.value.trim(); render(); });
$('#langZh').onclick = ()=>setLang('zh');
$('#langEn').onclick = ()=>setLang('en');
document.documentElement.lang = state.lang === 'en' ? 'en' : 'zh-CN';
$('#langZh').classList.toggle('on', state.lang==='zh');
$('#langEn').classList.toggle('on', state.lang==='en');
renderTabs(); render();
</script>
</body>
</html>
"""
out_path = os.path.join(ROOT, "viewer.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", payload))
print("已生成 viewer.html:", round(os.path.getsize(out_path)/1024/1024, 2), "MB")
