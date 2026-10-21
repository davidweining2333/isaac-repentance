# 中文覆盖层 / Chinese overlay

`zh.json` 是 `viewer.html` 使用的中文覆盖层。英文源数据始终保留在
`json/isaac_repentance_all.json` 的 `name`、`description`、`requirements` 等字段中；
查看器只在中文模式下叠加本文件，不会覆盖英文原文。

## 来源与许可

| 来源 | 用途 | 许可 |
|---|---|---|
| [以撒的结合中文维基（灰机 Wiki）](https://isaac.huijiwiki.com/) | 成就中文名 / 描述 / 解锁条件、怪物译名、角色名与头像、楼层名与截图、套装名与形象、挑战、道具池、房间类型 / 机制摘要 | **CC BY-NC-SA 3.0**（以站点声明为准；禁止商业使用，转载需署名并以相同方式共享） |
| [bindingofisaacrebirth.wiki.gg](https://bindingofisaacrebirth.wiki.gg/) | 英文源数据、品质、道具池、成就、实体、房间机制等 | CC BY-SA 4.0 |
| [External-Item-Descriptions](https://github.com/wofsauge/External-Item-Descriptions) | 道具 / 饰品 / 卡牌 / 药丸的中文名与效果 | 仓库未附 LICENSE，保留上游版权 |
| 游戏本体素材 | 道具、饰品、卡牌、角色、怪物、成就、楼层等图标 | © Nicalis / Edmund McMillen；非官方粉丝图鉴，仅作非商业展示 |

中文译名是社区译名，不保证与官方简体中文完全一致；缺失的中文会显示
**“中文待补”**，不会用英文或机器翻译冒充中文。

## 文件结构

```json
{
  "_meta": { "language": "zh-CN", "source": "...", "source_url": "...", "note": "..." },
  "achievements": { "1": { "name_zh": "...", "description_zh": "...", "image": "images/achievement/1.png" } },
  "entities": { "10.0.0": "皱眉裂口尸" },
  "entity_images": { "10.0.0": "images/entity/10.0.0.png" },
  "challenges": { "1": "漆黑一片" },
  "item_pools": { "Angel Room": "天使房" },
  "characters": { "Isaac": "以撒" },
  "character_images": { "Isaac": "images/player/isaac.png" },
  "transformations": { "Guppy": "嗝屁猫！" },
  "transformation_images": { "Guppy": "images/transformation/guppy.gif" },
  "floors": { "Basement": "地下室" },
  "room_types": { "Shop": "商店" },
  "room_guides": { "Shop": { "title_zh": "...", "summary_zh": "..." } }
}
```

- `entities` / `entity_images` 的键是 `id.variant.subtype`，与英文数据集一致。
- 角色数据有 40 条，对应 34 个独立头像；重复条目共用头像，当前 40 条均有图。
- 道具池、挑战、房间类型、房间机制目前没有逐条封面图标，查看器使用分类 SVG
  占位图；道具池条目内仍显示完整道具列表。

## 重新生成

```bash
cd isaac-repentance
.venv/bin/python build_i18n.py
.venv/bin/python make_viewer.py
```

`build_i18n.py` 从 `raw/` 下的抓取结果生成 `i18n/zh.json`；
`make_viewer.py` 把英文数据与中文覆盖层合并，生成可离线打开的单文件
`viewer.html`。

## 图片说明

- `images/achievement/{id}.png`：从中文 Wiki 的 `Achievement_sprite.jpg` 裁切。
- `images/player/*.png`：从中文 Wiki 角色精灵图裁切，48×48。
- `images/entity/{id.variant.subtype}.png`：中文 Wiki 的 `Entity_*.png` 原始小图。
- `images/transformation/*`：中文 Wiki 的套装形象图（部分为 GIF）。
- `images/stage/*.png`：中文 Wiki 的楼层截图 / 图标。
- `images/collectible`、`images/trinket`、`images/pickup`：英文 Wiki 图标。

如果公开部署，请保留本文件、查看器页脚和主应用「说明」页中的来源与许可说明。
