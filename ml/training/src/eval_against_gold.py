#!/usr/bin/env python3
"""
MAE/RMSE target fit vs gold + taxa de casos absurdos (sem PII).

  $env:PYTHONPATH="backend\src"
  $env:DJANGO_SETTINGS_MODULE="config.settings"
  python ml/training/src/eval_against_gold.py --user-email dev@local.seed.invalid
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BACKEND_SRC = REPO / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.accounts.infrastructure.models import User  # noqa: E402
from apps.analysis.models import AnalysisStatus, ResumeAnalysis  # noqa: E402


def _int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-email", required=True)
    ap.add_argument("--out", default="ml/training/reports/gold_eval.md")
    args = ap.parse_args()

    user = User.objects.filter(email=args.user_email.strip(), deleted_at__isnull=True).first()
    if user is None:
        print("User not found", file=sys.stderr)
        return 2

    qs = ResumeAnalysis.objects.filter(user_id=user.id, status=AnalysisStatus.DONE).order_by("-created_at")

    fit_rows: list[tuple[int, int]] = []
    absurd_tf = 0
    absurd_sen = 0
    absurd_fit_n = 0
    seniority_rows: list[tuple[str, str]] = []

    for a in qs.iterator(chunk_size=200):
        pj = a.payload_json or {}
        gold = pj.get("targetFitGoldScore")
        if gold is not None:
            try:
                g = int(float(gold))
            except (TypeError, ValueError):
                continue
            pred = _int(pj.get("targetFitFinalScore")) or _int(pj.get("targetFitScore"))
            if pred is None:
                continue
            fit_rows.append((pred, g))
            cs = pj.get("careerSwitch") if isinstance(pj.get("careerSwitch"), dict) else {}
            sem = (pj.get("targetFitEvidence") or {}).get("semanticEvidence") if isinstance(pj.get("targetFitEvidence"), dict) else {}
            kws = sem.get("keywords") if isinstance(sem, dict) else None
            has_sem = isinstance(kws, list) and len(kws) > 0
            if bool(cs.get("detected")) and pred > 70 and not has_sem:
                absurd_tf += 1
            absurd_fit_n += 1

        rev_s = (a.seniority_review_label or "").strip().lower()
        if rev_s:
            pred_s = (a.seniority_final_label or pj.get("seniorityClass") or "").strip().lower()
            seniority_rows.append((pred_s, rev_s))

        insuf = bool(pj.get("insufficientData"))
        sen = (a.seniority_final_label or pj.get("seniorityClass") or "").strip().lower()
        if insuf and sen == "senior":
            absurd_sen += 1

    lines = [
        "# Avaliação vs gold (revisão humana)",
        "",
        f"Usuário: `{args.user_email}`",
        "",
        "## Target fit (payload `targetFitGoldScore`)",
        "",
    ]

    if fit_rows:
        err = [abs(p - g) for p, g in fit_rows]
        mae = sum(err) / len(err)
        rmse = math.sqrt(sum(e * e for e in err) / len(err))
        lines.extend(
            [
                f"- N: **{len(fit_rows)}**",
                f"- MAE: **{mae:.2f}**",
                f"- RMSE: **{rmse:.2f}**",
                f"- Absurdos (career_switch + pred>70 + sem semanticEvidence): **{absurd_tf}** / {absurd_fit_n}",
                "",
            ]
        )
    else:
        lines.extend(["_Nenhuma análise com `targetFitGoldScore` encontrada._", ""])

    lines.extend(["## Senioridade (campo `seniority_review_label`)", ""])
    if seniority_rows:
        match = sum(1 for p, g in seniority_rows if p == g)
        lines.append(f"- N: **{len(seniority_rows)}**; acurácia exata: **{match}/{len(seniority_rows)}**")
    else:
        lines.append("_Nenhuma revisão de senioridade aplicada._")
    lines.extend(["", f"- Absurdos (insufficientData + senior): **{absurd_sen}** (varredura em análises do usuário)", ""])

    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", out_p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
