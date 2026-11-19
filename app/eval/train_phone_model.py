#!/usr/bin/env python3
"""训练 1000 类拍屏小模型，并导出 ONNX。

数据由 make_crop_dataset.py 生成：
  app/eval/data/phone_crops/{train,val}/*.jpg
  app/eval/data/phone_crops/labels.json

用法：
  .venv/bin/python app/eval/train_phone_model.py --epochs 30
  .venv/bin/python app/eval/train_phone_model.py --epochs 2 --limit-train 4000 --limit-val 1000

输出：
  app/eval/models/phone_model.pt
  app/eval/models/phone_model.onnx
  app/eval/models/phone_metrics.json

模型很小（约 0.9M 参数，float32 ONNX 约 3.5MB），输入 96×96 RGB，
输出 1000 类 logits。场景过滤在推理时对 logits 做 mask 即可。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "app" / "eval" / "data" / "phone_crops"
MODELS = ROOT / "app" / "eval" / "models"

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


class CropDataset(Dataset):
    def __init__(self, root: Path, split: str, train: bool, limit: int = 0):
        self.root = root
        self.split = split
        with open(root / f"manifest_{split}.json", encoding="utf-8") as f:
            self.items = json.load(f)["samples"]
        if limit:
            random.Random(123).shuffle(self.items)
            self.items = self.items[:limit]
        if train:
            self.tf = transforms.Compose([
                transforms.RandomAffine(degrees=10, translate=(0.06, 0.06), scale=(0.88, 1.12), shear=4,
                                        interpolation=transforms.InterpolationMode.BILINEAR, fill=0),
                transforms.ColorJitter(brightness=0.22, contrast=0.22, saturation=0.22, hue=0.035),
                transforms.ToTensor(),
                transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
                transforms.RandomErasing(p=0.14, scale=(0.015, 0.07), ratio=(0.3, 3.3), value=0),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
            ])

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        rec = self.items[i]
        img = Image.open(self.root / rec["file"]).convert("RGB")
        return self.tf(img), rec["label"]


class SmallNet(nn.Module):
    def __init__(self, n_classes: int):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1, bias=False), nn.BatchNorm2d(32), nn.SiLU(inplace=True),
            nn.Conv2d(32, 48, 3, padding=1, bias=False), nn.BatchNorm2d(48), nn.SiLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(48, 64, 3, padding=1, bias=False), nn.BatchNorm2d(64), nn.SiLU(inplace=True),
            nn.Conv2d(64, 96, 3, padding=1, bias=False), nn.BatchNorm2d(96), nn.SiLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(96, 128, 3, padding=1, bias=False), nn.BatchNorm2d(128), nn.SiLU(inplace=True),
            nn.Conv2d(128, 160, 3, padding=1, bias=False), nn.BatchNorm2d(160), nn.SiLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(160, 192, 3, padding=1, bias=False), nn.BatchNorm2d(192), nn.SiLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.15),
            nn.Linear(192, 256),
            nn.BatchNorm1d(256),
            nn.SiLU(inplace=True),
            nn.Dropout(0.10),
            nn.Linear(256, n_classes),
        )
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        return self.head(self.features(x))


def accuracy(logits, y, k=5):
    top = logits.topk(min(k, logits.shape[1]), dim=1).indices
    hit = top.eq(y[:, None]).any(dim=1)
    return int(hit.sum())


@torch.no_grad()
def evaluate(model, loader, device, k=5):
    model.eval()
    correct1 = correctk = n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        correct1 += int(logits.argmax(1).eq(y).sum())
        correctk += accuracy(logits, y, k)
        n += y.numel()
    return correct1 / max(1, n), correctk / max(1, n)


def normalize_name(s):
    s = str(s or "").lower().replace("=", " ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def scene_masks(labels):
    """场景名 -> 该场景允许的类别下标（饰品/卡牌始终允许）。"""
    with open(ROOT / "json" / "item_pools.json", encoding="utf-8") as f:
        pools = {p.get("name"): p for p in json.load(f)}
    by_name = {}
    for ci, rec in enumerate(labels["classes"]):
        if rec["kind"] == "item":
            by_name.setdefault(normalize_name(rec.get("name")), []).append(ci)
    out = {}
    for scene, pool_names in SCENES.items():
        ids = set()
        for pn in pool_names:
            for it in pools.get(pn, {}).get("items", []):
                ids.update(by_name.get(normalize_name(it.get("name")), []))
        keep = [ci for ci, rec in enumerate(labels["classes"]) if rec["kind"] in ("trinket", "card")]
        out[scene] = sorted(set(keep) | ids)
    return out


def expand_box(box, w, h, pad=0.18):
    x, y, bw, bh = box
    px, py = bw * pad, bh * pad
    x0, y0 = max(0, int(round(x - px))), max(0, int(round(y - py)))
    x1, y1 = min(w, int(round(x + bw + px))), min(h, int(round(y + bh + py)))
    return (x0, y0, max(1, x1 - x0), max(1, y1 - y0))


@torch.no_grad()
def eval_manifest(model, labels, manifest_path, data_dir, device, box_mode="exact", scene=True):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    by_key = {(r["kind"], r["id"]): i for i, r in enumerate(labels["classes"])}
    masks = scene_masks(labels) if scene else None
    correct1 = correct5 = n = 0
    rows = []
    model.eval()
    for s in manifest["samples"]:
        img = Image.open(data_dir / s["file"]).convert("RGB")
        box = s.get("boxes", {}).get(box_mode, s.get("box"))
        if not box:
            continue
        x, y, w, h = expand_box(box, img.width, img.height, 0.18)
        crop = img.crop((x, y, x + w, y + h)).resize((96, 96), Image.Resampling.BILINEAR)
        arr = np.asarray(crop).astype(np.float32) / 255.0
        arr = (arr - 0.5) / 0.5
        xb = torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0).to(device)
        logits = model(xb).cpu().numpy()[0]
        if masks is not None and s.get("scene") in masks:
            keep = np.zeros(len(labels["classes"]), dtype=bool)
            keep[masks[s["scene"]]] = True
            logits = np.where(keep, logits, -1e9)
        top = np.argsort(-logits)[:5]
        want = by_key.get((s["kind"], s["id"]))
        hit1 = bool(want is not None and top[0] == want)
        hit5 = bool(want is not None and want in top)
        correct1 += hit1
        correct5 += hit5
        n += 1
        rows.append({"file": s["file"], "scene": s.get("scene"), "kind": s["kind"], "id": s["id"],
                     "name": s.get("name"), "hit1": hit1, "hit5": hit5,
                     "top": [{"kind": labels["classes"][i]["kind"], "id": labels["classes"][i]["id"],
                              "name": labels["classes"][i]["name"]} for i in top]})
    return {"n": n, "top1": correct1 / max(1, n), "top5": correct5 / max(1, n), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=MODELS)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--limit-train", type=int, default=0)
    ap.add_argument("--limit-val", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.data / "labels.json", encoding="utf-8") as f:
        labels = json.load(f)
    n_classes = len(labels["classes"])
    print(f"classes={n_classes} train={args.limit_train or 'all'} val={args.limit_val or 'all'}")

    train_ds = CropDataset(args.data, "train", True, args.limit_train)
    val_ds = CropDataset(args.data, "val", False, args.limit_val)
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=args.workers,
                              pin_memory=False, drop_last=True, persistent_workers=args.workers > 0)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers,
                            pin_memory=False, persistent_workers=args.workers > 0)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print("device", device)
    model = SmallNet(n_classes).to(device)
    print("params", sum(p.numel() for p in model.parameters()) / 1e6, "M")
    criterion = nn.CrossEntropyLoss(label_smoothing=0.10)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    best = -1.0
    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        total = seen = correct = 0
        loss_sum = 0.0
        for bi, (x, y) in enumerate(train_loader):
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            opt.step()
            loss_sum += float(loss.item()) * y.numel()
            correct += int(logits.argmax(1).eq(y).sum())
            total += y.numel()
            seen += y.numel()
            if (bi + 1) % 50 == 0:
                print(f"  e{epoch:02d} {bi+1}/{len(train_loader)} loss={loss_sum/seen:.3f} acc={correct/seen:.3f} {(time.time()-t0):.0f}s", flush=True)
        sched.step()
        tr_loss, tr_acc = loss_sum / max(1, seen), correct / max(1, total)
        t1 = time.time()
        val1, val5 = evaluate(model, val_loader, device, 5)
        dt = t1 - t0
        print(f"epoch {epoch:02d}: train loss={tr_loss:.3f} acc={tr_acc:.3f} | val top1={val1:.3f} top5={val5:.3f} | {dt:.1f}s", flush=True)
        history.append({"epoch": epoch, "train_loss": tr_loss, "train_acc": tr_acc, "val_top1": val1, "val_top5": val5, "sec": round(dt, 1)})
        if val1 > best:
            best = val1
            torch.save({"model": model.state_dict(), "classes": labels["classes"], "size": 96,
                        "val_top1": val1, "val_top5": val5}, args.out / "phone_model.pt")
            print("  saved best", round(best, 4), flush=True)
    with open(args.out / "train_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # 载入最佳权重，导出 ONNX 并做一次全场景评测
    ckpt = torch.load(args.out / "phone_model.pt", map_location="cpu")
    model.load_state_dict(ckpt["model"])
    model.eval()
    dummy = torch.randn(1, 3, 96, 96)
    onnx_path = args.out / "phone_model.onnx"
    torch.onnx.export(
        model.cpu(), dummy, str(onnx_path),
        input_names=["pixel_values"], output_names=["logits"],
        opset_version=18, dynamo=False, external_data=False, do_constant_folding=True,
        dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
    )
    print("exported", onnx_path, onnx_path.stat().st_size / 1e6, "MB")

    metrics = {"best_val_top1": best, "classes": n_classes, "history": history}
    hard = ROOT / "app" / "eval" / "data" / "phone_bench_hard2"
    if (hard / "manifest.json").is_file():
        model_cpu = model
        for scene in (False, True):
            for bm in ("exact", "loose", "tight", "offset"):
                r = eval_manifest(model_cpu, labels, hard / "manifest.json", hard, torch.device("cpu"), bm, scene)
                key = f"hard2_{'scene' if scene else 'auto'}_{bm}"
                metrics[key] = {"n": r["n"], "top1": r["top1"], "top5": r["top5"]}
                print(key, r["n"], round(r["top1"], 3), round(r["top5"], 3))
        # 保存 exact/scene 的逐样本明细，方便定位
        r = eval_manifest(model_cpu, labels, hard / "manifest.json", hard, torch.device("cpu"), "exact", True)
        with open(args.out / "hard2_exact_scene_rows.json", "w", encoding="utf-8") as f:
            json.dump(r["rows"], f, ensure_ascii=False, indent=2)
    with open(args.out / "phone_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print("done")


if __name__ == "__main__":
    main()
