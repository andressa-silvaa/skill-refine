"""Append curated multilingual seniority examples focused on boundary cases.

Usage:
  python ml/training/src/expand_seniority_dataset.py
"""
from __future__ import annotations

import json
from pathlib import Path


SPLIT_VARIANTS = {
    "train.jsonl": {"pt-BR": 2, "en-US": 4, "es-ES": 4},
    "val.jsonl": {"pt-BR": 1, "en-US": 2, "es-ES": 2},
    "test.jsonl": {"pt-BR": 1, "en-US": 2, "es-ES": 2},
}

DOMAIN_TEMPLATES = [
    {
        "slug": "backend",
        "pt": "backend, APIs e integrações",
        "en": "backend services, APIs and integrations",
        "es": "backend, APIs e integraciones",
    },
    {
        "slug": "frontend",
        "pt": "frontend, componentes e experiência do usuário",
        "en": "frontend interfaces, components and user experience",
        "es": "frontend, componentes y experiencia de usuario",
    },
    {
        "slug": "data",
        "pt": "pipelines de dados e analytics",
        "en": "data pipelines and analytics",
        "es": "pipelines de datos y analítica",
    },
    {
        "slug": "devops",
        "pt": "plataforma, cloud e automação",
        "en": "platform engineering, cloud and automation",
        "es": "plataforma, nube y automatización",
    },
    {
        "slug": "qa",
        "pt": "qualidade, automação de testes e releases",
        "en": "quality engineering, automated testing and releases",
        "es": "calidad, automatización de pruebas y releases",
    },
    {
        "slug": "ml",
        "pt": "machine learning, NLP e serving",
        "en": "machine learning, NLP and model serving",
        "es": "machine learning, NLP y serving",
    },
]

YEARS_BY_LEVEL = {
    "intern": {"pt-BR": "11 meses", "en-US": "11 months", "es-ES": "11 meses"},
    "junior": {"pt-BR": "2 anos e 8 meses", "en-US": "2 years and 8 months", "es-ES": "2 años y 8 meses"},
    "mid": {"pt-BR": "4 anos e 9 meses", "en-US": "4 years and 9 months", "es-ES": "4 años y 9 meses"},
    "senior": {"pt-BR": "8 anos e 6 meses", "en-US": "8 years and 6 months", "es-ES": "8 años y 6 meses"},
}


