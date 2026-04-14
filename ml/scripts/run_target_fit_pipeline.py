#!/usr/bin/env python3
"""
One-shot target-fit pipeline: export → validate → split → train → eval → export metadata.

Requires DB for export (skip with --skip-export and an existing JSONL).

  python ml/scripts/run_target_fit_pipeline.py
  python ml/scripts/run_target_fit_pipeline.py --skip-export --continue-on-validate-warnings
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
    ap.add_argument("--skip-export", action="store_true")
    ap.add_argument("--since", default="365d")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--processed", default="ml/data/processed/target_fit_from_db.jsonl")
    ap.add_argument(
        "--in-jsonl",
        default="",
        help="Alias: output/input JSONL path (overrides --processed when set).",
    )
    ap.add_argument("--split_dir", default="ml/data/splits/target_fit_v1")
    ap.add_argument("--model_dir", default="ml/models/target_fit_v1")
    ap.add_argument(
        "--label-source",
        default="policy",
        choices=("policy", "review", "prefer-review"),
        help="Passed to export_target_fit_dataset (ignored when --skip-export).",
    )
    ap.add_argument(
        "--dataset-report",
        default="",
        help="Path for validate_target_fit_dataset.md (default: ml/training/reports/target_fit_dataset_report.md).",
    )
    ap.add_argument(
        "--eval-report",
        default="",
        help="Path for eval markdown (default: ml/training/reports/target_fit_eval.md).",
    )
    ap.add_argument(
        "--min-rows",
        type=int,
        default=0,
        help="After export, fail with code 2 if JSONL has fewer non-empty lines (0 = disabled).",
    )
    ap.add_argument("--continue-on-validate-warnings", action="store_true")
    args = ap.parse_args()

    backend = root / "backend"
    py = sys.executable
    processed_rel = (args.in_jsonl or args.processed).strip() or args.processed
    processed = root / processed_rel
    split_dir = root / args.split_dir
    model_dir = root / args.model_dir
    reports = root / "ml" / "training" / "reports"
    dataset_report = Path(args.dataset_report) if args.dataset_report.strip() else reports / "target_fit_dataset_report.md"
    if not dataset_report.is_absolute():
        dataset_report = root / dataset_report
    eval_md = Path(args.eval_report) if args.eval_report.strip() else reports / "target_fit_eval.md"
    if not eval_md.is_absolute():
        eval_md = root / eval_md
    metrics_json = model_dir / "test_metrics.json"
    split_meta = split_dir / "split_meta.json"

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if not args.skip_export:
        out_for_manage = os.path.relpath(processed.resolve(), backend.resolve())
        rc = _run(
            [
                py,
                str(backend / "manage.py"),
                "export_target_fit_dataset",
                "--out",
                out_for_manage,
                "--limit",
                str(args.limit),
                "--since",
                args.since,
                "--label-source",
                str(args.label_source),
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

    if args.min_rows > 0:
        n = 0
        if processed.is_file():
            with processed.open(encoding="utf-8") as f:
                n = sum(1 for line in f if line.strip())
        if n < args.min_rows:
            print(
                f"ERROR: dataset has {n} rows, need >= {args.min_rows} ({processed})",
                file=sys.stderr,
            )
            return 2

    rc = _run(
        [
            py,
            str(root / "ml/training/src/validate_target_fit_dataset.py"),
            "--in",
            str(processed),
            "--report",
            str(dataset_report.resolve()),
        ],
        cwd=root,
    )
    if rc != 0:
        if args.continue_on_validate_warnings:
            print("Warning: validate_target_fit_dataset reported issues; continuing.", file=sys.stderr)
        else:
            return rc

    rc = _run(
        [
            py,
            str(root / "ml/training/src/split_target_fit_dataset.py"),
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
            str(root / "ml/training/src/train_target_fit.py"),
            "--train_jsonl",
            str(split_dir / "train.jsonl"),
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
            str(root / "ml/training/src/eval_target_fit.py"),
            "--model_dir",
            str(model_dir),
            "--test_jsonl",
            str(split_dir / "test.jsonl"),
            "--report",
            str(eval_md.resolve()),
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
            str(root / "ml/training/src/export_target_fit_sklearn_model.py"),
            "--model_dir",
            str(model_dir),
            "--split_meta",
            str(split_meta),
            "--test_metrics_json",
            str(metrics_json),
        ],
        cwd=root,
    )
    if rc:
        return rc

    print("Done. Model:", model_dir)
    print("Reports:")
    print(" ", dataset_report.resolve())
    print(" ", eval_md.resolve())
    print(" ", (model_dir / "metadata.json").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
