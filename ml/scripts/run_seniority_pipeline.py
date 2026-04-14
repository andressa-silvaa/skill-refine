#!/usr/bin/env python3
"""
One-shot seniority signals pipeline (export → validate → split → train → eval → summarize → export metadata).

Run from **repository root** with DB available and Django configured:

  python ml/scripts/run_seniority_pipeline.py

Options:

  python ml/scripts/run_seniority_pipeline.py --skip-export --since 180d --limit 8000
  python ml/scripts/run_seniority_pipeline.py --with-tuning
  python ml/scripts/run_seniority_pipeline.py --continue-on-validate-warnings
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> int:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd or _repo_root(), env=env or os.environ.copy())
    return int(r.returncode)


def main() -> int:
    root = _repo_root()
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-export", action="store_true", help="Reuse existing processed JSONL.")
    ap.add_argument("--since", default="90d", help="Passed to export_seniority_dataset --since (e.g. 90d, 2025-01-01).")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--processed", default="ml/data/processed/seniority_from_db.jsonl")
    ap.add_argument("--split_dir", default="ml/data/splits/seniority_latest")
    ap.add_argument("--model_dir", default="ml/models/seniority_signals_v1")
    ap.add_argument("--continue-on-validate-warnings", action="store_true")
    ap.add_argument("--with-tuning", action="store_true", help="Run tune_thresholds + embed inference_thresholds in metadata.")
    args = ap.parse_args()

    backend = root / "backend"
    src = backend / "src"
    py = sys.executable
    processed = root / args.processed
    split_dir = root / args.split_dir
    model_dir = root / args.model_dir
    reports = root / "ml" / "training" / "reports"
    dataset_report = reports / "dataset_report.md"
    eval_md = reports / "eval_seniority.md"
    summary_md = reports / "seniority_signals_v1_summary.md"
    metrics_json = model_dir / "test_metrics.json"
    split_meta = split_dir / "split_meta.json"
    tune_md = reports / "threshold_tuning.md"
    tune_json = reports / "threshold_recommended.json"

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if not args.skip_export:
        out_for_manage = os.path.relpath(processed.resolve(), backend.resolve())
        rc = _run(
            [
                py,
                str(backend / "manage.py"),
                "export_seniority_dataset",
                "--out",
                out_for_manage,
                "--limit",
                str(args.limit),
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
            str(processed),
            "--report",
            str(dataset_report),
        ],
        cwd=root,
    )
    if rc != 0:
        if args.continue_on_validate_warnings:
            print("Warning: validate_dataset reported issues; continuing.", file=sys.stderr)
        else:
            print("validate_dataset reported issues; fix dataset or pass --continue-on-validate-warnings", file=sys.stderr)
            return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/split_dataset.py"),
            "--in",
            str(processed),
            "--out_dir",
            str(split_dir),
            "--seed",
            "42",
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/train_seniority.py"),
            "--split_dir",
            str(split_dir),
            "--out_dir",
            str(model_dir),
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/eval_seniority.py"),
            "--model_dir",
            str(model_dir),
            "--split_dir",
            str(split_dir),
            "--out",
            str(eval_md),
            "--metrics_json",
            str(metrics_json),
        ],
        cwd=root,
    )
    if rc:
        return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/summarize_seniority_run.py"),
            "--dataset_jsonl",
            str(processed),
            "--split_meta",
            str(split_meta),
            "--metrics_json",
            str(metrics_json),
            "--eval_md",
            str(eval_md),
            "--dataset_report",
            str(dataset_report),
            "--out",
            str(summary_md),
        ],
        cwd=root,
    )
    if rc:
        return rc

    extra_export: list[str] = []
    if args.with_tuning:
        rc = _run(
            [
                py,
                str(root / "ml/training/src/tune_thresholds.py"),
                "--model_dir",
                str(model_dir),
                "--split_dir",
                str(split_dir),
                "--out_md",
                str(tune_md),
                "--out_json",
                str(tune_json),
            ],
            cwd=root,
        )
        if rc:
            return rc
        extra_export.extend(["--inference_thresholds_json", str(tune_json)])

    rc = _run(
        [
            py,
            str(root / "ml/training/src/export_seniority_sklearn_model.py"),
            "--model_dir",
            str(model_dir),
            "--split_meta",
            str(split_meta),
            "--test_metrics_json",
            str(metrics_json),
            *extra_export,
        ],
        cwd=root,
    )
    if rc:
        return rc

    print("\nDone. Expected artifacts:", flush=True)
    for p in (dataset_report, split_meta, eval_md, model_dir / "metadata.json", summary_md):
        print(f"  - {p.relative_to(root)}", flush=True)
    if args.with_tuning:
        print(f"  - {tune_md.relative_to(root)}", flush=True)
        print(f"  - {tune_json.relative_to(root)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
