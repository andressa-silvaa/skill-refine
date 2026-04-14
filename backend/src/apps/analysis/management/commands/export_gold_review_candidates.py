"""
Exporta até N análises DONE para revisão humana (CSV ; UTF-8 BOM), sem texto de currículo.

Prioridade: career switch, domínios divergentes, scores em faixas intermediárias, depois recentes.

  python manage.py export_gold_review_candidates --user-email dev@local.seed.invalid --limit 50 --out ..\\ml\\data\\processed\\gold_review_candidates_ptbr.csv
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.infrastructure.models import User
from apps.analysis.application.internal_review import pseudo_key, resolve_review_hash_salt
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeTag


class Command(BaseCommand):
    help = "Export gold review candidate rows (hashed keys + scores, no resume text)."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", type=str, required=True, dest="user_email")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--out", type=str, required=True)
        parser.add_argument(
            "--prefer-controlled-tag",
            action="store_true",
            dest="prefer_controlled",
            help="Prioritize resumes tagged seed_controlled.",
        )

    def handle(self, *args, **options):
        email = (options.get("user_email") or "").strip()
        limit = max(1, min(500, int(options.get("limit") or 50)))
        out_path = Path(options["out"]).expanduser().resolve()
        prefer = bool(options.get("prefer_controlled"))

        user = User.objects.filter(email=email, deleted_at__isnull=True).first()
        if user is None:
            raise CommandError(f"User not found: {email}")

        salt = resolve_review_hash_salt()
        controlled_ids: set[str] = set()
        if prefer:
            controlled_ids = set(
                str(x)
                for x in ResumeTag.objects.filter(label="seed_controlled")
                .values_list("resume_id", flat=True)
                .distinct()
            )

        qs = (
            ResumeAnalysis.objects.filter(user_id=user.id, status=AnalysisStatus.DONE)
            .select_related("resume")
            .order_by("-created_at")
        )

        scored: list[tuple[int, ResumeAnalysis]] = []

        def score_row(a: ResumeAnalysis) -> int:
            pj = a.payload_json or {}
            pr = 0
            rid = str(a.resume_id)
            if rid in controlled_ids:
                pr += 500
            cs = pj.get("careerSwitch") if isinstance(pj.get("careerSwitch"), dict) else {}
            if bool(cs.get("detected")):
                pr += 200
            rd = str((pj.get("resumeDomain") or {}).get("category") or "")
            td = str((pj.get("targetRoleDomain") or {}).get("category") or "")
            if rd and td and rd != "general" and td != "general" and rd != td:
                pr += 150
            tf = pj.get("targetFitFinalScore")
            if tf is None:
                tf = pj.get("targetFitScore")
            try:
                tfn = int(float(tf))
            except (TypeError, ValueError):
                tfn = 50
            if 40 <= tfn <= 58:
                pr += 80
            if 59 <= tfn <= 72:
                pr += 60
            return pr

        for a in qs.iterator(chunk_size=100):
            scored.append((score_row(a), a))

        scored.sort(key=lambda x: (-x[0], -x[1].created_at.timestamp()))
        picked = [a for _, a in scored[:limit]]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "analysis_key",
            "resume_key",
            "target_position",
            "domain_resume",
            "domain_target",
            "overall_score",
            "target_fit_final_score",
            "seniority_final_label",
            "career_switch_detected",
            "review_target_fit_score",
            "review_seniority_label",
            "review_note",
        ]
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            w.writeheader()
            for a in picked:
                pj = a.payload_json or {}
                resume = a.resume
                tp = (resume.target_position or "")[:200] if resume else ""
                rd = str((pj.get("resumeDomain") or {}).get("category") or "")
                td = str((pj.get("targetRoleDomain") or {}).get("category") or "")
                cs = pj.get("careerSwitch") if isinstance(pj.get("careerSwitch"), dict) else {}
                tff = pj.get("targetFitFinalScore")
                if tff is None:
                    tff = pj.get("targetFitScore")
                w.writerow(
                    {
                        "analysis_key": pseudo_key(raw_id=str(a.id), salt=salt),
                        "resume_key": pseudo_key(raw_id=str(a.resume_id), salt=salt),
                        "target_position": tp,
                        "domain_resume": rd,
                        "domain_target": td,
                        "overall_score": a.score if a.score is not None else "",
                        "target_fit_final_score": tff if tff is not None else "",
                        "seniority_final_label": (a.seniority_final_label or pj.get("seniorityClass") or "").strip(),
                        "career_switch_detected": "1" if bool(cs.get("detected")) else "0",
                        "review_target_fit_score": "",
                        "review_seniority_label": "",
                        "review_note": "",
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(picked)} row(s) → {out_path}"))
