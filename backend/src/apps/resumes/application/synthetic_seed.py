"""
Deterministic synthetic resume payloads for seeding (no real PII).

Shapes match API / ``replace_experiences`` helpers (startDate YYYY-MM, descriptions as bullet list).
"""
from __future__ import annotations

import calendar
import random
from datetime import date
from typing import Any

PROFILE_ORDER = ("intern", "junior", "mid", "senior")

# Multi-domain presets for ``--domain-mix balanced`` (target + resume story alignment / mismatch).
DOMAIN_PRESETS: list[dict[str, Any]] = [
    {
        "key": "technology",
        "targets": [
            "Desenvolvedor Full Stack",
            "Engenheiro de Software Pleno",
            "Analista de Dados",
        ],
        "courses": ["Ciência da Computação", "Engenharia de Software", "Sistemas de Informação"],
        "position_titles": [
            "Desenvolvedor de Software",
            "Engenheiro de Software",
            "Analista de Sistemas",
            "Desenvolvedor Backend",
        ],
        "skills_pool": [
            "Python",
            "Django",
            "PostgreSQL",
            "React",
            "TypeScript",
            "Docker",
            "AWS",
            "Git",
            "REST",
            "SQL",
            "Kubernetes",
            "Linux",
        ],
        "summaries": [
            "Profissional de tecnologia focado em entrega e qualidade de software.",
            "Experiência em desenvolvimento de APIs e integração entre sistemas.",
        ],
    },
    {
        "key": "health",
        "targets": ["Enfermeiro(a) Hospitalar", "Técnico(a) em Enfermagem", "Coordenador(a) de Enfermagem"],
        "courses": ["Enfermagem", "Ciências Biológicas", "Fisioterapia"],
        "position_titles": [
            "Enfermeiro(a)",
            "Técnico(a) de Enfermagem",
            "Auxiliar de Enfermagem",
            "Enfermeiro(a) da UTI",
        ],
        "skills_pool": [
            "Sinais vitais",
            "Protocolos clínicos",
            "Passagem de plantão",
            "Cuidado ao paciente",
            "EPIS",
            "Farmacologia básica",
            "Documentação clínica",
            "Suporte em emergência",
        ],
        "summaries": [
            "Profissional da saúde com foco em segurança do paciente e equipe multidisciplinar.",
            "Atuação em ambiente hospitalar com rotinas de cuidado e compliance.",
        ],
    },
    {
        "key": "finance",
        "targets": ["Analista Financeiro Pleno", "Controller Júnior", "Analista FP&A"],
        "courses": ["Ciências Contábeis", "Administração", "Economia"],
        "position_titles": [
            "Analista Financeiro",
            "Assistente Contábil",
            "Analista de Orçamento",
            "Auxiliar Financeiro",
        ],
        "skills_pool": [
            "Excel avançado",
            "Conciliação",
            "Fluxo de caixa",
            "Orçamento",
            "IFRS básico",
            "Power BI",
            "Contas a pagar",
            "Auditoria interna",
        ],
        "summaries": [
            "Profissional financeiro com foco em planejamento e controles.",
            "Experiência em fechamento, conciliações e relatórios gerenciais.",
        ],
    },
    {
        "key": "education",
        "targets": ["Professor(a) de Ensino Médio", "Coordenador(a) Pedagógico", "Instrutor(a) Corporativo"],
        "courses": ["Pedagogia", "Matemática", "Letras", "História"],
        "position_titles": [
            "Professor(a)",
            "Monitor(a) de Sala",
            "Coordenador(a) Acadêmico",
            "Instrutor(a)",
        ],
        "skills_pool": [
            "Planejamento de aulas",
            "Avaliação formativa",
            "Metodologias ativas",
            "Google Classroom",
            "Didática",
            "PNLD",
            "Atendimento a famílias",
            "Sala de aula inclusiva",
        ],
        "summaries": [
            "Educador(a) com foco em aprendizagem ativa e acompanhamento de estudantes.",
            "Experiência em elaboração de planos de aula e avaliações.",
        ],
    },
    {
        "key": "legal",
        "targets": ["Advogado(a) Cível", "Analista Jurídico", "Assistente Legal"],
        "courses": ["Direito", "Relações Internacionais"],
        "position_titles": [
            "Advogado(a)",
            "Estagiário(a) Jurídico",
            "Analista de Contratos",
            "Assistente Jurídico",
        ],
        "skills_pool": [
            "Contratos",
            "Pesquisa jurisprudencial",
            "LGPD",
            "Compliance",
            "Petições",
            "Due diligence",
            "Negociação",
            "Processo civil",
        ],
        "summaries": [
            "Profissional jurídico com atenção a riscos e conformidade regulatória.",
            "Experiência em análise contratual e suporte a áreas internas.",
        ],
    },
    {
        "key": "marketing",
        "targets": ["Especialista em Marketing Digital", "Analista de Growth", "Coordenador(a) de Marca"],
        "courses": ["Publicidade e Propaganda", "Marketing", "Comunicação Social"],
        "position_titles": [
            "Analista de Marketing",
            "Assistente de Mídias Sociais",
            "Coordenador(a) de Campanhas",
            "Growth Analyst",
        ],
        "skills_pool": [
            "SEO",
            "CRM",
            "Google Ads",
            "Meta Ads",
            "Copywriting",
            "Analytics",
            "Branding",
            "Email marketing",
        ],
        "summaries": [
            "Profissional de marketing com foco em performance e conteúdo.",
            "Experiência em campanhas digitais e métricas de aquisição.",
        ],
    },
]

