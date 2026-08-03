"""
Convert ml/data/raw/resumes_v2/*.json into the text-classification JSONL format
expected by ml/training/train.py (labels.seniority + resume_text), using the
REAL production resume_to_text_sanitized (same text the live text_seniority
predictor receives at inference time).

Output: ml/data/processed/seniority_text_synthetic_v2.jsonl
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1].parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.analysis.application.inference.text_sanitizer import resume_to_text_sanitized  # noqa: E402

RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v2"
OUT_PATH = REPO_ROOT / "ml" / "data" / "processed" / "seniority_text_synthetic_v2.jsonl"


def main() -> None:
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No resumes found in {RAW_DIR} — run generate_resumes_v2.py first.")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for fp in files:
        row = json.loads(fp.read_text(encoding="utf-8"))
        resume_data = row["resume_data"]
        text = resume_to_text_sanitized(resume_data)
        rows.append(
            {
                "id": row["id"],
                "resume_id": row["id"],
                "resume_key": row["id"],
                "language": row.get("language", "pt-BR"),
                "resume_text": text,
                "labels": {
                    "seniority": row["intended_seniority"],
                    "quality_score": row.get("quality_score"),
                },
            }
        )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter

    dist = Counter(r["labels"]["seniority"] for r in rows)
    print(f"Wrote {len(rows)} records -> {OUT_PATH}")
    print("Label distribution:", dict(dist))


if __name__ == "__main__":
    main()