def _build_text(language: str, seniority: str, domain: dict[str, str], variant: int) -> str:
    area = domain["pt" if language == "pt-BR" else ("en" if language == "en-US" else "es")]
    years = YEARS_BY_LEVEL[seniority][language]
    if language == "pt-BR":
        if seniority == "intern":
            return (
                f"Estagiário com {years} de experiência em {area}. "
                f"Apoio em tarefas operacionais, documentação, testes básicos e pequenos ajustes. "
                f"Atua sob supervisão do time, sem liderança ou definição de arquitetura. Variante {variant}."
            )
        if seniority == "junior":
            return (
                f"Desenvolvedor júnior com {years} de experiência em {area}. "
                f"Entrega funcionalidades, corrige bugs, mantém serviços e participa de code review como aprendiz. "
                f"Ainda não lidera pessoas, mas já executa demandas com autonomia limitada. Variante {variant}."
            )
        if seniority == "mid":
            return (
                f"Engenheira pleno com {years} de experiência em {area}. "
                f"Conduz entregas técnicas com autonomia, propõe soluções, faz code review e orienta colegas menos experientes quando necessário. "
                f"Atua em decisões de implementação, sem responsabilidade ampla de arquitetura. Variante {variant}."
            )
        return (
            f"Especialista sênior com {years} de experiência em {area}. "
            f"Define arquitetura, lidera decisões técnicas, orienta o time e coordena entregas entre squads e stakeholders. "
            f"É referência técnica em iniciativas críticas e governa padrões da plataforma. Variante {variant}."
        )
    if language == "en-US":
        if seniority == "intern":
            return (
                f"Intern with {years} of experience in {area}. "
                f"Supports operational tasks, documentation, basic testing and small fixes. "
                f"Works under close supervision and has no ownership of architecture or leadership responsibilities. Variant {variant}."
            )
        if seniority == "junior":
            return (
                f"Junior engineer with {years} of experience in {area}. "
                f"Delivers features, fixes bugs, maintains services and joins code reviews as an individual contributor. "
                f"Does not mentor others yet, but handles scoped tasks with growing autonomy. Variant {variant}."
            )
        if seniority == "mid":
            return (
                f"Mid-level engineer with {years} of experience in {area}. "
                f"Owns technical deliveries, proposes implementation paths, reviews code and supports onboarding for newer teammates. "
                f"Operates independently on execution, without being the main architecture owner. Variant {variant}."
            )
        return (
            f"Senior engineer with {years} of experience in {area}. "
            f"Drives architecture decisions, mentors the team and coordinates delivery across squads and stakeholders. "
            f"Acts as a technical reference for cross-team initiatives and long-term platform direction. Variant {variant}."
        )
    if seniority == "intern":
        return (
            f"Practicante con {years} de experiencia en {area}. "
            f"Apoya tareas operativas, documentación, pruebas básicas y pequeños ajustes. "
            f"Trabaja bajo supervisión y no lidera iniciativas ni decisiones de arquitectura. Variante {variant}."
        )
    if seniority == "junior":
        return (
            f"Desarrollador junior con {years} de experiencia en {area}. "
            f"Entrega funcionalidades, corrige bugs, mantiene servicios y participa en code review como contribuidor individual. "
            f"Aún no lidera personas, pero ejecuta tareas acotadas con autonomía creciente. Variante {variant}."
        )
    if seniority == "mid":
        return (
            f"Ingeniera semi-senior con {years} de experiencia en {area}. "
            f"Conduce entregas técnicas con autonomía, propone soluciones, revisa código y apoya a perfiles menos experimentados. "
            f"Toma decisiones de implementación sin ser la principal dueña de la arquitectura. Variante {variant}."
        )
    return (
        f"Especialista senior con {years} de experiencia en {area}. "
        f"Define arquitectura, guía decisiones técnicas, mentorea al equipo y coordina entregas con varios squads y stakeholders. "
        f"Es referencia técnica en iniciativas críticas y establece estándares de plataforma. Variante {variant}."
    )


def _quality_labels(seniority: str, variant: int) -> tuple[int, str]:
    if seniority == "intern":
        score = 42 + (variant % 3) * 4
    elif seniority == "junior":
        score = 48 + (variant % 4) * 4
    elif seniority == "mid":
        score = 55 + (variant % 4) * 5
    else:
        score = 60 + (variant % 4) * 5
    if score < 40:
        level = "poor"
    elif score < 60:
        level = "ok"
    else:
        level = "strong"
    return score, level


def _generated_examples(filename: str) -> list[dict]:
    rows: list[dict] = []
    split = filename.replace(".jsonl", "")
    for language, variants in SPLIT_VARIANTS[filename].items():
        for domain in DOMAIN_TEMPLATES:
            for seniority in ("intern", "junior", "mid", "senior"):
                for variant in range(variants):
                    rows.append(
                        {
                            "resume_id": f"{split}_seniority_{language}_{domain['slug']}_{seniority}_{variant:02d}",
                            "resume_text": _build_text(language, seniority, domain, variant),
                            "labels": {
                                "seniority": seniority,
                                "quality_score": _quality_labels(seniority, variant)[0],
                                "quality_level": _quality_labels(seniority, variant)[1],
                            },
                            "language": language,
                        }
                    )
    return rows


def _upsert_rows(path: Path, rows: list[dict]) -> tuple[int, int]:
    existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    replacements = {row["resume_id"]: row for row in rows}
    seen: set[str] = set()
    changed = 0
    output: list[dict] = []
    for record in existing:
        resume_id = str(record.get("resume_id") or "")
        replacement = replacements.get(resume_id)
        if replacement is not None:
            output.append(replacement)
            seen.add(resume_id)
            changed += 1
        else:
            output.append(record)
    for row in rows:
        if row["resume_id"] in seen:
            continue
        output.append(row)
        changed += 1
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in output) + "\n", encoding="utf-8")
    return changed, len(output)


def main() -> None:
    splits_dir = Path(__file__).resolve().parents[2] / "data" / "splits"
    for filename in ("train.jsonl", "val.jsonl", "test.jsonl"):
        path = splits_dir / filename
        changed, total = _upsert_rows(path, _generated_examples(filename))
        print(f"{filename}: changed={changed} total={total}")


if __name__ == "__main__":
    main()
