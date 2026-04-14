#!/usr/bin/env python3
"""
Seleciona linhas para revisão humana (Excel) — fronteiras de score + possível career switch.

  python ml/training/src/build_target_fit_review_candidates.py \\
    --in ml/data/processed/target_fit_from_db.jsonl \\
    --out ml/data/processed/target_fit_review_candidates_ptbr.csv \\
    --limit 150
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _policy_score(row: dict) -> int:
    lab = row.get("labels") or {}
    if isinstance(lab.get("fit_score"), (int, float)):
        return int(lab["fit_score"])
    meta = row.get("meta") or {}
    if isinstance(meta.get("policy_score"), (int, float)):
        return int(meta["policy_score"])
    return 0


def _mismatch(row: dict) -> bool:
    rd = str(row.get("resume_domain_category") or "").strip().lower()
    td = str(row.get("domain_category") or "").strip().lower()
    if not rd or not td:
        return False
    if rd == "general" or td == "general":
        return False
    return rd != td


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument("--limit", type=int, default=150)
    args = ap.parse_args()

    rows: list[dict] = []
    with Path(args.in_path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    border_low: list[dict] = []
    border_high: list[dict] = []
    mismatch_rows: list[dict] = []
    for r in rows:
        s = _policy_score(r)
        if 30 <= s <= 50:
            border_low.append(r)
        if 60 <= s <= 80:
            border_high.append(r)
        if _mismatch(r):
            mismatch_rows.append(r)

    seen: set[str] = set()
    picked: list[dict] = []

    def take(bucket: list[dict]) -> None:
        nonlocal picked
        for r in bucket:
            if len(picked) >= args.limit:
                return
            k = str(r.get("analysis_key") or "")
            if not k or k in seen:
                continue
            seen.add(k)
            picked.append(r)

    # Prioridade: mismatch, depois fronteiras
    take(mismatch_rows)
    take(border_low)
    take(border_high)
    if len(picked) < args.limit:
        rest = [r for r in rows if str(r.get("analysis_key") or "") not in seen]
        take(rest)

    out_p = Path(args.out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "analysis_key",
        "resume_key",
        "target_position",
        "domain_category",
        "resume_domain_category",
        "required_terms_hit",
        "required_terms_total",
        "skills_hit",
        "experience_keyword_hits",
        "completeness_score",
        "mismatch_domain",
        "has_job_text",
        "policy_fit_score",
        "review_fit_score",
        "review_note",
    ]
    with out_p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        w.writeheader()
        for r in picked[: args.limit]:
            sig = r.get("signals") or {}
            mm = _mismatch(r)
            w.writerow(
                {
                    "analysis_key": str(r.get("analysis_key") or ""),
                    "resume_key": str(r.get("resume_key") or ""),
                    "target_position": str(r.get("target_position") or "")[:200],
                    "domain_category": str(r.get("domain_category") or ""),
                    "resume_domain_category": str(r.get("resume_domain_category") or ""),
                    "required_terms_hit": sig.get("required_terms_hit", ""),
                    "required_terms_total": sig.get("required_terms_total", ""),
                    "skills_hit": sig.get("skills_hit", ""),
                    "experience_keyword_hits": sig.get("experience_keyword_hits", ""),
                    "completeness_score": sig.get("completeness_score", ""),
                    "mismatch_domain": "1" if mm else "0",
                    "has_job_text": "1" if r.get("has_job_description") else "0",
                    "policy_fit_score": _policy_score(r),
                    "review_fit_score": "",
                    "review_note": "",
                }
            )

    print(f"Wrote {len(picked[: args.limit])} rows to {out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
