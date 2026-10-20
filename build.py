#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《以撒的结合：忏悔 / 忏悔+》数据整合脚本

数据来源：
  1. wofsauge/External-Item-Descriptions (EID)  —— 名称 / 效果描述（英文 + 简体中文）
  2. bindingofisaacrebirth.wiki.gg Cargo API    —— 品质 / 标签 / 解锁 / 道具池 / 成就 / 挑战 / 角色 / 实体
  3. wofsauge/Basement-Renovator resources      —— 房间类型 / 楼层定义

输出：
  json/*.json   结构化数据
  csv/*.csv     表格数据（UTF-8 BOM，可直接用 Excel 打开）
"""

import json, os, re, csv, html, glob, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(ROOT, "json")
CSV = os.path.join(ROOT, "csv")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CSV, exist_ok=True)


# ---------------------------------------------------------------- helpers
def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def lua_unescape(s):
    return (s.replace('\\"', '"').replace("\\'", "'")
             .replace("\\n", "\n").replace("\\\\", "\\"))


def strip_wiki(s):
    """把 wiki 标记 / HTML 转成纯文本。"""
    if not s:
        return ""
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    # 图片 / 文件链接整条移除
    s = re.sub(r"\[\[(?:File|Image|Media):[^\]]*\]\]", "", s, flags=re.I)
    # [[页面|显示文字]] / [[页面|a|b]] -> 最后一段
    s = re.sub(r"\[\[([^|\]]*\|)*([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\{\{(?:dlc|Dlc)\|([^}]*)\}\}", "", s)
    s = re.sub(r"\{\{[^}]*\|([^}|]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = s.replace("'''", "").replace("''", "")
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def clean_desc(s):
    """EID 描述标记 -> 可读纯文本。"""
    if not s:
        return ""
    s = s.replace("#", "\n")
    s = re.sub(r"\{\{[^}|]*\|([^}]*)\}\}", r"\1", s)   # {{图标|文字}} -> 文字
    s = re.sub(r"\{\{[^}]*\}\}", "", s)                 # {{图标}} -> ''
    s = re.sub(r"\{[^}]*\}", "", s)                     # {图标} -> ''
    s = s.replace("↑ ", "").replace("↓ ", "")
    s = s.replace("\\n", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ---------------------------------------------------------------- EID 解析
TABLE_RE = re.compile(
    r"(?:local\s+(\w+)|EID\.descriptions\[languageCode\]\.(\w+))\s*=\s*\{"
)
# {"id", "名称", "描述"}  —— 位置式或 [id] = {...} 键式都命中
TUPLE_RE = re.compile(
    r"\{\s*\"(\d+)\"\s*,\s*\"((?:[^\"\\]|\\.)*)\"\s*,\s*\"((?:[^\"\\]|\\.)*)\"",
    re.S,
)


def table_body(text, start):
    """从 `{` 开始返回配对的 table 内容（跳过字符串里的花括号）。"""
    depth = 1
    i = start
    n = len(text)
    in_str = False
    while i < n and depth > 0:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i]
        i += 1
    return text[start:]


KINDS = ["collectibles", "trinkets", "cards", "pills"]


def parse_kind(path, kind):
    """抽取某个文件里 kind 对应表的 {id: (名称, 描述)}。"""
    if not os.path.exists(path):
        return {}
    text = read(path)
    want = re.compile(r"^(rep)?" + kind + r"$", re.I)
    out = {}
    for m in TABLE_RE.finditer(text):
        name = m.group(1) or m.group(2)
        if not want.match(name or ""):
            continue
        body = table_body(text, m.end())
        for t in TUPLE_RE.finditer(body):
            out[int(t.group(1))] = (lua_unescape(t.group(2)), lua_unescape(t.group(3)))
    return out


def merge_desc(kind, suffix):
    """AB+ 基础 -> 忏悔覆盖 -> 忏悔+覆盖。"""
    merged = {}
    for tag in ["ab+", "rep", "rep+"]:
        merged.update(parse_kind(os.path.join(RAW, f"eid_{tag}_{suffix}.lua"), kind))
    return merged


EID = {}
for lang, suffix in (("en", "en_us"), ("zh", "zh_cn")):
    EID[lang] = {k: merge_desc(k, suffix) for k in KINDS}

# 名称表（完整，含 732 个道具 / 189 个饰品 / 97 个卡牌 / 51 个药丸）
NAME_RE = re.compile(
    r"\[(C_ID|T_ID|Card_ID|Pill_ID)\s*\.\.\s*(\d+)\]\s*=\s*\"((?:[^\"\\]|\\.)*)\""
)
NAME_MAP = {"C_ID": "collectibles", "T_ID": "trinkets",
            "Card_ID": "cards", "Pill_ID": "pills"}


def parse_names(path):
    res = {k: {} for k in KINDS}
    if not os.path.exists(path):
        return res
    for m in NAME_RE.finditer(read(path)):
        res[NAME_MAP[m.group(1)]][int(m.group(2))] = lua_unescape(m.group(3))
    return res


NAMES_EN = parse_names(os.path.join(RAW, "eid_names_en_us.lua"))
NAMES_ZH = parse_names(os.path.join(RAW, "eid_names_zh_cn.lua"))


# ---------------------------------------------------------------- Cargo
cargo = json.load(open(os.path.join(RAW, "wiki_cargo.json"), encoding="utf-8"))
cargo2 = json.load(open(os.path.join(RAW, "wiki_cargo2.json"), encoding="utf-8"))
cats = json.load(open(os.path.join(RAW, "wiki_categories.json"), encoding="utf-8"))

# 质量表里的 dlc 数值越大代表版本越新（8=忏悔，16=忏悔+，31=全版本）
def best_row(rows):
    if not rows:
        return {}
    def score(r):
        try:
            return int(r.get("dlc", 0))
        except ValueError:
            return 0
    return max(rows, key=score)


def group(rows, key):
    d = {}
    for r in rows:
        d.setdefault(r.get(key, ""), []).append(r)
    return d


def added_in(page, dlc_raw=""):
    """优先用 wiki 分类判断引入版本。"""
    for c in cats.get(page, []):
        if c.startswith("Category:Added in "):
            v = c.replace("Category:Added in ", "")
            if v.startswith("Booster Pack"):
                return "Afterbirth+ (" + v + ")"
            return v
    return "Rebirth"


def pick(d, *keys):
    """按候选键依次查表（wiki 页面名 vs 游戏内名称）。"""
    for k in keys:
        if k and k in d:
            return d[k]
    return []


# ---------------------------------------------------------------- 图片
imgs = json.load(open(os.path.join(RAW, "wiki_images.json"), encoding="utf-8"))


def imgmap(rows, key):
    d = {}
    for r in rows or []:
        k, f = r.get(key, ""), r.get("file", "")
        if k and f and k not in d:
            d[k] = f
    return d


IMG = {
    "collectible": imgmap(imgs.get("collectible_image"), "collectible"),
    "trinket": imgmap(imgs.get("trinket_image"), "trinket"),
    "pickup": imgmap(imgs.get("pickup_image"), "pickup"),
    "entity": imgmap(imgs.get("entity_image"), "entity"),
    "player": imgmap(imgs.get("player_image"), "player"),
    "transformation": imgmap(imgs.get("transformation_image"), "transformation"),
    "pool": imgmap(imgs.get("pool_icon"), "pool"),
    "stage": imgmap(imgs.get("stage_icon"), "stage"),
}
IMG_MANIFEST = {}   # 本地相对路径 -> wiki 文件名（供 fetch_images.py 下载）


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")
    return s or "x"


def add_img(rec, cat, path_name, *keys):
    f = pick(IMG.get(cat, {}), *keys)
    if isinstance(f, str) and f:
        rel = f"images/{cat}/{path_name}.png"
        rec["image"] = rel
        rec["image_url"] = ("https://bindingofisaacrebirth.wiki.gg/wiki/Special:FilePath/"
                            + urllib.parse.quote(f.replace(" ", "_")))
        IMG_MANIFEST[rel] = f
    else:
        rec["image"] = ""
        rec["image_url"] = ""


# ---------------------------------------------------------------- 道具
c_names = group(cargo["collectible_name"], "collectible")
c_quality = group(cargo["collectible_quality"], "collectible")
c_quotes = {r["collectible"]: r["quote"] for r in cargo["collectible_quote"]}
c_tags = group(cargo["collectible_tag"], "collectible")
c_shop = group(cargo2["collectible_shop_price"], "collectible")
c_devil = group(cargo2["collectible_devil_price"], "collectible")
c_recharge = group(cargo["collectible_recharge"], "collectible")

items = []
seen = set()
for r in cargo["collectible"]:
    if not str(r.get("id", "")).isdigit():
        continue
    iid = int(r["id"])
    if iid in seen:
        continue
    seen.add(iid)
    page = r["_pageName"]
    en_name, en_desc = EID["en"]["collectibles"].get(iid, ("", ""))
    zh_name, zh_desc = EID["zh"]["collectibles"].get(iid, ("", ""))
    keys = (page, en_name)
    q = best_row(pick(c_quality, *keys))
    sh = best_row(pick(c_shop, *keys))
    dv = best_row(pick(c_devil, *keys))
    rc = best_row(pick(c_recharge, *keys))
    items.append({
        "id": iid,
        "name": en_name or page,
        "name_zh": NAMES_ZH["collectibles"].get(iid, "") or zh_name,
        "quote": pick(c_quotes, *keys) or "",
        "quality": int(q["quality"]) if q.get("quality", "").isdigit() else None,
        "type": "active" if r.get("is activated") == "1" else "passive",
        "tags": sorted({t["tag"] for t in pick(c_tags, *keys)
                        if t.get("tag") and not t["tag"].startswith("@")}),
        "recharge": rc.get("recharge", ""),
        "shop_price": sh.get("shop price", ""),
        "devil_price": dv.get("devil price", ""),
        "unlocked_by": strip_wiki(r.get("unlocked_by", "")),
        "added_in": added_in(page),
        "description_en": clean_desc(en_desc) or clean_desc(zh_desc and en_desc),
        "description_zh": clean_desc(zh_desc),
        "wiki_description": strip_wiki(r.get("description", "")),
        "wiki_page": page,
    })
    add_img(items[-1], "collectible", str(iid), page, en_name)
# 描述兜底：EID 没有就用 wiki 描述
for it in items:
    if not it["description_en"]:
        it["description_en"] = it["wiki_description"]
    if not it["description_zh"]:
        it["description_zh"] = it["wiki_description"]
items.sort(key=lambda x: x["id"])


# ---------------------------------------------------------------- 饰品
t_names = group(cargo["trinket_name"], "trinket")
t_quotes = {r["trinket"]: r["quote"] for r in cargo["trinket_quote"]}
t_tags = group(cargo["trinket_tag"], "trinket")

trinkets = []
for r in cargo["trinket"]:
    iid = int(r["id"])
    page = r["_pageName"]
    en_name, en_desc = EID["en"]["trinkets"].get(iid, ("", ""))
    zh_name, zh_desc = EID["zh"]["trinkets"].get(iid, ("", ""))
    trinkets.append({
        "id": iid,
        "name": en_name or page,
        "name_zh": NAMES_ZH["trinkets"].get(iid, "") or zh_name,
        "quote": t_quotes.get(page, ""),
        "tags": sorted({t["tag"] for t in t_tags.get(page, [])
                        if t.get("tag") and not t["tag"].startswith("@")}),
        "unlocked_by": strip_wiki(r.get("unlocked_by", "")),
        "added_in": added_in(page),
        "description_en": clean_desc(en_desc),
        "description_zh": clean_desc(zh_desc),
        "wiki_description": strip_wiki(r.get("description", "")),
        "wiki_page": page,
    })
    add_img(trinkets[-1], "trinket", str(iid), page, en_name)
for t in trinkets:
    if not t["description_en"]:
        t["description_en"] = t["wiki_description"]
    if not t["description_zh"]:
        t["description_zh"] = t["wiki_description"]
trinkets.sort(key=lambda x: x["id"])


# ---------------------------------------------------------------- 卡牌 / 药丸
pickup_name = {r["pickup"]: r["name"] for r in cargo["pickup_name"]}
pickup_quote = {r["pickup"]: r["quote"] for r in cargo2.get("pickup_quote", [])}

cards = []
for r in cargo["pickup"]:
    iid = int(r["id"])
    page = r["_pageName"]
    en_name, en_desc = EID["en"]["cards"].get(iid, ("", ""))
    zh_name, zh_desc = EID["zh"]["cards"].get(iid, ("", ""))
    cards.append({
        "id": iid,
        "name": en_name or pickup_name.get(page, page),
        "name_zh": NAMES_ZH["cards"].get(iid, "") or zh_name,
        "quote": pickup_quote.get(page, ""),
        "description_en": clean_desc(en_desc),
        "description_zh": clean_desc(zh_desc),
        "added_in": added_in(page),
        "wiki_page": page,
    })
    add_img(cards[-1], "pickup", str(iid), page)
cards.sort(key=lambda x: x["id"])

pills = []
for iid in sorted(NAMES_EN["pills"]):
    en_name, en_desc = EID["en"]["pills"].get(iid, (NAMES_EN["pills"][iid], ""))
    zh_name, zh_desc = EID["zh"]["pills"].get(iid, ("", ""))
    pills.append({
        "id": iid,
        "name": en_name or NAMES_EN["pills"][iid],
        "name_zh": NAMES_ZH["pills"].get(iid, "") or zh_name,
        "description_en": clean_desc(en_desc),
        "description_zh": clean_desc(zh_desc),
    })


# ---------------------------------------------------------------- 道具池
pool_meta = group(cargo2["pool"], "alias")
pools_map = {}
for r in cargo["pool_collectible"]:
    pools_map.setdefault(r["pool"], []).append({
        "name": r["collectible"],
        "weight": int(r["weight"]) if str(r["weight"]).isdigit() else r["weight"],
    })
pool_out = []
for name, entries in sorted(pools_map.items()):
    meta = best_row(pool_meta.get(name, [{}]))
    pool_out.append({
        "name": name,
        "is_greed": meta.get("is greed") == "1",
        "price_type": meta.get("price type", ""),
        "decrease": meta.get("decrease", ""),
        "items": sorted(entries, key=lambda x: x["name"]),
    })
    add_img(pool_out[-1], "pool", slug(name), name)


# ---------------------------------------------------------------- 角色
char_names = {r["player"]: r["name"] for r in cargo["player_name"]}


def stat_map(rows, field):
    d = {}
    for r in rows:
        d.setdefault(r["player"], r.get(field, ""))
    return d


dmg = stat_map(cargo2["player_damage"], "damage")
tears = stat_map(cargo2["player_tears"], "tears")
spd = stat_map(cargo2["player_speed"], "speed")
rng = stat_map(cargo2["player_range"], "range_base")

characters = []
for r in cargo["player"]:
    page = r["_pageName"]
    characters.append({
        "id": int(r["id"]) if str(r.get("id", "")).isdigit() else None,
        "name": char_names.get(page, page),
        "unlocked_by": strip_wiki(r.get("unlocked_by", "")),
        "added_in": added_in(page),
        "damage": dmg.get(page, ""),
        "tears": tears.get(page, ""),
        "speed": spd.get(page, ""),
        "range": rng.get(page, ""),
        "wiki_page": page,
    })
    add_img(characters[-1], "player", slug(page), page, char_names.get(page, page))
characters.sort(key=lambda x: (x["id"] is None, x["id"] or 0))


# ---------------------------------------------------------------- 变形
trans_names = {r["transformation"]: r["name"] for r in cargo["transformation_name"]}
trans_items = {}
trans_src = os.path.join(RAW, "eid_rep_transformations.lua")
if os.path.exists(trans_src):
    for m in re.finditer(r'\["5\.100\.(\d+)"\]\s*=\s*"([\d, ]+)"', read(trans_src)):
        iid = int(m.group(1))
        for t in m.group(2).split(","):
            if t.strip():
                trans_items.setdefault(int(t), []).append(iid)

transformations = []
for r in cargo["transformation"]:
    tid = int(r["id"])
    transformations.append({
        "id": tid,
        "name": trans_names.get(r["_pageName"], r["_pageName"]),
        "items": sorted(trans_items.get(tid, [])),
        "wiki_page": r["_pageName"],
    })
    add_img(transformations[-1], "transformation",
            slug(trans_names.get(r["_pageName"], r["_pageName"])),
            trans_names.get(r["_pageName"], r["_pageName"]), r["_pageName"])
transformations.sort(key=lambda x: x["id"])


# ---------------------------------------------------------------- 成就
achievements = []
for r in cargo2["achievement"]:
    achievements.append({
        "id": int(r["id"]) if str(r.get("id", "")).isdigit() else None,
        "name": r.get("name", ""),
        "description": strip_wiki(r.get("description", "")),
        "requirements": strip_wiki(r.get("requirements", "")),
        "notes": strip_wiki(r.get("notes", "")),
        "added_in": added_in(r.get("_pageName", "")),
        "link": r.get("link", ""),
        "wiki_page": r.get("_pageName", ""),
    })
achievements.sort(key=lambda x: (x["id"] is None, x["id"] or 0))


# ---------------------------------------------------------------- 挑战
challenges = []
for r in cargo2["challenge"]:
    challenges.append({
        "number": int(r["number"]) if str(r.get("number", "")).isdigit() else None,
        "name": r.get("alias", "") or r.get("name", ""),
        "description": strip_wiki(r.get("description", "")),
        "goal": strip_wiki(r.get("goal", "")),
        "character": strip_wiki(r.get("used_character", "")),
        "starting_item": strip_wiki(r.get("item", "")),
        "starting_pickup": strip_wiki(r.get("pickup", "")),
        "starting_trinket": strip_wiki(r.get("trinket", "")),
        "blindfolded": r.get("blindfolded") == "1",
        "has_shops": r.get("has shops") == "1",
        "has_treasure_rooms": r.get("has treasure rooms") == "1",
        "unlocks": strip_wiki(r.get("unlocks", "")),
        "unlocked_by": strip_wiki(r.get("unlocked_by", "")),
        "added_in": added_in(r.get("_pageName", "")),
        "wiki_page": r.get("_pageName", ""),
    })
challenges.sort(key=lambda x: (x["number"] is None, x["number"] or 0))


# ---------------------------------------------------------------- 实体
ent_names = {r["entity"]: r["name"] for r in cargo["entity_name"]}
entities = []
for r in cargo["entity"]:
    entities.append({
        "name": ent_names.get(r["_pageName"], r["_pageName"]),
        "id": int(r["id"]) if str(r.get("id", "")).isdigit() else r.get("id", ""),
        "type": r.get("type", ""),
        "variant": int(r["variant"]) if str(r.get("variant", "")).isdigit() else r.get("variant", ""),
        "subtype": int(r["subtype"]) if str(r.get("subtype", "")).isdigit() else r.get("subtype", ""),
        "added_in": added_in(r.get("_pageName", "")),
        "wiki_page": r["_pageName"],
    })
    add_img(entities[-1], "entity", slug(entities[-1]["name"]), entities[-1]["name"])
entities.sort(key=lambda x: (x["type"], x["id"] if isinstance(x["id"], int) else 0))


# ---------------------------------------------------------------- 楼层 / 房间
def parse_stages():
    text = read(os.path.join(RAW, "StagesRepentance.xml"))
    out = []
    for m in re.finditer(r"<stage\s+([^>]+?)\s*/?>", text):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        out.append({
            "name": a.get("Name", ""),
            "base_game_path": a.get("BaseGamePath", ""),
            "stage": a.get("Stage", ""),
            "stage_type": a.get("StageType", ""),
            "pattern": a.get("Pattern", ""),
        })
    return out


