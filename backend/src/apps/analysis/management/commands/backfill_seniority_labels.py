"""
Backfill persisted seniority rule/final labels for DONE analyses (policy v1.0).

Does not overwrite rows that already have a human ``seniority_review_label``.

  python manage.py backfill_seniority_labels [--dry-run]
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.analysis.application.inference.resume_mapper import resume_to_text
from apps.analysis.application.inference.signals import extract_resume_signals
from apps.analysis.application.inference.seniority.rule_based import rule_based_seniority
from apps.analysis.application.seniority_persist import (
    SENIORITY_POLICY_VERSION,
    build_seniority_evidence_json,
)
from apps.analysis.application.worker import _get_user_language
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.interfaces.api.payloads import resume_detail_payload

_PREFETCH = (
    "resume__resumecontact",
    "resume__resumeexperience_set__resumeexperiencebullet_set",
    "resume__resumeeducation_set",
    "resume__resumeskill_set",
    "resume__resumelanguage_set",
)


class Command(BaseCommand):
    help = "Backfill seniority_rule_label / seniority_final_label from structural policy (skip reviewed rows)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print counts only; do not write.",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        qs = (
            ResumeAnalysis.objects.filter(status=AnalysisStatus.DONE)
            .select_related("resume", "user")
            .prefetch_related(*_PREFETCH)
            .order_by("created_at")
        )
        updated = 0
        skipped_review = 0
        for analysis in qs.iterator(chunk_size=40):
            if (analysis.seniority_review_label or "").strip():
                skipped_review += 1
                continue
            resume_data = resume_detail_payload(analysis.resume)
            lang = _get_user_language(str(analysis.user_id))
            sections = resume_to_text(resume_data, language=lang)
            rs = extract_resume_signals(resume_data, sections, language=lang)
            rule_label, rule_conf, rule_ev = rule_based_seniority(rs)
            conf = rule_conf if rule_conf in ("low", "medium", "high") else "low"
            ev_json = build_seniority_evidence_json(rs, rule_ev)
            if not dry:
                analysis.seniority_rule_label = rule_label
                analysis.seniority_final_label = rule_label
                analysis.seniority_label_source = "rule"
                analysis.seniority_policy_version = SENIORITY_POLICY_VERSION
                analysis.seniority_confidence = conf
                analysis.seniority_evidence = ev_json
                analysis.save(
                    update_fields=[
                        "seniority_rule_label",
                        "seniority_final_label",
                        "seniority_label_source",
                        "seniority_policy_version",
                        "seniority_confidence",
                        "seniority_evidence",
                        "updated_at",
                    ]
                )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {updated} row(s); skipped {skipped_review} with review label. dry_run={dry}"
            )
        )
