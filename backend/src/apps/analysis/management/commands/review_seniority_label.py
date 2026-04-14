"""
Apply a human seniority review label (same effect as POST /analysis/internal/review/seniority).

  python manage.py review_seniority_label --analysis-id <uuid> --label senior
  python manage.py review_seniority_label --analysis-key <pseudokey> --label mid
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.analysis.application.internal_review import pseudo_key, resolve_analysis_by_pseudo_key, resolve_review_hash_salt
from apps.analysis.application.seniority_persist import normalize_seniority_label
from apps.analysis.application.seniority_persist import SENIORITY_LABEL_TO_SCORE
from apps.analysis.models import AnalysisStatus, ResumeAnalysis


class Command(BaseCommand):
    help = "Set seniority_review_label + final label (internal gold standard)."

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--analysis-id", type=str, dest="analysis_id", help="Raw ResumeAnalysis UUID.")
        g.add_argument("--analysis-key", type=str, dest="analysis_key", help="32-char pseudo-key from low-confidence list.")
        parser.add_argument("--label", type=str, required=True, help="intern|junior|mid|senior")
        parser.add_argument("--note", type=str, default="", help="Optional audit note (stored in evidence).")

    def handle(self, *args, **options):
        raw_label = normalize_seniority_label(str(options["label"] or ""))
        if not raw_label:
            raise CommandError("Invalid --label (use intern|junior|mid|senior).")

        note = str(options.get("note") or "").strip()[:2000]
        analysis: ResumeAnalysis | None = None

        aid = (options.get("analysis_id") or "").strip()
        if aid:
            analysis = (
                ResumeAnalysis.objects.filter(id=aid, status=AnalysisStatus.DONE)
                .select_related("resume")
                .first()
            )
            if analysis is None:
                raise CommandError("DONE analysis not found for --analysis-id.")
        else:
            key = (options.get("analysis_key") or "").strip().lower()
            salt = resolve_review_hash_salt()
            analysis = resolve_analysis_by_pseudo_key(key, salt=salt)
            if analysis is None:
                raise CommandError("Analysis not found for --analysis-key.")

        pj = dict(analysis.payload_json or {})
        ev = pj.get("seniorityEvidence")
        ev_list = list(ev) if isinstance(ev, list) else []
        ev_list.append(
            {
                "type": "human_review",
                "label": raw_label,
                **({"note": note} if note else {}),
            }
        )
        pj["seniorityEvidence"] = ev_list[:24]
        pj["seniorityClass"] = raw_label
        pj["seniorityConfidence"] = "high"
        pj["seniorityMlStatus"] = "human_review_override"

        ts = dict(analysis.task_scores or {})
        ts["seniority"] = SENIORITY_LABEL_TO_SCORE.get(raw_label, 50)

        analysis.seniority_review_label = raw_label
        analysis.seniority_final_label = raw_label
        analysis.seniority_label_source = "review"
        analysis.seniority_confidence = "high"
        analysis.payload_json = pj
        analysis.task_scores = ts
        analysis.save(
            update_fields=[
                "seniority_review_label",
                "seniority_final_label",
                "seniority_label_source",
                "seniority_confidence",
                "payload_json",
                "task_scores",
                "updated_at",
            ]
        )

        salt = resolve_review_hash_salt()
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated analysis {analysis.id}; pseudo key={pseudo_key(raw_id=str(analysis.id), salt=salt)}"
            )
        )
