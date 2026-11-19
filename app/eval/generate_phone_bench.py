#!/usr/bin/env python3
"""生成“手机拍屏幕”合成评测集。

用法：
  .venv/bin/python app/eval/generate_phone_bench.py --count 200 --seed 7
  .venv/bin/python app/eval/generate_phone_bench.py --count 40 --seed 1 --out /tmp/phone_bench

每张图随机组合：
  - 以撒楼层贴图 + 拾取物/怪物杂项作为房间背景
  - 从道具池里选一个当前场景会出现的道具（也混入少量饰品/卡牌）
  - 道具缩放、描边、底座阴影
  - 整屏透视 + 显示器边框/桌面背景
  - 反光、摩尔纹、失焦/运动模糊、偏色、噪点、JPEG

输出：
  <out>/images/000001.jpg ...
  <out>/manifest.json

manifest 里带场景、真实 id、最终图像中的框、模糊/反光/摩尔纹/JPEG 等参数，
既可用于跑 app 的识别评测，也可用于训练小型端侧模型。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
JSON_DIR = ROOT / "json"
IMG_DIR = ROOT / "images"
DEFAULT_OUT = ROOT / "app" / "eval" / "data" / "phone_bench"

SCENES = {
    "treasure": ["Treasure Room", "Greed Treasure Room"],
    "shop": ["Shop", "Greed Shop", "Baby Shop"],
    "devil": ["Devil Room", "Greed Devil Room"],
    "angel": ["Angel Room", "Greed Angel Room"],
    "boss": ["Boss", "Greed Boss"],
    "secret": ["Secret Room", "Ultra Secret Room", "Greed Secret Room"],
    "library": ["Library", "Greed Library"],
    "planetarium": ["Planetarium"],
    "curse": ["Curse Room", "Greed Curse Room"],
}


def load_json(name):
    with open(JSON_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def norm_name(s):
    s = str(s or "").lower().replace("=", " ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def build_scene_items():
    """场景 -> 有图标、且属于该场景道具池的道具记录。"""
    items = load_json("items.json")
    by_name = {}
    for rec in items:
        by_name.setdefault(norm_name(rec.get("name")), []).append(rec)
    pool_by_name = {p.get("name"): p for p in load_json("item_pools.json")}
    result = {}
    for scene, names in SCENES.items():
        ids = set()
        for name in names:
            for it in pool_by_name.get(name, {}).get("items", []):
                for rec in by_name.get(norm_name(it.get("name")), []):
                    if rec.get("id") is not None:
                        ids.add(rec["id"])
        result[scene] = [r for r in items if r.get("id") in ids and _image_exists(r)]
    # 极端情况下回退到全道具，保证脚本还能跑
    for scene, recs in result.items():
        if not recs:
            result[scene] = [r for r in items if _image_exists(r)]
    return result


def _image_exists(rec):
    p = rec.get("image")
    return bool(p) and (ROOT / p).is_file()


def load_records():
    out = {}
    for kind, fname in (("item", "items.json"), ("trinket", "trinkets.json"), ("card", "cards.json")):
        recs = [r for r in load_json(fname) if _image_exists(r)]
        out[kind] = recs
    return out


def load_icon(rec):
    im = Image.open(ROOT / rec["image"]).convert("RGBA")
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.where(a > 8)
    if len(xs):
        im = im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return im


def load_stage_textures():
    tex = []
    for p in sorted((IMG_DIR / "stage").glob("*.png")):
        try:
            tex.append(Image.open(p).convert("RGB"))
        except Exception:
            pass
    if not tex:
        tex = [Image.new("RGB", (250, 160), (35, 30, 38))]
    return tex


def load_clutter():
    out = []
    for sub in ("pickup", "entity"):
        for p in (IMG_DIR / sub).glob("*.png"):
            try:
                im = Image.open(p).convert("RGBA")
                if im.width >= 8 and im.height >= 8:
                    out.append(im)
            except Exception:
                pass
    return out


def make_desk(w, h, rng):
    """显示器/电视外面的桌面：暗色、失焦、带一点噪点。"""
    base = np.zeros((h, w, 3), np.float32)
    base[:] = np.array([rng.uniform(8, 26), rng.uniform(7, 23), rng.uniform(8, 28)], np.float32)
    # 模糊的大色块，模拟桌面反光/杂物
    for _ in range(rng.randint(2, 5)):
        x0, y0 = rng.randrange(w), rng.randrange(h)
        rw, rh = rng.randrange(w // 6, w // 2 + 1), rng.randrange(h // 8, h // 2 + 1)
        col = np.array([rng.uniform(5, 45), rng.uniform(4, 40), rng.uniform(5, 50)], np.float32)
        cv2.rectangle(base, (x0, y0), (min(w, x0 + rw), min(h, y0 + rh)), col.tolist(), -1)
    base = cv2.GaussianBlur(base, (0, 0), max(3, min(w, h) * 0.02))
    base += np.random.default_rng(rng.randrange(1 << 30)).normal(0, 2.0, base.shape)
    return np.clip(base, 0, 255).astype(np.uint8)


def make_background(w, h, textures, rng):
    tex = rng.choice(textures)
    # 贴图是 250x160 左右的小图，放大后保留像素块，再轻微模糊
    bg = ImageOps.fit(tex, (w, h), method=Image.Resampling.NEAREST if rng.random() < 0.55 else Image.Resampling.BILINEAR)
    if rng.random() < 0.5:
        bg = bg.transpose(Image.Transpose.ROTATE_90)
    bg = ImageOps.fit(bg, (w, h), method=Image.Resampling.BILINEAR)
    arr = np.asarray(bg).astype(np.float32) * rng.uniform(0.42, 0.9)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xx - w / 2) / max(1, w / 2), (yy - h / 2) / max(1, h / 2)
    vignette = 1.0 - rng.uniform(0.12, 0.42) * (nx * nx + ny * ny) / 2.0
    arr *= vignette[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    # 随机墙/门槛/墙角
    for _ in range(rng.randint(1, 4)):
        if rng.random() < 0.5:
            x0 = rng.randrange(max(1, w // 3))
            y0 = rng.randrange(max(1, h // 3))
            x1 = min(w, x0 + rng.randrange(w // 8, w // 2))
            y1 = min(h, y0 + rng.randrange(h // 8, h // 2))
        else:
            x0 = rng.randrange(w // 2, w)
            y0 = rng.randrange(h // 2, h)
            x1 = min(w, x0 + rng.randrange(w // 8, w // 3))
            y1 = min(h, y0 + rng.randrange(h // 8, h // 3))
        col = (rng.randrange(5, 35), rng.randrange(5, 32), rng.randrange(8, 40), rng.randrange(90, 190))
        d.rectangle([x0, y0, x1, y1], fill=col)
    # 让背景稍微失焦，道具保持相对清楚
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 2.0)))
    return img.convert("RGB")


def add_pedestal(img, box, rng):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    x, y, w, h = box
    cx, by = x + w / 2, y + h * 0.92
    ew, eh = w * rng.uniform(0.85, 1.35), h * rng.uniform(0.12, 0.28)
    d.ellipse([cx - ew / 2, by - eh / 2, cx + ew / 2, by + eh / 2], fill=(8, 6, 12, rng.randrange(120, 210)))
    # 道具后面的暗色光晕，模拟 UI 高亮
    gw, gh = w * rng.uniform(1.05, 1.5), h * rng.uniform(1.05, 1.45)
    d.ellipse([cx - gw / 2, y + h / 2 - gh / 2, cx + gw / 2, y + h / 2 + gh / 2], fill=(18, 16, 24, rng.randrange(25, 80)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(2, int(min(w, h) * 0.08))))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def add_clutter(img, item_box, rng, clutter, item_min):
    if not clutter:
        return img
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y, w, h = item_box
    guard = (int(x - w * 0.15), int(y - h * 0.15), int(x + w * 1.15), int(y + h * 1.15))
    for _ in range(rng.randint(1, 5)):
        sp = rng.choice(clutter).copy()
        a = np.asarray(sp.getchannel("A"))
        ys, xs = np.where(a > 8)
        if not len(xs):
            continue
        sp = sp.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
        scale = rng.uniform(0.28, 0.95) * item_min / max(1, min(sp.size))
        nw, nh = max(1, int(sp.width * scale)), max(1, int(sp.height * scale))
        sp = sp.resize((nw, nh), Image.Resampling.NEAREST)
        if rng.random() < 0.5:
            sp = sp.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if rng.random() < 0.35:
            sp = sp.rotate(rng.uniform(-35, 35), expand=True, resample=Image.Resampling.NEAREST)
        px = rng.randrange(max(0, img.width - sp.width))
        py = rng.randrange(max(0, img.height - sp.height))
        # 避免把杂项压在真实道具上（部分重叠可以，完全盖住不行）
        if px < guard[2] and px + sp.width > guard[0] and py < guard[3] and py + sp.height > guard[1]:
            if rng.random() < 0.7:
                continue
        alpha = sp.getchannel("A").point(lambda v: int(v * rng.uniform(0.55, 1.0)))
        sp.putalpha(alpha)
        overlay.alpha_composite(sp, (px, py))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def make_icon_with_outline(rec, target_min, rng):
    icon = load_icon(rec)
    scale = target_min / max(1, min(icon.size))
    nw, nh = max(1, int(round(icon.width * scale))), max(1, int(round(icon.height * scale)))
    resample = Image.Resampling.LANCZOS if nw * nh > icon.width * icon.height else Image.Resampling.NEAREST
    icon = icon.resize((nw, nh), resample)
    if rng.random() < 0.75:
        outline = icon.getchannel("A").filter(ImageFilter.MaxFilter(3))
        pad = 2
        out = Image.new("RGBA", (nw + pad * 2, nh + pad * 2), (0, 0, 0, 0))
        black = Image.new("RGBA", (nw + pad * 2, nh + pad * 2), (0, 0, 0, 0))
        alpha = Image.new("L", (nw + pad * 2, nh + pad * 2), 0)
        alpha.paste(outline, (pad, pad))
        black.putalpha(alpha)
        out.alpha_composite(black)
        out.alpha_composite(icon, (pad, pad))
        return out, pad
    return icon, 0


def add_glare(img, rng):
    if rng.random() < 0.18:
        return img, 0.0
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    strength = rng.uniform(0.25, 1.0)
    # 一到两块大的柔光反射
    for _ in range(rng.randint(1, 2)):
        cx, cy = rng.uniform(0.05, 0.95) * w, rng.uniform(0.05, 0.95) * h
        rx, ry = rng.uniform(0.08, 0.32) * w, rng.uniform(0.08, 0.35) * h
        col = (255, rng.randrange(238, 255), rng.randrange(215, 250), rng.randrange(18, int(45 + 55 * strength)))
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col)
    # 偶尔来一条斜向高光
    if rng.random() < 0.60:
        x0 = rng.uniform(-0.2, 0.8) * w
        width = rng.uniform(0.04, 0.16) * w
        pts = [(x0, 0), (x0 + width, 0), (x0 + width + h * 0.45, h), (x0 + h * 0.45, h)]
        d.polygon(pts, fill=(255, 252, 235, rng.randrange(10, int(25 + 30 * strength))))
    overlay = overlay.filter(ImageFilter.GaussianBlur(rng.uniform(8, 36)))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), strength


def add_moire(arr, rng):
    if rng.random() < 0.50:
        return arr, 0.0
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    theta = rng.uniform(0, math.pi)
    freq = rng.uniform(0.012, 0.09)
    phase = rng.uniform(0, math.tau)
    pat = np.sin(math.tau * freq * (xx * math.cos(theta) + yy * math.sin(theta)) + phase)
    amp = rng.uniform(1.0, 8.0)
    return arr + (amp * pat)[..., None], amp


def screen_pixelate(img, rng):
    """模拟游戏在低分辨率屏幕上渲染，再被手机拍下来。"""
    if rng.random() < 0.28:
        return img
    W, H = img.size
    gw = rng.choice([320, 384, 426, 480, 640, 720, 854, 960])
    if gw >= W * 0.92:
        return img
    gh = max(1, int(H * gw / W))
    small = img.resize((gw, gh), Image.Resampling.BILINEAR)
    if rng.random() < 0.55:
        small = small.filter(ImageFilter.GaussianBlur(rng.uniform(0.25, 0.85)))
    method = Image.Resampling.NEAREST if rng.random() < 0.62 else Image.Resampling.BILINEAR
    return small.resize((W, H), method)


def add_screen_grid(arr, rng):
    """屏幕像素栅格/子像素感，轻量模拟拍屏。"""
    if rng.random() < 0.35:
        return arr
    h, w = arr.shape[:2]
    step = rng.randint(3, 8)
    dark = rng.uniform(0.86, 0.96)
    arr[::step, :, :] *= dark
    arr[:, ::step, :] *= dark
    return arr


def camera_resample(arr, rng):
    """模拟手机摄像头采样/平台压缩：先降到较低分辨率，再插值回大图。"""
    if rng.random() < 0.35:
        return arr
    h, w = arr.shape[:2]
    small_max = rng.randint(420, 900)
    sc = small_max / max(h, w)
    if sc >= 0.98:
        return arr
    small = cv2.resize(arr, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def add_camera_blur(arr, rng):
    sigma = rng.uniform(0.25, 1.35)
    if rng.random() < 0.35:
        sigma = rng.uniform(1.2, 2.8)
    if sigma > 0.05:
        arr = cv2.GaussianBlur(arr, (0, 0), sigmaX=sigma, sigmaY=sigma)
    # 运动模糊
    if rng.random() < 0.22:
        k = rng.choice([3, 5, 7, 9])
        ang = rng.uniform(0, math.pi)
        kernel = np.zeros((k, k), np.float32)
        c = k // 2
        dx, dy = math.cos(ang), math.sin(ang)
        for t in np.linspace(-c, c, k * 2):
            x, y = int(round(c + t * dx)), int(round(c + t * dy))
            if 0 <= x < k and 0 <= y < k:
                kernel[y, x] = 1
        if kernel.sum() > 0:
            kernel /= kernel.sum()
            arr = cv2.filter2D(arr, -1, kernel)
    return arr, sigma


def add_photo_color(arr, rng):
    # 白平衡 / 色温
    arr = arr * np.array([rng.uniform(0.90, 1.10), rng.uniform(0.92, 1.06), rng.uniform(0.88, 1.12)], np.float32)
    # 手机拍屏常见的降饱和/发灰
    if rng.random() < 0.65:
        gray = arr.mean(axis=2, keepdims=True)
        arr = gray + (arr - gray) * rng.uniform(0.62, 0.98)
    # 亮度 / 对比度 / gamma / 轻微雾化
    contrast = rng.uniform(0.78, 1.16)
    bright = rng.uniform(-18, 22)
    arr = (arr - 128.0) * contrast + 128.0 + bright
    if rng.random() < 0.55:
        arr = arr * rng.uniform(0.70, 0.96) + rng.uniform(6, 34)
    gamma = rng.uniform(0.80, 1.24)
    arr = 255.0 * np.power(np.clip(arr, 0, 255) / 255.0, gamma)
    # 噪声
    noise = rng.uniform(0.0, 5.5)
    if noise > 0.1:
        arr = arr + np.random.default_rng(rng.randrange(1 << 30)).normal(0, noise, arr.shape)
    return np.clip(arr, 0, 255).astype(np.uint8)


def transform_box(box, Hm, pad, w, h):
    x, y, bw, bh = box
    pts = np.float32([[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]]).reshape(-1, 1, 2)
    t = cv2.perspectiveTransform(pts, Hm).reshape(-1, 2)
    x0, y0 = t[:, 0].min(), t[:, 1].min()
    x1, y1 = t[:, 0].max(), t[:, 1].max()
    bw, bh = x1 - x0, y1 - y0
    px, py = bw * pad, bh * pad
    x0, y0, x1, y1 = x0 - px, y0 - py, x1 + px, y1 + py
    x0, y0 = max(0, int(round(x0))), max(0, int(round(y0)))
    x1, y1 = min(w, int(round(x1))), min(h, int(round(y1)))
    return [x0, y0, max(1, x1 - x0), max(1, y1 - y0)]


def clamp_box(box, w, h):
    x, y, bw, bh = [int(round(v)) for v in box]
    x0, y0 = max(0, min(w - 1, x)), max(0, min(h - 1, y))
    x1, y1 = max(x0 + 1, min(w, x + bw)), max(y0 + 1, min(h, y + bh))
    return [x0, y0, x1 - x0, y1 - y0]


def perturb_box(box, mode, rng, w, h):
    """模拟手动框选误差：紧框、松框、偏一点。"""
    x, y, bw, bh = box
    if mode == "tight":
        k = rng.uniform(0.04, 0.18)
        x += bw * k / 2
        y += bh * k / 2
        bw *= 1 - k
        bh *= 1 - k
    elif mode == "loose":
        k = rng.uniform(0.12, 0.45)
        x -= bw * k / 2
        y -= bh * k / 2
        bw *= 1 + k
        bh *= 1 + k
    elif mode == "offset":
        x += bw * rng.uniform(-0.12, 0.12)
        y += bh * rng.uniform(-0.12, 0.12)
    return clamp_box([x, y, bw, bh], w, h)


def generate_one(rec, kind, scene, textures, clutter, rng):
    # 画布/道具尺寸
    W = rng.randrange(720, 1281)
    H = int(W * rng.uniform(0.72, 1.18))
    H = max(560, min(1500, H))
    r = rng.random()
    if r < 0.32:
        item_min = rng.uniform(35, 70)
    elif r < 0.65:
        item_min = rng.uniform(70, 130)
    elif r < 0.90:
        item_min = rng.uniform(130, 220)
    else:
        item_min = rng.uniform(220, 320)
    icon, pad = make_icon_with_outline(rec, item_min, rng)
    iw, ih = icon.width - pad * 2, icon.height - pad * 2
    margin_x, margin_y = int(W * 0.08), int(H * 0.08)
    x = rng.randrange(margin_x, max(margin_x + 1, W - iw - margin_x))
    y = rng.randrange(margin_y, max(margin_y + 1, H - ih - margin_y))
    box = [x, y, iw, ih]

    screen = make_background(W, H, textures, rng)
    screen = add_pedestal(screen, box, rng)
    screen = add_clutter(screen, box, rng, clutter, item_min)
    # 粘贴道具（描边向外扩 pad）
    screen = screen.convert("RGBA")
    screen.alpha_composite(icon, (x - pad, y - pad))
    screen = screen.convert("RGB")
    screen = screen_pixelate(screen, rng)
    screen, glare = add_glare(screen, rng)

    # 整屏透视 + 显示器边框/桌面
    cw, ch = int(W * rng.uniform(1.06, 1.16)), int(H * rng.uniform(1.06, 1.16))
    jitter = min(cw, ch) * rng.uniform(0.018, 0.070)
    left, right = cw * rng.uniform(0.025, 0.11), cw * (1 - rng.uniform(0.025, 0.11))
    top, bottom = ch * rng.uniform(0.025, 0.11), ch * (1 - rng.uniform(0.025, 0.11))
    dst = np.float32([
        [left + rng.uniform(-jitter, jitter), top + rng.uniform(-jitter, jitter)],
        [right + rng.uniform(-jitter, jitter), top + rng.uniform(-jitter, jitter)],
        [right + rng.uniform(-jitter, jitter), bottom + rng.uniform(-jitter, jitter)],
        [left + rng.uniform(-jitter, jitter), bottom + rng.uniform(-jitter, jitter)],
    ])
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    Hm = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(np.asarray(screen), Hm, (cw, ch), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((H, W), 255, np.uint8), Hm, (cw, ch), flags=cv2.INTER_NEAREST, borderValue=0)
    desk = make_desk(cw, ch, rng)
    desk[mask > 0] = warped[mask > 0]
    # 显示器/电视边框
    cv2.polylines(desk, [dst.astype(np.int32)], True, (6, 6, 8), thickness=max(2, int(min(cw, ch) * 0.008)))
    box_pad = rng.uniform(0.03, 0.12)
    box2 = transform_box(box, Hm, box_pad, cw, ch)

    arr = desk.astype(np.float32)
    arr, moire = add_moire(arr, rng)
    arr = add_screen_grid(arr, rng)
    # 轻微色散
    if rng.random() < 0.30:
        shift = rng.randint(1, 3)
        arr[:, :, 0] = np.roll(arr[:, :, 0], shift, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -shift, axis=1)
    arr, sigma = add_camera_blur(arr, rng)
    arr = camera_resample(arr, rng)
    arr = add_photo_color(arr, rng)

    # 轻微旋转：整张照片倾斜，道具框也要跟着转
    angle = 0.0
    if rng.random() < 0.45:
        angle = rng.uniform(-3.5, 3.5)
        M = cv2.getRotationMatrix2D((cw / 2, ch / 2), angle, 1.0)
        arr = cv2.warpAffine(arr, M, (cw, ch), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        x, y, bw, bh = box2
        pts = np.float32([[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]])
        t = cv2.transform(pts.reshape(-1, 1, 2), M).reshape(-1, 2)
        box2 = clamp_box([t[:, 0].min(), t[:, 1].min(), t[:, 0].max() - t[:, 0].min(), t[:, 1].max() - t[:, 1].min()], cw, ch)

    # 随机缩放一点，模拟不同手机分辨率
    if rng.random() < 0.5:
        target = rng.randrange(760, 1501)
        sc = target / max(cw, ch)
        if abs(sc - 1) > 0.03:
            nw, nh = max(1, int(cw * sc)), max(1, int(ch * sc))
            arr = cv2.resize(arr, (nw, nh), interpolation=cv2.INTER_AREA)
            box2 = [int(round(v * sc)) for v in box2]
            cw, ch = nw, nh

    quality = rng.randrange(14, 39) if rng.random() < 0.28 else rng.randrange(32, 91)
    img = Image.fromarray(arr).convert("RGB")
    boxes = {
        "exact": box2,
        "tight": perturb_box(box2, "tight", rng, cw, ch),
        "loose": perturb_box(box2, "loose", rng, cw, ch),
        "offset": perturb_box(box2, "offset", rng, cw, ch),
    }
    min_px = min(box2[2], box2[3])
    return img, box2, {
        "boxes": boxes,
        "item_px": round(min_px, 1),
        "blur_sigma": round(float(sigma), 3),
        "glare": round(float(glare), 3),
        "moire": round(float(moire), 3),
        "jpeg": int(quality),
        "perspective": round(float(jitter / max(1, min(cw, ch))), 4),
        "box_pad": round(float(box_pad), 4),
        "angle": round(float(angle), 3),
        "width": int(cw),
        "height": int(ch),
        "difficulty": "hard" if (min_px < 80 or sigma > 1.6 or glare > 0.7) else ("medium" if (min_px < 150 or sigma > 0.9 or glare > 0.35) else "easy"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--clean", action="store_true", help="生成前清空输出目录")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    np.random.seed(args.seed)
    scene_items = build_scene_items()
    records = load_records()
    textures = load_stage_textures()
    clutter = load_clutter()
    scenes = list(SCENES)
    if args.clean and args.out.exists():
        shutil.rmtree(args.out)
    (args.out / "images").mkdir(parents=True, exist_ok=True)

    samples = []
    used = set()
    for i in range(args.count):
        scene = scenes[i % len(scenes)] if i < len(scenes) * 4 else rng.choice(scenes)
        kind_roll = rng.random()
        if kind_roll < 0.80 or not records["trinket"] or not records["card"]:
            kind = "item"
            pool = [r for r in scene_items[scene] if r.get("id") is not None]
            rec = rng.choice(pool)
        elif kind_roll < 0.90:
            kind = "trinket"
            rec = rng.choice(records["trinket"])
        else:
            kind = "card"
            rec = rng.choice(records["card"])
        key = (kind, rec.get("id"), scene)
        # 尽量不重复；小场景池允许重复
        tries = 0
        while key in used and tries < 20:
            rec = rng.choice(scene_items[scene] if kind == "item" else records[kind])
            key = (kind, rec.get("id"), scene)
            tries += 1
        used.add(key)
        img, box, meta = generate_one(rec, kind, scene, textures, clutter, rng)
        fname = f"{i + 1:06d}.jpg"
        path = args.out / "images" / fname
        # 用 PIL 的 quality 参数保存；文件大小接近手机照片
        img.save(path, "JPEG", quality=meta["jpeg"], optimize=True, subsampling=rng.choice([0, 1, 2]))
        samples.append({
            "file": f"images/{fname}",
            "scene": scene,
            "kind": kind,
            "id": rec.get("id"),
            "name": rec.get("name"),
            "name_zh": rec.get("name_zh"),
            "box": box,
            **meta,
        })
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{args.count}")

    manifest = {
        "version": 1,
        "generator": "app/eval/generate_phone_bench.py",
        "seed": args.seed,
        "count": len(samples),
        "scenes": list(SCENES),
        "samples": samples,
    }
    with open(args.out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"完成：{len(samples)} 张 -> {args.out}")


if __name__ == "__main__":
    main()
