# 《以撒的结合：忏悔 / 忏悔+》全资料数据集

一个可直接使用的结构化数据集，覆盖**道具、饰品、卡牌、药丸、道具池、角色、变形、成就、挑战、怪物、楼层、房间**等全部游戏资料，含**中文名称 + 中文效果描述**。

> 重新生成：`python3 build.py`（依赖 Python 3，无第三方库）

---

## 一、数据放在哪

```
isaac-repentance/
├── json/                     ← 结构化数据（推荐用这个）
│   ├── items.json            道具 719 条
│   ├── trinkets.json         饰品 188 条
│   ├── cards.json            卡牌 / 符文 / 特殊卡 97 条
│   ├── pills.json            药丸效果 51 条
│   ├── item_pools.json       道具池 33 个（含各池道具及权重）
│   ├── characters.json       角色 40 个（含初始属性）
│   ├── transformations.json  变形 16 个（含所需道具）
│   ├── achievements.json     成就 641 条（含解锁条件）
│   ├── challenges.json       挑战 45 个
│   ├── entities.json         怪物 / Boss 583 条
│   ├── floors.json           楼层 35 个（含 Boss、章节）
│   ├── room_types.json       房间类型 32 种
│   ├── room_guides.json      房间机制说明 27 篇
│   └── isaac_repentance_all.json   以上全部合并为单文件
│
├── csv/                      ← 表格数据（UTF-8 BOM，Excel 可直接打开）
│   ├── items.csv / trinkets.csv / cards.csv / pills.csv
│   ├── characters.csv / challenges.csv / achievements.csv
│   ├── entities.csv / floors.csv
│
├── wiki/rooms/               ← 房间机制说明纯文本（27 篇）
├── raw/                      ← 原始数据（EID Lua、Cargo JSON、游戏 XML，可忽略）
├── build.py                  ← 生成脚本
└── README.md
```

**只想查资料**：直接打开 `json/` 对应文件。
**想用 Excel 看**：打开 `csv/` 对应文件。
**要一次拿全部**：用 `json/isaac_repentance_all.json`。

---

## 二、每条记录有哪些字段

### 道具 `items.json`
| 字段 | 说明 |
|---|---|
| `id` | 游戏内道具 ID（1–732） |
| `name` / `name_zh` | 英文名 / 中文名 |
| `quote` | 拾取台词（英文） |
| `quality` | 品质 0–4（`null` = 该道具无品质，如剧情道具） |
| `type` | `active` 主动道具 / `passive` 被动道具 |
| `description_en` / `description_zh` | 英文 / **中文**效果描述 |
| `wiki_description` | wiki 原始效果说明（补充细节） |
| `tags` | 标签（offensive、familiar、tearsup…） |
| `recharge` | 充能格数（主动道具） |
| `shop_price` / `devil_price` | 商店价 / 恶魔房价 |
| `unlocked_by` | 解锁条件 |
| `added_in` | 引入版本（Rebirth / Afterbirth / Afterbirth+ / Repentance） |
| `wiki_page` | 对应 wiki 页面名 |

### 饰品 `trinkets.json`
`id`、`name`、`name_zh`、`quote`、`description_en`、`description_zh`、`wiki_description`、`tags`、`unlocked_by`、`added_in`、`wiki_page`

### 卡牌 `cards.json` / 药丸 `pills.json`
`id`、`name`、`name_zh`、`description_en`、`description_zh`、（卡牌另有 `quote`、`added_in`）

### 道具池 `item_pools.json`
`name`、`is_greed`（贪婪模式）、`price_type`、`items`（`{name, weight}` 数组）

### 角色 `characters.json`
`id`、`name`、`damage`、`tears`、`speed`、`range`、`unlocked_by`、`added_in`

### 成就 `achievements.json`
`id`、`name`、`description`、`requirements`（解锁要求）、`notes`、`added_in`

### 挑战 `challenges.json`
`number`、`name`、`character`、`description`、`goal`、`starting_item/pickup/trinket`、`blindfolded`、`unlocks`、`added_in`

