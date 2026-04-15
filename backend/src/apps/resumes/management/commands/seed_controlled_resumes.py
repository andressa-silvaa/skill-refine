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
from apps.resumes.interfaces.api.service_utils import (
    replace_educations,
    replace_experiences,
    replace_languages,
    replace_skills,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _fake_contact(i: int) -> dict:
    return {
        "fullName": f"Perfil Controle {i}",
        "email": f"seed.ctrl.{i}@local.invalid",
        "phone": "",
        "city": "",
        "country": "",
        "linkedin": None,
        "github": None,
        "portfolio": None,
        "website": None,
    }


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

        scenarios: list[tuple[str, dict]] = []

        scenarios.append(
            (
                "empty",
                {
                    "name": "CTRL-empty",
                    "target_position": "",
                    "summary": "",
                    "contact": _fake_contact(1),
                    "experiences": [],
                    "educations": [],
                    "skills": [],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "junior",
                {
                    "name": "CTRL-junior",
                    "target_position": "Desenvolvedor Junior",
                    "summary": "Estudante de computação, primeiro estágio em desenvolvimento.",
                    "contact": _fake_contact(2),
                    "experiences": [
                        {
                            "company": "Empresa Alfa",
                            "position": "Estagiário de desenvolvimento",
                            "startDate": "2024-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Suporte a APIs internas.", "Testes automatizados."],
                        }
                    ],
                    "educations": [{"institution": "Universidade Pública", "course": "Ciência da Computação", "degree": "Bacharelado", "startDate": "2022-01-01", "endDate": "", "status": "in_progress"}],
                    "skills": [{"name": "Python", "level": None}, {"name": "Git", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "mid",
                {
                    "name": "CTRL-mid",
                    "target_position": "Desenvolvedor Pleno Backend",
                    "summary": "Desenvolvedor backend com cerca de 3 anos em APIs REST e bancos relacionais.",
                    "contact": _fake_contact(3),
                    "experiences": [
                        {
                            "company": "Tech Beta",
                            "position": "Desenvolvedor Backend",
                            "startDate": "2022-06-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["APIs REST", "PostgreSQL", "Code review"],
                        },
                        {
                            "company": "Startup Gama",
                            "position": "Desenvolvedor",
                            "startDate": "2021-01-01",
                            "endDate": "2022-05-31",
                            "isCurrent": False,
                            "description": ["Manutenção de serviços internos."],
                        },
                    ],
                    "educations": [],
                    "skills": [{"name": "Python", "level": None}, {"name": "Django", "level": None}, {"name": "SQL", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "senior_explicit",
                {
                    "name": "CTRL-senior",
                    "target_position": "Staff Engineer",
                    "summary": (
                        "Desenvolvedor sênior full-stack com 10 anos de experiência. "
                        "Líder de tecnologia e arquitetura em produtos SaaS. Mentoria de times."
                    ),
                    "contact": _fake_contact(4),
                    "experiences": [
                        {
                            "company": "Corp Delta",
                            "position": "Staff Software Engineer",
                            "startDate": "2018-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Arquitetura de microsserviços", "Roadmap técnico", "Mentoria."],
                        }
                    ],
                    "educations": [{"institution": "Universidade", "course": "Engenharia", "degree": "Bacharelado", "startDate": "2010-01-01", "endDate": "2014-12-01", "status": "completed"}],
                    "skills": [{"name": "Python", "level": None}, {"name": "Kubernetes", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "migration_no_evidence",
                {
                    "name": "CTRL-migration-A",
                    "target_position": "Desenvolvedor Backend Sênior",
                    "summary": (
                        "Enfermeiro com 12 anos em UTI e gestão de equipe clínica. "
                        "Foco em protocolos e indicadores hospitalares."
                    ),
                    "contact": _fake_contact(5),
                    "experiences": [
                        {
                            "company": "Hospital Epsilon",
                            "position": "Enfermeiro coordenador",
                            "startDate": "2012-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["UTI", "Escalas", "Treinamento de equipe"],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "Protocolos clínicos", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "migration_with_evidence",
                {
                    "name": "CTRL-migration-B",
                    "target_position": "Desenvolvedor Backend",
                    "summary": (
                        "Profissional de saúde migrando para tecnologia. "
                        "Projetos pessoais com Python, Django e APIs."
                    ),
                    "contact": _fake_contact(6),
                    "experiences": [
                        {
                            "company": "Hospital Zeta",
                            "position": "Técnico em informática hospitalar",
                            "startDate": "2020-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Integração de sistemas", "Suporte a ERP"],
                        }
                    ],
                    "educations": [],
                    "skills": [
                        {"name": "Python", "level": None},
                        {"name": "Django", "level": None},
                        {"name": "PostgreSQL", "level": None},
                        {"name": "REST", "level": None},
                    ],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "aligned_high_tech",
                {
                    "name": "CTRL-aligned",
                    "target_position": "Engenheiro de Software Backend Sênior",
                    "summary": (
                        "Engenheiro backend sênior: Python, Django, PostgreSQL, filas, observabilidade, 8 anos."
                    ),
                    "contact": _fake_contact(7),
                    "experiences": [
                        {
                            "company": "SaaS Omega",
                            "position": "Senior Backend Engineer",
                            "startDate": "2017-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Django", "Celery", "Redis", "Kubernetes"],
                        }
                    ],
                    "educations": [],
                    "skills": [
                        {"name": "Python", "level": None},
                        {"name": "Django", "level": None},
                        {"name": "PostgreSQL", "level": None},
                        {"name": "Docker", "level": None},
                    ],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "no_target_position",
                {
                    "name": "CTRL-no-target",
                    "target_position": "",
                    "summary": "Analista com experiência em relatórios e planilhas.",
                    "contact": _fake_contact(8),
                    "experiences": [
                        {
                            "company": "Consultoria",
                            "position": "Analista",
                            "startDate": "2020-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Relatórios", "Excel avançado"],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "Excel", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "many_skills_little_exp",
                {
                    "name": "CTRL-skills-heavy",
                    "target_position": "Desenvolvedor Full Stack",
                    "summary": "Autodidata, muitos cursos online.",
                    "contact": _fake_contact(9),
                    "experiences": [],
                    "educations": [],
                    "skills": [
                        {"name": n, "level": None}
                        for n in (
                            "Python",
                            "JavaScript",
                            "React",
                            "Node",
                            "Docker",
                            "AWS",
                            "GraphQL",
                            "MongoDB",
                            "TypeScript",
                            "Kubernetes",
                        )
                    ],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "much_exp_few_skills",
                {
                    "name": "CTRL-exp-heavy",
                    "target_position": "Gerente de Operações",
                    "summary": "Gestão operacional e processos.",
                    "contact": _fake_contact(10),
                    "experiences": [
                        {
                            "company": "Logística 1",
                            "position": "Supervisor",
                            "startDate": "2015-01-01",
                            "endDate": "2019-12-31",
                            "isCurrent": False,
                            "description": ["KPIs", "Turnos"],
                        },
                        {
                            "company": "Logística 2",
                            "position": "Gerente operacional",
                            "startDate": "2020-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Melhoria contínua", "Contratos"],
                        },
                    ],
                    "educations": [],
                    "skills": [{"name": "Excel", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "target_with_short_job",
                {
                    "name": "CTRL-jobtext",
                    "target_position": "Analista de Dados",
                    "summary": "SQL, dashboards, indicadores.",
                    "contact": _fake_contact(11),
                    "experiences": [
                        {
                            "company": "Retail",
                            "position": "Analista",
                            "startDate": "2021-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["SQL", "Power BI"],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "SQL", "level": None}, {"name": "Python", "level": None}],
                    "languages": [],
                    "job_description_text": "Vaga: SQL, Python, análise de dados, dashboards.",
                },
            )
        )
        scenarios.append(
            (
                "summary_en",
                {
                    "name": "CTRL-en",
                    "target_position": "Senior Software Engineer",
                    "summary": (
                        "Senior software engineer with 9 years building distributed systems and leading squads."
                    ),
                    "contact": _fake_contact(12),
                    "experiences": [
                        {
                            "company": "Tech US",
                            "position": "Senior Engineer",
                            "startDate": "2019-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Microservices", "AWS", "Mentoring"],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "Java", "level": None}, {"name": "AWS", "level": None}],
                    "languages": [{"name": "English", "level": "fluent"}],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "intern_like",
                {
                    "name": "CTRL-intern",
                    "target_position": "Estágio em desenvolvimento",
                    "summary": "Buscando primeiro estágio na área de tecnologia.",
                    "contact": _fake_contact(13),
                    "experiences": [],
                    "educations": [{"institution": "Faculdade", "course": "ADS", "degree": "Tecnólogo", "startDate": "2023-01-01", "endDate": "", "status": "in_progress"}],
                    "skills": [{"name": "HTML", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "career_switch_marketing_dev",
                {
                    "name": "CTRL-mkt-dev",
                    "target_position": "Desenvolvedor Frontend",
                    "summary": "Especialista em marketing digital e conteúdo, 6 anos em agências.",
                    "contact": _fake_contact(14),
                    "experiences": [
                        {
                            "company": "Agência",
                            "position": "Coordenador de marketing",
                            "startDate": "2018-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Campanhas", "SEO", "Métricas"],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "Google Analytics", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "data_aligned",
                {
                    "name": "CTRL-data",
                    "target_position": "Cientista de Dados",
                    "summary": "Modelos preditivos, feature engineering, MLOps básico, 5 anos.",
                    "contact": _fake_contact(15),
                    "experiences": [
                        {
                            "company": "Insurtech",
                            "position": "Cientista de dados",
                            "startDate": "2020-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["scikit-learn", "pipelines", "monitoramento"],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "Python", "level": None}, {"name": "pandas", "level": None}, {"name": "SQL", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )
        scenarios.append(
            (
                "senior_sparse_structured",
                {
                    "name": "CTRL-senior-sparse",
                    "target_position": "Arquiteto de Software",
                    "summary": "Sênior; arquitetura; integrações; 12 anos.",
                    "contact": _fake_contact(16),
                    "experiences": [
                        {
                            "company": "Empresa K",
                            "position": "Arquiteto de software",
                            "startDate": "2013-01-01",
                            "endDate": "",
                            "isCurrent": True,
                            "description": ["Integrações."],
                        }
                    ],
                    "educations": [],
                    "skills": [{"name": "Java", "level": None}],
                    "languages": [],
                    "job_description_text": None,
                },
            )
        )

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
