#!/usr/bin/env python3
"""用 4 张本机实拍/合成照片检查拍屏小模型。

这些照片不是正式评测集，只用于确认模型在真实模糊图上没有完全崩掉。
框是手动标的“道具本体”大致范围；脚本会再按 app 的 18% 外扩裁切。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_phone_model import SmallNet, scene_masks  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# 手动框：x, y, w, h（原图像素）
REAL = [
    {"file": ".playwright-mcp/testimg/sacred.jpg", "kind": "item", "id": 182, "name": "Sacred Heart", "box": [140, 80, 340, 460], "scene": "angel"},
    {"file": ".playwright-mcp/testimg/d6.jpg", "kind": "item", "id": 105, "name": "The D6", "box": [140, 110, 340, 340], "scene": None},
    {"file": ".playwright-mcp/testimg/tick.jpg", "kind": "trinket", "id": 53, "name": "Tick", "box": [210, 210, 250, 250], "scene": None},
    {"file": ".playwright-mcp/testimg/card_fool.jpg", "kind": "card", "id": 1, "name": "0 - The Fool", "box": [150, 120, 340, 390], "scene": None},
]


def expand(box, w, h, pad):
    x, y, bw, bh = box
    px, py = bw * pad, bh * pad
    return (max(0, int(x - px)), max(0, int(y - py)), min(w, int(x + bw + px)), min(h, int(y + bh + py)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=ROOT / "app/eval/models/phone_model.pt")
    ap.add_argument("--labels", type=Path, default=ROOT / "app/eval/data/phone_crops/labels.json")
    ap.add_argument("--pad", type=float, default=0.18)
    args = ap.parse_args()

    ck = torch.load(args.model, map_location="cpu", weights_only=False)
    labels = json.load(open(args.labels, encoding="utf-8"))
    model = SmallNet(len(labels["classes"]))
    model.load_state_dict(ck["model"])
    model.eval()
    by_key = {(r["kind"], r["id"]): i for i, r in enumerate(labels["classes"])}
    masks = scene_masks(labels)

    for r in REAL:
        path = ROOT / r["file"]
        img = Image.open(path).convert("RGB")
        x0, y0, x1, y1 = expand(r["box"], img.width, img.height, args.pad)
        crop = img.crop((x0, y0, x1, y1)).resize((96, 96), Image.Resampling.BILINEAR)
        arr = np.asarray(crop).astype(np.float32) / 255.0
        arr = (arr - 0.5) / 0.5
        with torch.no_grad():
            logits = model(torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0))[0].numpy()
        masked = logits.copy()
        if r["scene"] in masks:
            keep = np.zeros(len(labels["classes"]), bool)
            keep[masks[r["scene"]]] = True
            masked = np.where(keep, masked, -1e9)
        top = np.argsort(-masked)[:5]
        want = by_key[(r["kind"], r["id"])]
        print(f"{r['name']} ({r['file']}) crop=({x0},{y0})-({x1},{y1}) pad={args.pad} scene={r['scene']}")
        for rank, i in enumerate(top, 1):
            c = labels["classes"][i]
            mark = " <--" if i == want else ""
            print(f"  {rank}. {c['kind']} {c['id']} {c['name_zh']} / {c['name']} logit={masked[i]:.2f}{mark}")
        print(f"  correct rank: {list(top).index(want)+1 if want in top else '>5'}")
        print()


if __name__ == "__main__":
    main()
