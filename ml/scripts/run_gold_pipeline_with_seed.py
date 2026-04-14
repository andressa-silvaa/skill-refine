#!/usr/bin/env python3
"""
End-to-end: optional seed + batch analysis + export v1.1 + ML pipeline + A/B + dataset_evolution.md.

From repository root:

  python ml/scripts/run_gold_pipeline_with_seed.py --user-email dev@local.test --seed-count 200 --batch-limit 200 --sync

Use --sync when Celery is not running (runs analysis worker inline).

Production (Celery workers up): omit --sync and keep --concurrency modest.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> int:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd, env=env or os.environ.copy())
    return int(r.returncode)


def main() -> int:
    root = _root()
    backend = root / "backend"
    py = sys.executable
    manage = str(backend / "manage.py")

    ap = argparse.ArgumentParser()
    ap.add_argument("--user-email", default="dev@local.seed.invalid")
    ap.add_argument("--seed-count", type=int, default=0, help="0 = skip seed_resumes")
    ap.add_argument("--seed-base", type=int, default=42)
    ap.add_argument("--profiles", default="balanced")
    ap.add_argument("--skip-seed", action="store_true")
    ap.add_argument("--skip-batch", action="store_true")
    ap.add_argument("--batch-limit", type=int, default=500)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--sleep-ms", type=int, default=30)
    ap.add_argument("--sync", action="store_true", help="Inline analysis worker (no Celery).")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--export-limit", type=int, default=5000)
    ap.add_argument("--since", default="180d")
    ap.add_argument("--resume-tag", default="seed_synthetic")
    args = ap.parse_args()

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if not args.skip_seed and args.seed_count > 0:
        rc = _run(
            [
                py,
                manage,
                "seed_resumes",
                "--user-email",
                args.user_email,
                "--count",
                str(args.seed_count),
                "--seed",
                str(args.seed_base),
                "--profiles",
                args.profiles,
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

    if not args.skip_batch:
        batch_cmd = [
            py,
            manage,
            "batch_run_analysis",
            "--user-email",
            args.user_email,
            "--limit",
            str(args.batch_limit),
            "--concurrency",
            str(args.concurrency),
            "--sleep-ms",
            str(args.sleep_ms),
            "--resume-tag",
            args.resume_tag,
        ]
        if args.only_missing:
            batch_cmd.append("--only-missing")
        if args.sync:
            batch_cmd.append("--sync")
        rc = _run(batch_cmd, cwd=backend, env=env)
        if rc:
            return rc

    rc = _run(
        [
            py,
            manage,
            "export_seniority_dataset",
            "--out",
            str(root / "ml/data/processed/seniority_from_db.jsonl"),
            "--schema-version",
            "1.1",
            "--limit",
            str(args.export_limit),
            "--since",
            args.since,
        ],
        cwd=backend,
        env=env,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/validate_dataset.py"),
            "--in",
            str(root / "ml/data/processed/seniority_from_db.jsonl"),
            "--report",
            str(root / "ml/training/reports/dataset_report.md"),
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/scripts/run_seniority_pipeline.py"),
            "--skip-export",
            "--since",
            args.since,
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            manage,
            "export_low_confidence_cases",
            "--out",
            str(root / "ml/data/processed/low_confidence.jsonl"),
            "--limit",
            "2000",
            "--schema-version",
            "1.1",
        ],
        cwd=backend,
        env=env,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/ab_compare_low_confidence.py"),
            "--in_jsonl",
            str(root / "ml/data/processed/low_confidence.jsonl"),
            "--model_dir",
            str(root / "ml/models/seniority_signals_v1"),
            "--out_md",
            str(root / "ml/training/reports/ab_low_confidence_report.md"),
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/report_dataset_evolution.py"),
            "--jsonl",
            str(root / "ml/data/processed/seniority_from_db.jsonl"),
            "--split_meta",
            str(root / "ml/data/splits/seniority_latest/split_meta.json"),
            "--metrics_json",
            str(root / "ml/models/seniority_signals_v1/test_metrics.json"),
            "--eval_md",
            str(root / "ml/training/reports/eval_seniority.md"),
            "--ab_md",
            str(root / "ml/training/reports/ab_low_confidence_report.md"),
            "--out",
            str(root / "ml/training/reports/dataset_evolution.md"),
        ],
        cwd=root,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
