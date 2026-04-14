#!/usr/bin/env python3
"""
QA orquestrador (sem UI): migrate → seed multi-domínio → batch análises → pipeline target fit → CSV de revisão.

PowerShell (raiz do repo):

  python ml/scripts/run_target_fit_qa_no_ui.py --smoke
  python ml/scripts/run_target_fit_qa_no_ui.py

Falha se ``validate_target_fit_dataset`` retornar código != 0 (não use --continue-on-validate-warnings aqui).
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


def _django_count_done(*, user_email: str) -> int:
    root = _repo_root()
    src = root / "backend" / "src"
    sys.path.insert(0, str(src))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from apps.analysis.models import AnalysisStatus, ResumeAnalysis

    return int(
        ResumeAnalysis.objects.filter(
            user__email__iexact=user_email.strip(),
            user__deleted_at__isnull=True,
            status=AnalysisStatus.DONE,
        ).count()
    )


def main() -> int:
    root = _repo_root()
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="Seed/batch 50, min_done=10, min_rows=5, skip se já OK.")
    ap.add_argument("--user-email", default="dev@local.seed.invalid")
    ap.add_argument("--seed-count", type=int, default=1200)
    ap.add_argument("--batch-limit", type=int, default=1200)
    ap.add_argument("--min-done", type=int, default=800, help="Mínimo de ResumeAnalysis DONE para o usuário.")
    ap.add_argument("--min-dataset-rows", type=int, default=500)
    ap.add_argument("--since", default="365d")
    ap.add_argument("--export-limit", type=int, default=50000)
    ap.add_argument("--skip-migrate", action="store_true")
    ap.add_argument("--skip-seed", action="store_true")
    ap.add_argument("--skip-batch", action="store_true")
    ap.add_argument("--skip-pipeline", action="store_true")
    ap.add_argument("--skip-review-csv", action="store_true")
    ap.add_argument("--auto-scale-on-shortfall", action="store_true", help="Se min_done ou min_rows falhar, sugere 2000 e sai 3.")
    args = ap.parse_args()

    email = args.user_email.strip()
    seed_count = 50 if args.smoke else int(args.seed_count)
    batch_limit = 50 if args.smoke else int(args.batch_limit)
    min_done = 10 if args.smoke else int(args.min_done)
    min_rows = 5 if args.smoke else int(args.min_dataset_rows)

    backend = root / "backend"
    py = sys.executable
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if not args.skip_migrate:
        rc = _run([py, str(backend / "manage.py"), "migrate"], cwd=backend, env=env)
        if rc:
            return rc

    if not args.skip_seed:
        rc = _run(
            [
                py,
                str(backend / "manage.py"),
                "seed_resumes",
                "--user-email",
                email,
                "--count",
                str(seed_count),
                "--seed",
                "42",
                "--profiles",
                "balanced",
                "--with-target-positions",
                "--domain-mix",
                "balanced",
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

    if not args.skip_batch:
        rc = _run(
            [
                py,
                str(backend / "manage.py"),
                "batch_run_analysis",
                "--user-email",
                email,
                "--limit",
                str(batch_limit),
                "--concurrency",
                "10",
                "--sleep-ms",
                "50",
                "--only-missing",
                "--sync",
            ],
            cwd=backend,
            env=env,
        )
        if rc:
            return rc

    done_n = _django_count_done(user_email=email)
    print(f"ResumeAnalysis DONE (approx) for {email}: {done_n}", flush=True)
    if done_n < min_done:
        msg = f"Shortfall: need >= {min_done} DONE analyses, got {done_n}."
        if args.auto_scale_on_shortfall:
            print(f"{msg} Re-run with --seed-count 2000 --batch-limit 2000", file=sys.stderr)
            return 3
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    processed = root / "ml" / "data" / "processed" / "target_fit_from_db.jsonl"
    review_csv = root / "ml" / "data" / "processed" / "target_fit_review_candidates_ptbr.csv"

    if not args.skip_pipeline:
        rc = _run(
            [
                py,
                str(root / "ml/scripts/run_target_fit_pipeline.py"),
                "--since",
                args.since,
                "--limit",
                str(args.export_limit),
                "--min-rows",
                str(min_rows),
                "--processed",
                "ml/data/processed/target_fit_from_db.jsonl",
            ],
            cwd=root,
            env=env,
        )
        if rc:
            if rc == 2 and args.auto_scale_on_shortfall:
                print("Dataset too small. Re-run seed/batch with --seed-count 2000 --batch-limit 2000", file=sys.stderr)
                return 3
            return rc

    if not args.skip_review_csv:
        rc = _run(
            [
                py,
                str(root / "ml/training/src/build_target_fit_review_candidates.py"),
                "--in",
                str(processed),
                "--out",
                str(review_csv),
                "--limit",
                "150",
            ],
            cwd=root,
        )
        if rc:
            return rc

    print("", flush=True)
    print("=== Target Fit QA — artefatos ===", flush=True)
    print(" Dataset JSONL:", processed.resolve(), flush=True)
    print(" Dataset report:", (root / "ml/training/reports/target_fit_dataset_report.md").resolve(), flush=True)
    print(" Eval report:", (root / "ml/training/reports/target_fit_eval.md").resolve(), flush=True)
    print(" Model metadata:", (root / "ml/models/target_fit_v1/metadata.json").resolve(), flush=True)
    print(" Review CSV:", review_csv.resolve(), flush=True)
    print("", flush=True)
    print("Próximos passos (manual):", flush=True)
    print(" 1) Preencher review_fit_score no CSV; aplicar:", flush=True)
    print(f"    cd backend; python manage.py apply_target_fit_reviews_from_csv --csv ..\\ml\\data\\processed\\target_fit_review_candidates_ptbr.csv", flush=True)
    print(" 2) Pipeline reviewed:", flush=True)
    print("    python ml/scripts/run_target_fit_pipeline_reviewed.py", flush=True)
    print(" 3) Relatório TCC:", flush=True)
    print("    python ml/training/src/report_target_fit_results.py", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
