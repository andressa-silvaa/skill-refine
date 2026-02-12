"""
Generate synthetic resumes for the ML pipeline (PT-BR first; EN/ES ready).
No PII: fictional names, placeholder links, optional "bad" resumes for class balance.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

LANGUAGES = ("pt", "en", "es")
SENIORITIES = ("intern", "junior", "mid", "senior")
SOURCES = ("synthetic",)

# Seniority -> (years_range, role_keyword by lang). Used when balance_seniority=True
SENIORITY_YEARS = {"intern": (0, 1), "junior": (1, 3), "mid": (3, 6), "senior": (6, 15)}
SENIORITY_KEYWORDS = {
    "pt": {"intern": "Estagiário", "junior": "Desenvolvedor Júnior", "mid": "Analista Pleno", "senior": "Engenheiro Sênior"},
    "en": {"intern": "Intern", "junior": "Junior Developer", "mid": "Mid-Level Analyst", "senior": "Senior Engineer"},
    "es": {"intern": "Practicante", "junior": "Desarrollador Junior", "mid": "Analista Semi-Senior", "senior": "Ingeniero Senior"},
}

# PT-BR templates (priority)
TEMPLATES_PT = {
    "summary_good": "Profissional com {years} anos de experiência em {area}. Foco em {focus}. {role}.",
    "summary_good_no_role": "Profissional com {years} anos de experiência em {area}. Foco em {focus}.",
    "summary_bad": "Busco oportunidade na área.",
    "experience_bullet_metrics": "Liderou projeto que aumentou {metric} em {pct}% em 1 ano.",
    "experience_bullet_verbs": "Desenvolveu e manteve sistemas críticos; coordenou equipe de {n} pessoas.",
    "experience_bullet_vague": "Trabalhou em projetos diversos.",
    "education": "Bacharelado em {field}, {institution}.",
    "skills": "{skills}",
    "contact_placeholder": "E-mail: [EMAIL] | Telefone: [PHONE] | LinkedIn: [LINK_LINKEDIN] | GitHub: [LINK_GITHUB]",
}

TEMPLATES_EN = {
    "summary_good": "Professional with {years} years of experience in {area}. Focus on {focus}. {role}.",
    "summary_good_no_role": "Professional with {years} years of experience in {area}. Focus on {focus}.",
    "summary_bad": "Seeking opportunity in the field.",
    "experience_bullet_metrics": "Led project that increased {metric} by {pct}% in 1 year.",
    "experience_bullet_verbs": "Developed and maintained critical systems; coordinated team of {n} people.",
    "experience_bullet_vague": "Worked on various projects.",
    "education": "Bachelor's in {field}, {institution}.",
    "skills": "{skills}",
    "contact_placeholder": "Email: [EMAIL] | Phone: [PHONE] | LinkedIn: [LINK_LINKEDIN] | GitHub: [LINK_GITHUB]",
}

TEMPLATES_ES = {
    "summary_good": "Profesional con {years} años de experiencia en {area}. Enfoque en {focus}. {role}.",
    "summary_good_no_role": "Profesional con {years} años de experiencia en {area}. Enfoque en {focus}.",
    "summary_bad": "Busco oportunidad en el área.",
    "experience_bullet_metrics": "Lideró proyecto que aumentó {metric} en {pct}% en 1 año.",
    "experience_bullet_verbs": "Desarrolló y mantuvo sistemas críticos; coordinó equipo de {n} personas.",
    "experience_bullet_vague": "Trabajó en diversos proyectos.",
    "education": "Licenciatura en {field}, {institution}.",
    "skills": "{skills}",
    "contact_placeholder": "Email: [EMAIL] | Teléfono: [PHONE] | LinkedIn: [LINK_LINKEDIN] | GitHub: [LINK_GITHUB]",
}

TEMPLATES = {"pt": TEMPLATES_PT, "en": TEMPLATES_EN, "es": TEMPLATES_ES}

# Fictional data (no PII)
AREAS_PT = ["desenvolvimento de software", "ciência de dados", "produto", "design", "engenharia"]
AREAS_EN = ["software development", "data science", "product", "design", "engineering"]
AREAS_ES = ["desarrollo de software", "ciencia de datos", "producto", "diseño", "ingeniería"]
FIELDS_PT = ["Ciência da Computação", "Engenharia", "Matemática", "Design"]
FIELDS_EN = ["Computer Science", "Engineering", "Mathematics", "Design"]
FIELDS_ES = ["Ciencia de la Computación", "Ingeniería", "Matemáticas", "Diseño"]
INSTITUTIONS = ["Universidade X", "University Y", "Instituto Z"]
SKILLS_PT = ["Python", "SQL", "React", "Django", "AWS", "Docker", "Git", "Análise de dados"]
SKILLS_EN = ["Python", "SQL", "React", "Django", "AWS", "Docker", "Git", "Data analysis"]
SKILLS_ES = ["Python", "SQL", "React", "Django", "AWS", "Docker", "Git", "Análisis de datos"]

SECTION_HEADERS_PT = {"summary": "Resumo", "experience": "Experiência Profissional", "education": "Formação", "skills": "Habilidades", "contact": "Contato"}
SECTION_HEADERS_EN = {"summary": "Summary", "experience": "Work Experience", "education": "Education", "skills": "Skills", "contact": "Contact"}
SECTION_HEADERS_ES = {"summary": "Resumen", "experience": "Experiencia Profesional", "education": "Formación", "skills": "Habilidades", "contact": "Contacto"}


def _pick(rng: random.Random, *args: list) -> str:
    return rng.choice(args[0]) if args else ""


def generate_one(
    language: str = "pt",
    seniority: str = "mid",
    include_metrics: bool = True,
    include_links: bool = True,
    include_action_verbs: bool = True,
    resume_id: str | None = None,
    seed: int | None = None,
) -> dict:
    """
    Generate one synthetic resume. No PII; placeholders for email/phone/links.
    Returns dict: id, resume_id, language, resume_text, sections, source, created_at, and derived flags.
    """
    rng = random.Random(seed)
    lang = language if language in LANGUAGES else "pt"
    templates = TEMPLATES.get(lang, TEMPLATES_PT)
    areas = AREAS_PT if lang == "pt" else (AREAS_EN if lang == "en" else AREAS_ES)
    fields = FIELDS_PT if lang == "pt" else (FIELDS_EN if lang == "es" else FIELDS_ES)
    skills_list = SKILLS_PT if lang == "pt" else (SKILLS_EN if lang == "es" else SKILLS_ES)
    headers = SECTION_HEADERS_PT if lang == "pt" else (SECTION_HEADERS_EN if lang == "en" else SECTION_HEADERS_ES)

    rid = resume_id or str(uuid4())
    # Align years with seniority when provided (for learnable signals)
    min_y, max_y = SENIORITY_YEARS.get(seniority, (3, 6))
    years = rng.randint(min_y, max_y) if max_y > 0 else 0
    area = rng.choice(areas)
    focus = rng.choice(["entrega de valor", "qualidade", "liderança técnica"]) if lang == "pt" else (rng.choice(["delivery", "quality", "tech leadership"]) if lang == "en" else rng.choice(["entrega", "calidad", "liderazgo técnico"]))
    n_people = rng.randint(3, 15)
    metric = "receita" if lang == "pt" else ("revenue" if lang == "en" else "ingresos")
    pct = rng.randint(10, 50)
    field = rng.choice(fields)
    institution = rng.choice(INSTITUTIONS)
    num_skills = rng.randint(4, 8)
    skills = ", ".join(rng.sample(skills_list, num_skills))

    # Summary (include seniority keyword for heuristic alignment)
    role = SENIORITY_KEYWORDS.get(lang, SENIORITY_KEYWORDS["pt"]).get(seniority, "")
    if include_action_verbs and include_metrics:
        tpl = templates.get("summary_good", templates["summary_good_no_role"])
        summary = tpl.format(years=years, area=area, focus=focus, role=role)
    else:
        summary = templates["summary_bad"]

    # Experience bullets
    bullets = []
    if include_action_verbs:
        bullets.append(templates["experience_bullet_verbs"].format(n=n_people))
    if include_metrics:
        bullets.append(templates["experience_bullet_metrics"].format(metric=metric, pct=pct))
    if not bullets or rng.random() < 0.3:
        bullets.append(templates["experience_bullet_vague"])

    education = templates["education"].format(field=field, institution=institution)
    skills_block = templates["skills"].format(skills=skills)
    contact = templates["contact_placeholder"] if include_links else "E-mail: [EMAIL] | Telefone: [PHONE]"

    parts = [
        headers["summary"],
        summary,
        "",
        headers["experience"],
        "\n".join(f"• {b}" for b in bullets),
        "",
        headers["education"],
        education,
        "",
        headers["skills"],
        skills_block,
        "",
        headers["contact"],
        contact,
    ]
    resume_text = "\n".join(parts)

    sections = {
        "summary": summary,
        "experience": "\n".join(f"• {b}" for b in bullets),
        "education": education,
        "skills": skills_block,
        "contact": contact,
    }

    heuristics = {
        "has_metrics": include_metrics,
        "has_links": include_links,
        "has_action_verbs": include_action_verbs,
    }

    return {
        "id": str(uuid4()),
        "resume_id": rid,
        "language": lang,
        "resume_text": resume_text,
        "sections": sections,
        "labels": {"seniority": seniority},
        "heuristics": heuristics,
        "source": "synthetic",
        "label_source": "synthetic",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run(
    count: int = 100,
    language: str = "pt",
    balance_bad: bool = True,
    bad_ratio: float = 0.2,
    balance_seniority: bool = False,
    seed: int = 42,
    output: Path | None = None,
) -> list[dict]:
    """
    Generate count synthetic resumes. If balance_bad, bad_ratio are "bad" (no metrics, vague).
    If balance_seniority, distribute evenly across intern, junior, mid, senior.
    """
    rng = random.Random(seed)
    out: list[dict] = []
    n_bad = int(count * bad_ratio) if balance_bad else 0
    n_good = count - n_bad

    def seniority_iter():
        if balance_seniority:
            per_class = max(1, n_good // len(SENIORITIES))
            for s in SENIORITIES:
                for _ in range(per_class):
                    yield s
            # Fill remainder
            remainder = n_good - per_class * len(SENIORITIES)
            for i in range(remainder):
                yield SENIORITIES[i % len(SENIORITIES)]
        else:
            for _ in range(n_good):
                yield rng.choice(SENIORITIES)

    seniorities = list(seniority_iter())[:n_good]
    for i, s in enumerate(seniorities):
        rec = generate_one(
            language=language,
            seniority=s,
            include_metrics=True,
            include_links=rng.random() > 0.2,
            include_action_verbs=True,
            seed=seed + i,
        )
        out.append(rec)
    for i in range(n_bad):
        s = SENIORITIES[i % len(SENIORITIES)] if balance_seniority else rng.choice(SENIORITIES)
        rec = generate_one(
            language=language,
            seniority=s,
            include_metrics=False,
            include_links=False,
            include_action_verbs=False,
            seed=seed + 1000 + i,
        )
        out.append(rec)
    rng.shuffle(out)
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            for rec in out:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Generate synthetic resumes (PT-BR first)")
    p.add_argument("-n", "--count", type=int, default=50)
    p.add_argument("--language", type=str, default="pt", choices=list(LANGUAGES))
    p.add_argument("--no-balance-bad", action="store_true", help="Do not add bad resumes")
    p.add_argument("--bad-ratio", type=float, default=0.2)
    p.add_argument("--balance-seniority", action="store_true", help="Balance counts across intern/junior/mid/senior")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("-o", "--output", type=Path, help="Output JSONL path")
    args = p.parse_args()
    run(
        count=args.count,
        language=args.language,
        balance_bad=not args.no_balance_bad,
        bad_ratio=args.bad_ratio,
        balance_seniority=args.balance_seniority,
        seed=args.seed,
        output=args.output,
    )
    print(f"Generated {args.count} synthetic resumes ({args.language})", flush=True)


if __name__ == "__main__":
    main()
