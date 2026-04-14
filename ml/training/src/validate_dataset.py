#!/usr/bin/env python3
"""
Validate seniority dataset JSONL (schema v1.0 / v1.1) and write a short markdown report.

Run from repository root:

  python ml/training/src/validate_dataset.py --in ml/data/processed/seniority_from_db.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_TOP = (
    "schema_version",
    "dataset_kind",
    "analysis_key",
    "resume_key",
    "created_at",
    "language",
    "signals",
    "labels",
    "targets",
    "gating_reasons",
    "insufficient_data",
    "meta",
)
ALLOW_LABELS = frozenset({"intern", "junior", "mid", "senior"})
ALLOW_LABELS_LEGACY = frozenset({"intern", "junior", "mid", "senior", ""})


def _check_row(row: dict[str, Any], line_no: int, issues: list[str]) -> None:
    for k in REQUIRED_TOP:
        if k not in row:
            issues.append(f"line {line_no}: missing {k}")

    sv = str(row.get("schema_version") or "")
    if sv not in ("1.0", "1.1"):
        issues.append(f"line {line_no}: unexpected schema_version {row.get('schema_version')!r}")

    labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
    sl = str(labels.get("seniority_label", "")).strip()
    if sv == "1.1":
        if sl not in ALLOW_LABELS:
            issues.append(f"line {line_no}: v1.1 requires non-empty seniority_label, got {sl!r}")
        src = str(labels.get("source") or "").strip()
        if src and src not in ("rule", "review"):
            issues.append(f"line {line_no}: invalid labels.source {src!r}")
        if "reviewed" in labels and not isinstance(labels.get("reviewed"), bool):
            issues.append(f"line {line_no}: labels.reviewed must be bool")
    else:
        if sl not in ALLOW_LABELS_LEGACY:
            issues.append(f"line {line_no}: invalid seniority_label {sl!r}")

    targets = row.get("targets") if isinstance(row.get("targets"), dict) else {}
    for key in ("overall_score", "completeness_score"):
        v = targets.get(key)
        if v is None:
            continue
        if not isinstance(v, int) or v < 0 or v > 100:
            issues.append(f"line {line_no}: {key} out of range or not int: {v!r}")

    ts = targets.get("task_scores")
    if ts is not None and isinstance(ts, dict):
        for tk, tv in ts.items():
            if tv is None:
                continue
            if isinstance(tv, (int, float)) and not (0 <= float(tv) <= 100):
                issues.append(f"line {line_no}: task_scores.{tk} out of 0..100: {tv!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument(
        "--report",
        default="ml/training/reports/dataset_report.md",
        help="Markdown report output path.",
    )
    args = ap.parse_args()

    in_path = Path(args.in_path)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    issues: list[str] = []
    label_dist: Counter[str] = Counter()
    conf_dist: Counter[str] = Counter()
    reason_dist: Counter[str] = Counter()
    n = 0
    resume_keys: set[str] = set()

    with in_path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(f"line {i}: JSON error {exc}")
                continue
            if not isinstance(row, dict):
                issues.append(f"line {i}: row is not an object")
                continue
            _check_row(row, i, issues)
            n += 1
            labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
            label_dist[str(labels.get("seniority_label") or "(empty)")] += 1
            conf_dist[str(labels.get("confidence") or "(empty)")] += 1
            rk = str(row.get("resume_key") or "")
            if rk:
                resume_keys.add(rk)
            for r in row.get("gating_reasons") or []:
                reason_dist[str(r)] += 1

    lines_out = [
        "# Dataset validation report",
        "",
        f"- **input**: `{in_path.as_posix()}`",
        f"- **rows**: {n}",
        f"- **unique resume_key**: {len(resume_keys)}",
        f"- **issues**: {len(issues)}",
        "",
        "## Seniority label distribution",
        "",
    ]
    for k, v in sorted(label_dist.items(), key=lambda x: (-x[1], x[0])):
        lines_out.append(f"- `{k}`: {v}")
    lines_out.extend(["", "## Confidence distribution", ""])
    for k, v in sorted(conf_dist.items(), key=lambda x: (-x[1], x[0])):
        lines_out.append(f"- `{k}`: {v}")
    lines_out.extend(["", "## Top gating reasons", ""])
    for k, v in reason_dist.most_common(30):
        lines_out.append(f"- `{k}`: {v}")
    if issues:
        lines_out.extend(["", "## Issues (first 50)", ""])
        for msg in issues[:50]:
            lines_out.append(f"- {msg}")
        if len(issues) > 50:
            lines_out.append(f"- … and {len(issues) - 50} more")

    report_path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    print(f"Wrote {report_path} ({len(issues)} issues)")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
