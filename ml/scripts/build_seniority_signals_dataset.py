"""
Convert ml/data/raw/resumes_v2/*.json (real resume_data schema) into the
schema_version 1.1 JSONL format expected by ml/training/src/train_seniority.py,
by running each resume through the REAL production extract_resume_signals /
resume_to_text (not a reimplementation) so the "signals" block is genuine.

Output: ml/data/processed/seniority_synthetic_v2.jsonl
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1].parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.signals.resume_signals import extract_resume_signals  # noqa: E402
from apps.analysis.application.inference.tasks.seniority.rule_based import (  # noqa: E402
    clamp_seniority_vetoes,
    rule_based_seniority,
)
from apps.analysis.application.inference.tasks.seniority.constants import SENIORITY_POLICY_VERSION  # noqa: E402

RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v2"
OUT_PATH = REPO_ROOT / "ml" / "data" / "processed" / "seniority_synthetic_v2.jsonl"


def _pseudo_key(raw_id: str) -> str:
    return sha256(f"synthetic-v2:{raw_id}".encode("utf-8")).hexdigest()[:32]


def main() -> None:
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No resumes found in {RAW_DIR} — run generate_resumes_v2.py first.")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    label_mismatches = 0
    for fp in files:
        row = json.loads(fp.read_text(encoding="utf-8"))
        resume_data = row["resume_data"]
        language = row.get("language", "pt-BR")
        sections = resume_to_text(resume_data, language=language)
        rs = extract_resume_signals(resume_data, sections, language=language)

        base_label, base_conf, _ev = rule_based_seniority(rs)
        rule_label, _veto_ev = clamp_seniority_vetoes(base_label, rs)
        intended_label = row["intended_seniority"]
        if rule_label != intended_label:
            label_mismatches += 1

        record = {
            "schema_version": "1.1",
            "dataset_kind": "seniority",
            "analysis_key": _pseudo_key(row["id"]),
            "resume_key": _pseudo_key(row["id"] + ":resume"),
            "user_key": _pseudo_key("synthetic-generator"),
            "created_at": now,
            "language": language,
            "signals": asdict(rs),
            "labels": {
                "seniority_label": intended_label,
                "rule_label": rule_label,
                "ml_label": None,
                "confidence": "high",
                "source": "review",
                "policy_version": SENIORITY_POLICY_VERSION,
                "reviewed": True,
            },
            "targets": {
                "overall_score": None,
                "task_scores": {"quality": row.get("quality_score")},
                "completeness_score": rs.completeness_score,
                "completeness_level": rs.completeness_level,
            },
            "gating_reasons": [],
            "insufficient_data": rs.insufficient_data,
            "meta": {
                "seniority_ml_status": "",
                "provider": "synthetic_v2",
                "model_version": "",
                "dataset_version": "synthetic_v2",
                "label_source": "synthetic_authored",
                "policy_version": SENIORITY_POLICY_VERSION,
                "domain": row.get("domain"),
                "title_mismatch": row.get("title_mismatch"),
                "total_months_design": row.get("total_months_design"),
            },
        }
        rows.append(record)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter

    dist = Counter(r["labels"]["seniority_label"] for r in rows)
    print(f"Wrote {len(rows)} records -> {OUT_PATH}")
    print("Label distribution (intended/authored):", dict(dist))
    print(
        f"rule_based_seniority (heuristic) agrees with authored label in "
        f"{len(rows) - label_mismatches}/{len(rows)} cases "
        f"({100 * (len(rows) - label_mismatches) / len(rows):.1f}%) — "
        f"the rest is exactly the signal the ML model has to learn beyond the heuristic."
    )


if __name__ == "__main__":
    main()