def parse_room_types():
    text = read(os.path.join(RAW, "RoomTypesRepentance.xml"))
    out = []
    for m in re.finditer(r"<room\s+([^>]+?)\s*/?>", text):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        out.append({
            "name": a.get("Name", ""),
            "type": a.get("Type", ""),
            "stage_name": a.get("StageName", ""),
            "id_range": a.get("ID", ""),
            "show_in_menu": a.get("ShowInMenu", "") == "1",
        })
    return out


stages = parse_stages()
room_types = parse_room_types()

stage_wiki = group(cargo2["stage"], "alias")
for s in stages:
    w = best_row(stage_wiki.get(s["name"], [{}]))
    s["chapter"] = w.get("chapter", "")
    s["bosses"] = [b.strip() for b in w.get("bosses 1", "").split(",") if b.strip()]
    s["unlocked_by"] = strip_wiki(w.get("unlocked_by", ""))
    s["wiki_page"] = w.get("link", "")
    add_img(s, "stage", slug(s["name"]), s["name"])

room_guides = {}
for p in sorted(glob.glob(os.path.join(ROOT, "wiki", "rooms", "*.txt"))):
    title = os.path.basename(p)[:-4].replace("_", " ")
    txt = read(p).strip()
    if txt:
        room_guides[title] = txt


