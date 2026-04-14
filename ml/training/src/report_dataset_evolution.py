#!/usr/bin/env python3
"""
Append a timestamped snapshot to ml/training/reports/dataset_evolution.md (TCC evidence).

Reads:
  - dataset JSONL (v1.1): row count, label distribution, % reviewed
  - split_meta.json: dataset_version
  - test_metrics.json: accuracy, f1_macro
  - eval_seniority.md: first headline lines (optional)
  - ab_low_confidence_report.md: senior % lines (optional)

  python ml/training/src/report_dataset_evolution.py \\
    --jsonl ml/data/processed/seniority_from_db.jsonl \\
    --split_meta ml/data/splits/seniority_latest/split_meta.json \\
    --metrics_json ml/models/seniority_signals_v1/test_metrics.json \\
    --eval_md ml/training/reports/eval_seniority.md \\
    --ab_md ml/training/reports/ab_low_confidence_report.md \\
    --out ml/training/reports/dataset_evolution.md
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _scan_jsonl(path: Path) -> tuple[int, Counter[str], int, int]:
    n = 0
    by_label: Counter[str] = Counter()
    reviewed = 0
    with_source = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n += 1
            labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
            lab = str(labels.get("seniority_label") or "").strip() or "(empty)"
            by_label[lab] += 1
            if labels.get("reviewed") is True:
                reviewed += 1
            if str(labels.get("source") or "").strip():
                with_source += 1
    return n, by_label, reviewed, with_source


def _extract_ab_senior_pct(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if "senior" in line.lower() and "%" in line:
            out.append(line.strip())
        if len(out) >= 4:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--split_meta", default="")
    ap.add_argument("--metrics_json", default="")
    ap.add_argument("--eval_md", default="")
    ap.add_argument("--ab_md", default="")
    ap.add_argument("--out", default="ml/training/reports/dataset_evolution.md")
    args = ap.parse_args()

    jp = Path(args.jsonl)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n, by_label, reviewed, _ = _scan_jsonl(jp)
    pct_rev = 100.0 * reviewed / n if n else 0.0

    split_ver = ""
    if args.split_meta:
        sm = _read_json(Path(args.split_meta))
        split_ver = str(sm.get("dataset_version") or "").strip()

    acc = f1 = ""
    if args.metrics_json:
        m = _read_json(Path(args.metrics_json))
        acc = str(m.get("accuracy", ""))
        f1 = str(m.get("f1_macro", ""))

    eval_head = ""
    if args.eval_md and Path(args.eval_md).is_file():
        lines = Path(args.eval_md).read_text(encoding="utf-8").splitlines()[:25]
        eval_head = "\n".join(f"  > {ln}" for ln in lines if ln.strip())

    ab_bits = ""
    if args.ab_md and Path(args.ab_md).is_file():
        ab_bits = "\n".join(f"  - {s}" for s in _extract_ab_senior_pct(Path(args.ab_md).read_text(encoding="utf-8")))

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    block = [
        f"## Snapshot — {ts}",
        "",
        f"- **jsonl**: `{jp.as_posix()}`",
        f"- **rows (N)**: {n}",
        f"- **dataset_version** (split_meta): `{split_ver or 'n/a'}`",
        f"- **reviewed rows**: {reviewed} ({pct_rev:.2f}% of N)",
        "",
        "### Label distribution (gold `seniority_label`)",
        "",
    ]
    for lab, c in sorted(by_label.items(), key=lambda x: (-x[1], x[0])):
        pct = 100.0 * c / n if n else 0.0
        block.append(f"- `{lab}`: {c} ({pct:.1f}%)")

    block.extend(
        [
            "",
            "### Model metrics (held-out test)",
            "",
            f"- **accuracy**: {acc or 'n/a'}",
            f"- **F1 macro**: {f1 or 'n/a'}",
            "",
        ]
    )
    if eval_head:
        block.extend(["### Eval excerpt (head)", "", eval_head, ""])
    if ab_bits:
        block.extend(["### A/B low-confidence (excerpt)", "", ab_bits, ""])
    block.append("---")
    block.append("")

    prev = ""
    if out_path.is_file():
        prev = out_path.read_text(encoding="utf-8")
    if not prev.strip():
        prev = "# Dataset evolution log (TCC)\n\nAutomated snapshots from `report_dataset_evolution.py`.\n\n---\n\n"

    out_path.write_text(prev.rstrip() + "\n\n" + "\n".join(block), encoding="utf-8")
    print(f"Appended snapshot to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
