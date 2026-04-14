"""
Create synthetic resumes (no PII) for ML dataset scaling.

  python manage.py seed_resumes --user-email dev@local.test --count 100 --seed 42 --profiles balanced

Reuses templates inspired by client stress mocks; data is generated locally (fake emails *.local.seed.invalid).
"""
from __future__ import annotations

import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.infrastructure.models import User, UserStatus
from apps.resumes.application.synthetic_seed import (
    DOMAIN_PRESETS,
    build_synthetic_resume,
    pick_profile,
)
from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeStatus,
    ResumeTag,
)
from apps.resumes.interfaces.api.service_utils import (
    replace_educations,
    replace_experiences,
    replace_languages,
    replace_skills,
)


class Command(BaseCommand):
    help = "Seed N synthetic resumes for a user (deterministic --seed, profile mix)."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", type=str, default="", dest="user_email")
        parser.add_argument("--user-id", type=str, default="", dest="user_id")
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--profiles",
            type=str,
            default="balanced",
            help="balanced | senior_heavy | junior_heavy | intern_heavy",
        )
        parser.add_argument(
            "--tag",
            type=str,
            default="seed_synthetic",
            help="ResumeTag label attached to each seeded resume (empty to skip).",
        )
        parser.add_argument(
            "--with-target-positions",
            action="store_true",
            dest="with_target_positions",
            help="Ensure target_position is always non-empty; with --domain-mix balanced, titles follow domain rotation.",
        )
        parser.add_argument(
            "--domain-mix",
            type=str,
            default="",
            dest="domain_mix",
            help="Empty = legacy tech-only bodies. 'balanced' = rotate health/finance/education/legal/marketing/tech + some career-switch pairs.",
        )

    def handle(self, *args, **options):
        email = (options.get("user_email") or "").strip()
        uid = (options.get("user_id") or "").strip()
        count = int(options["count"])
        base_seed = int(options["seed"])
        profiles_mode = str(options["profiles"] or "balanced")
        tag_label = (options.get("tag") or "").strip()
        with_target_positions = bool(options.get("with_target_positions"))
        domain_mix = str(options.get("domain_mix") or "").strip().lower()

        if count < 1 or count > 50_000:
            raise CommandError("--count must be between 1 and 50000.")
        if not email and not uid:
            raise CommandError("Provide --user-email or --user-id.")
        if domain_mix and domain_mix != "balanced":
            raise CommandError("--domain-mix must be empty or 'balanced'.")

        if uid:
            user = User.objects.filter(id=uid, deleted_at__isnull=True).first()
            if user is None:
                raise CommandError("User not found for --user-id.")
        else:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": "Usuário Seed",
                    "status": UserStatus.ACTIVE,
                },
            )
            if created:
                self.stdout.write(self.style.WARNING(f"Created user {user.email}"))

        rng = random.Random(base_seed)
        created = 0
        rot_titles = [
            "Desenvolvedor(a) de Software",
            "Analista de Dados",
            "Engenheiro(a) de Software",
            "Desenvolvedor(a) Full Stack",
            "Engenheiro(a) de Dados",
        ]
        n_dom = len(DOMAIN_PRESETS)
        for i in range(count):
            profile = pick_profile(i, profiles_mode, rng)
            dc: dict | None = None
            dt: dict | None = None
            if domain_mix == "balanced" and n_dom > 0:
                ci = i % n_dom
                career_switch = i % 11 == 0
                ti = (ci + max(1, n_dom // 2)) % n_dom if career_switch else ci
                dc = DOMAIN_PRESETS[ci]
                dt = DOMAIN_PRESETS[ti]
            payload = build_synthetic_resume(
                profile=profile,
                rng=rng,
                index=i,
                base_seed=base_seed,
                domain_content=dc,
                domain_target=dt,
            )
            tp = (payload.get("target_position") or "").strip()
            if not tp:
                payload["target_position"] = rot_titles[i % len(rot_titles)]
            elif with_target_positions and domain_mix != "balanced":
                payload["target_position"] = rot_titles[i % len(rot_titles)]
            with transaction.atomic():
                resume = Resume.objects.create(
                    user_id=user.id,
                    name=payload["name"],
                    status=ResumeStatus.DRAFT,
                    target_position=payload["target_position"],
                    summary=payload["summary"],
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
                        "linkedin": c.get("linkedin") or None,
                        "github": c.get("github") or None,
                        "portfolio": c.get("portfolio") or None,
                        "website": c.get("website") or None,
                    },
                )
                exps = []
                for e in payload["experiences"]:
                    exps.append(
                        {
                            "company": e["company"],
                            "position": e["position"],
                            "startDate": e["startDate"],
                            "endDate": e.get("endDate") or "",
                            "isCurrent": e.get("isCurrent", False),
                            "description": e.get("description") or [],
                        }
                    )
                replace_experiences(resume, exps)
                replace_educations(resume, payload["educations"])
                replace_skills(resume, payload["skills"])
                replace_languages(resume, payload["languages"])
                if tag_label:
                    ResumeTag.objects.create(
                        resume=resume,
                        label=tag_label,
                        position_index=0,
                    )
            created += 1
            if created % 100 == 0:
                self.stdout.write(f"  … {created}/{count}")

        self.stdout.write(self.style.SUCCESS(f"Created {created} synthetic resume(s) for user {user.id}"))
