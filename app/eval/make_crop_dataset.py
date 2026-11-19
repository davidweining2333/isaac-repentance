#!/usr/bin/env python3
"""生成拍屏小模型的训练/验证裁剪集。

和 generate_phone_bench.py 的区别：这里直接输出“用户框选后”的 96×96 裁剪，
包含背景、杂项、失焦、反光、屏幕像素化、JPEG，用来训练一个小的端侧分类器。
训练集/验证集分开生成，类顺序一致。

用法：
  .venv/bin/python app/eval/make_crop_dataset.py --per-class 24 --val-per-class 4
  .venv/bin/python app/eval/make_crop_dataset.py --per-class 4 --val-per-class 1 --out /tmp/crops
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_phone_bench as g  # noqa: E402

ROOT = g.ROOT
DEFAULT_OUT = ROOT / "app" / "eval" / "data" / "phone_crops"
S = 96


def build_classes():
    out = []
    for kind, fname in (("item", "items.json"), ("trinket", "trinkets.json"), ("card", "cards.json")):
        for rec in g.load_json(fname):
            if g._image_exists(rec) and rec.get("id") is not None:
                out.append({"kind": kind, "id": rec["id"], "name": rec.get("name"), "name_zh": rec.get("name_zh"), "image": rec["image"]})
    out.sort(key=lambda r: (r["kind"], r["id"]))
    return out


def solid_bg(rng):
    base = np.zeros((S, S, 3), np.float32)
    base[:] = [rng.uniform(5, 40), rng.uniform(5, 38), rng.uniform(6, 45)]
    base += np.random.default_rng(rng.randrange(1 << 30)).normal(0, rng.uniform(1, 5), base.shape)
    return np.clip(base, 0, 255).astype(np.uint8)


def room_bg(textures, rng):
    tex = rng.choice(textures)
    # 从贴图里随机取一块，放大到 96
    w, h = tex.size
    side = min(w, h)
    x = rng.randrange(0, max(1, w - side + 1))
    y = rng.randrange(0, max(1, h - side + 1))
    patch = tex.crop((x, y, x + side, y + side)).resize((S, S), Image.Resampling.NEAREST if rng.random() < 0.5 else Image.Resampling.BILINEAR)
    arr = np.asarray(patch).astype(np.float32) * rng.uniform(0.35, 0.95)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    nx, ny = (xx - S / 2) / (S / 2), (yy - S / 2) / (S / 2)
    arr *= (1 - rng.uniform(0.05, 0.35) * (nx * nx + ny * ny) / 2)[..., None]
    if rng.random() < 0.55:
        arr = cv2.GaussianBlur(arr, (0, 0), rng.uniform(0.4, 1.4))
    return np.clip(arr, 0, 255).astype(np.uint8)


def add_clutter_patch(img, target_box, clutter, rng):
    if not clutter or rng.random() < 0.25:
        return img
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y, w, h = target_box
    for _ in range(rng.randint(1, 2)):
        sp = rng.choice(clutter).copy()
        a = np.asarray(sp.getchannel("A"))
        ys, xs = np.where(a > 8)
        if not len(xs):
            continue
        sp = sp.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
        scale = rng.uniform(0.25, 0.85) * min(w, h) / max(1, min(sp.size))
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.Resampling.NEAREST)
        if rng.random() < 0.5:
            sp = sp.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if rng.random() < 0.3:
            sp = sp.rotate(rng.uniform(-40, 40), expand=True, resample=Image.Resampling.NEAREST)
        px = rng.randrange(max(1, S - sp.width))
        py = rng.randrange(max(1, S - sp.height))
        # 不要完全盖住目标；允许边缘重叠
        if px < x + w and px + sp.width > x and py < y + h and py + sp.height > y:
            if rng.random() < 0.65:
                continue
        alpha = sp.getchannel("A").point(lambda v: int(v * rng.uniform(0.45, 0.95)))
        sp.putalpha(alpha)
        overlay.alpha_composite(sp, (px, py))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def add_shadow(img, box, rng):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    x, y, w, h = box
    cx, by = x + w / 2, y + h * 0.92
    ew, eh = w * rng.uniform(0.8, 1.3), h * rng.uniform(0.10, 0.28)
    d.ellipse([cx - ew / 2, by - eh / 2, cx + ew / 2, by + eh / 2], fill=(6, 4, 9, rng.randrange(100, 200)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(1, int(min(w, h) * 0.12))))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def pixelate_crop(img, rng):
    if rng.random() < 0.25:
        return img
    target = rng.choice([28, 32, 40, 48, 56, 64, 80])
    if target >= S * 0.95:
        return img
    small = img.resize((target, target), Image.Resampling.BILINEAR)
    method = Image.Resampling.NEAREST if rng.random() < 0.65 else Image.Resampling.BILINEAR
    return small.resize((S, S), method)


def crop_glare(img, rng):
    if rng.random() < 0.35:
        return img, 0.0
    arr = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    strength = rng.uniform(0.2, 1.0)
    for _ in range(rng.randint(1, 2)):
        cx, cy = rng.uniform(0.05, 0.95) * S, rng.uniform(0.05, 0.95) * S
        sx, sy = rng.uniform(0.08, 0.32) * S, rng.uniform(0.08, 0.35) * S
        blob = np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) * 2.0)
        arr += blob[..., None] * np.array([255, 248, 228], np.float32) * (0.12 + 0.20 * strength)
    # 斜向高光
    if rng.random() < 0.5:
        overlay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay, "RGBA")
        x0 = rng.uniform(-0.4, 0.6) * S
        width = rng.uniform(0.08, 0.22) * S
        d.polygon([(x0, 0), (x0 + width, 0), (x0 + width + S * 0.5, S), (x0 + S * 0.5, S)], fill=(255, 252, 235, rng.randrange(10, 70)))
        overlay = overlay.filter(ImageFilter.GaussianBlur(rng.uniform(2, 10)))
        arr = np.asarray(Image.alpha_composite(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA"), overlay).convert("RGB")).astype(np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), strength


def make_crop(rec, textures, clutter, rng):
    if rng.random() < 0.18:
        bg = solid_bg(rng)
    else:
        bg = room_bg(textures, rng)
    img = Image.fromarray(bg).convert("RGB")

    # 目标尺寸：留出 18% 外扩后，道具在 96 里通常占 30–80px
    hard = rng.random() < 0.35
    if hard:
        target_min = rng.uniform(20, 48)
    elif rng.random() < 0.6:
        target_min = rng.uniform(44, 70)
    else:
        target_min = rng.uniform(66, 86)
    icon = g.load_icon(rec)
    scale = target_min / max(1, min(icon.size))
    nw, nh = max(1, int(icon.width * scale)), max(1, int(icon.height * scale))
    icon = icon.resize((nw, nh), Image.Resampling.LANCZOS if nw * nh > icon.width * icon.height else Image.Resampling.NEAREST)
    # 屏幕像素化：先把图标降到游戏像素级，再放大
    if rng.random() < 0.35:
        small = max(8, int(min(icon.size) * rng.uniform(0.35, 0.8)))
        icon = icon.resize((small, max(1, int(small * icon.height / icon.width))), Image.Resampling.BILINEAR)
        icon = icon.resize((nw, nh), Image.Resampling.NEAREST if rng.random() < 0.7 else Image.Resampling.BILINEAR)
    # 深色描边
    if rng.random() < 0.7:
        pad = 1 if min(nw, nh) < 50 else 2
        outline = icon.getchannel("A").filter(ImageFilter.MaxFilter(3))
        out = Image.new("RGBA", (icon.width + pad * 2, icon.height + pad * 2), (0, 0, 0, 0))
        black = Image.new("RGBA", out.size, (0, 0, 0, 0))
        alpha = Image.new("L", out.size, 0)
        alpha.paste(outline, (pad, pad))
        black.putalpha(alpha)
        out.alpha_composite(black)
        out.alpha_composite(icon, (pad, pad))
        icon, pad = out, pad
    else:
        pad = 0

    iw, ih = icon.width - pad * 2, icon.height - pad * 2
    # 12% 概率故意切到一部分，模拟紧框
    cut = rng.random() < 0.12
    if cut:
        overflow_x = rng.uniform(0.05, 0.25) * iw
        overflow_y = rng.uniform(0.05, 0.25) * ih
    else:
        overflow_x = overflow_y = 0
    x0 = (S - iw) / 2
    y0 = (S - ih) / 2
    x = int(round(x0 + rng.uniform(-0.22, 0.22) * S))
    y = int(round(y0 + rng.uniform(-0.22, 0.22) * S))
    x = max(-int(overflow_x), min(S - iw + int(overflow_x), x))
    y = max(-int(overflow_y), min(S - ih + int(overflow_y), y))
    box = [x, y, iw, ih]

    img = add_shadow(img, box, rng)
    img = add_clutter_patch(img, box, clutter, rng)
    img = img.convert("RGBA")
    img.alpha_composite(icon, (x - pad, y - pad))
    img = img.convert("RGB")
    img = pixelate_crop(img, rng)
    img, glare = crop_glare(img, rng)

    arr = np.asarray(img).astype(np.float32)
    if rng.random() < 0.45:
        # 屏幕栅格 / 摩尔纹
        step = rng.randint(2, 5)
        arr[::step, :, :] *= rng.uniform(0.86, 0.97)
        arr[:, ::step, :] *= rng.uniform(0.86, 0.97)
    if rng.random() < 0.45:
        theta = rng.uniform(0, math.pi)
        freq = rng.uniform(0.02, 0.12)
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        pat = np.sin(math.tau * freq * (xx * math.cos(theta) + yy * math.sin(theta)) + rng.uniform(0, math.tau))
        arr += (rng.uniform(0.8, 5.0) * pat)[..., None]
    sigma = rng.uniform(0.15, 1.15)
    if rng.random() < 0.30:
        sigma = rng.uniform(1.1, 2.6)
    if sigma > 0.05:
        arr = cv2.GaussianBlur(arr, (0, 0), sigmaX=sigma, sigmaY=sigma)
    if rng.random() < 0.16:
        k = rng.choice([3, 5, 7])
        ang = rng.uniform(0, math.pi)
        kernel = np.zeros((k, k), np.float32)
        c = k // 2
        for t in np.linspace(-c, c, k * 2):
            xx, yy = int(round(c + t * math.cos(ang))), int(round(c + t * math.sin(ang)))
            if 0 <= xx < k and 0 <= yy < k:
                kernel[yy, xx] = 1
        if kernel.sum():
            kernel /= kernel.sum()
            arr = cv2.filter2D(arr, -1, kernel)
    arr = g.add_photo_color(arr, rng)
    # 轻微的本地对比度/色偏
    if rng.random() < 0.35:
        arr = arr * rng.uniform(0.8, 1.1) + rng.uniform(-12, 12)
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    quality = rng.randrange(55, 96)
    img = Image.fromarray(arr).convert("RGB")
    return img, {
        "target_px": round(float(min(nw, nh)), 1),
        "crop_px": S,
        "blur_sigma": round(float(sigma), 3),
        "glare": round(float(glare), 3),
        "jpeg": int(quality),
        "cut": bool(cut),
        "hard": bool(hard),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=24)
    ap.add_argument("--val-per-class", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()

    classes = build_classes()
    textures = g.load_stage_textures()
    clutter = g.load_clutter()
    if args.clean and args.out.exists():
        shutil.rmtree(args.out)
    for split in ("train", "val"):
        (args.out / split).mkdir(parents=True, exist_ok=True)

    labels = {"size": S, "classes": classes}
    with open(args.out / "labels.json", "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    for split, per_class, seed in (("train", args.per_class, args.seed), ("val", args.val_per_class, args.seed + 1000)):
        rng = random.Random(seed)
        np.random.seed(seed)
        manifest = []
        for ci, rec in enumerate(classes):
            for j in range(per_class):
                img, meta = make_crop(rec, textures, clutter, rng)
                fname = f"{ci:04d}_{j:03d}.jpg"
                img.save(args.out / split / fname, "JPEG", quality=meta["jpeg"], optimize=True, subsampling=rng.choice([0, 1, 2]))
                manifest.append({"file": f"{split}/{fname}", "label": ci, "meta": meta})
            if (ci + 1) % 100 == 0:
                print(f"  {split}: {ci + 1}/{len(classes)}")
        with open(args.out / f"manifest_{split}.json", "w", encoding="utf-8") as f:
            json.dump({"split": split, "classes": len(classes), "samples": manifest}, f, ensure_ascii=False, indent=2)
        print(f"{split}: {len(manifest)} 张")
    print(f"完成：{args.out}")


if __name__ == "__main__":
    main()
