#!/usr/bin/env python3
"""
Export JSONL com ``--label-source prefer-review`` e treina modelo em diretórios separados.

Pré-requisito: reviews aplicadas via ``apply_target_fit_reviews_from_csv``.

  python ml/scripts/run_target_fit_pipeline_reviewed.py

Saídas:
  ml/data/processed/target_fit_from_db_prefer_review.jsonl
  ml/training/reports/target_fit_dataset_report_reviewed.md
  ml/training/reports/target_fit_eval_reviewed.md
  ml/models/target_fit_v2_reviewed/metadata.json
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    root = _repo_root()
    py = sys.executable
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    backend = root / "backend"
    out_abs = (root / "ml/data/processed/target_fit_from_db_prefer_review.jsonl").resolve()
    out_rel = os.path.relpath(out_abs, backend.resolve())
    rc = subprocess.run(
        [
            py,
            str(backend / "manage.py"),
            "export_target_fit_dataset",
            "--out",
            out_rel,
            "--limit",
            "50000",
            "--since",
            "3650d",
            "--label-source",
            "prefer-review",
        ],
        cwd=str(backend),
        env=env,
    )
    if rc.returncode:
        return int(rc.returncode)
    pipeline = [
        py,
        str(root / "ml/scripts/run_target_fit_pipeline.py"),
        "--skip-export",
        "--in-jsonl",
        "ml/data/processed/target_fit_from_db_prefer_review.jsonl",
        "--split_dir",
        "ml/data/splits/target_fit_reviewed_v1",
        "--model_dir",
        "ml/models/target_fit_v2_reviewed",
        "--dataset-report",
        "ml/training/reports/target_fit_dataset_report_reviewed.md",
        "--eval-report",
        "ml/training/reports/target_fit_eval_reviewed.md",
    ]
    r2 = subprocess.run(pipeline, cwd=str(root), env=env)
    return int(r2.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
