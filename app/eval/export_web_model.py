#!/usr/bin/env python3
"""把训练好的拍屏 CNN 导出成 Transformers.js 可直接加载的本地模型。

输出目录（默认 app/web/vendor/models/phone-cnn）：
  onnx/model.onnx          单文件，输入 pixel_values，输出 logits
  config.json              model_type=resnet，让 Transformers.js 用通用分类头加载
  preprocessor_config.json 不缩放/不裁切，只做 /255 和均值 0.5 归一化
  labels.json              1000 类顺序表（kind/id），供前端映射到图鉴条目

用法：
  .venv/bin/python app/eval/export_web_model.py
  .venv/bin/python app/eval/export_web_model.py --checkpoint app/eval/models/phone_model.pt
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_phone_model import SmallNet  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, default=ROOT / "app/eval/models/phone_model.pt")
    ap.add_argument("--labels", type=Path, default=ROOT / "app/eval/data/phone_crops/labels.json")
    ap.add_argument("--out", type=Path, default=ROOT / "app/web/vendor/models/phone-cnn")
    ap.add_argument("--metrics", type=Path, default=ROOT / "app/eval/models/phone_metrics.json")
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    labels = json.load(open(args.labels, encoding="utf-8"))
    classes = labels["classes"]
    model = SmallNet(len(classes))
    model.load_state_dict(ck["model"])
    model.eval()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "onnx").mkdir(parents=True, exist_ok=True)
    onnx_path = args.out / "onnx" / "model.onnx"
    dummy = torch.randn(1, 3, 96, 96)
    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names=["pixel_values"], output_names=["logits"],
        opset_version=18, dynamo=False, external_data=False,
        do_constant_folding=True, dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}},
    )

    id2label = {str(i): f"{c['kind']}:{c['id']}" for i, c in enumerate(classes)}
    config = {
        "architectures": ["ResNetForImageClassification"],
        "model_type": "resnet",
        "num_labels": len(classes),
        "image_size": 96,
        "id2label": id2label,
        "label2id": {v: int(k) for k, v in id2label.items()},
    }
    with open(args.out / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False)
    pre = {
        "do_convert_rgb": True,
        "do_resize": False,
        "do_center_crop": False,
        "do_rescale": True,
        "rescale_factor": 0.00392156862745098,
        "do_normalize": True,
        "image_mean": [0.5, 0.5, 0.5],
        "image_std": [0.5, 0.5, 0.5],
        "image_processor_type": "BitImageProcessor",
        "size": {"height": 96, "width": 96},
        "crop_size": {"height": 96, "width": 96},
    }
    with open(args.out / "preprocessor_config.json", "w", encoding="utf-8") as f:
        json.dump(pre, f, ensure_ascii=False, indent=2)
    with open(args.out / "labels.json", "w", encoding="utf-8") as f:
        json.dump({"size": 96, "classes": [{"kind": c["kind"], "id": c["id"]} for c in classes]}, f, ensure_ascii=False)

    meta = {
        "format": "isaac-phone-cnn",
        "size": 96,
        "classes": len(classes),
        "checkpoint_val_top1": ck.get("val_top1"),
        "checkpoint_val_top5": ck.get("val_top5"),
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    if args.metrics.is_file():
        try:
            metrics = json.load(open(args.metrics, encoding="utf-8"))
            meta["bench"] = {k: v for k, v in metrics.items() if k.startswith("hard2_")}
        except Exception:
            pass
    with open(args.out / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 用 ORT 验证单文件模型，并对比 PyTorch 输出
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        x = np.random.randn(2, 3, 96, 96).astype(np.float32)
        y_onnx = sess.run(None, {"pixel_values": x})[0]
        with torch.no_grad():
            y_torch = model(torch.from_numpy(x)).numpy()
        ok = np.allclose(y_onnx, y_torch, atol=2e-4)
        print(f"onnx check: {'OK' if ok else 'MISMATCH'} max_abs={np.abs(y_onnx-y_torch).max():.2e}")
    except ImportError:
        print("onnxruntime 未安装，跳过验证")

    print(f"wrote {onnx_path} {onnx_path.stat().st_size/1e6:.2f} MB")
    print(f"wrote {args.out}/config.json, preprocessor_config.json, labels.json, meta.json")


if __name__ == "__main__":
    main()
