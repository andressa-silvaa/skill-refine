"""
Generate a large synthetic matching dataset with hard negatives.

Output:
  ml/data/matching_splits/train.jsonl
  ml/data/matching_splits/val.jsonl
  ml/data/matching_splits/test.jsonl

Usage:
  python ml/training/src/generate_matching_dataset.py
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DomainTemplate:
    name: str
    titles: dict[str, str]
    skills: list[str]
    optional_skills: list[str]
    responsibilities: list[str]
    achievements: list[str]
    job_focus: list[str]


SENIORITY_YEARS = {
    "intern": "1 ano",
    "junior": "2 anos",
    "mid": "5 anos",
    "senior": "9 anos",
}


DOMAINS: list[DomainTemplate] = [
    DomainTemplate(
        name="backend",
        titles={"intern": "Estagiario de Backend", "junior": "Desenvolvedor Backend Junior", "mid": "Engenheiro Backend Pleno", "senior": "Senior Backend Engineer"},
        skills=["Python", "Django", "FastAPI", "PostgreSQL", "Redis", "REST APIs", "Docker"],
        optional_skills=["Kafka", "Celery", "Kubernetes", "gRPC"],
        responsibilities=["desenvolvimento de APIs", "integracoes entre servicos", "otimizacao de consultas SQL", "observabilidade de servicos"],
        achievements=["reduziu latencia em 24%", "aumentou cobertura de testes para 82%", "cortou falhas em deploy em 19%"],
        job_focus=["construir APIs escalaveis", "evoluir arquitetura de servicos", "garantir performance e confiabilidade"],
    ),
    DomainTemplate(
        name="frontend",
        titles={"intern": "Estagiario de Frontend", "junior": "Frontend Developer Junior", "mid": "Frontend Engineer", "senior": "Senior Frontend Engineer"},
        skills=["React", "TypeScript", "Next.js", "CSS", "Jest", "Testing Library", "Design Systems"],
        optional_skills=["GraphQL", "Redux", "Storybook", "Cypress"],
        responsibilities=["criacao de componentes", "integracao com APIs", "acessibilidade", "otimizacao de performance do frontend"],
        achievements=["melhorou web vitals em 21%", "reduziu bugs de UI em 26%", "aumentou reutilizacao de componentes em 34%"],
        job_focus=["evoluir a experiencia do usuario", "desenvolver interfaces performaticas", "manter design system consistente"],
    ),
    DomainTemplate(
        name="data",
        titles={"intern": "Estagiario de Dados", "junior": "Analista de Dados Junior", "mid": "Data Engineer", "senior": "Senior Data Engineer"},
        skills=["SQL", "Python", "ETL", "Airflow", "dbt", "BigQuery", "Data Modeling"],
        optional_skills=["Spark", "Kafka", "Looker", "Power BI"],
        responsibilities=["construcao de pipelines", "modelagem analitica", "qualidade de dados", "orquestracao de jobs"],
        achievements=["reduziu tempo de pipeline em 31%", "melhorou SLA de dados em 18%", "automatizou 14 rotinas de ingestao"],
        job_focus=["evoluir pipelines de dados", "garantir confiabilidade analitica", "entregar dados para negocio"],
    ),
    DomainTemplate(
        name="ml",
        titles={"intern": "Estagiario de Machine Learning", "junior": "ML Engineer Junior", "mid": "Machine Learning Engineer", "senior": "Senior ML Engineer"},
        skills=["Python", "PyTorch", "Transformers", "NLP", "MLflow", "Feature Engineering", "Model Serving"],
        optional_skills=["ONNX", "Ray", "XGBoost", "MLOps"],
        responsibilities=["treino de modelos", "avaliacao offline", "serving de inferencia", "versionamento de datasets"],
        achievements=["aumentou F1 em 12 pontos", "reduziu tempo de inferencia em 27%", "automatizou validacao de modelos"],
        job_focus=["construir pipelines de ML", "servir modelos em producao", "melhorar qualidade preditiva"],
    ),
    DomainTemplate(
        name="devops",
        titles={"intern": "Estagiario de DevOps", "junior": "DevOps Engineer Junior", "mid": "DevOps Engineer", "senior": "Senior Platform Engineer"},
        skills=["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Monitoring"],
        optional_skills=["Helm", "Prometheus", "Grafana", "ArgoCD"],
        responsibilities=["automacao de infraestrutura", "pipelines de deploy", "monitoramento", "governanca de ambientes"],
        achievements=["reduziu tempo de deploy em 38%", "diminuiu incidentes em 22%", "automatizou provisionamento de ambientes"],
        job_focus=["garantir confiabilidade da plataforma", "automatizar deploys", "aumentar observabilidade"],
    ),
    DomainTemplate(
        name="qa",
        titles={"intern": "Estagiario de QA", "junior": "QA Analyst Junior", "mid": "QA Engineer", "senior": "Senior QA Engineer"},
        skills=["Testes Funcionais", "Cypress", "Playwright", "API Testing", "Test Plans", "Regression Testing", "Quality Metrics"],
        optional_skills=["Selenium", "Postman", "Contract Testing", "Performance Testing"],
        responsibilities=["automacao de testes", "planejamento de qualidade", "regressoes", "analise de defeitos"],
        achievements=["reduziu bugs criticos em 29%", "aumentou cobertura automatizada em 36%", "encurtou ciclo de homologacao em 18%"],
        job_focus=["elevar qualidade de entregas", "automatizar testes", "reduzir regressao"],
    ),
    DomainTemplate(
        name="mobile",
        titles={"intern": "Estagiario de Mobile", "junior": "Mobile Developer Junior", "mid": "Mobile Engineer", "senior": "Senior Mobile Engineer"},
        skills=["Kotlin", "Swift", "React Native", "Flutter", "Mobile CI", "REST APIs", "Performance Mobile"],
        optional_skills=["Firebase", "App Store", "Play Store", "Crashlytics"],
        responsibilities=["desenvolvimento de apps", "publicacao em lojas", "integracao com APIs", "otimizacao de performance mobile"],
        achievements=["melhorou crash free users em 17%", "reduziu tamanho do app em 14%", "acelerou startup em 21%"],
        job_focus=["evoluir aplicacoes moveis", "melhorar experiencia mobile", "garantir estabilidade em producao"],
    ),
    DomainTemplate(
        name="product",
        titles={"intern": "Estagiario de Produto", "junior": "Product Analyst", "mid": "Product Manager", "senior": "Senior Product Manager"},
        skills=["Discovery", "Roadmap", "Metrics", "Stakeholder Management", "Backlog", "Experimentation", "User Research"],
        optional_skills=["SQL", "Amplitude", "Mixpanel", "A/B Testing"],
        responsibilities=["priorizacao de backlog", "discovery", "analise de metricas", "alinhamento com negocio"],
        achievements=["aumentou conversao em 11%", "reduziu churn em 9%", "acelerou lead time de discovery"],
        job_focus=["definir estrategia de produto", "validar hipoteses", "alinhar times de negocio e engenharia"],
    ),
]


LANGUAGES = ["pt-BR", "en-US", "es-ES"]
SPLIT_RESUME_COUNTS = {
    "train": {"pt-BR": 220, "en-US": 60, "es-ES": 60},
    "val": {"pt-BR": 40, "en-US": 15, "es-ES": 15},
    "test": {"pt-BR": 40, "en-US": 15, "es-ES": 15},
}

DOMAIN_AFFINITY = {
    ("backend", "data"): 0.35,
    ("backend", "ml"): 0.30,
    ("backend", "devops"): 0.25,
    ("data", "ml"): 0.45,
    ("data", "devops"): 0.15,
    ("frontend", "mobile"): 0.40,
    ("qa", "backend"): 0.20,
    ("qa", "frontend"): 0.20,
    ("product", "frontend"): 0.18,
    ("product", "backend"): 0.12,
}


def _sample(rng: random.Random, items: list[str], k: int) -> list[str]:
    k = min(k, len(items))
    return rng.sample(items, k)


def _domain_affinity(domain_a: str, domain_b: str) -> float:
    if domain_a == domain_b:
        return 1.0
    return DOMAIN_AFFINITY.get((domain_a, domain_b)) or DOMAIN_AFFINITY.get((domain_b, domain_a)) or 0.0


def _translate(language: str, text_pt: str) -> str:
    if language == "pt-BR":
        return text_pt
    if language == "en-US":
        replacements = {
            "Experiencia": "Experience",
            "Resumo": "Summary",
            "anos": "years",
            "desenvolvimento de APIs": "API development",
            "integracoes entre servicos": "service integrations",
            "otimizacao de consultas SQL": "SQL query optimization",
            "observabilidade de servicos": "service observability",
            "construcao de pipelines": "pipeline development",
            "modelagem analitica": "analytics modeling",
            "qualidade de dados": "data quality",
            "orquestracao de jobs": "job orchestration",
            "automacao de infraestrutura": "infrastructure automation",
            "pipelines de deploy": "deployment pipelines",
            "automacao de testes": "test automation",
            "planejamento de qualidade": "quality planning",
            "desenvolvimento de apps": "mobile app development",
            "priorizacao de backlog": "backlog prioritization",
            "analise de metricas": "metrics analysis",
        }
        text = text_pt
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text
    replacements = {
        "anos": "anos",
        "desenvolvimento de APIs": "desarrollo de APIs",
        "integracoes entre servicos": "integraciones entre servicios",
        "otimizacao de consultas SQL": "optimizacion de consultas SQL",
        "observabilidade de servicos": "observabilidad de servicios",
        "construcao de pipelines": "construccion de pipelines",
        "modelagem analitica": "modelado analitico",
        "qualidade de dados": "calidad de datos",
        "orquestracao de jobs": "orquestacion de jobs",
        "automacao de infraestrutura": "automatizacion de infraestructura",
        "pipelines de deploy": "pipelines de despliegue",
        "automacao de testes": "automatizacion de pruebas",
        "planejamento de qualidade": "planificacion de calidad",
        "desenvolvimento de apps": "desarrollo de apps",
        "priorizacao de backlog": "priorizacion de backlog",
        "analise de metricas": "analisis de metricas",
    }
    text = text_pt
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def build_resume_text(
    language: str,
    seniority: str,
    domain: DomainTemplate,
    resume_idx: int,
    core_skills: list[str],
    extra_skills: list[str],
    responsibilities: list[str],
    achievements: list[str],
) -> str:
    years = SENIORITY_YEARS[seniority]
    title = domain.titles[seniority]
    text_pt = (
        f"Resumo\n{title} com {years} de experiencia em {domain.name}. "
        f"Atuacao com {', '.join(core_skills)} e apoio em {', '.join(extra_skills)}. "
        f"Experiencia Profissional\n- Responsavel por {responsibilities[0]}.\n"
        f"- Tambem atuou em {responsibilities[1]}.\n"
        f"- Alcancou resultados como {achievements[0]} e {achievements[1]}.\n"
        f"Habilidades\n{', '.join(core_skills + extra_skills)}\n"
        f"Contato\nLinkedIn: linkedin.com/in/{domain.name}-{seniority}-{resume_idx} GitHub: github.com/{domain.name}-{resume_idx}"
    )
    return _translate(language, text_pt)


def build_resume_profile(rng: random.Random, language: str, seniority: str, domain: DomainTemplate, resume_idx: int) -> dict:
    core_skills = _sample(rng, domain.skills, 4)
    extra_skills = _sample(rng, domain.optional_skills, 2)
    responsibilities = _sample(rng, domain.responsibilities, 2)
    achievements = _sample(rng, domain.achievements, 2)
    resume_text = build_resume_text(
        language,
        seniority,
        domain,
        resume_idx,
        core_skills,
        extra_skills,
        responsibilities,
        achievements,
    )
    return {
        "domain": domain.name,
        "seniority": seniority,
        "language": language,
        "resume_text": resume_text,
        "core_skills": core_skills,
        "extra_skills": extra_skills,
        "all_skills": list(dict.fromkeys(core_skills + extra_skills)),
        "responsibilities": responsibilities,
        "achievements": achievements,
    }


def build_job_text(
    language: str,
    seniority: str,
    domain: DomainTemplate,
    required: list[str],
    nice_to_have: list[str],
    focus: list[str],
    responsibilities: list[str],
) -> str:
    title = domain.titles[seniority]
    text_pt = (
        f"Vaga para {title}. Procuramos pessoa para {focus[0]} e {focus[1]}. "
        f"Requisitos obrigatorios: {', '.join(required)}. "
        f"Desejavel: {', '.join(nice_to_have)}. "
        f"Responsabilidades incluem {', '.join(responsibilities)}."
    )
    return _translate(language, text_pt)


def build_job_profile(
    rng: random.Random,
    language: str,
    seniority: str,
    domain: DomainTemplate,
    variant: int,
    hard_stack_shift: bool = False,
    shared_skills_hint: list[str] | None = None,
) -> dict:
    required = _sample(rng, domain.skills, 4)
    if shared_skills_hint:
        for idx, skill in enumerate(shared_skills_hint[: min(2, len(required))]):
            required[idx] = skill
    nice_to_have = _sample(rng, domain.optional_skills, 2)
    focus = _sample(rng, domain.job_focus, 2)
    responsibilities = _sample(rng, domain.responsibilities, 2)
    if hard_stack_shift and len(domain.optional_skills) >= 2:
        required = required[:2] + _sample(rng, domain.optional_skills, 2)
    job_text = build_job_text(language, seniority, domain, required, nice_to_have, focus, responsibilities)
    return {
        "domain": domain.name,
        "seniority": seniority,
        "language": language,
        "job_text": job_text,
        "required_skills": required,
        "nice_to_have": nice_to_have,
        "all_skills": list(dict.fromkeys(required + nice_to_have)),
        "responsibilities": responsibilities,
        "focus": focus,
    }


def score_pair(resume_profile: dict, job_profile: dict, hard_negative: bool, rng: random.Random, partial_penalty: float = 0.0) -> int:
    seniority_rank = {"intern": 0, "junior": 1, "mid": 2, "senior": 3}
    resume_domain = resume_profile["domain"]
    job_domain = job_profile["domain"]
    resume_seniority = resume_profile["seniority"]
    job_seniority = job_profile["seniority"]
    resume_skills = set(resume_profile["all_skills"])
    job_required = set(job_profile["required_skills"])
    job_all = set(job_profile["all_skills"])
    shared_required = len(resume_skills & job_required)
    shared_all = len(resume_skills & job_all)
    domain_affinity = _domain_affinity(resume_domain, job_domain)
    seniority_gap = abs(seniority_rank[resume_seniority] - seniority_rank[job_seniority])
    score = 6.0
    score += domain_affinity * 34.0
    score += min(26.0, shared_required * 8.0)
    score += min(12.0, max(0, shared_all - shared_required) * 3.0)
    if seniority_gap == 0:
        score += 12.0
    elif seniority_gap == 1:
        score += 6.0
    else:
        score -= 9.0
    if resume_domain == job_domain and resume_seniority == job_seniority:
        score += 6.0
    score -= partial_penalty
    if hard_negative:
        score -= 14.0
    score += rng.uniform(-6.0, 6.0)
    return max(0, min(100, int(round(score))))


def generate_split(split: str, rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    for language in LANGUAGES:
        for resume_idx in range(SPLIT_RESUME_COUNTS[split][language]):
            domain = rng.choice(DOMAINS)
            seniority = rng.choices(["intern", "junior", "mid", "senior"], weights=[1, 3, 4, 3], k=1)[0]
            resume_id = f"{split}_{language}_{domain.name}_{seniority}_{resume_idx:04d}"
            resume_profile = build_resume_profile(rng, language, seniority, domain, resume_idx)
            resume_text = resume_profile["resume_text"]

            # Strong positives
            for variant in range(2):
                job_profile = build_job_profile(
                    rng,
                    language,
                    seniority,
                    domain,
                    variant,
                    shared_skills_hint=resume_profile["core_skills"][:2],
                )
                score = score_pair(resume_profile, job_profile, hard_negative=False, rng=rng)
                rows.append({
                    "resume_id": resume_id,
                    "language": language,
                    "inputs": {"resume_text": resume_text, "job_text": job_profile["job_text"]},
                    "labels": {"matching_score": score},
                })

            # Partial positives: same domain, adjacent seniority or shifted stack
            adjacent_seniority = seniority
            if seniority == "junior":
                adjacent_seniority = "mid"
            elif seniority == "mid":
                adjacent_seniority = rng.choice(["junior", "senior"])
            elif seniority == "senior":
                adjacent_seniority = "mid"
            elif seniority == "intern":
                adjacent_seniority = "junior"
            for variant in range(3):
                job_profile = build_job_profile(
                    rng,
                    language,
                    adjacent_seniority,
                    domain,
                    variant,
                    hard_stack_shift=(variant % 2 == 0),
                    shared_skills_hint=resume_profile["all_skills"][:1],
                )
                score = score_pair(resume_profile, job_profile, hard_negative=False, rng=rng, partial_penalty=8.0)
                rows.append({
                    "resume_id": resume_id,
                    "language": language,
                    "inputs": {"resume_text": resume_text, "job_text": job_profile["job_text"]},
                    "labels": {"matching_score": score},
                })

            # Stretch positives: same domain but a larger seniority gap to calibrate the middle ranges.
            stretch_seniority = seniority
            if seniority == "intern":
                stretch_seniority = "mid"
            elif seniority == "junior":
                stretch_seniority = "senior"
            elif seniority == "mid":
                stretch_seniority = "intern"
            elif seniority == "senior":
                stretch_seniority = "junior"
            stretch_profile = build_job_profile(
                rng,
                language,
                stretch_seniority,
                domain,
                99,
                hard_stack_shift=True,
                shared_skills_hint=resume_profile["all_skills"][:1],
            )
            score = score_pair(resume_profile, stretch_profile, hard_negative=False, rng=rng, partial_penalty=14.0)
            rows.append({
                "resume_id": resume_id,
                "language": language,
                "inputs": {"resume_text": resume_text, "job_text": stretch_profile["job_text"]},
                "labels": {"matching_score": score},
            })

            negative_domains = [d for d in DOMAINS if d.name != domain.name]

            # Bridge matches: related domains with some stack overlap and compatible seniority.
            related_domains = [d for d in negative_domains if _domain_affinity(domain.name, d.name) >= 0.2]
            if related_domains:
                bridge_domain = rng.choice(related_domains)
                bridge_profile = build_job_profile(
                    rng,
                    language,
                    adjacent_seniority,
                    bridge_domain,
                    0,
                    hard_stack_shift=False,
                    shared_skills_hint=resume_profile["all_skills"][:2],
                )
                score = score_pair(resume_profile, bridge_profile, hard_negative=False, rng=rng, partial_penalty=6.0)
                rows.append({
                    "resume_id": resume_id,
                    "language": language,
                    "inputs": {"resume_text": resume_text, "job_text": bridge_profile["job_text"]},
                    "labels": {"matching_score": score},
                })

            # Soft negatives: nearby domain with some lexical overlap but poor semantic fit.
            for variant in range(2):
                neg_domain = rng.choice(negative_domains)
                neg_seniority = rng.choice(["junior", "mid", "senior"])
                overlap_hint = resume_profile["all_skills"][:1] if _domain_affinity(domain.name, neg_domain.name) > 0 else None
                job_profile = build_job_profile(
                    rng,
                    language,
                    neg_seniority,
                    neg_domain,
                    variant,
                    hard_stack_shift=False,
                    shared_skills_hint=overlap_hint,
                )
                score = score_pair(resume_profile, job_profile, hard_negative=False, rng=rng, partial_penalty=10.0)
                rows.append({
                    "resume_id": resume_id,
                    "language": language,
                    "inputs": {"resume_text": resume_text, "job_text": job_profile["job_text"]},
                    "labels": {"matching_score": score},
                })

            # Hard negatives: similar language tokens, wrong domain or severe seniority mismatch.
            for variant in range(2):
                neg_domain = rng.choice(negative_domains)
                neg_seniority = rng.choice(["intern", "junior", "mid", "senior"])
                overlap_hint = resume_profile["all_skills"][:2] if variant == 0 else None
                job_profile = build_job_profile(
                    rng,
                    language,
                    neg_seniority,
                    neg_domain,
                    variant,
                    hard_stack_shift=True,
                    shared_skills_hint=overlap_hint,
                )
                score = score_pair(resume_profile, job_profile, hard_negative=True, rng=rng, partial_penalty=10.0)
                rows.append({
                    "resume_id": resume_id,
                    "language": language,
                    "inputs": {"resume_text": resume_text, "job_text": job_profile["job_text"]},
                    "labels": {"matching_score": score},
                })
    return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rng = random.Random(42)
    out_dir = Path(__file__).resolve().parents[2] / "data" / "matching_splits"
    for split in ("train", "val", "test"):
        rows = generate_split(split, rng)
        write_rows(out_dir / f"{split}.jsonl", rows)
        print(f"{split}: {len(rows)} rows")


if __name__ == "__main__":
    main()
