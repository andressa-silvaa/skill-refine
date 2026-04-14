#!/usr/bin/env python3
"""
Build a short diagnostic summary from dataset + split + eval artifacts.

  python ml/training/src/summarize_seniority_run.py \\
    --dataset_jsonl ml/data/processed/seniority_from_db.jsonl \\
    --split_meta ml/data/splits/seniority_latest/split_meta.json \\
    --metrics_json ml/models/seniority_signals_v1/test_metrics.json \\
    --eval_md ml/training/reports/eval_seniority.md \\
    --dataset_report ml/training/reports/dataset_report.md \\
    --out ml/training/reports/seniority_signals_v1_summary.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

def _count_dataset(path: Path) -> tuple[int, Counter[str]]:
    n = 0
    c: Counter[str] = Counter()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n += 1
            labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
            lab = str(labels.get("seniority_label") or "(empty)")
            c[lab] += 1
    return n, c


def _parse_dataset_report_md(text: str) -> dict[str, int]:
    """Extract label counts from validate_dataset.py output."""
    out: dict[str, int] = {}
    in_section = False
    for line in text.splitlines():
        if line.strip() == "## Seniority label distribution":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            m = re.match(r"- `([^`]+)`: (\d+)", line.strip())
            if m:
                out[m.group(1)] = int(m.group(2))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset_jsonl", required=True)
    ap.add_argument("--split_meta", required=True)
    ap.add_argument("--metrics_json", required=True)
    ap.add_argument("--eval_md", default="")
    ap.add_argument("--dataset_report", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    n_rows, dist = _count_dataset(Path(args.dataset_jsonl))
    split_meta = json.loads(Path(args.split_meta).read_text(encoding="utf-8"))
    dv = split_meta.get("dataset_version", "unknown")
    splits = split_meta.get("splits") or {}

    metrics_path = Path(args.metrics_json)
    metrics: dict[str, Any] = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    pairs = metrics.get("confusion_pairs") or {}
    top_confusions = sorted(pairs.items(), key=lambda x: -x[1])[:12]

    report_dist: dict[str, int] = {}
    if args.dataset_report:
        rp = Path(args.dataset_report)
        if rp.exists():
            report_dist = _parse_dataset_report_md(rp.read_text(encoding="utf-8"))

    imbalance_note = ""
    if n_rows > 0 and dist:
        most = dist.most_common(1)[0][1]
        ratio = most / n_rows
        if ratio > 0.55:
            imbalance_note = (
                f"\n⚠️ **Class imbalance**: top label share ≈ {ratio:.1%}. "
                "Consider increasing `--since` / `--limit` or reviewing labels/policy before relying on thresholds.\n"
            )

    lines = [
        "# Seniority signals — run summary (auto)",
        "",
        "## Dataset",
        "",
        f"- **rows (processed JSONL)**: {n_rows}",
        f"- **dataset_version** (split fingerprint): `{dv}`",
        f"- **split row counts**: {json.dumps(splits, ensure_ascii=False)}",
        "",
        "### Class distribution (from JSONL labels)",
        "",
    ]
    for k, v in sorted(dist.items(), key=lambda x: (-x[1], x[0])):
        pct = f" ({100 * v / n_rows:.1f}%)" if n_rows else ""
        lines.append(f"- `{k}`: {v}{pct}")

    if report_dist:
        lines.extend(["", "### Cross-check (dataset_report.md)", ""])
        for k, v in sorted(report_dist.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- `{k}`: {v}")

    lines.extend(
        [
            imbalance_note,
            "## Test metrics (held-out split)",
            "",
            f"- **accuracy**: {metrics.get('accuracy', 'n/a')}",
            f"- **F1 macro**: {metrics.get('f1_macro', 'n/a')}",
            "",
            "### Top confusion cells (test)",
            "",
        ]
    )
    for k, v in top_confusions:
        lines.append(f"- `{k}`: **{v}**")

    lines.extend(
        [
            "",
            "## Adjacent-class focus",
            "",
            "Policy-sensitive pairs: **mid↔senior**, **junior↔mid**, **intern↔junior** (see eval report for full matrix).",
            "",
        ]
    )
    if args.eval_md:
        lines.append(f"- Eval markdown: `{Path(args.eval_md).as_posix()}`")
    lines.append("")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
