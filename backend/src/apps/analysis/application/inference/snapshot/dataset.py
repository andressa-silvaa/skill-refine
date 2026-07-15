"""
Golden resume cases covering cascade branch points for analyze_resume().

Cases intentionally exercise insufficient_data, thin/intern profiles, with/without
job_description_text and targetPosition, PT/EN/ES, and each seniority band.
"""
from __future__ import annotations

from typing import Any, Iterator


def _base(
    *,
    summary: str = "",
    experiences: list | None = None,
    educations: list | None = None,
    skills: list | None = None,
    languages: list | None = None,
    contact: dict | None = None,
    target_position: str = "",
    projects: list | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "summary": summary,
        "contact": contact if contact is not None else {},
        "experiences": experiences if experiences is not None else [],
        "educations": educations if educations is not None else [],
        "skills": skills if skills is not None else [],
        "languages": languages if languages is not None else [],
    }
    if target_position:
        data["targetPosition"] = target_position
    if projects is not None:
        data["projects"] = projects
    return {"data": data}


def _exp(
    company: str,
    position: str,
    description: list[str],
    start: str | None = None,
    end: str | None = None,
    current: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "company": company,
        "position": position,
        "description": description,
    }
    if start:
        row["startDate"] = start
    if end:
        row["endDate"] = end
    if current:
        row["isCurrent"] = True
    return row


