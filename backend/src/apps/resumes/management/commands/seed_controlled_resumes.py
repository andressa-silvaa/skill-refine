"""
Currículos de prova (sem PII) para validação TCC — cenários fixos.

  cd backend
  python manage.py seed_controlled_resumes --user-email dev@local.seed.invalid

Grava ml/data/controlled/controlled_resumes.json (ids + scenario_key; sem texto).
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.infrastructure.models import User, UserStatus
from apps.resumes.infrastructure.models import Resume, ResumeContact, ResumeStatus, ResumeTag
from .controlled_scenarios import build_scenarios
from apps.resumes.interfaces.api.service_utils import (
    replace_educations,
    replace_experiences,
    replace_languages,
    replace_skills,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]



class Command(BaseCommand):
    help = "Create 16 controlled test resumes (no PII) and write ml/data/controlled/controlled_resumes.json."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", type=str, required=True, dest="user_email")
        parser.add_argument(
            "--out",
            type=str,
            default="",
            help="Override output JSON path (default: <repo>/ml/data/controlled/controlled_resumes.json).",
        )

    def handle(self, *args, **options):
        email = (options.get("user_email") or "").strip()
        if not email:
            raise CommandError("--user-email is required.")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"full_name": "Usuário Validação TCC", "status": UserStatus.ACTIVE},
        )
        if created:
            self.stdout.write(self.style.WARNING(f"Created user {user.email}"))

        out_path = (options.get("out") or "").strip()
        if out_path:
            json_path = Path(out_path).expanduser().resolve()
        else:
            json_path = _repo_root() / "ml" / "data" / "controlled" / "controlled_resumes.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)

        scenarios = build_scenarios()

        items: list[dict] = []
        tag_label = "seed_controlled"

        for idx, (scenario_key, payload) in enumerate(scenarios, start=1):
            with transaction.atomic():
                resume = Resume.objects.create(
                    user_id=user.id,
                    name=payload["name"],
                    status=ResumeStatus.DRAFT,
                    target_position=(payload.get("target_position") or "")[:500],
                    summary=payload.get("summary") or "",
                )
                c = payload["contact"]
                ResumeContact.objects.update_or_create(
                    resume=resume,
                    defaults={
                        "full_name": c.get("fullName") or "",
                        "email": c.get("email") or "",
                        "phone": c.get("phone") or "",
                        "city": c.get("city") or "",
                        "country": c.get("country") or "",
                        "linkedin": c.get("linkedin"),
                        "github": c.get("github"),
                        "portfolio": c.get("portfolio"),
                        "website": c.get("website"),
                    },
                )
                exps = []
                for e in payload.get("experiences") or []:
                    exps.append(
                        {
                            "company": e.get("company") or "",
                            "position": e.get("position") or "",
                            "startDate": e.get("startDate") or "",
                            "endDate": e.get("endDate") or "",
                            "isCurrent": bool(e.get("isCurrent")),
                            "description": list(e.get("description") or []),
                        }
                    )
                replace_experiences(resume, exps)
                eds = []
                for ed in payload.get("educations") or []:
                    eds.append(
                        {
                            "institution": ed.get("institution") or "",
                            "course": ed.get("course") or "",
                            "degree": ed.get("degree") or "",
                            "startDate": ed.get("startDate") or "",
                            "endDate": ed.get("endDate") or "",
                            "status": ed.get("status") or "",
                        }
                    )
                replace_educations(resume, eds)
                sks = [{"name": s.get("name") or "", "level": s.get("level")} for s in (payload.get("skills") or [])]
                replace_skills(resume, sks)
                replace_languages(resume, payload.get("languages") or [])
                ResumeTag.objects.get_or_create(
                    resume=resume,
                    label=tag_label,
                    defaults={"position_index": 0},
                )

            items.append(
                {
                    "resume_id": str(resume.id),
                    "scenario_key": scenario_key,
                    "job_description_text": payload.get("job_description_text"),
                }
            )

        doc = {
            "version": 1,
            "user_email": user.email,
            "user_id": str(user.id),
            "tag": tag_label,
            "items": items,
        }
        json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(items)} resume(s) → {json_path}"))
