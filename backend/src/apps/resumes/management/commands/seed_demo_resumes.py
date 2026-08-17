"""
Vinte currículos variados para testar a análise pela interface.

Diferente de ``seed_controlled_resumes``, que são fixtures de borda para validação: aqui a intenção é
cobrir a faixa de resultados que a tela mostra. Os cenários variam de propósito em qualidade da
prosa, senioridade, idioma do documento, área profissional, completude e aderência ao cargo alvo.

  cd backend
  python manage.py seed_demo_resumes --delete-existing --analyze

A exclusão fica atrás de ``--delete-existing`` e nunca acontece como efeito colateral. Sem
``--user-email``, o comando só age se existir exatamente um usuário — apagar currículo do alvo errado
não é erro recuperável.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.infrastructure.models import User
from apps.analysis.models import ResumeAnalysis
from apps.resumes.infrastructure.models import Resume, ResumeContact, ResumeStatus, ResumeTag
from apps.resumes.interfaces.api.service_utils import (
    replace_educations,
    replace_experiences,
    replace_languages,
    replace_skills,
)

SCENARIOS_PATH = Path(__file__).resolve().parent / "demo_scenarios.json"
TAG_LABEL = "seed_demo"


def load_scenarios() -> list[tuple[str, dict]]:
    rows = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return [(str(r["key"]), dict(r["payload"])) for r in rows]


class Command(BaseCommand):
    help = "Cria 20 currículos variados (sem PII) para testar a análise pela interface."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", type=str, default="", dest="user_email")
        parser.add_argument(
            "--delete-existing",
            action="store_true",
            help="Apaga os currículos do usuário (e as análises deles) antes de criar os novos.",
        )
        parser.add_argument(
            "--analyze-only",
            action="store_true",
            help="Nao cria nada: apenas roda a analise dos curriculos com a tag seed_demo.",
        )
        parser.add_argument(
            "--analyze",
            action="store_true",
            help="Roda a análise de cada currículo em seguida, de forma síncrona.",
        )

    def _resolve_user(self, email: str) -> User:
        if email:
            user = User.objects.filter(email=email).first()
            if user is None:
                raise CommandError(f"Nenhum usuário com email {email!r}.")
            return user
        users = list(User.objects.all()[:3])
        if not users:
            raise CommandError("Nenhum usuário no banco. Passe --user-email ou crie um usuário.")
        if len(users) > 1:
            emails = ", ".join(u.email for u in users)
            raise CommandError(
                f"Mais de um usuário no banco ({emails}...). Passe --user-email explicitamente: "
                "apagar currículo do alvo errado não é recuperável."
            )
        return users[0]

    def _delete_existing(self, user: User) -> None:
        resume_ids = list(Resume.objects.filter(user_id=user.id).values_list("id", flat=True))
        if not resume_ids:
            self.stdout.write("Nenhum currículo existente para apagar.")
            return
        analyses = ResumeAnalysis.objects.filter(resume_id__in=resume_ids).count()
        self.stdout.write(
            self.style.WARNING(
                f"Apagando {len(resume_ids)} currículo(s) e {analyses} análise(s) de {user.email}"
            )
        )
        with transaction.atomic():
            ResumeAnalysis.objects.filter(resume_id__in=resume_ids).delete()
            Resume.objects.filter(id__in=resume_ids).delete()

    def _create(self, user: User, key: str, payload: dict) -> Resume:
        with transaction.atomic():
            resume = Resume.objects.create(
                user_id=user.id,
                name=payload["name"],
                status=ResumeStatus.DRAFT,
                target_position=(payload.get("target_position") or "")[:500],
                summary=payload.get("summary") or "",
            )
            contact = payload.get("contact") or {}
            ResumeContact.objects.update_or_create(
                resume=resume,
                defaults={
                    "full_name": contact.get("fullName") or "",
                    "email": contact.get("email") or "",
                    "phone": contact.get("phone") or "",
                    "city": contact.get("city") or "",
                    "country": contact.get("country") or "",
                    "linkedin": contact.get("linkedin"),
                    "github": contact.get("github"),
                    "portfolio": contact.get("portfolio"),
                    "website": contact.get("website"),
                },
            )
            replace_experiences(
                resume,
                [
                    {
                        "company": e.get("company") or "",
                        "position": e.get("position") or "",
                        "startDate": e.get("startDate") or "",
                        "endDate": e.get("endDate") or "",
                        "isCurrent": bool(e.get("isCurrent")),
                        "description": list(e.get("description") or []),
                    }
                    for e in payload.get("experiences") or []
                ],
            )
            replace_educations(
                resume,
                [
                    {
                        "institution": ed.get("institution") or "",
                        "course": ed.get("course") or "",
                        "degree": ed.get("degree") or "",
                        "startDate": ed.get("startDate") or "",
                        "endDate": ed.get("endDate") or "",
                        "status": ed.get("status") or "",
                    }
                    for ed in payload.get("educations") or []
                ],
            )
            replace_skills(
                resume,
                [{"name": s.get("name") or "", "level": s.get("level")} for s in (payload.get("skills") or [])],
            )
            replace_languages(resume, payload.get("languages") or [])
            ResumeTag.objects.get_or_create(
                resume=resume, label=TAG_LABEL, defaults={"position_index": 0}
            )
        return resume

    def _analyze(self, user: User, resume: Resume, job_text: str | None, key: str) -> None:
        from apps.analysis.interfaces.api.services import run_analysis

        analysis, error = run_analysis(
            str(user.id), str(resume.id), job_description_text=job_text, sync=True
        )
        if error or analysis is None:
            self.stdout.write(self.style.ERROR(f"  {key}: run_analysis falhou ({error})"))
            return
        analysis.refresh_from_db()
        if analysis.status != "done":
            reason = (analysis.error_message or "")[:90]
            self.stdout.write(self.style.WARNING(f"  {key}: {analysis.status} — {reason}"))
            return
        payload = analysis.payload_json or {}
        integrity = payload.get("analysisIntegrity") or {}
        low = ",".join(integrity.get("lowConfidenceTasks") or []) or "-"
        self.stdout.write(
            f"  {key:34s} score={analysis.score:3d} "
            f"seniority={payload.get('seniorityClass') or '-':7s} "
            f"fit={payload.get('targetFitScore') if payload.get('targetFitScore') is not None else '-':>4} "
            f"lowConf={low}"
        )

    def handle(self, *args, **options):
        user = self._resolve_user((options.get("user_email") or "").strip())
        self.stdout.write(f"Usuário: {user.email} ({user.id})")

        if options.get("analyze_only"):
            targets = list(
                Resume.objects.filter(user_id=user.id, resumetag__label=TAG_LABEL).order_by("created_at")
            )
            by_name = {key: payload.get("job_description_text") for key, payload in load_scenarios()}
            names = {payload["name"]: key for key, payload in load_scenarios()}
            self.stdout.write(f"Analisando {len(targets)} currículo(s) existentes...")
            for resume in targets:
                key = names.get(resume.name, resume.name)
                self._analyze(user, resume, by_name.get(key), key)
            return

        if options.get("delete_existing"):
            self._delete_existing(user)
        else:
            # Recusar, nao avisar. Um aviso seguido de criacao duplica o seed em silencio, que foi
            # exatamente o que aconteceu na primeira vez que este comando rodou duas vezes.
            already = Resume.objects.filter(user_id=user.id, resumetag__label=TAG_LABEL).count()
            if already:
                raise CommandError(
                    f"{already} currículo(s) com a tag {TAG_LABEL} já existem. Rode com "
                    "--delete-existing para substituir, ou --analyze-only para só analisar os atuais."
                )

        scenarios = load_scenarios()
        created: list[tuple[str, Resume, str | None]] = []
        for key, payload in scenarios:
            resume = self._create(user, key, payload)
            created.append((key, resume, payload.get("job_description_text")))
        self.stdout.write(self.style.SUCCESS(f"Criados {len(created)} currículos (tag {TAG_LABEL})."))

        if options.get("analyze"):
            self.stdout.write("Analisando...")
            for key, resume, job_text in created:
                self._analyze(user, resume, job_text, key)
