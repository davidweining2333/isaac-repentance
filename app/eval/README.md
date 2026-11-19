# 拍屏识别评测 / 小模型工具

这里放的是“手机拍屏幕”方向的实验工具，不参与默认图鉴构建。生成数据和训练产物都在
`app/eval/data/`、`app/eval/models/`，已被 `.gitignore` 忽略；只有脚本和 `app/web/` 下
导出后的最终模型会提交。

## 目录

| 文件 | 作用 |
|---|---|
| `generate_phone_bench.py` | 生成完整场景的合成拍屏评测图（透视、摩尔纹、反光、模糊、JPEG、杂乱背景、四种选框） |
| `make_crop_dataset.py` | 生成 96×96 单图标训练/验证裁剪图，1000 类 |
| `train_phone_model.py` | 训练小型 CNN（约 0.98M 参数），导出单文件 ONNX，跑 hard2 评测 |
| `export_web_model.py` | 把 checkpoint 导出到 `app/web/vendor/models/phone-cnn/`，并生成 Transformers.js 配置 |
| `eval_real_photos.py` | 用本机 4 张实拍/半实拍照片做快速 sanity check |

## 常用命令

```bash
# 1. 生成训练裁剪图（约 24k train + 4k val）
.venv/bin/python app/eval/make_crop_dataset.py \
  --per-class 24 --val-per-class 4 --seed 42 \
  --out app/eval/data/phone_crops --clean

# 2. 训练（MPS；30 epochs 约 30 分钟）
.venv/bin/python app/eval/train_phone_model.py \
  --epochs 30 --workers 6 --out app/eval/models

# 3. 导出给网页用的单文件 ONNX + config
.venv/bin/python app/eval/export_web_model.py

# 4. 本机照片 sanity check
.venv/bin/python app/eval/eval_real_photos.py \
  --model app/eval/models/phone_model.pt

# 5. 重新生成完整场景评测集（需要先有阶段背景/杂物图）
.venv/bin/python app/eval/generate_phone_bench.py --count 24 --seed 20261023 \
  --out app/eval/data/phone_bench_hard2 --clean
```

快速冒烟训练：

```bash
.venv/bin/python app/eval/train_phone_model.py \
  --epochs 3 --limit-train 4000 --limit-val 1000 --workers 2 \
  --out /tmp/phone_model_test
```

## 模型输入 / 输出

- 输入：RGB 96×96，`pixel_values`，`(x/255 - 0.5)/0.5`
- 输出：1000 类 logits，顺序见 `app/eval/data/phone_crops/labels.json`
- 类别按 `(kind, id)` 排序，和网页 `MODEL` 的顺序不同，网页用 `labels.json` 映射，不能直接按数组下标复用
- 训练增强：随机旋转/平移/缩放/剪切、颜色抖动、随机擦除；训练裁剪图本身已经带透视、模糊、摩尔纹、反光、屏幕像素化和 JPEG

## 网页端混合方式

`app/web/app.js` 的“拍屏小模型”后端：

1. CNN 对 96×96 裁切图前向，取场景过滤后的前 64 个候选；
2. 只对这 64 个候选计算像素模板距离（避免对 1000 类全扫）；
3. `综合 = 模板分数 * 0.65 + CNN softmax * 0.35`，取前 8 展示。

这样比纯 CNN 更稳：CNN 能压过模板在 `Error` / `NO!` / 黑色剪影上的误判，模板又能
纠正 CNN 偶发的“高置信但形似”错误。场景过滤只过滤道具，饰品/卡牌始终保留。

## 当前结果（合成集，非真实准确率承诺）

hard2 是 24 张合成拍屏图、24 个类别，包含不同选框。模板和 CNN 的结果会随随机种子/
训练轮次变化；以实际运行输出为准。训练脚本会在 `app/eval/models/phone_metrics.json`
里记录 hard2 的 auto/scene × exact/loose/tight/offset 结果。

本机 4 张实拍照片（手动框选完整图标）是 sanity check，不是正式评测集；样本量太小，
不能据此推断线上准确率。真实手机照片仍然需要更多失败样本才能校准。
