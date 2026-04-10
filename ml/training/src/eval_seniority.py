#!/usr/bin/env python3
"""
Evaluate a signals-based seniority bundle (model.joblib) on a JSONL dataset.

  python ml/training/src/eval_seniority.py \\
    --model_dir ml/models/seniority_signals_v1 \\
    --test_jsonl ml/data/splits/seniority_latest/test.jsonl \\
    --out_md ml/training/reports/seniority_signals_v1_eval.md \\
    --metrics_json ml/models/seniority_signals_v1/test_metrics.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from signals_features import feature_dict_from_signals


def _confusion_pairs(cm: np.ndarray, labels: list[str]) -> dict[str, int]:
    """Count specific confusions (symmetric pairs)."""
    idx = {lab: i for i, lab in enumerate(labels)}
    out: dict[str, int] = {}

    def add_pair(a: str, b: str) -> None:
        ia, ib = idx[a], idx[b]
        out[f"{a}_as_{b}"] = int(cm[ia, ib])

    if "mid" in idx and "senior" in idx:
        add_pair("mid", "senior")
        add_pair("senior", "mid")
    if "junior" in idx and "mid" in idx:
        add_pair("junior", "mid")
        add_pair("mid", "junior")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--test_jsonl", required=True)
    ap.add_argument("--out", default="", help="Optional plain-text report (legacy).")
    ap.add_argument("--out_md", default="", help="Markdown report path.")
    ap.add_argument("--metrics_json", default="", help="Optional JSON with accuracy, f1_macro, confusion.")
    args = ap.parse_args()

    bundle = joblib.load(Path(args.model_dir) / "model.joblib")
    clf = bundle["pipeline"]
    le: object = bundle["label_encoder"]
    feature_names: list[str] = bundle["feature_names"]

    known_classes = set(getattr(le, "classes_", []))
    X_list: list[list[float]] = []
    y_true: list[str] = []
    skipped_unknown = 0
    with Path(args.test_jsonl).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labels = row.get("labels") or {}
            lab = str(labels.get("seniority_label") or "").strip()
            if lab not in ("intern", "junior", "mid", "senior"):
                continue
            if lab not in known_classes:
                skipped_unknown += 1
                continue
            sig = row.get("signals") if isinstance(row.get("signals"), dict) else {}
            feat = feature_dict_from_signals(sig)
            vec = [feat.get(n, 0.0) for n in feature_names]
            X_list.append(vec)
            y_true.append(lab)

    if not X_list:
        print("No labeled rows in test set.", file=sys.stderr)
        return 1

    X = np.asarray(X_list, dtype=np.float64)
    y_enc = le.transform(np.array(y_true))
    pred = clf.predict(X)
    acc = accuracy_score(y_enc, pred)
    f1m = f1_score(y_enc, pred, average="macro", zero_division=0)
    report = classification_report(y_enc, pred, target_names=le.classes_, zero_division=0)
    cm = confusion_matrix(y_enc, pred)
    labels = list(le.classes_)
    pairs = _confusion_pairs(cm, labels)

    metrics = {
        "accuracy": float(acc),
        "f1_macro": float(f1m),
        "confusion_matrix": cm.tolist(),
        "labels": labels,
        "confusion_pairs": pairs,
    }
    if args.metrics_json:
        mp = Path(args.metrics_json)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    md_lines = [
        "# Seniority signals model — evaluation",
        "",
        f"- **model_dir**: `{Path(args.model_dir).as_posix()}`",
        f"- **test_jsonl**: `{Path(args.test_jsonl).as_posix()}`",
        f"- **rows (evaluated)**: {len(y_true)}",
        f"- **rows skipped (label not in model classes)**: {skipped_unknown}",
        "",
        "## Headline metrics",
        "",
        f"- **accuracy**: {acc:.4f}",
        f"- **F1 macro**: {f1m:.4f}",
        "",
        "## Confusion matrix (rows = true, cols = predicted)",
        "",
        "| | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for i, row_name in enumerate(labels):
        md_lines.append("| " + row_name + " | " + " | ".join(str(int(cm[i, j])) for j in range(len(labels))) + " |")
    md_lines.extend(
        [
            "",
            "## High-risk confusions",
            "",
            "Focus on adjacent seniority steps (policy-sensitive):",
            "",
        ]
    )
    for k, v in sorted(pairs.items(), key=lambda x: -x[1]):
        md_lines.append(f"- `{k}`: **{v}**")
    md_lines.extend(["", "## Classification report", "", "```", report.rstrip(), "```", ""])

    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"Wrote {out_md}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"accuracy: {acc:.4f}",
            f"f1_macro: {f1m:.4f}",
            "",
            "classification_report:",
            report,
            "",
            "confusion_matrix (rows=true, cols=pred):",
            str(cm),
            "",
            "confusion_pairs:",
            json.dumps(pairs, indent=2),
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {out_path}")

    if not args.out_md and not args.out:
        print("\n".join(md_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
