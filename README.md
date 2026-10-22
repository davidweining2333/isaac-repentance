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
├── images/                   ← 本地图标（道具 / 饰品 / 卡牌 / 成就 / 角色 / 怪物 / 楼层 / 套装）
├── i18n/                     ← 中文覆盖层 zh.json 与来源 / 许可说明
├── viewer.html               ← 单文件、可离线打开的双语全资料查看器
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
| `recharge` | 主动道具充能：数字=房间数，`Ns`=秒数自动充能，`unlimited`=无限使用，`one time`=一次性，`variable` / `damage` / `1f`=特殊充能 |
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
| [以撒的结合中文维基（灰机 Wiki）](https://isaac.huijiwiki.com/) | 中文成就 / 怪物 / 角色 / 楼层 / 套装译名，以及部分角色、怪物、成就、楼层图标 | **CC BY-NC-SA 3.0**（非商业使用；转载需署名并以相同方式共享） |
| [wofsauge/Basement-Renovator](https://github.com/wofsauge/Basement-Renovator) | 房间类型、楼层定义（游戏 XML） | [LICENSE.md](https://github.com/wofsauge/Basement-Renovator/blob/main/LICENSE.md) 写明 All Rights Reserved |
| [bindingofisaacrebirth.wiki.gg](https://bindingofisaacrebirth.wiki.gg) `Special:FilePath` | 道具 / 饰品 / 卡牌等图标 | Wiki 图片；游戏素材版权归 Nicalis / Edmund McMillen，具体图片许可以文件页为准 |

- 道具 / 饰品 / 卡牌 / 药丸的中文名称与效果主要来自 EID 模组的 `zh_cn` 语言包；成就、怪物、角色、楼层、套装等中文覆盖层来自灰机 Wiki（见 `i18n/README.md`）。
- 「引入版本」`added_in` 由 wiki 页面分类（`Category:Added in X`）判定。
- 保留上游数据的版权声明；对外再分发时请注明出处与相应许可。灰机 Wiki 的中文文本为 **CC BY-NC-SA 3.0**，不能用于商业用途。
- **这不是一个统一开源许可的数据集**：wiki 文本是 CC BY-SA 4.0 / CC BY-NC-SA 3.0，EID 与 Basement Renovator 并没有明确开源授权。若要公开再分发，请先确认上游授权；游戏图标/美术属于游戏版权方，不属于开源素材。本项目仅作非官方粉丝图鉴使用。

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

`app/web/` 是可直接使用的图鉴应用：模糊搜索 + 拍照识别，纯前端；默认使用免模型的像素模板，也可选 OpenCV ORB 或端侧 DINOv2 向量识别。搜索栏和分类栏吸顶，结果一次全部显示、不再分页；桌面端图标保持原大小，手机端缩小到约四分之一面积。卡片只显示图标，类型用边框颜色区分；道具图标右上角显示品质等级，主动道具左下角显示充能（如 `4房`=4 房间，`自动4s`=每 4 秒自动充能），点开详情会写明充能数和充能方式。「全部」只混合道具 / 饰品 / 卡牌，药丸在独立分类中显示为文字卡片。

### 全资料查看器 `viewer.html`

根目录的 `viewer.html` 是一个**单文件、可离线打开**的全资料查看器，包含 13 个分类：道具、饰品、卡牌、药丸、道具池、角色、套装、成就、挑战、怪物、楼层、房间类型、房间机制。

- 中 / EN 双语切换，语言选择保存在 `localStorage`；英文原文始终保留，中文缺失显示 **“中文待补”**。
- 点击卡片展开字段，支持搜索中文 / 英文 / 描述 / ID。
- 道具图标右上角显示品质等级；主动道具显示充能数并标注是否随时间自动充能；角色、怪物、成就、楼层、套装使用本地图片，缺失时显示分类 SVG 占位图。
- 当前封面图覆盖：道具 716/719、饰品 188/188、卡牌 96/97、成就 641/641、角色 40/40 条、怪物 568/583、楼层 30/35、套装 15/16；道具池、挑战、房间类型、房间机制使用分类 SVG 占位图。药丸没有固定外观，查看器只显示通用占位图，主应用使用文字卡片。
- 生成方式：

```bash
.venv/bin/python build_i18n.py   # 生成 i18n/zh.json
.venv/bin/python make_viewer.py  # 生成 viewer.html
```

图片覆盖情况、中文来源与许可见 [`i18n/README.md`](i18n/README.md)。

### 本地运行

```bash
cd isaac-repentance
python3 -m http.server 8765
# 浏览器打开 http://localhost:8765/
```

> 直接双击 `app/web/index.html` 也能用（file:// 模式），但 Service Worker / 离线缓存需要 http(s)。

### 手机上使用

部署到任意静态托管后，用手机浏览器打开，选择「添加到主屏幕」，即可像 App 一样全屏使用。
默认像素模板的搜索与识别在首次加载后即全部本地化；ORB / 端侧 DINOv2 首次切换需联网下载一次（约 15MB / 35–37MB），之后也会缓存并离线可用。在「说明」页点「缓存全部图标（约 4MB）」可把 1000 张图标也存到本地。

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

### 部署（Cloudflare Workers 静态资源，推荐）

> 部署**整个仓库根目录**，不是只部署 `app/web/`。`images/`、`manifest.json`、`sw.js`、`_headers` 都在根目录，缺一不可。

仓库根目录已包含 `wrangler.jsonc`，其中 `assets.directory: "."` 会把整个仓库作为静态资源上传；Worker 名称固定为 `isaac-repentance`。`.assetsignore` 会排除 `.git`、`.venv`、`raw/`、`.playwright-mcp/`、`.wrangler/` 等本地文件。

**Dashboard 部署**
1. Cloudflare Dashboard → Workers & Pages → Create application → Workers → Create Worker
2. 名称填 `isaac-repentance`，连接 GitHub 仓库（或先用 `npx wrangler deploy` 上传）
3. 构建命令留空，部署命令 `npx wrangler deploy`
4. 部署完成后，在 Worker → Settings → Domains & Routes 绑定自定义域名（域名需托管在 Cloudflare）
5. 以后 `git push` 后重新部署即可；绑定自定义域名后访问速度通常比 `*.workers.dev` 更稳定

**命令行部署**
```bash
cd isaac-repentance
npx wrangler deploy
```

**其他静态托管**
- Vercel / Netlify：Root Directory `./`，Build Command 留空，Output Directory 填 `.`
- GitHub Pages：Settings → Pages → Deploy from a branch，分支 `main`、目录 `/ (root)`；根目录已有 `.nojekyll`

**部署后自检**
- 根路径落地页能打开，点「打开图鉴」正常
- `/manifest.json`、`/sw.js` 都返回 200
- `/app/web/vendor/transformers/ort-wasm.wasm` 返回 200，响应头 `Content-Type: application/wasm`
- 控制台没有 `no available backend found` / `both async and sync fetching of the wasm failed`
- 桌面浏览器 DevTools → Application：Manifest 显示可安装，Service Worker 为 activated；缓存里能看到 `isaac-guide-v17`
- 手机「添加到主屏幕」后开飞行模式：搜索、识别仍可用

> 必须 HTTPS 才能启用 Service Worker / 离线缓存。本地预览用 `python3 -m http.server 8765`。`_headers` 负责 WASM MIME 和 `app.js` / `sw.js` 的缓存头；如果托管平台不支持 `_headers`，至少确保服务器把 `.wasm` 返回为 `application/wasm`。

### 更新

`git push` 后 Cloudflare Worker 会重新部署。改过 HTML/JS 后，把 `sw.js` 顶部的 `V` 加一（当前 `isaac-guide-v17`），强制老用户换新外壳；替换图标时把 `IMG` 加一；改 ORB 特征库、DINOv2 模型或运行库时把 `ENGINE` 加一（当前 `isaac-engine-v1`），否则老的引擎缓存会继续命中。仅新增 `ort-wasm.wasm` 这类按需加载的缺失文件时不需要清空 `ENGINE`，Service Worker 会自动补下载。

### 四个识别后端

| 后端 | 首次加载 | 说明 |
|---|---|---|
| ① 像素模板 | 0（默认） | 24×24 彩色模板 + alpha 掩码（腐蚀 1px）；先做前景/背景分离，再去掉与边缘连通的背景，保留中央前景块；原图高分辨率裁切 + 新/旧两套自动前景框 + 中心/多圈裁切 + 5 旋转 × 9 平移，偏色照片再生成按通道标准化副本，最多约 1800–1900 候选；桌面单次约 0.8–1.4s |
| ② OpenCV ORB | 约 15MB | OpenCV.js 4.13 + 1000 个图标预计算 ORB 描述子（约 10 万点，192×192，nfeatures=100）；查询图先刷白背景，只在图标前景 mask 内提特征；BFMatcher Hamming + ratio test，按模板投票；匹配点少于 3 个时自动回退像素模板。单次约 0.2s |
| ③ 端侧 DINOv2 | 约 35–37MB | Transformers.js 2.17 + DINOv2-small int8（Apache 2.0）+ 本地向量库；查询图先做前景分离并刷白背景；CLS 384 维 + 颜色 512 + Sobel 边缘 256 + 灰度 256，分块 int8 量化后按权重算余弦；再用像素模板对前 24 个候选复核。桌面单次约 1.3s（非 SIMD；支持 SIMD 会更快） |
| ④ 自定义模板 | 用户文件 | 加载与 `recognition.js` 同格式的 JSON，用于替换 / 扩充图标库 |

> ②③ 的引擎和模型只在切换到对应后端时按需下载，并保存在 Service Worker 的 `isaac-engine-v1` 缓存中；之后离线可用。默认 ① 不需要任何额外下载。不支持 WASM SIMD 的浏览器会额外使用 `app/web/vendor/transformers/ort-wasm.wasm`，避免 ORT 报 `no available backend found`。药丸外观随机，所有后端都不识别药丸。

**本机实拍回归**（3 张游戏照片 + 1 张卡牌，手动框选，非正式评测）：

| 场景 | 像素模板 | OpenCV ORB | 端侧 DINOv2 |
|---|---|---|---|
| 六面骰照片 | Top1 94–98% | Top1（5 个匹配点） | Top1（综合 88%） |
| 圣心照片 | Top1 76–77% | Top1（6 个匹配点） | Top1（综合 85%） |
| 血虱照片 | Top1 80–86% | 回退像素模板，Top1 | Top1（综合 74%） |
| 0-愚者卡牌 | Top1 82% | — | Top1（综合 80%） |

样本量小，真实截图/照片受背景、缩放、反光、遮挡影响；结果页会列前 8 个候选，低置信时请点开确认。旧版 20 张合成紧裁回归已不作为当前准确率承诺。

模型 JSON 格式（数组，每条）：

```json
{ "kind": "item", "id": 105, "name": "The D6", "name_zh": "六面骰",
  "image": "images/collectible/105.png", "image_url": "",
  "v": "<base64 int8 z-score>", "m": "<base64 32字节掩码>" }
```

`v` / `m` 由 `app/build_recognition.py` 生成。

> 识别覆盖道具 / 饰品 / 卡牌共 1000 个图标模板；药丸没有固定外观，按设计不参与识别。一次只框一个图标本体，留一点边；识别会先自动去掉与选框边缘连通的背景，并保留描边、火焰和触须。框大一点/歪一点/边缘被裁到会自动多圈兜底；「整图特写」只适合图标占满画面，游戏截图请框选。严重透视、反光、遮挡的实拍未做保证。结果上方会提示“候选很接近/匹配度偏低”，此时请从候选里点开确认。
>
> 开源模型说明：DINOv2-small 采用 Apache 2.0，已随应用本地打包为 int8 ONNX；OpenCV.js 采用 Apache 2.0。Isaac 专用 YOLO 权重没有明确许可证，未打包。上述实拍回归样本量小，不能替代正式评测；若需要更高实拍准确率，需要更多实拍训练/校准数据。

### 重新构建前端数据

```bash
cd isaac-repentance
.venv/bin/python app/build_guide.py        # 生成 web/guide.js + web/images.json
.venv/bin/python app/build_recognition.py  # 生成 web/recognition.js
```
