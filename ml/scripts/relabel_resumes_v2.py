"""
Re-apply the (corrected) holistic labeling function to the already-generated
ml/data/raw/resumes_v2/*.json files, without regenerating resume content —
only intended_seniority is recomputed, using the real signals from the actual
production extract_resume_signals.
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

from apps.analysis.application.inference.resume_mapper import resume_to_text  # noqa: E402
from apps.analysis.application.inference.signals.resume_signals import extract_resume_signals  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_resumes_v2 import _holistic_seniority_label  # noqa: E402

RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v2"


def main() -> None:
    changed = 0
    total = 0
    from collections import Counter

    dist = Counter()
    for fp in sorted(RAW_DIR.glob("*.json")):
        if fp.name == "index.jsonl":
            continue
        row = json.loads(fp.read_text(encoding="utf-8"))
        total += 1
        sections = resume_to_text(row["resume_data"], language=row.get("language", "pt-BR"))
        rs = extract_resume_signals(row["resume_data"], sections, language=row.get("language", "pt-BR"))
        new_label = _holistic_seniority_label(
            rs.total_months_experience, rs.experiences_count, rs.bullets_count, rs.has_leadership_terms
        )
        if new_label != row["intended_seniority"]:
            print(f"{fp.name}: {row['intended_seniority']} -> {new_label} "
                  f"(months={rs.total_months_experience}, exp={rs.experiences_count}, "
                  f"bullets={rs.bullets_count}, leadership={rs.has_leadership_terms})")
            row["intended_seniority"] = new_label
            fp.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            changed += 1
        dist[new_label] += 1

    print(f"\nRelabeled {changed}/{total} resumes.")
    print("New distribution:", dict(dist))


if __name__ == "__main__":
    main()
