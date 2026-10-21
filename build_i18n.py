#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Simplified-Chinese overlay used by viewer.html.

The source dataset stays English-first (`name`, `description`, ...).  This
script creates `i18n/zh.json`, which is merged by make_viewer.py at render
time.  Keeping the overlay separate means we can update translations without
touching the scraped/raw dataset and it is always possible to display the
original English text.

Chinese achievement rows were read from the Chinese Isaac wiki (灰机 wiki)
on 2026-10-21.  See i18n/README.md for sources and attribution.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


def load(name):
    with open(os.path.join(RAW, name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- achievements
# The wiki table gives us both the Chinese unlock text and the Chinese
# requirement.  A handful of "names" are only symbols; make sure they still
# have something readable in Chinese mode.
ACH_FALLBACK_NAMES = {
    32: "？？？",
    175: "〇",
    235: "1001%！！",
    339: "1000000%",
    458: "'M",
}
achievements = {}
for row in load("zh_achievements.json"):
    aid = str(row["id"])
    name_zh = (row.get("name_zh") or "").strip()
    if not name_zh:
        name_zh = ACH_FALLBACK_NAMES.get(row["id"], "")
    entry = {
        "name_zh": name_zh,
        "description_zh": (row.get("description_zh") or "").strip(),
        "requirements_zh": (row.get("requirements_zh") or "").strip(),
        "reward_zh": (row.get("reward_zh") or "").strip(),
        "image": f"images/achievement/{row['id']}.png",
    }
    achievements[aid] = {k: v for k, v in entry.items() if v}

# ---------------------------------------------------------------- entities
# Keys are id.variant.subtype, matching the fields in the English dataset.
entities = {}
for key, name in load("zh_entities.json").items():
    if name and name not in {"#", " "}:
        entities[key] = name

# ---------------------------------------------------------------- challenges
challenges = {
    "1": "漆黑一片",
    "2": "格调高雅",
    "3": "头部创伤",
    "4": "黑暗降临",
    "5": "坦克",
    "6": "太阳系",
    "7": "自杀之王",
    "8": "好奇害死猫",
    "9": "拆迁办",
    "10": "诅咒！",
    "11": "玻璃大炮",
    "12": "当生活充满酸意",
    "13": "豆子！",
    "14": "尽在卡牌中",
    "15": "慢吞吞",
    "16": "技术宅",
    "17": "吐豆人",
    "18": "宿主",
    "19": "顾家男人",
    "20": "返璞归真",
    "21": "超超超超超大层",
    "22": "快马加鞭！",
    "23": "蓝色炸弹人",
    "24": "充钱游戏",
    "25": "没心没肺",
    "26": "以撒传说！",
    "27": "脑子！",
    "28": "彩虹日！",
    "29": "俄南连击",
    "30": "守护者",
    "31": "本末倒置",
    "32": "愚人节",
    "33": "宝可萌",
    "34": "终极困难",
    "35": "乒乓",
    "36": "掏粪男孩",
    "37": "血腥玛丽",
    "38": "圣火洗礼",
    "39": "以撒织梦岛",
    "40": "重影幻视",
    "41": "异食游戏",
    "42": "烫手山芋",
    "43": "大量过牌！",
    "44": "赤键救赎",
    "45": "删除这个",
}

# ---------------------------------------------------------------- item pools
item_pools = {
    "Angel Room": "天使房",
    "Baby Shop": "宝宝商店",
    "Battery Bum": "电池乞丐",
    "Beggar": "乞丐",
    "Bomb Bum": "炸弹乞丐",
    "Boss": "头目房",
    "Crane Game": "夹娃娃机",
    "Curse Room": "诅咒房",
    "Devil Beggar": "恶魔乞丐",
    "Devil Room": "恶魔房",
    "Golden Chest": "金箱子",
    "Greed Angel Room": "贪婪模式天使房",
    "Greed Boss": "贪婪模式头目房",
    "Greed Curse Room": "贪婪模式诅咒房",
    "Greed Devil Room": "贪婪模式恶魔房",
    "Greed Golden Chest": "贪婪模式金箱子",
    "Greed Library": "贪婪模式图书馆",
    "Greed Secret Room": "贪婪模式隐藏房",
    "Greed Shop": "贪婪模式商店",
    "Greed Treasure Room": "贪婪模式宝箱房",
    "Key Master": "钥匙大师",
    "Library": "图书馆",
    "Mom's Chest": "妈妈的箱子",
    "Old Chest": "旧箱子",
    "Planetarium": "星象房",
    "Red Chest": "红箱子",
    "Rotten Beggar": "腐烂乞丐",
    "Secret Room": "隐藏房",
    "Shell Game": "猜壳游戏",
    "Shop": "商店",
    "Treasure Room": "宝箱房",
    "Ultra Secret Room": "究极隐藏房",
    "Wooden Chest": "木箱子",
}

# ---------------------------------------------------------------- characters
characters = {
    "Jacob & Esau": "雅各和以扫",
    "Cain": "该隐",
    "Magdalene": "抹大拉",
    "Judas": "犹大",
    "??? (Character)": "？？？",
    "Eve": "夏娃",
    "Samson": "参孙",
    "Azazel": "阿撒泻勒",
    "Lazarus": "拉撒路",
    "Eden": "伊甸",
    "The Lost": "游魂",
    "Lilith": "莉莉丝",
    "Isaac": "以撒",
    "Keeper": "店主",
    "Apollyon": "亚玻伦",
    "The Forgotten": "遗骸",
    "Bethany": "伯大尼",
    "Tainted Isaac": "堕化以撒",
    "Tainted Magdalene": "堕化抹大拉",
    "Tainted Cain": "堕化该隐",
    "Tainted Judas": "堕化犹大",
    "Tainted ???": "堕化？？？",
    "Tainted Eve": "堕化夏娃",
    "Tainted Samson": "堕化参孙",
    "Tainted Azazel": "堕化阿撒泻勒",
    "Tainted Lazarus": "堕化拉撒路",
    "Tainted Eden": "堕化伊甸",
    "Tainted Lost": "堕化游魂",
    "Tainted Lilith": "堕化莉莉丝",
    "Tainted Keeper": "堕化店主",
    "Tainted Apollyon": "堕化亚玻伦",
    "Tainted Forgotten": "堕化遗骸",
    "Tainted Bethany": "堕化伯大尼",
    "Tainted Jacob": "堕化雅各",
}
def load_optional(name):
    try:
        return load(name)
    except FileNotFoundError:
        return {}


character_images = load_optional("zh_char_images.json")
entity_images = load_optional("zh_entity_images.json")
transformation_images = load_optional("zh_transformation_images.json")

# ---------------------------------------------------------------- transformations
transformations = {
    "Guppy": "嗝屁猫！",
    "Beelzebub": "苍蝇套装",
    "Fun Guy": "蘑菇套装",
    "Seraphim (Transformation)": "天使套装",
    "Bob": "鲍勃套装",
    "Spun": "针套装",
    "Yes Mother?": "妈妈套装",
    "Conjoined": "连体套装",
    "Leviathan": "恶魔套装",
    "Oh Crap": "大便套装",
    "Bookworm": "书套装",
    "Adult": "成人套装",
    "Spider Baby (Transformation)": "蜘蛛套装",
    "Stompy": "践踏套装",
    "Necromancer": "死灵法师套装",
    "Super Bum": "乞丐套装",
}

# ---------------------------------------------------------------- floors
floors = {
    "Special Rooms": "特殊房间",
    "Basement": "地下室",
    "Cellar": "地窖",
    "Burning Basement": "燃烧地下室",
    "Caves": "洞穴",
    "Catacombs": "墓穴",
    "Flooded Caves": "淹水洞穴",
    "Depths": "深牢",
    "Necropolis": "坟场",
    "Dank Depths": "阴湿深牢",
    "Womb": "子宫",
    "Utero": "血宫",
    "Scarred Womb": "结痂子宫",
    "Blue Womb": "？？？（蓝子宫）",
    "Sheol": "阴间",
    "Cathedral": "教堂",
    "Dark Room": "暗室",
    "Chest": "玩具箱",
    "Downpour": "下水道",
    "Dross": "污水井",
    "Mines": "矿洞",
    "Ashpit": "灰坑",
    "Mausoleum": "陵墓",
    "Gehenna": "炼狱",
    "Corpse": "尸宫",
    "Mortis": "Mortis（暂译）",
    "Home": "家",
    "Special Rooms [Greed]": "特殊房间（贪婪）",
    "Basement [Greed]": "地下室（贪婪）",
    "Caves [Greed]": "洞穴（贪婪）",
    "Depths [Greed]": "深牢（贪婪）",
    "Womb [Greed]": "子宫（贪婪）",
    "Sheol [Greed]": "阴间（贪婪）",
    "The Shop [Greed]": "商店（贪婪）",
    "Ultra Greed [Greed]": "究极贪婪（贪婪）",
}

# ---------------------------------------------------------------- room types
room_types = {
    "Null Room": "空房间",
    "Normal Room": "普通房间",
    "Grave Room": "墓室",
    "Home Room": "家房间",
    "Shop": "商店",
    "Error Room": "错误房",
    "Treasure Room": "宝箱房",
    "Boss Room": "头目房",
    "Mini-Boss Room": "小头目房",
    "Secret Room": "隐藏房",
    "Super Secret Room": "超级隐藏房",
    "Arcade": "赌博房",
    "Curse Room": "诅咒房",
    "Challenge Room": "挑战房",
    "Library": "图书馆",
    "Sacrifice Room": "献祭房",
    "Devil Room": "恶魔房",
    "Angel Room": "天使房",
    "Crawlspace": "夹层",
    "Boss Rush Room": "头目车轮战房",
    "Isaac's Room": "以撒的房间",
    "Barren Room": "荒芜房间",
    "Chest Room": "箱子房",
    "Dice Room": "骰子房",
    "Black Market": "黑市",
    "Greed Mode Descent": "贪婪模式下降层",
    "Planetarium": "星象房",
    "Teleporter": "传送器",
    "Teleporter Exit": "传送器出口",
    "Secret Exit": "秘密出口",
    "Blue Room": "蓝色房间",
    "Ultra Secret Room": "究极隐藏房",
}

# Add names scraped from the Chinese wiki's room page for any extra aliases.
try:
    for en, zh in load("zh_room_types.json").items():
        room_types.setdefault(en, zh)
except FileNotFoundError:
    pass

# ---------------------------------------------------------------- room guides
# Long Wiki articles are kept in English as the source text.  A short Chinese
# summary gives the Chinese reader the essential rule at a glance.
room_guides = {
    "Achievements": ("成就", "完成挑战、通关标记、隐藏目标或解锁条件后获得的游戏内成就；Steam 成就与游戏秘密基本一一对应。"),
    "Angel Room": ("天使房", "恶魔房的圣洁对应房间，通常提供免费道具；拿取一个后其余道具会消失。"),
    "Arcade": ("赌博房", "偶数层且离开上一层时持有至少 5 枚硬币才可能出现，需要 1 枚硬币开门。"),
    "Bedroom": ("卧室", "稀有房间，通常需要睡袋等道具生成，睡觉可恢复红心。"),
    "Black Market": ("黑市", "隐藏商店，出售道具、掉落物，有时可用生命或钥匙交易。"),
    "Boss Room": ("头目房", "每层尽头的主要头目房间，击败头目后会出现通往下一层的活板门。"),
    "Boss Rush": ("头目车轮战", "在妈妈头目战后的房间中，20 分钟内进入可挑战连续头目波次。"),
    "Challenge Room": ("挑战房", "进入后门会关闭，必须清空房间内所有敌人才能离开并获得奖励。"),
    "Challenges": ("挑战模式", "带有预设角色、道具或特殊规则的特殊游戏模式，完成后解锁对应奖励。"),
    "Closet": ("贮藏室", "稀有的小型死胡同布局，常由特定道具或地形组合生成。"),
    "Crawl Space": ("夹层", "位于楼层地图之外的狭小空间，通常通过破坏特定墙壁进入。"),
    "Curse Room": ("诅咒房", "进入会损失半颗心，内部可能有道具、掉落物或通往恶魔房的通道。"),
    "Devil Room": ("恶魔房", "用红心容器交换强力道具的房间；交易会降低之后天使房的出现概率。"),
    "Dice Room": ("骰子房", "提供一次性骰子效果，可重 roll 道具、掉落物或房间内容。"),
    "Grave Room": ("墓室", "特殊房间类型，通常与墓地/陵墓主题楼层相关。"),
    "I AM ERROR": ("错误房", "错误房／I AM ERROR，连接地图之外的房间，可能包含商店或特殊道具。"),
    "Item Pool": ("道具池", "决定不同房间、商店和乞丐生成哪些道具的权重表。"),
    "Library": ("图书馆", "包含书架的房间，可拾取书籍类主动道具；部分楼层有图书馆。"),
    "Mini-Boss Room": ("小头目房", "包含小头目的特殊房间，清理后可能获得道具或掉落物。"),
    "Planetarium": ("星象房", "拥有星象道具池的特殊房间，需要特定条件才会生成。"),
    "Rooms": ("房间", "楼层由不同类型、大小和布局的房间组成，房间类型决定内容与规则。"),
    "Sacrifice Room": ("献祭房", "通过献祭红心获得奖励，连续献祭可触发天使、传送或特殊掉落。"),
    "Secret Room": ("隐藏房", "需要通过炸弹、红钥匙等发现的秘密房间，通常包含道具或掉落物。"),
    "Shop": ("商店", "用硬币购买道具、掉落物或电池的房间，部分商品需要钥匙解锁。"),
    "Transformations": ("套装 / 变形", "收集指定组合的道具后自动获得的变身效果，提供额外能力。"),
    "Treasure Room": ("宝箱房", "每层通常出现的道具房，从第二层开始需要钥匙开门。"),
    "Vault": ("宝库", "需要两把钥匙打开的特殊房间，内部通常有大量硬币。"),
}

overlay = {
    "_meta": {
        "language": "zh-CN",
        "source": "以撒的结合中文维基（灰机 wiki） / EID",
        "source_url": "https://isaac.huijiwiki.com/",
        "note": "中文为社区译名/说明；英文原文字段始终保留在数据集中。",
    },
    "achievements": achievements,
    "entities": entities,
    "challenges": challenges,
    "item_pools": item_pools,
    "characters": characters,
    "character_images": character_images,
    "entity_images": entity_images,
    "transformation_images": transformation_images,
    "transformations": transformations,
    "floors": floors,
    "room_types": room_types,
    "room_guides": {k: {"title_zh": v[0], "summary_zh": v[1]} for k, v in room_guides.items()},
}

out = os.path.join(ROOT, "i18n", "zh.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(overlay, f, ensure_ascii=False, indent=1)
print("wrote", out)
print({k: (len(v) if hasattr(v, "__len__") else 0) for k, v in overlay.items() if not k.startswith("_")})