# ---------------------------------------------------------------- 输出
def dump(name, data):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n = len(data) if hasattr(data, "__len__") else ""
    print(f"  json/{name}: {n}")


counts = {
    "items": len(items), "trinkets": len(trinkets), "cards": len(cards),
    "pills": len(pills), "item_pools": len(pool_out),
    "characters": len(characters), "transformations": len(transformations),
    "achievements": len(achievements), "challenges": len(challenges),
    "entities": len(entities), "floors": len(stages),
    "room_types": len(room_types), "room_guides": len(room_guides),
}

print("生成 JSON：")
dump("items.json", items)
dump("trinkets.json", trinkets)
dump("cards.json", cards)
dump("pills.json", pills)
dump("item_pools.json", pool_out)
dump("characters.json", characters)
dump("transformations.json", transformations)
dump("achievements.json", achievements)
dump("challenges.json", challenges)
dump("entities.json", entities)
dump("floors.json", stages)
dump("room_types.json", room_types)
dump("room_guides.json", room_guides)
dump("isaac_repentance_all.json", {
    "meta": {
        "game": "The Binding of Isaac: Repentance / Repentance+",
        "sources": [
            "https://github.com/wofsauge/External-Item-Descriptions (GPL-3.0)",
            "https://bindingofisaacrebirth.wiki.gg (CC BY-SA)",
            "https://github.com/wofsauge/Basement-Renovator (GPL-3.0)",
        ],
        "counts": counts,
    },
    "items": items, "trinkets": trinkets, "cards": cards, "pills": pills,
    "item_pools": pool_out, "characters": characters,
    "transformations": transformations, "achievements": achievements,
    "challenges": challenges, "entities": entities,
    "floors": stages, "room_types": room_types, "room_guides": room_guides,
})

