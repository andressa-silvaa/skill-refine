#!/usr/bin/env python3
"""
Dispara análise para currículos controlados e grava CSV sem PII (apenas scores, labels, hashes).

  cd <repo>
  $env:PYTHONPATH="backend\src"
  $env:DJANGO_SETTINGS_MODULE="config.settings"
  python ml/scripts/run_analysis_and_dump.py --user-email dev@local.seed.invalid --resume-ids-file ml/data/controlled/controlled_resumes.json --out ml/training/reports/analysis_dump.csv --sync
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.accounts.infrastructure.models import User  # noqa: E402
from apps.analysis.application.internal_review import pseudo_key, resolve_review_hash_salt  # noqa: E402
from apps.analysis.interfaces.api.services import run_analysis  # noqa: E402
from apps.analysis.models import AnalysisStatus, ResumeAnalysis  # noqa: E402


def _wait_done(analysis_id: str, timeout_s: float = 180.0) -> ResumeAnalysis:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        a = ResumeAnalysis.objects.get(pk=analysis_id)
        if a.status == AnalysisStatus.DONE:
            return a
        if a.status == AnalysisStatus.FAILED:
            return a
        time.sleep(0.35)
    return ResumeAnalysis.objects.get(pk=analysis_id)


def _pick_int(v) -> str:
    if v is None:
        return ""
    try:
        return str(int(round(float(v))))
    except (TypeError, ValueError):
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-email", required=True)
    ap.add_argument("--resume-ids-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sync", action="store_true", help="Run worker inline (no Celery).")
    ap.add_argument("--language", default="pt-BR")
    args = ap.parse_args()

    user = User.objects.filter(email=args.user_email.strip(), deleted_at__isnull=True).first()
    if user is None:
        print("User not found:", args.user_email, file=sys.stderr)
        return 2

    path = Path(args.resume_ids_file).expanduser()
    if not path.is_file():
        print("File not found:", path, file=sys.stderr)
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if not items:
        print("No items in JSON", file=sys.stderr)
        return 2

    salt = resolve_review_hash_salt()
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario_key",
        "analysis_key",
        "resume_key",
        "status",
        "overall_score",
        "task_quality",
        "task_seniority",
        "task_target_fit",
        "task_matching",
        "seniority_final_label",
        "seniority_label_source",
        "seniority_text_confidence",
        "target_fit_provider",
        "target_fit_embedding_score",
        "target_fit_signals_score",
        "target_fit_final_score",
        "debug_quality_score",
        "debug_seniority_general_score",
        "debug_target_fit_score",
        "debug_matching_score",
        "debug_overall_mode",
        "debug_overall_formula",
    ]

    rows: list[dict[str, str]] = []

    for it in items:
        rid = str(it.get("resume_id") or "").strip()
        scenario = str(it.get("scenario_key") or "").strip()
        job_txt = it.get("job_description_text")
        job_txt = (job_txt or "").strip() if job_txt else None

        analysis, err = run_analysis(
            str(user.id),
            rid,
            job_description_text=job_txt,
            sync=bool(args.sync),
        )
        if analysis is None:
            rows.append(
                {
                    "scenario_key": scenario,
                    "analysis_key": "",
                    "resume_key": pseudo_key(raw_id=rid, salt=salt) if rid else "",
                    "status": "enqueue_failed",
                    "overall_score": "",
                    "task_quality": "",
                    "task_seniority": "",
                    "task_target_fit": "",
                    "task_matching": "",
                    "seniority_final_label": "",
                    "seniority_label_source": "",
                    "seniority_text_confidence": "",
                    "target_fit_provider": "",
                    "target_fit_embedding_score": "",
                    "target_fit_signals_score": "",
                    "target_fit_final_score": "",
                    "debug_quality_score": "",
                    "debug_seniority_general_score": "",
                    "debug_target_fit_score": "",
                    "debug_matching_score": "",
                    "debug_overall_mode": "",
                    "debug_overall_formula": "",
                }
            )
            continue

        aid = str(analysis.id)
        if not args.sync:
            analysis = _wait_done(aid)
        else:
            analysis.refresh_from_db()

        ts = analysis.task_scores or {}
        pj = analysis.payload_json or {}
        dbg = pj.get("debug") if isinstance(pj.get("debug"), dict) else {}
        br = dbg.get("scoreBreakdown") if isinstance(dbg.get("scoreBreakdown"), dict) else {}

        rows.append(
            {
                "scenario_key": scenario,
                "analysis_key": pseudo_key(raw_id=aid, salt=salt),
                "resume_key": pseudo_key(raw_id=rid, salt=salt),
                "status": str(analysis.status),
                "overall_score": _pick_int(analysis.score),
                "task_quality": _pick_int(ts.get("ats")),
                "task_seniority": _pick_int(ts.get("seniority")),
                "task_target_fit": _pick_int(ts.get("target_fit")),
                "task_matching": _pick_int(ts.get("matching")),
                "seniority_final_label": (analysis.seniority_final_label or pj.get("seniorityClass") or "").strip(),
                "seniority_label_source": (analysis.seniority_label_source or "").strip(),
                "seniority_text_confidence": (analysis.seniority_text_confidence or "").strip(),
                "target_fit_provider": str(pj.get("targetFitProvider") or "").strip(),
                "target_fit_embedding_score": _pick_int(pj.get("targetFitEmbeddingScore")),
                "target_fit_signals_score": _pick_int(pj.get("targetFitSignalsScore")),
                "target_fit_final_score": _pick_int(pj.get("targetFitFinalScore") or pj.get("targetFitScore")),
                "debug_quality_score": _pick_int(br.get("quality_score")),
                "debug_seniority_general_score": _pick_int(br.get("seniority_general_score")),
                "debug_target_fit_score": _pick_int(br.get("target_fit_score")),
                "debug_matching_score": _pick_int(br.get("matching_score")),
                "debug_overall_mode": str(br.get("overall_mode") or ""),
                "debug_overall_formula": str(br.get("overall_formula") or ""),
            }
        )

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} row(s) → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
