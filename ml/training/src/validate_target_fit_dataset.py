#!/usr/bin/env python3
"""
Validate target-fit JSONL (schema 1.0) and write a short markdown report.

  python ml/training/src/validate_target_fit_dataset.py \\
    --in ml/data/processed/target_fit_from_db.jsonl \\
    --report ml/training/reports/target_fit_dataset_report.md
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def _validate_row(row: dict, idx: int) -> list[str]:
    errs: list[str] = []
    if row.get("schema_version") != "1.0":
        errs.append(f"line {idx}: schema_version must be 1.0")
    if row.get("dataset_kind") != "target_fit":
        errs.append(f"line {idx}: dataset_kind must be target_fit")
    for k in ("analysis_key", "resume_key", "user_key", "lang", "target_position", "domain_category", "resume_domain_category"):
        if not str(row.get(k) or "").strip():
            errs.append(f"line {idx}: missing {k}")
    sig = row.get("signals")
    if not isinstance(sig, dict):
        errs.append(f"line {idx}: signals must be object")
        return errs
    for k in (
        "required_terms_total",
        "required_terms_hit",
        "skills_total",
        "skills_hit",
        "experience_keyword_hits",
        "completeness_score",
    ):
        if k not in sig:
            errs.append(f"line {idx}: signals.{k} missing")
    if "education_alignment" not in sig:
        errs.append(f"line {idx}: signals.education_alignment missing")
    if "portfolio_evidence" not in sig:
        errs.append(f"line {idx}: signals.portfolio_evidence missing")
    lab = row.get("labels")
    if not isinstance(lab, dict):
        errs.append(f"line {idx}: labels must be object")
        return errs
    fs = lab.get("fit_score")
    if not isinstance(fs, (int, float)) or int(fs) < 0 or int(fs) > 100:
        errs.append(f"line {idx}: labels.fit_score must be 0..100")
    src = str(lab.get("label_source") or "")
    if src not in ("policy", "review"):
        errs.append(f"line {idx}: labels.label_source must be policy|review")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--top_domains", type=int, default=20)
    args = ap.parse_args()

    in_path = Path(args.in_path)
    rows: list[dict] = []
    errors: list[str] = []
    if not in_path.is_file():
        print(f"Missing input: {in_path}", flush=True)
        return 1
    with in_path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append(f"line {i}: JSON error: {e}")

    for j, row in enumerate(rows, start=1):
        errors.extend(_validate_row(row, j))

    dom_ctr = Counter(str(r.get("domain_category") or "") for r in rows)
    lang_ctr = Counter(str(r.get("lang") or "") for r in rows)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Target fit dataset report",
        "",
        f"- **path**: `{in_path.as_posix()}`",
        f"- **rows**: {len(rows)}",
        f"- **errors**: {len(errors)}",
        "",
    ]
    if errors:
        lines.append("## Validation errors")
        lines.append("")
        for e in errors[:80]:
            lines.append(f"- {e}")
        if len(errors) > 80:
            lines.append(f"- … ({len(errors) - 80} more)")
        lines.append("")

    lines.append("## domain_category (top N)")
    lines.append("")
    for name, c in dom_ctr.most_common(args.top_domains):
        lines.append(f"- `{name}`: {c}")
    lines.append("")
    lines.append("## lang")
    lines.append("")
    for name, c in lang_ctr.most_common(12):
        lines.append(f"- `{name}`: {c}")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
