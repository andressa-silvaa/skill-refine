#!/usr/bin/env python3
"""
Evaluate target_fit model.joblib on a labeled JSONL (MAE, RMSE, R²).

  python ml/training/src/eval_target_fit.py \\
    --model_dir ml/models/target_fit_v1 \\
    --test_jsonl ml/data/splits/target_fit_v1/test.jsonl \\
    --report ml/training/reports/target_fit_eval.md \\
    --metrics_json ml/models/target_fit_v1/test_metrics.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def _bootstrap_backend_src() -> None:
    root = Path(__file__).resolve().parents[3]
    src = root / "backend" / "src"
    sys.path.insert(0, str(src))


def _row_to_x(row: dict) -> list[float]:
    from apps.analysis.application.inference.tasks.target_fit.ml_feature_row import target_fit_feature_row_from_jsonl

    return target_fit_feature_row_from_jsonl(row)


def main() -> int:
    _bootstrap_backend_src()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--test_jsonl", required=True)
    ap.add_argument("--report", default="")
    ap.add_argument("--metrics_json", default="")
    args = ap.parse_args()

    model_dir = Path(args.model_dir)
    bundle = joblib.load(model_dir / "model.joblib")
    model = bundle["model"]
    scaler = bundle["scaler"]
    fn = bundle.get("feature_names") or []

    rows: list[dict] = []
    with Path(args.test_jsonl).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        print("Empty test set.", file=sys.stderr)
        return 1

    X = np.asarray([_row_to_x(r) for r in rows], dtype=np.float64)
    if fn and X.shape[1] != len(fn):
        print(f"Feature count mismatch: X={X.shape[1]} bundle={len(fn)}", file=sys.stderr)
        return 1
    y = np.asarray([int((r.get("labels") or {}).get("fit_score") or 0) for r in rows], dtype=np.float64)
    pred = model.predict(scaler.transform(X))
    pred = np.clip(pred, 0, 100)

    mae = float(mean_absolute_error(y, pred))
    rmse = float(math.sqrt(mean_squared_error(y, pred)))
    r2 = float(r2_score(y, pred))

    metrics = {
        "n_test": len(rows),
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
    }
    print(f"MAE={mae:.4f} RMSE={rmse:.4f} R2={r2:.4f}")

    if args.metrics_json:
        Path(args.metrics_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.metrics_json).write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if args.report:
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Target fit evaluation",
            "",
            f"- **n_test**: {len(rows)}",
            f"- **MAE**: {mae:.4f}",
            f"- **RMSE**: {rmse:.4f}",
            f"- **R²**: {r2:.4f}",
            "",
            "## Notes",
            "",
            "- Labels are policy-derived in default export; metrics measure agreement with that deterministic baseline.",
            "",
        ]
        rp.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
