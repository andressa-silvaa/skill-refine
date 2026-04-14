#!/usr/bin/env python3
"""
Orquestra validação TCC sem UI (PowerShell / Windows).

Smoke (sem gold):
  python ml/scripts/run_ai_real_validation_no_ui.py --user-email dev@local.seed.invalid --sync --skip-gold

Completo — exporta gold; se o CSV já tiver revisões, aplica + eval automaticamente:
  python ml/scripts/run_ai_real_validation_no_ui.py --user-email dev@local.seed.invalid --sync

Forçar apply + eval:
  python ml/scripts/run_ai_real_validation_no_ui.py --user-email dev@local.seed.invalid --sync --apply-gold
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
MANAGE = BACKEND / "manage.py"
PY = sys.executable


def run(args: list[str], *, cwd: Path | None = None) -> int:
    r = subprocess.run(args, cwd=cwd or REPO)
    return int(r.returncode)


def csv_has_reviews(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open(encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";\t,")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            s1 = (row.get("review_target_fit_score") or row.get("review_fit_score") or "").strip()
            s2 = (row.get("review_seniority_label") or "").strip()
            if s1 or s2:
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-email", required=True)
    ap.add_argument("--sync", action="store_true", help="Análise síncrona (worker inline).")
    ap.add_argument("--skip-gold", action="store_true")
    ap.add_argument("--no-seed", action="store_true")
    ap.add_argument("--apply-gold", action="store_true")
    args = ap.parse_args()

    if not args.no_seed:
        rc = run([PY, str(MANAGE), "seed_controlled_resumes", "--user-email", args.user_email], cwd=BACKEND)
        if rc != 0:
            return rc

    controlled_json = REPO / "ml" / "data" / "controlled" / "controlled_resumes.json"
    dump_csv = REPO / "ml" / "training" / "reports" / "analysis_dump.csv"
    gold_csv = REPO / "ml" / "data" / "processed" / "gold_review_candidates_ptbr.csv"

    dump_args = [
        PY,
        str(REPO / "ml" / "scripts" / "run_analysis_and_dump.py"),
        "--user-email",
        args.user_email,
        "--resume-ids-file",
        str(controlled_json),
        "--out",
        str(dump_csv),
    ]
    if args.sync:
        dump_args.append("--sync")

    rc = run(dump_args, cwd=REPO)
    if rc != 0:
        return rc

    rc = run(
        [
            PY,
            str(REPO / "ml" / "training" / "src" / "analyze_dump_stats.py"),
            "--in",
            str(dump_csv),
            "--out",
            str(REPO / "ml" / "training" / "reports" / "analysis_dump_stats.md"),
        ],
        cwd=REPO,
    )
    if rc != 0:
        return rc

    rc = run(
        [
            PY,
            str(REPO / "ml" / "training" / "src" / "tune_overall_weights.py"),
            "--in",
            str(dump_csv),
        ],
        cwd=REPO,
    )
    if rc != 0:
        return rc

    next_steps = REPO / "ml" / "training" / "reports" / "VALIDATION_NEXT_STEPS.txt"

    if not args.skip_gold:
        rc = run(
            [
                PY,
                str(MANAGE),
                "export_gold_review_candidates",
                "--user-email",
                args.user_email,
                "--limit",
                "50",
                "--out",
                str(gold_csv),
                "--prefer-controlled-tag",
            ],
            cwd=BACKEND,
        )
        if rc != 0:
            return rc

        csv_arg = os.path.relpath(str(gold_csv), str(BACKEND))
        apply_eval = bool(args.apply_gold) or csv_has_reviews(gold_csv)
        if apply_eval:
            rc = run([PY, str(MANAGE), "apply_target_fit_reviews_from_csv", "--csv", csv_arg], cwd=BACKEND)
            if rc != 0:
                return rc
            rc = run(
                [PY, str(REPO / "ml" / "training" / "src" / "eval_against_gold.py"), "--user-email", args.user_email],
                cwd=REPO,
            )
            if rc != 0:
                return rc
        else:
            next_steps.write_text(
                "\n".join(
                    [
                        "1) Preencha review_target_fit_score e/ou review_seniority_label em:",
                        f"   {gold_csv}",
                        "2) cd backend",
                        "   python manage.py apply_target_fit_reviews_from_csv --csv ..\\ml\\data\\processed\\gold_review_candidates_ptbr.csv",
                        f"3) python ml/training/src/eval_against_gold.py --user-email {args.user_email}",
                        "4) python ml/training/src/build_tcc_validation_doc.py",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            print("Wrote", next_steps)

    rc = run([PY, str(REPO / "ml" / "training" / "src" / "build_tcc_validation_doc.py")], cwd=REPO)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
