"""
Export trained model: save_pretrained (already done in train), metadata.json, optional ONNX.
Usage:
  python ml/training/export.py --model_dir ml/models/analysis_v1_seniority_mono_xxx
  python ml/training/export.py --model_dir ml/models/... --onnx
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def load_training_config(model_dir: Path) -> dict:
    config_path = model_dir / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def write_metadata(
    model_dir: Path,
    *,
    model_name_base: str = "",
    model_version: str = "",
    dataset_version: str = "",
    languages: list[str] | None = None,
    task: str = "",
    metrics: dict | None = None,
) -> Path:
    metadata = {
        "model_name_base": model_name_base or str(model_dir.name),
        "model_version": model_version or model_dir.name,
        "dataset_version": dataset_version or "unknown",
        "languages_supported": languages or [],
        "task": task or "unknown",
        "metrics": metrics or {},
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    path = model_dir / "metadata.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    return path


def export_onnx(model_dir: Path, output_dir: Path | None = None) -> Path:
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
    except ImportError:
        raise RuntimeError("transformers and torch required for ONNX export")
    output_dir = output_dir or (model_dir / "onnx")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    # Dummy input
    dummy = tokenizer("dummy text", return_tensors="pt", padding="max_length", max_length=512, truncation=True)
    with open(output_dir / "model.onnx", "wb") as f:
        torch.onnx.export(
            model,
            (dummy["input_ids"], dummy["attention_mask"]),
            f,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={"input_ids": {0: "batch"}, "attention_mask": {0: "batch"}, "logits": {0: "batch"}},
            opset_version=14,
        )
    tokenizer.save_pretrained(output_dir)
    return output_dir


def main() -> None:
    p = argparse.ArgumentParser(description="Export model: metadata.json, optional ONNX")
    p.add_argument("--model_dir", type=Path, required=True, help="Path to saved model (from train.py)")
    p.add_argument("--onnx", action="store_true", help="Export to ONNX in model_dir/onnx/")
    p.add_argument("--metrics", type=Path, help="JSON file with metrics to embed in metadata")
    args = p.parse_args()
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model dir not found: {model_dir}")
    cfg = load_training_config(model_dir)
    metrics = {}
    if args.metrics and Path(args.metrics).exists():
        with open(args.metrics, encoding="utf-8") as f:
            metrics = json.load(f)
    # Prefer metrics from a separate run report; else keep config metrics if present
    if not metrics and "metrics" in cfg:
        metrics = cfg.get("metrics", {})
    path = write_metadata(
        model_dir,
        model_name_base=cfg.get("base_model", ""),
        model_version=cfg.get("model_version", model_dir.name),
        dataset_version=cfg.get("dataset_version", ""),
        languages=cfg.get("languages", []),
        task=cfg.get("task", ""),
        metrics=metrics,
    )
    print(f"Metadata written: {path}")
    if args.onnx:
        out = export_onnx(model_dir)
        print(f"ONNX exported: {out}")


if __name__ == "__main__":
    main()