_SKILLS_POOL = [
    "Python",
    "Django",
    "PostgreSQL",
    "React",
    "TypeScript",
    "Docker",
    "AWS",
    "Git",
    "REST",
    "GraphQL",
    "Kubernetes",
    "Linux",
    "SQL",
    "Redis",
    "Celery",
    "Pytest",
    "CI/CD",
    "Scrum",
    "Java",
    "Spring",
    "Go",
    "Terraform",
    "Observability",
    "Product discovery",
    "API design",
]


def add_months(d: date, delta_m: int) -> date:
    y, m = d.year, d.month + delta_m
    while m > 12:
        y += 1
        m -= 12
    while m < 1:
        y -= 1
        m += 12
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def _ym(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _bullet_bank(rng: random.Random) -> list[str]:
    opts = [
        "Implementou melhorias com impacto mensurável em indicadores de equipe.",
        "Colaborou com squads multidisciplinares em ciclos curtos de entrega.",
        "Automatizou rotinas reduzindo retrabalho operacional.",
        "Documentou processos e padrões para onboarding mais rápido.",
        "Participou de revisões técnicas e definição de arquitetura.",
        "Integrou serviços internos com APIs REST e filas assíncronas.",
        "Monitorou métricas de confiabilidade e performance.",
        "Apoiou mentoria de pares em boas práticas de código.",
    ]
    rng.shuffle(opts)
    return opts


def apply_domain_mix_to_payload(
    payload: dict[str, Any],
    *,
    rng: random.Random,
    domain_content: dict[str, Any],
    domain_target: dict[str, Any],
) -> None:
    """Mutate payload: resume story from content domain, target role from target domain (may differ)."""
    tgt = domain_target
    cnt = domain_content
    targets = list(tgt.get("targets") or [])
    if targets:
        payload["target_position"] = str(rng.choice(targets))
    summaries = list(cnt.get("summaries") or [])
    if summaries:
        payload["summary"] = str(rng.choice(summaries))
    courses = list(cnt.get("courses") or [])
    edus = payload.get("educations")
    if courses and isinstance(edus, list) and edus:
        e0 = dict(edus[0])
        e0["course"] = str(rng.choice(courses))
        edus[0] = e0
        payload["educations"] = edus
    titles = list(cnt.get("position_titles") or [])
    if titles:
        for exp in payload.get("experiences") or []:
            if isinstance(exp, dict):
                exp["position"] = str(rng.choice(titles))
    pool = list(cnt.get("skills_pool") or [])
    if pool:
        rng.shuffle(pool)
        skills = payload.get("skills") or []
        n = len(skills) if skills else rng.randint(4, 14)
        payload["skills"] = [
            {
                "name": str(pool[i % len(pool)]),
                "level": rng.choice(["beginner", "intermediate", "advanced", "expert"]),
            }
            for i in range(n)
        ]


def pick_profile(index: int, profiles_mode: str, rng: random.Random) -> str:
    mode = (profiles_mode or "balanced").strip().lower()
    if mode == "balanced":
        return PROFILE_ORDER[index % 4]
    if mode == "senior_heavy":
        return rng.choices(
            list(PROFILE_ORDER),
            weights=[1, 2, 3, 6],
            k=1,
        )[0]
    if mode == "junior_heavy":
        return rng.choices(
            list(PROFILE_ORDER),
            weights=[4, 6, 3, 1],
            k=1,
        )[0]
    if mode == "intern_heavy":
        return rng.choices(
            list(PROFILE_ORDER),
            weights=[6, 3, 2, 1],
            k=1,
        )[0]
    return PROFILE_ORDER[index % 4]


def build_synthetic_resume(
    *,
    profile: str,
    rng: random.Random,
    index: int,
    base_seed: int,
    today: date | None = None,
    domain_content: dict[str, Any] | None = None,
    domain_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns dict with keys: name, target_position, summary, contact, experiences, educations, skills, languages.
    """
    today = today or date.today()
    anchor_end = today
    bullets_pool = _bullet_bank(rng)

    def take_bullets(n: int) -> list[str]:
        out = []
        for i in range(n):
            out.append(bullets_pool[i % len(bullets_pool)])
        return out

    idx = f"{base_seed}-{index:05d}"
    include_links = rng.random() < 0.35
    contact: dict[str, Any] = {
        "fullName": "Usuário Teste",
        "email": f"seed.{idx}@local.seed.invalid",
        "phone": "",
        "city": "Cidade Teste",
        "country": "BR",
    }
    if include_links:
        contact["github"] = f"https://github.com/seed-local-{base_seed % 10000}/repo-{index % 50}"
        contact["linkedin"] = f"https://linkedin.com/in/seed-local-profile-{index % 200}"

    summary_len = rng.choice(["short", "medium", "long"])
    if summary_len == "short":
        summary = "Profissional de tecnologia focado em entrega e aprendizado contínuo."
    elif summary_len == "medium":
        summary = (
            "Profissional com experiência em desenvolvimento de software, atuando em times ágeis "
            "e entregas iterativas com foco em qualidade e colaboração."
        )
    else:
        summary = (
            "Profissional com trajetória em tecnologia, combinando execução técnica e visão de produto. "
            "Experiência em ambientes colaborativos, priorização por valor e melhoria contínua de processos. "
            "Interesse em escalabilidade, observabilidade e boas práticas de engenharia."
        )

    experiences: list[dict[str, Any]] = []
    educations: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    languages = [
        {"name": "Português", "level": "native"},
        {"name": "Inglês", "level": rng.choice(["intermediate", "advanced", "fluent"])},
    ]

    n_skills = rng.randint(0, 30)
    rng.shuffle(_SKILLS_POOL)
    for si, name in enumerate(_SKILLS_POOL[:n_skills]):
        skills.append(
            {
                "name": name,
                "level": rng.choice(["beginner", "intermediate", "advanced", "expert"]),
            }
        )

    if rng.random() < 0.85:
        educations.append(
            {
                "institution": "Instituição de Ensino Teste",
                "course": "Ciência da Computação",
                "degree": "Bacharelado",
                "startDate": "2014-02",
                "endDate": "2018-12",
                "status": "completed",
            }
        )

    profile = profile.strip().lower()
    if profile not in PROFILE_ORDER:
        profile = "junior"

    if profile == "intern":
        use_internship_word = rng.random() < 0.7
        if use_internship_word:
            months = rng.randint(3, 8)
            start = add_months(anchor_end, -(months + 1))
            end = anchor_end
            experiences.append(
                {
                    "company": f"Empresa Teste {index % 40}",
                    "position": "Estágio em Engenharia de Software",
                    "startDate": _ym(start),
                    "endDate": _ym(end),
                    "isCurrent": False,
                    "description": take_bullets(rng.randint(0, 3)),
                }
            )
        else:
            months = rng.randint(4, 11)
            start = add_months(anchor_end, -(months + 1))
            end = anchor_end
            experiences.append(
                {
                    "company": f"Empresa Teste {index % 40}",
                    "position": "Assistente de Operações",
                    "startDate": _ym(start),
                    "endDate": _ym(end),
                    "isCurrent": False,
                    "description": take_bullets(rng.randint(0, 2)),
                }
            )
        target_position = "Estagiário de Tecnologia"

    elif profile == "junior":
        months = rng.randint(12, 22)
        start = add_months(anchor_end, -(months + 1))
        experiences.append(
            {
                "company": f"Empresa Teste {index % 60}",
                "position": "Desenvolvedor Júnior",
                "startDate": _ym(start),
                "endDate": _ym(anchor_end),
                "isCurrent": True,
                "description": take_bullets(rng.randint(1, 5)),
            }
        )
        target_position = "Desenvolvedor de Software"

    elif profile == "mid":
        e1_end = add_months(anchor_end, -rng.randint(14, 20))
        e1_start = add_months(e1_end, -rng.randint(14, 22))
        experiences.append(
            {
                "company": f"Empresa Alfa {index % 30}",
                "position": "Desenvolvedor Pleno",
                "startDate": _ym(e1_start),
                "endDate": _ym(e1_end),
                "isCurrent": False,
                "description": take_bullets(rng.randint(2, 6)),
            }
        )
        experiences.append(
            {
                "company": f"Empresa Beta {index % 35}",
                "position": "Engenheiro de Software",
                "startDate": _ym(add_months(e1_end, 1)),
                "endDate": _ym(anchor_end),
                "isCurrent": True,
                "description": take_bullets(rng.randint(2, 6)),
            }
        )
        target_position = "Engenheiro de Software Pleno"

    else:  # senior — long non-overlapping timeline, >=2 exp, enough bullets for policy
        n_exp = rng.choice([2, 4, 6])
        min_bullets_target = 8
        per = max(2, min_bullets_target // max(2, n_exp))
        gap = 1
        end_cur = anchor_end
        for ei in range(n_exp):
            span = rng.randint(18, 26)
            start_cur = add_months(end_cur, -span)
            is_newest = ei == 0
            nb = per + rng.randint(0, 3)
            experiences.insert(
                0,
                {
                    "company": f"Empresa Gamma {(index + ei) % 25}",
                    "position": "Engenheiro de Software Sênior" if is_newest else "Desenvolvedor",
                    "startDate": _ym(start_cur),
                    "endDate": "" if (is_newest and rng.random() < 0.6) else _ym(end_cur),
                    "isCurrent": is_newest,
                    "description": take_bullets(nb),
                },
            )
            end_cur = add_months(start_cur, -gap)
        experiences.sort(key=lambda e: e["startDate"])
        target_position = "Engenheiro de Software Sênior"

    name = f"Seed s{base_seed} {profile} {index:05d}"

    result: dict[str, Any] = {
        "name": name,
        "target_position": target_position,
        "summary": summary,
        "contact": contact,
        "experiences": experiences,
        "educations": educations,
        "skills": skills,
        "languages": languages,
        "profile": profile,
    }
    if domain_content is not None and domain_target is not None:
        apply_domain_mix_to_payload(
            result,
            rng=rng,
            domain_content=domain_content,
            domain_target=domain_target,
        )
    return result
