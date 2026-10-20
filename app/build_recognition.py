#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为「无模型识别」生成图标指纹。

方案：24×24 彩色模板 + alpha 掩码（传统 CV，无任何 AI 模型）
  1. 图标裁到精灵本体（alpha 包围盒）
  2. 缩放到 24×24
  3. 只在 alpha>0.45 的像素上做整体 z-score
  4. 掩码向内腐蚀 1px，去掉最外圈受背景/描边污染的像素
  5. z-score 量化为 int8，掩码按 S×S 位打包（24×24=72 字节），均以 base64 存储

前端识别时：用户框选图标 → 从原图高分辨率裁切 → 多圈裁切 × 5 旋转 × 平移候选 →
对每个图标只比对掩码内像素，取最小归一化相关距离。
实测（照片级：旋转/纹理/阴影/JPEG）：精确框选 Top1 稳定；
选区偏大/偏移时用多圈裁切兜底。

输出 web/recognition.js:
  window.RECOG_META = {S:24, scale:40, entries:...}
  window.RECOG = [{kind,id,name,name_zh,image,image_url,v,m}, ...]
  v = base64(int8 z-score, 长度 = 3 × 掩码像素数)
  m = base64(72 字节 bitmask, bit i = 第 i 个像素是否参与比对)
"""
import json, os, base64
import numpy as np
from PIL import Image

S = 24
SCALE = 40.0
ALPHA_THR = 0.45
MIN_PIXELS = 32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATASET = os.path.join(ROOT, "json")
OUT = os.path.join(HERE, "web")


def erode(m, times=1):
    """腐蚀掩码：去掉最外圈像素，避免背景/描边/抗锯齿污染比对。"""
    for _ in range(times):
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        if e.sum() < MIN_PIXELS:
            break
        m = e
    return m


def encode_icon(path):
    im = Image.open(path).convert("RGBA")
    bb = im.split()[3].getbbox()
    if bb:
        im = im.crop(bb)
    a = np.asarray(im.resize((S, S), Image.BILINEAR), dtype=np.float32) / 255.0
    m = a[..., 3] > ALPHA_THR
    if m.sum() < MIN_PIXELS:
        m = np.ones((S, S), bool)
    m = erode(m, 1)
    cm = np.repeat(m.reshape(-1), 3)
    v = a[..., :3].reshape(-1)[cm]
    v = (v - v.mean()) / (v.std() or 1.0)
    q = np.clip(np.round(v * SCALE), -127, 127).astype(np.int8)
    mask_bytes = np.packbits(m.reshape(-1))  # MSB first, (S*S+7)//8 bytes
    return (base64.b64encode(q.tobytes()).decode("ascii"),
            base64.b64encode(mask_bytes.tobytes()).decode("ascii"))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


entries = []
for fname, kind in (("items.json", "item"), ("trinkets.json", "trinket"), ("cards.json", "card")):
    p = os.path.join(DATASET, fname)
    if not os.path.exists(p):
        continue
    for rec in load(p):
        rel = rec.get("image", "")
        if not rel:
            continue
        ip = os.path.join(ROOT, rel)
        if not os.path.exists(ip):
            continue
        try:
            v, m = encode_icon(ip)
        except Exception:
            continue
        entries.append({
            "kind": kind, "id": rec.get("id"),
            "name": rec.get("name", ""), "name_zh": rec.get("name_zh", ""),
            "image": rel, "image_url": rec.get("image_url", ""),
            "v": v, "m": m,
        })

meta = {"S": S, "scale": SCALE, "alpha": ALPHA_THR}
js = ("window.RECOG_META = " + json.dumps(meta, separators=(",", ":")) + ";\n"
      "window.RECOG = " + json.dumps(entries, ensure_ascii=False, separators=(",", ":")) + ";\n")
open(os.path.join(OUT, "recognition.js"), "w", encoding="utf-8").write(js)
print(f"识别模板: {len(entries)} 条（item+trinket+card）")
print(f"web/recognition.js {len(js)/1024/1024:.2f}MB")
