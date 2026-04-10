#!/usr/bin/env python3
"""
Stamp dataset_version and optional test metrics into sklearn seniority bundle metadata.

  python ml/training/src/export_seniority_sklearn_model.py \\
    --model_dir ml/models/seniority_signals_v1 \\
    --split_meta ml/data/splits/seniority_latest/split_meta.json \\
    --test_metrics_json ml/models/seniority_signals_v1/test_metrics.json

Copies nothing by default; updates ``metadata.json`` in place.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import joblib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--split_meta", required=True, help="split_meta.json from split_dataset.py")
    ap.add_argument(
        "--test_metrics_json",
        default="",
        help="Optional test metrics from eval_seniority.py --metrics_json",
    )
    ap.add_argument("--out_dir", default="", help="Optional copy destination (full directory copy).")
    args = ap.parse_args()

    model_dir = Path(args.model_dir)
    meta_path = model_dir / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    split_meta = json.loads(Path(args.split_meta).read_text(encoding="utf-8"))
    dv = split_meta.get("dataset_version", "unknown")
    meta["dataset_version"] = dv
    meta["exported_at"] = datetime.now(timezone.utc).isoformat()
    meta.setdefault("model_name", "seniority_signals")
    if args.test_metrics_json:
        tm_path = Path(args.test_metrics_json)
        if tm_path.exists():
            test_m = json.loads(tm_path.read_text(encoding="utf-8"))
            ms = dict(meta.get("metrics_summary") or {})
            ms["test_accuracy"] = test_m.get("accuracy")
            ms["test_f1_macro"] = test_m.get("f1_macro")
            meta["metrics_summary"] = ms
            meta["test_metrics"] = {
                "accuracy": test_m.get("accuracy"),
                "f1_macro": test_m.get("f1_macro"),
                "confusion_pairs": test_m.get("confusion_pairs"),
            }

    joblib_meta_path = model_dir / "model.joblib"
    if joblib_meta_path.exists():
        try:
            bundle = joblib.load(joblib_meta_path)
            fn = bundle.get("feature_names")
            if isinstance(fn, list):
                meta["features_schema"] = fn
        except Exception:
            pass

    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if args.out_dir:
        dest = Path(args.out_dir)
        if dest.exists():
            raise SystemExit(f"Refusing to overwrite existing {dest}")
        shutil.copytree(model_dir, dest)
        (dest / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Updated {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