GOLDEN_CASES: list[dict[str, Any]] = [
    # --- insufficient / thin ---
    {
        "id": "insufficient_empty_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["insufficient_data", "pt"],
        "resume_data": _base(summary="Estudante"),
    },
    {
        "id": "insufficient_blank_en",
        "language": "en-US",
        "job_description_text": None,
        "tags": ["insufficient_data", "en"],
        "resume_data": _base(),
    },
    {
        "id": "thin_intern_biology_vs_dev_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["thin_profile", "intern", "target", "pt"],
        "resume_data": _base(
            target_position="Programador",
            summary="Estudante de biologia buscando oportunidades em desenvolvimento.",
            experiences=[
                _exp("Empresa X", "Estagiário de TI", ["Apoio em projetos por duas semanas."]),
            ],
            educations=[
                {
                    "institution": "Universidade",
                    "course": "Biologia",
                    "degree": "Graduação em andamento",
                }
            ],
        ),
    },
    {
        "id": "thin_shallow_no_intern_keyword_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["thin_profile", "pt"],
        "resume_data": _base(
            target_position="Programador",
            summary="Buscando primeira oportunidade.",
            experiences=[_exp("Empresa", "Programador", ["Duas semanas de atividades."])],
            educations=[{"institution": "UF", "course": "Biologia", "degree": "Graduação"}],
        ),
    },
    # --- intern / junior ---
    {
        "id": "intern_estagio_software_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["intern", "pt"],
        "resume_data": _base(
            summary="Estudante de computação em estágio.",
            experiences=[
                _exp(
                    "Startup Y",
                    "Estagiário de Desenvolvimento",
                    ["Corrigi bugs em Python.", "Acompanhei daily meetings."],
                    start="2024-06",
                    end="2024-12",
                )
            ],
            educations=[
                {
                    "institution": "UFX",
                    "course": "Ciência da Computação",
                    "degree": "Graduação em andamento",
                }
            ],
            skills=[{"name": "Python"}, {"name": "Git"}],
        ),
    },
    {
        "id": "junior_with_dates_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["junior", "pt"],
        "resume_data": _base(
            target_position="Desenvolvedor Júnior",
            summary="Foco em APIs e qualidade de código.",
            experiences=[
                _exp(
                    "Tech Co",
                    "Desenvolvedor Júnior",
                    ["Desenvolvimento de APIs REST.", "Participação em code review."],
                    start="2023-01-01",
                    end="2024-12-31",
                )
            ],
            educations=[
                {
                    "institution": "UF",
                    "course": "Ciência da Computação",
                    "degree": "Bacharelado",
                }
            ],
            skills=[{"name": "Python"}, {"name": "Django"}, {"name": "PostgreSQL"}],
        ),
    },
    {
        "id": "junior_two_years_summary_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["junior", "pt"],
        "resume_data": _base(
            target_position="Desenvolvedor Front-end",
            summary=(
                "Desenvolvedor júnior com 2 anos de experiência em desenvolvimento front-end."
            ),
            experiences=[
                _exp(
                    "Empresa",
                    "Desenvolvedor Front-end",
                    ["Componentes React e integração com APIs."],
                )
            ],
            skills=[{"name": "React"}, {"name": "TypeScript"}],
        ),
    },
    {
        "id": "junior_en",
        "language": "en-US",
        "job_description_text": None,
        "tags": ["junior", "en"],
        "resume_data": _base(
            summary="Junior developer with 2 years building REST APIs and writing tests.",
            experiences=[
                _exp(
                    "Acme",
                    "Junior Developer",
                    [
                        "Implemented 8 REST endpoints.",
                        "Reduced bug rate by 12% with automated tests.",
                    ],
                    start="2023-03",
                    end="2025-03",
                )
            ],
            educations=[
                {"institution": "State U", "course": "Computer Science", "degree": "BSc"}
            ],
            skills=[{"name": "Python"}, {"name": "Django"}, {"name": "PostgreSQL"}],
            contact={"github": "github.com/junior-dev"},
        ),
    },
    {
        "id": "junior_es",
        "language": "es-ES",
        "job_description_text": None,
        "tags": ["junior", "es"],
        "resume_data": _base(
            summary="Desarrollador junior con 2 años en backend y APIs.",
            experiences=[
                _exp(
                    "Empresa Latam",
                    "Desarrollador Junior",
                    ["Desarrolló APIs con Django.", "Participó en code reviews."],
                    start="2023-01",
                    end="2025-01",
                )
            ],
            skills=[{"name": "Python"}, {"name": "SQL"}],
        ),
    },
    # --- mid ---
    {
        "id": "mid_backend_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["mid", "pt"],
        "resume_data": _base(
            summary=(
                "Desenvolvedor com 5 anos em backend. Implementei 10 APIs e reduzi latência em 15%."
            ),
            experiences=[
                _exp(
                    "Empresa X",
                    "Desenvolvedor Pleno",
                    [
                        "Desenvolvi sistemas críticos em Python e Django.",
                        "Coordenei equipe de 3 pessoas em entregas ágeis.",
                    ],
                    start="2019-01",
                    end="2024-12",
                )
            ],
            educations=[
                {"institution": "UFX", "course": "Computação", "degree": "Bacharelado"}
            ],
            skills=[{"name": "Python"}, {"name": "Django"}, {"name": "AWS"}, {"name": "Docker"}],
            contact={"linkedin": "linkedin.com/in/foo", "github": "github.com/foo"},
            languages=[{"name": "Português", "level": "native"}],
        ),
    },
    {
        "id": "mid_with_job_pt",
        "language": "pt-BR",
        "job_description_text": (
            "Vaga backend com Python, Django e PostgreSQL. Experiência com APIs REST e Docker."
        ),
        "tags": ["mid", "matching", "job", "pt"],
        "resume_data": _base(
            summary="Engenheiro backend com 5 anos. Implementei 10 APIs e reduzi latencia em 15%.",
            experiences=[
                _exp("X", "Dev Pleno", ["Python e Django.", "PostgreSQL e filas."], start="2019-01", end="2024-06")
            ],
            skills=[{"name": "Python"}, {"name": "Django"}, {"name": "PostgreSQL"}],
            contact={"github": "github.com/foo"},
        ),
    },
    {
        "id": "mid_finance_target_pt",
        "language": "pt-BR",
        "job_description_text": "Orçamento forecast FP&A e Power BI.",
        "tags": ["mid", "target", "job", "pt"],
        "resume_data": _base(
            target_position="Analista Financeiro Pleno",
            summary="Analista financeiro com 5 anos em FP&A e orçamento.",
            experiences=[
                _exp("ACME", "Analista Financeiro", ["Forecast", "Budget", "Reporting"], start="2019-01", end="2024-01")
            ],
            educations=[{"course": "Administração", "degree": "Graduação", "institution": "FGV"}],
            skills=[{"name": "Excel"}, {"name": "Orçamento"}, {"name": "Power BI"}],
            contact={"linkedin": "https://linkedin.com/in/x"},
        ),
    },
    {
        "id": "mid_en_product",
        "language": "en-US",
        "job_description_text": "Looking for a mid-level product engineer with React and APIs.",
        "tags": ["mid", "matching", "en", "job"],
        "resume_data": _base(
            summary="Product engineer with 4 years shipping web apps and APIs.",
            experiences=[
                _exp(
                    "ProdCo",
                    "Software Engineer",
                    [
                        "Built React dashboards used by 20k users.",
                        "Improved API latency by 25%.",
                    ],
                    start="2020-01",
                    end="2024-06",
                )
            ],
            skills=[{"name": "React"}, {"name": "TypeScript"}, {"name": "Node.js"}],
            contact={"github": "github.com/mid"},
        ),
    },
    {
        "id": "mid_es_data",
        "language": "es-ES",
        "job_description_text": None,
        "tags": ["mid", "es"],
        "resume_data": _base(
            summary="Analista de datos con 4 años en Python, SQL y visualización.",
            experiences=[
                _exp(
                    "Datos SA",
                    "Analista de Datos",
                    ["Pipelines ETL en Python.", "Dashboards en Power BI."],
                    start="2020-02",
                    end="2024-08",
                )
            ],
            skills=[{"name": "Python"}, {"name": "SQL"}, {"name": "Power BI"}],
        ),
    },
    # --- senior ---
    {
        "id": "senior_leadership_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["senior", "pt"],
        "resume_data": _base(
            summary=(
                "Engenheiro sênior com 10 anos. Liderou arquitetura de microsserviços e "
                "mentoria de equipes."
            ),
            experiences=[
                _exp(
                    "BigTech",
                    "Engenheiro de Software Sênior",
                    [
                        "Liderou roadmap de plataforma e governança.",
                        "Mentoria de 8 engenheiros; reduziu incidentes em 40%.",
                        "Definiu arquitetura de microsserviços e observabilidade.",
                    ],
                    start="2014-01",
                    end="2024-12",
                ),
                _exp(
                    "Startup Z",
                    "Tech Lead",
                    ["Coordenei squad de 6 pessoas.", "Implementei CI/CD na AWS."],
                    start="2010-01",
                    end="2013-12",
                ),
            ],
            educations=[
                {"institution": "USP", "course": "Engenharia", "degree": "Mestrado"}
            ],
            skills=[
                {"name": "Python"},
                {"name": "Kubernetes"},
                {"name": "AWS"},
                {"name": "Arquitetura"},
            ],
            contact={"linkedin": "linkedin.com/in/senior", "github": "github.com/senior"},
        ),
    },
    {
        "id": "senior_with_job_and_target_pt",
        "language": "pt-BR",
        "job_description_text": (
            "Vaga sênior: Python, arquitetura de microsserviços, mentoria, AWS, Kubernetes."
        ),
        "tags": ["senior", "matching", "target", "job", "pt"],
        "resume_data": _base(
            target_position="Engenheiro de Software Sênior",
            summary="Engenheiro sênior com 10 anos em plataformas e mentoria.",
            experiences=[
                _exp(
                    "Cloud Co",
                    "Staff Engineer",
                    [
                        "Arquitetura de microsserviços e observability.",
                        "Mentoria técnica e code review.",
                    ],
                    start="2015-01",
                    current=True,
                )
            ],
            skills=[{"name": "Python"}, {"name": "Kubernetes"}, {"name": "AWS"}],
            contact={"github": "github.com/staff"},
        ),
    },
    {
        "id": "senior_en",
        "language": "en-US",
        "job_description_text": "Senior engineer role: mentoring, architecture, cloud.",
        "tags": ["senior", "en", "job", "matching"],
        "resume_data": _base(
            target_position="Senior Software Engineer",
            summary="Senior engineer with 12 years leading platform teams.",
            experiences=[
                _exp(
                    "MegaCorp",
                    "Senior Software Engineer",
                    [
                        "Led architecture for multi-region services.",
                        "Mentored 10 engineers; cut MTTR by 35%.",
                    ],
                    start="2012-01",
                    end="2024-12",
                )
            ],
            skills=[{"name": "Go"}, {"name": "Kubernetes"}, {"name": "AWS"}],
            contact={"linkedin": "linkedin.com/in/senior-en"},
        ),
    },
    {
        "id": "senior_es",
        "language": "es-ES",
        "job_description_text": None,
        "tags": ["senior", "es"],
        "resume_data": _base(
            summary="Ingeniero senior con 11 años liderando equipos y arquitectura.",
            experiences=[
                _exp(
                    "Corp ES",
                    "Ingeniero Senior",
                    [
                        "Lideró arquitectura de microservicios.",
                        "Mentoría de equipos multidisciplinares.",
                    ],
                    start="2013-01",
                    end="2024-12",
                )
            ],
            skills=[{"name": "Java"}, {"name": "Kubernetes"}, {"name": "AWS"}],
        ),
    },
    # --- target fit divergence / career switch ---
    {
        "id": "career_switch_bio_to_dev_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["target", "career_switch", "pt"],
        "resume_data": _base(
            target_position="Desenvolvedor(a) Full Stack",
            summary="Bióloga com 10 anos de pesquisa em ecologia e laboratório.",
            experiences=[
                _exp(
                    "USP",
                    "Pesquisadora",
                    ["Campo", "Análise de dados ecológicos", "Publicações"],
                    start="2014-01",
                    end="2024-01",
                )
            ],
            educations=[
                {"course": "Biologia", "degree": "Mestrado", "institution": "Universidade"}
            ],
            skills=[{"name": "PCR"}, {"name": "Ecologia"}, {"name": "Estatística"}],
        ),
    },
    {
        "id": "career_switch_finance_to_ux_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["target", "career_switch", "pt"],
        "resume_data": _base(
            target_position="UX Designer",
            summary="Analista financeiro com 5 anos em FP&A e orçamento.",
            experiences=[
                _exp("ACME", "Analista Financeiro", ["Forecast", "Budget", "Reporting"])
            ],
            educations=[{"course": "Administração", "degree": "Graduação", "institution": "FGV"}],
            skills=[{"name": "Excel"}, {"name": "Orçamento"}, {"name": "Power BI"}],
        ),
    },
    {
        "id": "aligned_bio_senior_target_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["target", "senior", "pt"],
        "resume_data": _base(
            target_position="Bióloga Sênior",
            summary="Bióloga com 10 anos de pesquisa em ecologia e laboratório.",
            experiences=[
                _exp(
                    "USP",
                    "Pesquisadora",
                    ["Campo", "Análise de dados ecológicos", "Publicações"],
                    start="2014-01",
                    end="2024-01",
                )
            ],
            educations=[
                {"course": "Biologia", "degree": "Mestrado", "institution": "Universidade"}
            ],
            skills=[{"name": "PCR"}, {"name": "Ecologia"}, {"name": "Estatística"}],
        ),
    },
    {
        "id": "target_only_no_job_analista_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["target", "pt"],
        "resume_data": _base(
            target_position="Analista",
            summary="Profissional com experiência.",
            experiences=[
                _exp("Co", "Analista", ["Relatórios e conciliação."], start="2020-01", end="2024-01")
            ],
            skills=[{"name": "Excel"}],
        ),
    },
    {
        "id": "job_only_no_target_pt",
        "language": "pt-BR",
        "job_description_text": "Precisamos de Python, Django, testes automatizados e SQL.",
        "tags": ["matching", "job", "pt"],
        "resume_data": _base(
            summary="Desenvolvedor com 3 anos em Python.",
            experiences=[_exp("X", "Dev", ["Django e testes."], start="2021-01", end="2024-01")],
            skills=[{"name": "Python"}, {"name": "Django"}],
        ),
    },
    # --- multilang + target + job ---
    {
        "id": "en_target_nurse_switch",
        "language": "en-US",
        "job_description_text": "Registered nurse position in hospital care unit.",
        "tags": ["en", "target", "job", "career_switch"],
        "resume_data": _base(
            target_position="Registered Nurse",
            summary="Software engineer with 6 years building healthcare SaaS backends.",
            experiences=[
                _exp(
                    "HealthTech",
                    "Backend Engineer",
                    ["Built patient scheduling APIs.", "HIPAA-aware data pipelines."],
                    start="2018-01",
                    end="2024-01",
                )
            ],
            skills=[{"name": "Python"}, {"name": "PostgreSQL"}],
        ),
    },
    {
        "id": "es_target_profesor_aligned",
        "language": "es-ES",
        "job_description_text": "Profesor de matemáticas para secundaria.",
        "tags": ["es", "target", "job"],
        "resume_data": _base(
            target_position="Profesor de matemáticas",
            summary="Profesor con 7 años enseñando matemáticas y algebra.",
            experiences=[
                _exp(
                    "Colegio Norte",
                    "Profesor",
                    ["Clases de algebra y calculo.", "Tutorias semanales."],
                    start="2017-01",
                    end="2024-01",
                )
            ],
            educations=[
                {"course": "Matemáticas", "degree": "Licenciatura", "institution": "UNAM"}
            ],
            skills=[{"name": "Pedagogía"}, {"name": "Álgebra"}],
        ),
    },
    # --- edge / completeness variants ---
    {
        "id": "partial_skills_only_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["insufficient_data", "pt"],
        "resume_data": _base(
            summary="",
            skills=[{"name": "Python"}, {"name": "Excel"}],
        ),
    },
    {
        "id": "education_heavy_no_exp_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["intern", "pt"],
        "resume_data": _base(
            summary="Recém-formado buscando primeira vaga.",
            educations=[
                {
                    "institution": "Unicamp",
                    "course": "Engenharia de Computação",
                    "degree": "Bacharelado",
                }
            ],
            skills=[{"name": "C++"}, {"name": "Python"}],
            projects=[{"name": "TCC", "description": ["Sistema web de inventário."]}],
        ),
    },
    {
        "id": "rich_links_metrics_pt",
        "language": "pt-BR",
        "job_description_text": "Python Django AWS Docker métricas latência.",
        "tags": ["mid", "matching", "job", "pt"],
        "resume_data": _base(
            summary="Profissional com 6 anos. Reduzi latência em 30% e custo em R$ 50 mil.",
            experiences=[
                _exp(
                    "Empresa Q",
                    "Analista Pleno",
                    [
                        "Implementou microsserviços com Docker.",
                        "Liderou projeto que aumentou conversão em 18%.",
                    ],
                    start="2018-01",
                    end="2024-06",
                )
            ],
            skills=[{"name": "Python"}, {"name": "Django"}, {"name": "AWS"}, {"name": "Docker"}],
            contact={
                "linkedin": "linkedin.com/in/rich",
                "github": "github.com/rich",
                "portfolio": "https://rich.dev",
            },
        ),
    },
    {
        "id": "interno_not_intern_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["junior", "pt"],
        "resume_data": _base(
            target_position="Dev",
            summary="Sistemas internos e integrações.",
            experiences=[
                _exp(
                    "Banco",
                    "Desenvolvedor Interno",
                    ["Sistemas internos e APIs.", "2 anos em integração bancária."],
                    start="2022-01",
                    end="2024-01",
                )
            ],
            skills=[{"name": "Java"}, {"name": "SQL"}],
        ),
    },
    {
        "id": "mid_no_skills_list_pt",
        "language": "pt-BR",
        "job_description_text": None,
        "tags": ["mid", "pt"],
        "resume_data": _base(
            summary="Desenvolvedor com 4 anos em produto web e APIs REST.",
            experiences=[
                _exp(
                    "WebCo",
                    "Desenvolvedor",
                    ["APIs REST.", "Frontend React.", "Code review."],
                    start="2020-01",
                    end="2024-01",
                )
            ],
            educations=[
                {"institution": "UFSC", "course": "Sistemas de Informação", "degree": "Bacharelado"}
            ],
        ),
    },
    {
        "id": "senior_target_ml_path_shape_pt",
        "language": "pt-BR",
        "job_description_text": "Machine learning engineer: Python, NLP, models, mentorship.",
        "tags": ["senior", "target", "job", "matching", "pt"],
        "resume_data": _base(
            target_position="Machine Learning Engineer",
            summary="Engenheiro ML com 8 anos em NLP e modelos em produção.",
            experiences=[
                _exp(
                    "AI Lab",
                    "ML Engineer",
                    [
                        "Deployed NLP models reducing ticket time by 22%.",
                        "Mentored juniors on experiment design.",
                    ],
                    start="2016-01",
                    end="2024-12",
                )
            ],
            skills=[{"name": "Python"}, {"name": "NLP"}, {"name": "PyTorch"}, {"name": "AWS"}],
            contact={"github": "github.com/ml"},
        ),
    },
    {
        "id": "sparse_with_job_en",
        "language": "en-US",
        "job_description_text": "Need Django and PostgreSQL experience.",
        "tags": ["insufficient_data", "job", "matching", "en"],
        "resume_data": _base(summary="Student looking for a job."),
    },
    {
        "id": "mid_target_same_domain_en",
        "language": "en-US",
        "job_description_text": None,
        "tags": ["mid", "target", "en"],
        "resume_data": _base(
            target_position="Backend Engineer",
            summary="Backend engineer with 5 years in Python APIs and Postgres.",
            experiences=[
                _exp(
                    "ApiCo",
                    "Backend Engineer",
                    ["Built billing APIs.", "Cut query latency by 20%."],
                    start="2019-01",
                    end="2024-01",
                )
            ],
            skills=[{"name": "Python"}, {"name": "PostgreSQL"}, {"name": "Django"}],
            contact={"github": "github.com/be"},
        ),
    },
    {
        "id": "intern_en",
        "language": "en-US",
        "job_description_text": None,
        "tags": ["intern", "en"],
        "resume_data": _base(
            summary="CS student seeking internship opportunities.",
            experiences=[
                _exp("Campus Lab", "Software Intern", ["Fixed UI bugs.", "Wrote unit tests."])
            ],
            educations=[
                {
                    "institution": "Tech U",
                    "course": "Computer Science",
                    "degree": "BSc in progress",
                }
            ],
            skills=[{"name": "JavaScript"}],
        ),
    },
    {
        "id": "mid_healthcare_es",
        "language": "es-ES",
        "job_description_text": None,
        "tags": ["mid", "target", "es"],
        "resume_data": _base(
            target_position="Enfermero hospitalar",
            summary="Enfermero con 5 años en cuidados intensivos.",
            experiences=[
                _exp(
                    "Hospital Central",
                    "Enfermero",
                    ["Cuidados intensivos.", "Protocolos de seguridad del paciente."],
                    start="2019-01",
                    end="2024-01",
                )
            ],
            educations=[
                {"course": "Enfermería", "degree": "Licenciatura", "institution": "Universidad"}
            ],
            skills=[{"name": "Cuidados intensivos"}, {"name": "Protocolos"}],
        ),
    },
]


def iter_golden_cases() -> Iterator[dict[str, Any]]:
    for case in GOLDEN_CASES:
        yield case


def golden_case_ids() -> list[str]:
    return [str(c["id"]) for c in GOLDEN_CASES]