### 怪物 `entities.json`
`name`、`id`、`type`、`variant`、`subtype`、`added_in`

### 楼层 `floors.json`
`name`、`chapter`、`stage`、`stage_type`、`bosses`、`pattern`、`unlocked_by`

### 房间
- `room_types.json`：房间类型（名称、类型 ID、所属楼层、ID 区间）
- `room_guides.json`：各房间机制说明全文（宝物房、商店、恶魔房、天使房、献祭房、赌博房、错误房、星球房、黑市、爬行空间…）

---

## 三、数量统计

| 分类 | 数量 |
|---|---|
| 道具 | 719 |
| 饰品 | 188 |
| 卡牌 / 符文 | 97 |
| 药丸 | 51 |
| 道具池 | 33 |
| 角色 | 40 |
| 变形 | 16 |
| 成就 | 641 |
| 挑战 | 45 |
| 怪物 / Boss | 583 |
| 楼层 | 35 |
| 房间类型 | 32 |
| 房间机制说明 | 27 |

---

## 四、数据来源与许可

| 来源 | 用途 | 许可 |
|---|---|---|
| [wofsauge/External-Item-Descriptions](https://github.com/wofsauge/External-Item-Descriptions) | 名称、效果描述（中英文） | 仓库未附 LICENSE；代码公开但**没有明确开源许可**，默认保留版权 |
| [bindingofisaacrebirth.wiki.gg](https://bindingofisaacrebirth.wiki.gg) | 品质、标签、解锁、道具池、成就、挑战、角色、实体、房间机制 | CC BY-SA 4.0 |
| [wofsauge/Basement-Renovator](https://github.com/wofsauge/Basement-Renovator) | 房间类型、楼层定义（游戏 XML） | [LICENSE.md](https://github.com/wofsauge/Basement-Renovator/blob/main/LICENSE.md) 写明 All Rights Reserved |
| [bindingofisaacrebirth.wiki.gg](https://bindingofisaacrebirth.wiki.gg) `Special:FilePath` | 道具 / 饰品 / 卡牌等图标 | Wiki 图片；游戏素材版权归 Nicalis / Edmund McMillen，具体图片许可以文件页为准 |

- 中文名称与描述来自 EID 模组的 `zh_cn` 语言包。
- 「引入版本」`added_in` 由 wiki 页面分类（`Category:Added in X`）判定。
- 保留上游数据的版权声明；对外再分发时请注明出处与相应许可。
- **这不是一个统一开源许可的数据集**：wiki 文本是 CC BY-SA 4.0，EID 与 Basement Renovator 并没有明确开源授权。若要公开再分发，请先确认上游授权；游戏图标/美术属于游戏版权方，不属于开源素材。本项目仅作非官方粉丝图鉴使用。

---

## 五、已知边界

1. **道具总数 719**：游戏内 ID 编号到 732，但部分 ID 为未使用 / 占位（如 43、61、235…），实际有效道具为 719 条。
2. **品质为空（3 条）**：`Money = Power`、`Broken Shovel`×2 —— wiki 品质表本身无值（Broken Shovel 为剧情道具，无品质），非抓取错误。
3. **房间「布局」未包含**：完整的房间格子布局存储在游戏的二进制 `rooms.stb` 中，社区无公开的纯 JSON 全量布局数据。本数据集提供**房间类型 + 各房间机制说明 + 楼层/Boss**；若需逐个房间的布局，请用 Basement Renovator 打开自己购买的游戏目录下的 `resources/rooms/`。
4. `quote`（拾取台词）与部分 wiki 原文为英文；中文集中在 `name_zh` 与 `description_zh`。

---

## 六、如何更新

数据随游戏版本更新（当前对齐 Repentance+ v1.9.7.x）：

```bash
cd isaac-repentance
# 1. 重新下载 EID 最新 Lua（raw/ 目录）
# 2. 重新抓取 wiki Cargo（raw/wiki_cargo.json / wiki_cargo2.json / wiki_categories.json）
# 3. 重新生成
python3 build.py
```

`build.py` 顶部注释说明了各来源与解析逻辑，可按需扩展字段。

---

## 七、图鉴 App（网页版 / PWA）

`app/web/` 是可直接使用的图鉴应用：模糊搜索 + 拍照识别，纯前端、无 AI 模型。

### 本地运行

```bash
cd isaac-repentance
python3 -m http.server 8765
# 浏览器打开 http://localhost:8765/
```

> 直接双击 `app/web/index.html` 也能用（file:// 模式），但 Service Worker / 离线缓存需要 http(s)。

### 手机上使用

部署到任意静态托管后，用手机浏览器打开，选择「添加到主屏幕」，即可像 App 一样全屏使用。
搜索与识别所需数据在首次加载后即全部本地化；在「说明」页点「缓存全部图标（约 4MB）」可把 1000 张图标也存到本地，之后**完全离线可用**。

### 推到 GitHub

```bash
cd isaac-repentance
git add -A
git commit -m "以撒图鉴 PWA"
git branch -M main
# 先在 GitHub 新建空仓库（不要勾选 README / .gitignore）
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

### 部署（PWA）

> 部署**整个仓库根目录**，不是只部署 `app/web/`。`images/`、`manifest.json`、`sw.js` 都在根目录，缺一不可。

**Vercel（推荐，私有仓库也可）**
1. Vercel → Add New → Project → 导入刚推的仓库
2. Framework Preset 选 `Other`
3. Root Directory `./`；Build Command 留空；Output Directory 填 `.`
4. Deploy，访问 `https://<项目名>.vercel.app/`

**GitHub Pages（仓库需公开）**
1. 仓库 Settings → Pages → Source 选 `Deploy from a branch`
2. 分支选 `main`（或当前的 `master`）、目录 `/ (root)` → Save
3. 等 1–2 分钟，访问 `https://<用户名>.github.io/<仓库名>/`
4. 根目录已有 `.nojekyll`，无需额外配置

**Netlify**
- 导入仓库，Build Command 留空，Publish directory 填 `.`

**部署后自检**
- 根路径落地页能打开，点「打开图鉴」正常
- `/manifest.json`、`/sw.js` 都返回 200
- 桌面浏览器 DevTools → Application：Manifest 显示可安装，Service Worker 为 activated
- 手机「添加到主屏幕」后开飞行模式：搜索、识别仍可用

> 必须 HTTPS 才能启用 Service Worker / 离线缓存。本地预览用 `python3 -m http.server 8765`。

### 更新

`git push` 后 Vercel / Pages 会自动重新部署。改过 HTML/JS 后，把 `sw.js` 顶部的 `V` 加一（如 `isaac-guide-v3` → `v4`），强制老用户换新外壳；替换图标时把 `IMG` 加一。

### 三个识别后端

| 后端 | 状态 | 说明 |
|---|---|---|
| ① 无模型·像素模板 | 默认可用 | 16×16 彩色模板 + alpha 掩码（腐蚀 1px）+ 6 尺度 × 5 旋转 × 9 平移 = 270 候选；照片级测试 Top1 5/5，单次 75–100ms |
| ② 本地小模型 | 加载槽 | 可加载与 `recognition.js` 同格式的 JSON |
| ③ 用户自定义模型 | 加载槽 | 同上，用于替换 / 扩充图标库 |

模型 JSON 格式（数组，每条）：

```json
{ "kind": "item", "id": 105, "name": "The D6", "name_zh": "六面骰",
  "image": "images/collectible/105.png", "image_url": "",
  "v": "<base64 int8 z-score>", "m": "<base64 32字节掩码>" }
```

`v` / `m` 由 `app/build_recognition.py` 生成。

> 识别覆盖道具 / 饰品 / 卡牌共 1000 个图标模板；药丸没有固定外观，按设计不参与识别。构图越接近正面、道具占比越大越准；严重透视、反光、遮挡的实拍未做保证。识别结果可以点击打开完整详情。

### 重新构建前端数据

```bash
cd isaac-repentance
.venv/bin/python app/build_guide.py        # 生成 web/guide.js + web/images.json
.venv/bin/python app/build_recognition.py  # 生成 web/recognition.js
```
