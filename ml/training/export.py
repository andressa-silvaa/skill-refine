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
    training_config_path = model_dir / "training_config.json"
    if training_config_path.exists():
        with open(training_config_path, encoding="utf-8") as f:
            return json.load(f)
    hybrid_training_config_path = model_dir / "hybrid" / "training_config.json"
    if hybrid_training_config_path.exists():
        with open(hybrid_training_config_path, encoding="utf-8") as f:
            return json.load(f)
    matching_training_config_path = model_dir / "matching" / "training_config.json"
    if matching_training_config_path.exists():
        with open(matching_training_config_path, encoding="utf-8") as f:
            return json.load(f)

    # Backward compatibility: older runs wrote training config to config.json.
    config_path = model_dir / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    # If it looks like a HF config, ignore it as training metadata.
    if "architectures" in data or "model_type" in data:
        return {}
    return data


def write_metadata(
    model_dir: Path,
    *,
    model_name_base: str = "",
    model_version: str = "",
    dataset_version: str = "",
    languages: list[str] | None = None,
    task: str = "",
    metrics: dict | None = None,
    trained_at: str | None = None,
    input_limits: dict | None = None,
    provider: str | None = None,
    artifact_kind: str | None = None,
) -> Path:
    """Write metadata.json (required for backend model discovery)."""
    metadata = {
        "model_name_base": model_name_base or str(model_dir.name),
        "model_version": model_version or model_dir.name,
        "dataset_version": dataset_version or "unknown",
        "task": task or "unknown",
        "languages_supported": languages or [],
        "trained_at": trained_at or datetime.now(timezone.utc).isoformat(),
        "metrics": metrics or {},
        "input_limits": input_limits or {"max_tokens": 512, "max_chars": 12000},
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider or "local",
        "artifact_kind": artifact_kind or "hf",
    }
    path = model_dir / "metadata.json"
    model_dir.mkdir(parents=True, exist_ok=True)
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
    p.add_argument("--model_dir", type=Path, help="Path to saved model dir (e.g. ml/models/analysis_v1_pt)")
    p.add_argument("--model_version", type=str, help="Model version name (e.g. analysis_v1_pt); uses ml/models/<model_version>/hf")
    p.add_argument("--format", type=str, choices=["hf", "onnx"], default="hf", help="Export format (hf=metadata only, onnx=+ONNX)")
    p.add_argument("--onnx", action="store_true", help="Also export ONNX (deprecated: use --format onnx)")
    p.add_argument("--metrics", type=Path, help="JSON file with metrics to embed in metadata")
    args = p.parse_args()
    if args.model_dir:
        model_dir = Path(args.model_dir)
    elif args.model_version:
        models_root = Path(__file__).resolve().parent.parent / "models"
        model_dir = (models_root / args.model_version).resolve()
    else:
        p.error("Either --model_dir or --model_version is required")
    has_hf = (model_dir / "hf").exists() or (model_dir / "config.json").exists()
    has_hybrid = (model_dir / "hybrid" / "model.pkl").exists()
    has_matching = (model_dir / "matching" / "model.pt").exists()
    if has_hf:
        artifact_dir = model_dir / "hf" if (model_dir / "hf").exists() else model_dir
        artifact_kind = "hf"
    elif has_hybrid:
        artifact_dir = model_dir / "hybrid"
        artifact_kind = "hybrid"
    elif has_matching:
        artifact_dir = model_dir / "matching"
        artifact_kind = "matching"
    else:
        raise FileNotFoundError(f"Model dir not found: {model_dir} (expected hf/, hybrid/model.pkl or matching/model.pt)")
    cfg = load_training_config(artifact_dir)
    metrics = {}
    if args.metrics and Path(args.metrics).exists():
        with open(args.metrics, encoding="utf-8") as f:
            metrics = json.load(f)
    # Prefer metrics from a separate run report; else keep config metrics if present
    if not metrics and "metrics" in cfg:
        metrics = cfg.get("metrics", {})
    meta_dir = model_dir.parent if (model_dir.name in {"hf", "hybrid"}) else model_dir
    path = write_metadata(
        meta_dir,
        model_name_base=cfg.get("base_model", ""),
        model_version=cfg.get("model_version", meta_dir.name),
        dataset_version=cfg.get("dataset_version", ""),
        languages=cfg.get("languages", []),
        task=(
            "quality-hybrid" if artifact_kind == "hybrid" and cfg.get("task") == "quality"
            else ("matching" if artifact_kind == "matching" else cfg.get("task", ""))
        ),
        metrics=metrics,
        trained_at=cfg.get("trained_at"),
        input_limits={"max_tokens": cfg.get("max_length", 512), "max_chars": 12000},
        provider="hybrid-local" if artifact_kind == "hybrid" else "local",
        artifact_kind=artifact_kind,
    )
    print(f"Metadata written: {path}")
    if args.onnx or args.format == "onnx":
        if artifact_kind != "hf":
            raise RuntimeError("ONNX export is only supported for HF artifacts")
        out = export_onnx(artifact_dir, output_dir=meta_dir / "onnx")
        print(f"ONNX exported: {out}")


if __name__ == "__main__":
    main()
