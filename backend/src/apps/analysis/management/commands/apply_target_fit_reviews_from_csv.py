"""
Aplica scores de revisão humana (CSV do Excel) às análises DONE.

  python manage.py apply_target_fit_reviews_from_csv --csv ..\\ml\\data\\processed\\gold_review_candidates_ptbr.csv

Colunas (delimitador ``;``):
  - analysis_key (obrigatório)
  - review_fit_score OU review_target_fit_score (0–100)
  - review_seniority_label opcional: intern|junior|mid|senior → ``seniority_review_label``
  - review_note opcional
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.analysis.application.internal_review import resolve_analysis_by_pseudo_key, resolve_review_hash_salt
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.audit.infrastructure.logger import OrmAuditLogger

logger = logging.getLogger(__name__)

_VALID_SENIORITY = frozenset({"intern", "junior", "mid", "senior"})


class Command(BaseCommand):
    help = "Apply target fit human review scores from a semicolon CSV (analysis_key → payload_json)."

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=str, required=True, help="Path to CSV (; delimiter, UTF-8 BOM ok).")

    def handle(self, *args, **options):
        path = Path(options["csv"]).expanduser().resolve()
        if not path.is_file():
            raise CommandError(f"CSV not found: {path}")

        salt = resolve_review_hash_salt()
        applied = 0
        skipped = 0
        audit = OrmAuditLogger()

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
                key = (row.get("analysis_key") or row.get("analysisKey") or "").strip().lower()
                raw_score = (
                    row.get("review_fit_score")
                    or row.get("reviewFitScore")
                    or row.get("review_target_fit_score")
                    or row.get("reviewTargetFitScore")
                    or ""
                )
                raw_score = str(raw_score).strip()
                raw_sen = (
                    row.get("review_seniority_label")
                    or row.get("reviewSeniorityLabel")
                    or ""
                )
                raw_sen = str(raw_sen).strip().lower()
                if not key:
                    skipped += 1
                    continue
                if not raw_score and not raw_sen:
                    skipped += 1
                    continue

                score = None
                if raw_score:
                    try:
                        score = int(float(raw_score.replace(",", ".")))
                    except ValueError:
                        skipped += 1
                        continue
                    score = max(0, min(100, score))

                sen_lab = raw_sen if raw_sen in _VALID_SENIORITY else ""

                analysis = resolve_analysis_by_pseudo_key(key, salt=salt)
                if analysis is None or analysis.status != AnalysisStatus.DONE:
                    self.stdout.write(self.style.WARNING(f"No DONE analysis for key …{key[-8:]}"))
                    skipped += 1
                    continue

                pj = dict(analysis.payload_json or {})
                update_fields = ["payload_json", "updated_at"]
                if score is not None:
                    pj["targetFitGoldScore"] = score
                    pj["targetFitLabelSource"] = "review"
                note = (row.get("review_note") or row.get("reviewNote") or "").strip()[:2000]
                if note:
                    pj["targetFitReviewNote"] = note
                analysis.payload_json = pj
                if sen_lab:
                    analysis.seniority_review_label = sen_lab
                    update_fields.extend(["seniority_review_label"])
                analysis.save(update_fields=update_fields)
                applied += 1

                try:
                    audit.log(
                        action="analysis.internal.review.target_fit_set",
                        actor_user_id=None,
                        subject_user_id=str(analysis.user_id),
                        ip=None,
                        user_agent="cli:apply_target_fit_reviews_from_csv",
                        metadata={
                            "analysis_key_suffix": key[-8:],
                            "fit_score": score,
                            "seniority_review": bool(sen_lab),
                            "has_note": bool(note),
                        },
                    )
                except Exception:
                    logger.exception("audit log failed (ignored)")

        self.stdout.write(self.style.SUCCESS(f"Applied {applied} review(s); skipped {skipped} row(s)."))
