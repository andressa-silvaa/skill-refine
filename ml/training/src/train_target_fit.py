#!/usr/bin/env python3
"""
Train Ridge regressor on target-fit JSONL (schema 1.0).

Feature vector must match ``apps.analysis.application.inference.tasks.target_fit.ml_feature_row``.

  python ml/training/src/train_target_fit.py \\
    --train_jsonl ml/data/splits/target_fit_v1/train.jsonl \\
    --out_dir ml/models/target_fit_v1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def _bootstrap_backend_src() -> None:
    root = Path(__file__).resolve().parents[3]
    src = root / "backend" / "src"
    if not (src / "apps" / "analysis").is_dir():
        print(f"Could not find Django apps under {src}", file=sys.stderr)
        raise SystemExit(1)
    sys.path.insert(0, str(src))


def _row_to_x(row: dict) -> list[float]:
    from apps.analysis.application.inference.tasks.target_fit.ml_feature_row import target_fit_feature_row_from_jsonl

    return target_fit_feature_row_from_jsonl(row)


def _feature_names() -> list[str]:
    from apps.analysis.application.inference.tasks.target_fit.ml_feature_row import target_fit_feature_names

    return target_fit_feature_names()


def main() -> int:
    _bootstrap_backend_src()
    ap = argparse.ArgumentParser()
    ap.add_argument("--train_jsonl", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--alpha", type=float, default=1.0)
    args = ap.parse_args()

    path = Path(args.train_jsonl)
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if len(rows) < 8:
        print("Need at least 8 training rows.", file=sys.stderr)
        return 1

    names = _feature_names()
    X = np.asarray([_row_to_x(r) for r in rows], dtype=np.float64)
    if X.shape[1] != len(names):
        print(f"Feature dim mismatch: X={X.shape[1]} names={len(names)}", file=sys.stderr)
        return 1
    y = np.asarray([int((r.get("labels") or {}).get("fit_score") or 0) for r in rows], dtype=np.float64)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = Ridge(alpha=float(args.alpha), random_state=42)
    model.fit(Xs, y)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "scaler": scaler,
        "feature_names": names,
        "input_schema_version": "1.0",
        "task": "target_fit_signals",
    }
    joblib.dump(bundle, out / "model.joblib")
    stub_meta = {
        "task": "target_fit_signals",
        "model_name": "target_fit_signals",
        "model_version": "target_fit_v1",
        "input_schema_version": "1.0",
        "features_schema": names,
        "languages_supported": ["pt-BR", "en-US", "es-ES"],
    }
    (out / "metadata.json").write_text(json.dumps(stub_meta, indent=2), encoding="utf-8")
    print(f"Saved {out / 'model.joblib'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
