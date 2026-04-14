#!/usr/bin/env python3
"""
Train a lightweight seniority classifier from structured signals (mode A).

Uses train + validation JSONL (from split_dataset.py). Fits LogisticRegression + StandardScaler,
then optional probability calibration (Platt / isotonic) on the validation split.

Example (from repo root):

  python ml/training/src/train_seniority.py \\
    --train_jsonl ml/data/splits/seniority_latest/train.jsonl \\
    --val_jsonl ml/data/splits/seniority_latest/val.jsonl \\
    --model_version seniority_signals_v1 \\
    --out_dir ml/models/seniority_signals_v1
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from signals_features import feature_dict_from_signals

_LABELS = ("intern", "junior", "mid", "senior")


def _calibration_cv_folds(y_enc: np.ndarray) -> int:
    """Folds for CalibratedClassifierCV; stratified CV needs each class count >= n_folds."""
    if y_enc.size == 0:
        return 0
    min_c = min(Counter(int(x) for x in y_enc).values())
    if min_c < 2:
        return 0
    return min(5, min_c)


def _fit_calibrated_classifier(
    base: Pipeline,
    X_va: np.ndarray,
    y_va_enc: np.ndarray,
    *,
    method: str,
) -> tuple[Any, bool, str]:
    """
    sklearn ≥1.8: use FrozenEstimator + CV on the validation set (prefit removed).
    sklearn antigo: tenta cv='prefit'.
    """
    cv_eff = _calibration_cv_folds(y_va_enc)
    if cv_eff < 2:
        return base, False, "none"

    try:
        from sklearn.frozen import FrozenEstimator

        cal = CalibratedClassifierCV(FrozenEstimator(base), method=method, cv=cv_eff)
        cal.fit(X_va, y_va_enc)
        return cal, True, method
    except Exception as exc:
        print(f"Calibration failed ({method}), retrying sigmoid: {exc}", file=sys.stderr)
    try:
        from sklearn.frozen import FrozenEstimator

        cal = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid", cv=cv_eff)
        cal.fit(X_va, y_va_enc)
        return cal, True, "sigmoid"
    except Exception as exc:
        print(f"FrozenEstimator calibration disabled: {exc}", file=sys.stderr)

    try:
        cal = CalibratedClassifierCV(base, cv="prefit", method=method)
        cal.fit(X_va, y_va_enc)
        return cal, True, method
    except Exception:
        pass
    try:
        cal = CalibratedClassifierCV(base, cv="prefit", method="sigmoid")
        cal.fit(X_va, y_va_enc)
        return cal, True, "sigmoid"
    except Exception as exc2:
        print(f"Calibration disabled: {exc2}", file=sys.stderr)
    return base, False, "none"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _build_xy(rows: list[dict[str, Any]], feature_names: list[str], le: LabelEncoder | None = None) -> tuple[np.ndarray, np.ndarray, LabelEncoder]:
    X_list: list[list[float]] = []
    y_raw: list[str] = []
    for row in rows:
        labels = row.get("labels") or {}
        lab = str(labels.get("seniority_label") or "").strip()
        if lab not in _LABELS:
            continue
        sig = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        feat = feature_dict_from_signals(sig)
        vec = [feat.get(n, 0.0) for n in feature_names]
        X_list.append(vec)
        y_raw.append(lab)
    encoder = LabelEncoder() if le is None else le
    y = encoder.fit_transform(np.array(y_raw)) if le is None else encoder.transform(np.array(y_raw))
    X = np.asarray(X_list, dtype=np.float64)
    return X, y, encoder


def _infer_feature_names(rows: list[dict[str, Any]]) -> list[str]:
    feature_names: list[str] | None = None
    for row in rows:
        labels = row.get("labels") or {}
        lab = str(labels.get("seniority_label") or "").strip()
        if lab not in _LABELS:
            continue
        sig = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        feat = feature_dict_from_signals(sig)
        if not feat:
            continue
        feature_names = sorted(feat.keys())
        break
    return feature_names or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split_dir", default="", help="Directory with train.jsonl + val.jsonl (alternative to --train_jsonl).")
    ap.add_argument("--train_jsonl", default="", help="Training JSONL (schema v1.0).")
    ap.add_argument("--val_jsonl", default="", help="Validation JSONL for calibration (recommended).")
    ap.add_argument("--model_version", default="", help="Default: last segment of --out_dir.")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument(
        "--mode",
        choices=("signals", "hf"),
        default="signals",
        help="signals: LogReg on numeric features; hf: not implemented (see train.py).",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--calibration_min_val",
        type=int,
        default=50,
        help="Minimum validation rows to attempt calibration.",
    )
    ap.add_argument(
        "--isotonic_min_val",
        type=int,
        default=400,
        help="Use isotonic calibration when val set has at least this many rows (else sigmoid).",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    model_version = (args.model_version or "").strip() or out_dir.name

    if args.split_dir:
        sd = Path(args.split_dir)
        train_path = sd / "train.jsonl"
        val_path = sd / "val.jsonl"
    elif args.train_jsonl:
        train_path = Path(args.train_jsonl)
        val_path = Path(args.val_jsonl) if args.val_jsonl else None
    else:
        print("Provide --split_dir or --train_jsonl.", file=sys.stderr)
        return 2

    if args.mode == "hf":
        print(
            "Mode 'hf' is not implemented in this script; use ml/training/src/train.py --task seniority.",
            file=sys.stderr,
        )
        return 2

    train_rows = _load_rows(train_path)
    if len(train_rows) < 8:
        print("Need at least 8 training rows for a stable run.", file=sys.stderr)
        return 1

    labeled = sum(
        1
        for row in train_rows
        if str((row.get("labels") or {}).get("seniority_label") or "").strip() in _LABELS
    )
    if labeled == 0:
        print(
            f"No training rows have labels.seniority_label in {_LABELS}. "
            "Backfill or export labeled analyses before training.",
            file=sys.stderr,
        )
        return 1

    feature_names = _infer_feature_names(train_rows)
    if len(feature_names) < 2:
        print(
            "Could not infer feature names: labeled rows have empty or non-numeric signals.",
            file=sys.stderr,
        )
        return 1

    X_tr, y_tr, le = _build_xy(train_rows, feature_names)
    if len(X_tr) < 8:
        print("Not enough labeled rows after filtering.", file=sys.stderr)
        return 1

    base = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "lr",
                LogisticRegression(
                    max_iter=400,
                    class_weight="balanced",
                    random_state=args.seed,
                ),
            ),
        ]
    )
    base.fit(X_tr, y_tr)

    calibrated = False
    calibration_method = "none"
    final_estimator: Any = base

    if isinstance(val_path, Path) and val_path.exists():
        val_rows = _load_rows(val_path)
        try:
            X_va, y_va_enc, _ = _build_xy(val_rows, feature_names, le=le)
        except ValueError:
            print("Validation set contains labels not seen in training; skipping calibration.", file=sys.stderr)
            X_va = np.empty((0, len(feature_names)))
            y_va_enc = np.array([], dtype=int)
        if len(X_va) >= args.calibration_min_val:
            cal_method = "isotonic" if len(X_va) >= args.isotonic_min_val else "sigmoid"
            final_estimator, calibrated, calibration_method = _fit_calibrated_classifier(
                base, X_va, y_va_enc, method=cal_method
            )

    pred_va = final_estimator.predict(X_tr)
    report = classification_report(y_tr, pred_va, target_names=le.classes_, zero_division=0)

    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": final_estimator,
        "label_encoder": le,
        "feature_names": feature_names,
        "model_version": model_version,
        "mode": "signals_logreg_calibrated" if calibrated else "signals_logreg",
        "calibrated": calibrated,
        "calibration_method": calibration_method,
    }
    joblib.dump(bundle, out_dir / "model.joblib")

    train_metrics = {
        "accuracy": float(accuracy_score(y_tr, pred_va)),
        "f1_macro": float(f1_score(y_tr, pred_va, average="macro", zero_division=0)),
    }
    (out_dir / "train_fit_metrics.json").write_text(json.dumps(train_metrics, indent=2), encoding="utf-8")

    meta = {
        "model_name": "seniority_signals",
        "model_version": model_version,
        "dataset_version": "unknown",
        "task": "seniority_signals",
        "mode": bundle["mode"],
        "feature_count": len(feature_names),
        "features_schema": list(feature_names),
        "classes": list(le.classes_),
        "calibrated": calibrated,
        "calibration_method": calibration_method,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "metrics_summary": train_metrics,
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out_dir / "train_classification_report.txt").write_text(report, encoding="utf-8")
    print(f"Saved {out_dir / 'model.joblib'} (calibrated={calibrated}, method={calibration_method})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