# 图片下载清单
with open(os.path.join(RAW, "image_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(IMG_MANIFEST, f, ensure_ascii=False, indent=1)
print(f"图片清单: {len(IMG_MANIFEST)} 张 -> raw/image_manifest.json")


# ---------------------------------------------------------------- CSV
def write_csv(name, rows, cols):
    with open(os.path.join(CSV, name), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([" / ".join(map(str, r[c])) if isinstance(r.get(c), list)
                        else r.get(c, "") for c in cols])


print("生成 CSV：")
write_csv("items.csv", items,
          ["id", "name", "name_zh", "type", "quality", "quote",
           "description_en", "description_zh", "tags", "unlocked_by",
           "added_in", "wiki_page"])
write_csv("trinkets.csv", trinkets,
          ["id", "name", "name_zh", "quote", "description_en", "description_zh",
           "tags", "unlocked_by", "added_in", "wiki_page"])
write_csv("cards.csv", cards,
          ["id", "name", "name_zh", "description_en", "description_zh", "added_in"])
write_csv("pills.csv", pills,
          ["id", "name", "name_zh", "description_en", "description_zh"])
write_csv("characters.csv", characters,
          ["id", "name", "damage", "tears", "speed", "range",
           "unlocked_by", "added_in"])
write_csv("challenges.csv", challenges,
          ["number", "name", "character", "description", "goal", "unlocks", "added_in"])
write_csv("achievements.csv", achievements,
          ["id", "name", "description", "requirements", "added_in"])
write_csv("entities.csv", entities,
          ["id", "variant", "subtype", "name", "type", "added_in"])
write_csv("floors.csv", stages,
          ["name", "chapter", "stage", "stage_type", "bosses", "unlocked_by"])

print("完成。数量统计：", json.dumps(counts, ensure_ascii=False))
