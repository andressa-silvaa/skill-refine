#!/usr/bin/env python3
"""
Finalize metadata.json for target_fit bundle (dataset_version, metrics, audit fields).

  python ml/training/src/export_target_fit_sklearn_model.py \\
    --model_dir ml/models/target_fit_v1 \\
    --split_meta ml/data/splits/target_fit_v1/split_meta.json \\
    --test_metrics_json ml/models/target_fit_v1/test_metrics.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--split_meta", required=True, help="split_meta.json from split_target_fit_dataset.py")
    ap.add_argument("--test_metrics_json", default="", help="Optional test metrics from eval_target_fit.py")
    args = ap.parse_args()

    model_dir = Path(args.model_dir)
    meta_path = model_dir / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    split_meta = json.loads(Path(args.split_meta).read_text(encoding="utf-8"))
    dv = split_meta.get("dataset_version", "unknown")
    meta["dataset_version"] = dv
    meta["trained_at"] = datetime.now(timezone.utc).isoformat()
    meta.setdefault("model_name", "target_fit_signals")
    meta.setdefault("model_version", "target_fit_v1")
    meta.setdefault("task", "target_fit_signals")
    meta.setdefault("input_schema_version", "1.0")
    meta.setdefault("languages_supported", ["pt-BR", "en-US", "es-ES"])

    job_path = model_dir / "model.joblib"
    if job_path.exists():
        try:
            bundle = joblib.load(job_path)
            fn = bundle.get("feature_names")
            if isinstance(fn, list):
                meta["features_schema"] = fn
        except Exception:
            pass

    if args.test_metrics_json:
        tm_path = Path(args.test_metrics_json)
        if tm_path.exists():
            test_m = json.loads(tm_path.read_text(encoding="utf-8"))
            meta["metrics_summary"] = {
                "test_mae": test_m.get("mae"),
                "test_rmse": test_m.get("rmse"),
                "test_r2": test_m.get("r2"),
                "n_test": test_m.get("n_test"),
            }

    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Updated {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
