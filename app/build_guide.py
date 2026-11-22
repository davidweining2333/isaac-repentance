#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建图鉴搜索库 web/guide.js（window.GUIDE = {...}）。
别名/象形三层：
  1. curated：开发期 AI 手写的俗称 + 象形（按英文/中文名匹配）
  2. auto-look：从中文名提取「像什么」名词标签
  3. color：用 Pillow 从图标内部提取主色标签（去掉透明边缘和描边）
再加拼音。全部合并进 search 串供前端模糊搜索。
"""
import json, os, re, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATASET = os.path.join(ROOT, "json")
IMGROOT = os.path.join(ROOT, "images")
OUT = os.path.join(HERE, "web")
os.makedirs(OUT, exist_ok=True)

from pypinyin import lazy_pinyin
from PIL import Image
import numpy as np

def pinyin(s):
    return "".join(lazy_pinyin(s or ""))

def norm(s):
    """归一化名称：去空格/标点，但保留 ?/!（区分「0-愚者」与「0-愚者？」这类同名卡）。"""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff?？!！]+", "", (s or "").lower())

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

# ---- curated：按 名字(英/中) 索引，支持多个 curated*.json 合并 ----
cur_map = {}
for cp in sorted(glob.glob(os.path.join(HERE, "curated*.json"))):
    cur_raw = load(cp)
    for kind in ("items", "trinkets", "cards", "pills"):
        for name, info in cur_raw.get(kind, {}).items():
            if name.startswith("_"):
                continue
            cur_map[(kind, norm(name))] = info

# ---- 中文名 → 象形名词标签 ----
NOUNS = {
    "心": ["心"], "刀": ["刀"], "菜刀": ["刀"], "剑": ["剑"], "匕首": ["刀"], "剪": ["剪刀"],
    "蘑菇": ["蘑菇"], "书": ["书"], "眼": ["眼睛"], "目": ["眼睛"], "炸弹": ["炸弹"],
    "猫": ["猫"], "头": ["头"], "血": ["血"], "蜘蛛": ["蜘蛛"], "蛛": ["蜘蛛"],
    "苍蝇": ["苍蝇"], "蝇": ["苍蝇"], "骨": ["骨头"], "骷髅": ["骷髅"], "牙": ["牙齿"],
    "钥匙": ["钥匙"], "币": ["钱"], "钱": ["钱"], "硬币": ["硬币"], "美元": ["钱"],
    "电池": ["电池"], "药": ["药丸"], "丸": ["药丸"], "胶囊": ["药丸"], "泪": ["眼泪"],
    "翅": ["翅膀"], "翼": ["翅膀"], "环": ["环"], "戒指": ["戒指"], "星": ["星"],
    "月": ["月亮"], "太阳": ["太阳"], "蛋": ["蛋"], "奶": ["奶"], "水": ["水"],
    "火": ["火"], "冰": ["冰"], "毒": ["毒"], "恶魔": ["恶魔"], "天使": ["天使"],
    "幽灵": ["幽灵"], "魂": ["灵魂"], "灵魂": ["灵魂"], "糖": ["糖果"], "肉": ["肉"],
    "鱼": ["鱼"], "纸": ["纸"], "卡": ["卡片"], "笔": ["笔"], "帽": ["帽子"],
    "鞋": ["鞋"], "袜": ["袜子"], "衣": ["衣服"], "袍": ["衣服"], "袋": ["袋子"],
    "包": ["袋子"], "盒": ["盒子"], "箱": ["盒子"], "罐": ["罐子"], "瓶": ["瓶子"],
    "杯": ["杯子"], "针": ["针"], "线": ["线"], "绷": ["绷带"], "石": ["石头"],
    "金": ["金色"], "银": ["银色"], "玻璃": ["玻璃"], "木": ["木头"], "铁": ["金属"],
    "十字": ["十字"], "王冠": ["王冠"], "花": ["花"], "树": ["树"], "草": ["草"],
    "手": ["手"], "脚": ["脚"], "指": ["手指"], "脑": ["脑"], "胃": ["胃"],
    "骰": ["骰子"], "沙漏": ["沙漏"], "镜": ["镜子"], "灯": ["灯"], "蜡烛": ["蜡烛"],
    "甲": ["壳"], "壳": ["壳"], "虫": ["虫"], "龙": ["龙"], "羊": ["羊"], "狗": ["狗"],
    "蘑菇": ["蘑菇"], "洋葱": ["洋葱"], "柠檬": ["柠檬"], "香蕉": ["水果"], "苹果": ["水果"],
}

def auto_look(name_zh):
    tags = set()
    s = name_zh or ""
    for noun, tags_out in NOUNS.items():
        if noun in s:
            tags.update(tags_out)
    return sorted(tags)

# ---- 图标主色 ----
def color_name(r, g, b):
    import colorsys
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    h *= 360
    if l < 0.18: return "黑色"
    if l > 0.85 and s < 0.18: return "白色"
    if s < 0.16: return "灰色"
    if 15 <= h < 45: return "棕色" if l < 0.45 else "橙色"
    if h < 15 or h >= 330: return "红色"
    if h < 70: return "黄色"
    if h < 160: return "绿色"
    if h < 200: return "青色"
    if h < 255: return "蓝色"
    if h < 290: return "紫色"
    return "粉色"

def _erode(mask, n):
    """向内腐蚀 alpha 掩码，去掉图标最外圈的描边/抗锯齿。"""
    for _ in range(n):
        p = np.pad(mask, 1, constant_values=False)
        mask = (p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:] & p[1:-1, 1:-1])
    return mask


def icon_colors(image_rel, n=2):
    p = os.path.join(ROOT, image_rel)
    if not image_rel or not os.path.exists(p):
        return []
    try:
        im = Image.open(p).convert("RGBA")
    except Exception:
        return []

    a = np.asarray(im)
    alpha = a[:, :, 3]
    if (alpha < 200).any():
        # 图标带透明背景：按尺寸腐蚀 1–2px（大图按比例），避开黑色描边。
        er = max(1, min(12, int(min(im.size) * 0.05 + 0.5)))
        mask = _erode(alpha >= 200, er)
        if int(mask.sum()) < 20:
            mask = alpha >= 200
    else:
        # 卡牌是整块不透明图，最外圈是深色边框；裁掉 1px 再取色。
        a = a[1:-1, 1:-1]
        mask = np.ones(a.shape[:2], dtype=bool)
    if not mask.any():
        return []

    counts = {}
    for px in a[mask][:, :3]:
        c = color_name(int(px[0]), int(px[1]), int(px[2]))
        counts[c] = counts.get(c, 0) + 1
    total = sum(counts.values()) or 1
    ranked = sorted(counts.items(), key=lambda x: -x[1])

    # 黑色要同时满足「占比高」和「成片」：描边/细线腐蚀 1px 后就没了，
    # 真正的黑色主体（黑球、黑影、黑衣）会留下明显的黑色核心。
    rgb = a[:, :, :3].astype(np.float32) / 255
    lum = (rgb.max(axis=2) + rgb.min(axis=2)) / 2
    black_mask = (lum < 0.18) & mask
    black_px = int(black_mask.sum())
    black_core = int(_erode(black_mask, 1).sum()) if black_px else 0
    black_solid = black_px > 0 and black_core / black_px >= 0.2

    out = []
    for c, v in ranked:
        share = v / total
        # 黑色大多是图标外描边：只有黑色是主色、占内部一半以上、且有成片黑色才保留。
        if c == "黑色" and (ranked[0][0] != "黑色" or share < 0.5 or not black_solid):
            continue
        if share < 0.06:
            continue
        out.append(c)
        if len(out) >= n:
            break
    if not out and ranked:
        out = [ranked[0][0]]
    return out

def build_entry(kind, rec):
    cur = cur_map.get((kind, norm(rec.get("name")))) or cur_map.get((kind, norm(rec.get("name_zh")))) or {}
    nick = cur.get("nick", [])
    look = sorted(set(cur.get("look", [])) | set(auto_look(rec.get("name_zh"))) | set(icon_colors(rec.get("image", ""))))
    name_zh = rec.get("name_zh", "") or ""
    name = rec.get("name", "") or ""
    py = sorted({pinyin(name_zh), pinyin("".join(nick))} - {""})
    kw = {name, name_zh, rec.get("quote", "")} | set(rec.get("tags", []))
    terms = {t for t in (kw | set(nick) | set(look) | set(py)) if t}
    return {
        "id": rec.get("id"), "name": name, "name_zh": name_zh,
        "quote": rec.get("quote", ""), "quality": rec.get("quality"),
        "type": rec.get("type", ""), "recharge": rec.get("recharge", ""),
        "desc_zh": rec.get("description_zh", ""),
        "unlocked_by": rec.get("unlocked_by", ""),
        "unlocked_by_zh": rec.get("unlocked_by_zh", ""),
        "requirements": rec.get("requirements", ""),
        "requirements_zh": rec.get("requirements_zh", ""),
        "wiki_page": rec.get("wiki_page", ""),
        "nick": nick, "look": look, "pinyin": py,
        "image": rec.get("image", ""), "image_url": rec.get("image_url", ""),
        "search": " ".join(terms).lower(),
    }

items = [build_entry("items", r) for r in load(os.path.join(DATASET, "items.json"))]
trinkets = [build_entry("trinkets", r) for r in load(os.path.join(DATASET, "trinkets.json"))]
cards = [build_entry("cards", r) for r in load(os.path.join(DATASET, "cards.json"))]
pills = [build_entry("pills", r) for r in load(os.path.join(DATASET, "pills.json"))]

# ---- 房间说明：room_guides（英文机制文）+ i18n 中文摘要 ----
zh_rooms = load(os.path.join(ROOT, "i18n", "zh.json")).get("room_guides", {})
rooms = []
for key in load(os.path.join(DATASET, "room_guides.json")):
    z = zh_rooms.get(key, {})
    name_zh = z.get("title_zh", "") or key
    summary = z.get("summary_zh", "")
    rooms.append({
        "name": key, "name_zh": name_zh, "desc_zh": summary,
        "nick": [], "look": [], "pinyin": [pinyin(name_zh)],
        "image": "", "image_url": "", "wiki_page": key,
        "search": " ".join(filter(None, [key, name_zh, summary])).lower(),
    })

guide = {"meta": {"items": len(items), "trinkets": len(trinkets), "cards": len(cards),
                  "pills": len(pills), "rooms": len(rooms)},
         "items": items, "trinkets": trinkets, "cards": cards, "pills": pills, "rooms": rooms}
js = "window.GUIDE = " + json.dumps(guide, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(os.path.join(OUT, "guide.js"), "w", encoding="utf-8").write(js)

# 图片清单（供 PWA 一键离线缓存；相对于仓库根目录）
imgs = sorted({x["image"] for x in items + trinkets + cards + pills if x.get("image")})
open(os.path.join(OUT, "images.json"), "w", encoding="utf-8").write(
    json.dumps(imgs, ensure_ascii=False, separators=(",", ":")))

n_nick = sum(1 for x in items+trinkets+cards+pills if x["nick"])
n_look = sum(1 for x in items+trinkets+cards+pills if x["look"])
print(f"items={len(items)} trinkets={len(trinkets)} cards={len(cards)} pills={len(pills)} rooms={len(rooms)}")
print(f"含俗称={n_nick}  含象形标签={n_look}")
print(f"web/guide.js {len(js)/1024:.0f}KB  ·  web/images.json {len(imgs)} 张")
