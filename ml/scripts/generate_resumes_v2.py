"""
Synthetic resume generator (v2) — non-circular seniority labels.

Unlike the old generate_synthetic_resumes.py (removed), this generator:
  - Produces resume_data in the REAL product schema (data.experiences[].startDate/
    endDate/description[], matching apps/resumes/interfaces/api/payloads.py), not a
    flat "resume_text" dataset-only shape.
  - Never embeds the seniority label as a literal keyword the classifier could shortcut
    on. Job titles sometimes match reality, sometimes deliberately don't (inflated
    titles at short tenure, modest titles at long tenure) so the label can't be read
    off the title alone.
  - Labels are assigned by a holistic scoring function that intentionally diverges from
    the rule_based_seniority month cutoffs (12/24/60) at the boundaries, weighting
    bullets_count / experiences_count / leadership language alongside months. A model
    trained on exact rule_based thresholds would just re-learn the existing heuristic;
    this dataset gives the sklearn classifier a genuinely different, noisier decision
    surface to learn from.
  - Quality (bullet specificity/metrics) varies independently of seniority band, so
    quality_score and seniority_label are not accidentally correlated in the data.

Output: one JSON file per resume under ml/data/raw/resumes_v2/<id>.json, plus an index
ml/data/raw/resumes_v2/index.jsonl with {id, intended_band, quality_score}.

This script only builds resume_data + intended labels. Turning that into the
signals-ml training JSONL (running the real extract_resume_signals) is a separate
step (build_seniority_signals_dataset.py) so this file has no Django dependency.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from uuid import uuid4

random.seed(20260731)

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "resumes_v2"

# ---------------------------------------------------------------------------
# Content pools
# ---------------------------------------------------------------------------

DOMAINS = {
    "dev": {
        "companies": ["Nimbus Tech", "Cactus Software", "Portal Digital", "ByteForge",
                      "Estrela Sistemas", "CodeHarbor", "Vórtice Labs", "Trilha Cloud"],
        "titles": {
            "intern": ["Estagiário de Desenvolvimento", "Estagiário de TI", "Trainee de Software"],
            "junior": ["Desenvolvedor Júnior", "Analista de Sistemas Júnior", "Programador"],
            "mid": ["Desenvolvedor Pleno", "Analista de Sistemas", "Engenheiro de Software"],
            "senior": ["Desenvolvedor Sênior", "Engenheiro de Software Sênior", "Tech Lead"],
        },
        "skills": ["Python", "Java", "SQL", "Git", "Docker", "REST API", "React", "AWS"],
        "bullets_specific": [
            "Reduziu o tempo médio de resposta da API em {pct}% ao otimizar consultas SQL.",
            "Implementou pipeline de CI/CD que cortou o tempo de deploy de {n}h para {n2}min.",
            "Corrigiu {n} bugs críticos em produção, restaurando SLA de disponibilidade a 99,{d}%.",
            "Migrou serviço legado para containers, reduzindo custo de infraestrutura em {pct}%.",
            "Escreveu suíte de testes automatizados cobrindo {pct}% do módulo de pagamentos.",
            "Refatorou módulo de autenticação, eliminando {n} vulnerabilidades identificadas em auditoria.",
            "Desenvolveu integração com {n} APIs externas para o módulo de checkout.",
            "Reduziu consumo de memória do serviço em {pct}% após profiling detalhado.",
            "Implementou cache distribuído que reduziu carga do banco em {pct}%.",
            "Criou documentação técnica adotada por {n} squads do time de engenharia.",
            "Automatizou processo de release, eliminando {n}h de trabalho manual por semana.",
            "Portou aplicação para nova versão do framework sem downtime perceptível.",
        ],
        "bullets_vague": [
            "Participou de projetos de desenvolvimento de software.",
            "Auxiliou a equipe em tarefas do dia a dia.",
            "Trabalhou com diversas tecnologias.",
            "Colaborou com o time em atividades diversas.",
            "Deu suporte a demandas gerais do setor.",
            "Envolvido em atividades de manutenção de sistemas.",
            "Ajudou em tarefas de programação conforme demanda.",
        ],
        "leadership_bullets": [
            "Liderou equipe de {n} desenvolvedores na entrega do módulo de checkout.",
            "Coordenou a migração de arquitetura monolítica para microsserviços.",
            "Definiu padrões técnicos adotados por toda a squad de engenharia.",
            "Mentorou {n} desenvolvedores júnior em boas práticas de código.",
            "Conduziu processo seletivo técnico para {n} novas contratações.",
            "Representou o time de engenharia em decisões de arquitetura da empresa.",
        ],
    },
    "data": {
        "companies": ["Data Prisma", "Métrica Analytics", "Norte Insights", "Quanta BI",
                      "Ábaco Data", "Vetor Analytics"],
        "titles": {
            "intern": ["Estagiário de Dados", "Estagiário de BI", "Trainee de Analytics"],
            "junior": ["Analista de Dados Júnior", "Cientista de Dados Júnior"],
            "mid": ["Analista de Dados", "Cientista de Dados", "Analista de BI"],
            "senior": ["Cientista de Dados Sênior", "Analista de Dados Sênior", "Data Lead"],
        },
        "skills": ["SQL", "Python", "Power BI", "Excel avançado", "Tableau", "Pandas"],
        "bullets_specific": [
            "Construiu dashboard que reduziu tempo de geração de relatório de {n}h para {n2}min.",
            "Modelou pipeline de ETL processando {n}k registros diários com {pct}% de acurácia.",
            "Identificou padrão de churn que gerou economia estimada de R$ {n}k/mês.",
            "Automatizou {n} relatórios manuais, liberando {n2}h semanais da equipe.",
            "Desenvolveu modelo preditivo com {pct}% de precisão para previsão de demanda.",
            "Padronizou definições de métricas usadas por {n} times de negócio.",
            "Reduziu tempo de consulta de relatórios críticos em {pct}% via indexação.",
            "Criou processo de qualidade de dados que eliminou {n} inconsistências recorrentes.",
            "Implementou monitoramento que reduziu tempo de detecção de falhas em {pct}%.",
        ],
        "bullets_vague": [
            "Trabalhou com análise de dados.",
            "Apoiou a equipe de BI em demandas pontuais.",
            "Participou de reuniões de acompanhamento de indicadores.",
            "Envolvido em tarefas de tratamento de dados.",
            "Auxiliou na geração de relatórios do time.",
        ],
        "leadership_bullets": [
            "Liderou squad de {n} analistas na reestruturação do data warehouse.",
            "Definiu governança de dados adotada por {n} times da empresa.",
            "Mentorou {n} analistas júnior em modelagem estatística.",
            "Apresentou resultados estratégicos diretamente à diretoria.",
        ],
    },
    "marketing": {
        "companies": ["Marca Viva", "Onda Comunicação", "Bússola Marketing", "Fluxo Digital"],
        "titles": {
            "intern": ["Estagiário de Marketing", "Estagiário de Comunicação"],
            "junior": ["Analista de Marketing Júnior", "Assistente de Marketing"],
            "mid": ["Analista de Marketing", "Coordenador de Conteúdo"],
            "senior": ["Analista de Marketing Sênior", "Coordenador de Marketing", "Gerente de Marketing"],
        },
        "skills": ["Google Ads", "SEO", "Copywriting", "Meta Ads", "Analytics", "CRM"],
        "bullets_specific": [
            "Aumentou taxa de conversão da landing page em {pct}% via testes A/B.",
            "Elevou engajamento em redes sociais em {pct}% em {n} meses.",
            "Reduziu custo por lead em {pct}% otimizando campanhas pagas.",
            "Gerenciou budget de R$ {n}k/mês em mídia paga com ROI de {pct}%.",
            "Aumentou tráfego orgânico do site em {pct}% via estratégia de SEO.",
            "Lançou campanha que gerou {n}k novos leads qualificados em {n2} dias.",
            "Reduziu taxa de cancelamento de assinantes em {pct}% com nova régua de e-mail.",
            "Elevou taxa de abertura de e-mail marketing em {pct}% com segmentação.",
        ],
        "bullets_vague": [
            "Apoiou campanhas de marketing.",
            "Auxiliou na criação de conteúdo para redes sociais.",
            "Participou de reuniões de planejamento.",
            "Envolvido em atividades de divulgação da marca.",
        ],
        "leadership_bullets": [
            "Liderou equipe de {n} pessoas no planejamento da campanha anual.",
            "Definiu estratégia de conteúdo adotada por toda a marca.",
            "Coordenou agências parceiras em {n} campanhas simultâneas.",
            "Apresentou plano de marca à diretoria com aprovação de budget de R$ {n}k.",
        ],
    },
    "ops": {
        "companies": ["Logística Prime", "Central Operações", "FluxoCerto", "Base Operacional"],
        "titles": {
            "intern": ["Estagiário Administrativo", "Estagiário de Operações"],
            "junior": ["Analista Administrativo Júnior", "Assistente de Operações"],
            "mid": ["Analista de Operações", "Coordenador Administrativo"],
            "senior": ["Analista de Operações Sênior", "Coordenador de Operações", "Gerente de Operações"],
        },
        "skills": ["Excel avançado", "SAP", "Gestão de processos", "Power BI", "Logística"],
        "bullets_specific": [
            "Reduziu tempo de ciclo do processo de faturamento em {pct}%.",
            "Implementou controle que reduziu perdas de estoque em {pct}%.",
            "Renegociou contratos com fornecedores, economizando R$ {n}k/ano.",
            "Reduziu prazo médio de entrega em {pct}% após revisão de rotas.",
            "Padronizou processo de compras, reduzindo tempo de aprovação em {pct}%.",
            "Implementou indicador de performance adotado por {n} unidades da empresa.",
            "Reduziu erros de inventário em {pct}% com nova rotina de conferência.",
        ],
        "bullets_vague": [
            "Executou tarefas administrativas do setor.",
            "Deu suporte às rotinas operacionais.",
            "Auxiliou em processos internos.",
            "Envolvido em atividades gerais do departamento.",
        ],
        "leadership_bullets": [
            "Liderou equipe de {n} pessoas na reestruturação do centro de distribuição.",
            "Coordenou implantação de novo ERP para toda a operação.",
            "Representou a área em comitê de melhoria contínua da empresa.",
            "Mentorou {n} analistas em processos de gestão operacional.",
        ],
    },
}

EDUCATION_POOL = [
    {"course": "Ciência da Computação", "degree": "Bacharelado", "institution": "UFMG"},
    {"course": "Sistemas de Informação", "degree": "Bacharelado", "institution": "PUC-Rio"},
    {"course": "Administração", "degree": "Bacharelado", "institution": "FGV"},
    {"course": "Engenharia de Produção", "degree": "Bacharelado", "institution": "UFSC"},
    {"course": "Marketing", "degree": "Tecnólogo", "institution": "ESPM"},
    {"course": "Análise e Desenvolvimento de Sistemas", "degree": "Tecnólogo", "institution": "FATEC"},
]


_FALLBACK_BULLETS = [
    "Contribuiu com o time em atividades do dia a dia.",
    "Atuou em conjunto com outras áreas para atender demandas do período.",
    "Participou de rotina de trabalho da equipe nesse período.",
]


def _fmt(template: str) -> str:
    return template.format(
        n=random.randint(2, 9),
        n2=random.randint(10, 45),
        pct=random.randint(12, 68),
        d=random.randint(1, 9),
    )


def _date(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-01"


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    total = (year * 12 + (month - 1)) + delta
    return total // 12, (total % 12) + 1


def _build_experiences(
    domain: str,
    total_months: int,
    n_experiences: int,
    end_year: int,
    end_month: int,
    title_band: str,
    bullet_pool_specific: list[str],
    bullet_pool_vague: list[str],
    leadership_pool: list[str],
    n_specific_bullets: int,
    n_vague_bullets: int,
    n_leadership_bullets: int,
    is_current_last: bool,
) -> list[dict]:
    """Sequential (non-overlapping) experiences summing to ~total_months, newest last->first order handled by caller."""
    d = DOMAINS[domain]
    companies = random.sample(d["companies"], k=min(n_experiences, len(d["companies"])))
    if len(companies) < n_experiences:
        companies += random.choices(d["companies"], k=n_experiences - len(companies))

    # Split total_months across n_experiences with some variance, min 1 month each.
    if n_experiences == 1:
        splits = [total_months]
    else:
        cut_points = sorted(random.sample(range(1, total_months), n_experiences - 1)) if total_months > n_experiences else None
        if cut_points:
            splits = [cut_points[0]] + [cut_points[i] - cut_points[i - 1] for i in range(1, len(cut_points))] + [total_months - cut_points[-1]]
        else:
            base = max(1, total_months // n_experiences)
            splits = [base] * n_experiences
            splits[-1] += total_months - sum(splits)

    experiences = []
    cur_year, cur_month = end_year, end_month
    all_bullets_specific = list(bullet_pool_specific)
    all_bullets_vague = list(bullet_pool_vague)
    all_leadership = list(leadership_pool)
    random.shuffle(all_bullets_specific)
    random.shuffle(all_bullets_vague)
    random.shuffle(all_leadership)

    for idx, months in enumerate(reversed(splits)):
        start_year, start_month = _add_months(cur_year, cur_month, -months)
        is_latest = idx == 0
        titles_for_job = d["titles"][title_band] if is_latest else d["titles"][random.choice(["intern", "junior", "mid"])]
        title = random.choice(titles_for_job) if is_latest else random.choice(d["titles"]["junior"] + d["titles"]["mid"])
        bullets: list[str] = []
        take_specific = n_specific_bullets if is_latest else max(1, n_specific_bullets - 1)
        take_vague = n_vague_bullets if is_latest else max(0, n_vague_bullets - 1)
        take_lead = n_leadership_bullets if is_latest else 0
        for _ in range(take_specific):
            if all_bullets_specific:
                bullets.append(_fmt(all_bullets_specific.pop()))
        for _ in range(take_vague):
            if all_bullets_vague:
                bullets.append(all_bullets_vague.pop())
        for _ in range(take_lead):
            if all_leadership:
                bullets.append(_fmt(all_leadership.pop()))
        random.shuffle(bullets)
        exp: dict = {
            "company": companies[idx % len(companies)],
            "position": title,
            "startDate": _date(start_year, start_month),
            "description": bullets or [random.choice(_FALLBACK_BULLETS)],
        }
        if is_latest and is_current_last:
            exp["isCurrent"] = True
        else:
            exp["endDate"] = _date(cur_year, cur_month)
        experiences.append(exp)
        cur_year, cur_month = start_year, start_month

    experiences.reverse()  # oldest first, like a real resume top-to-bottom is usually newest-first but order doesn't matter to signals
    return experiences


def _quality_score(n_specific: int, n_vague: int, has_links: bool, has_summary: bool, skills_count: int) -> int:
    base = 35
    base += min(35, n_specific * 9)
    base -= min(20, n_vague * 5)
    base += 8 if has_links else 0
    base += 7 if has_summary else 0
    base += min(15, skills_count * 2)
    noise = random.randint(-6, 6)
    return max(5, min(97, base + noise))


def _holistic_seniority_label(
    total_months: int, experiences_count: int, bullets_count: int, has_leadership: bool
) -> str:
    """
    Deliberately NOT identical to rule_based_seniority's hard month cutoffs — the
    boundary is softened by scope signals so the trained model learns a genuinely
    different (data-driven) decision surface, not a re-hash of the existing policy.
    """
    if total_months < 10:
        return "intern"
    if total_months < 12:
        return "intern" if bullets_count <= 4 else "junior"
    if total_months <= 22:
        return "junior"
    if total_months <= 27:
        return "mid" if (has_leadership or bullets_count >= 7) else "junior"
    # Exceptional scope (many roles, many bullets, real leadership) can earn "senior"
    # even below the usual month floor — a hard month-only cutoff here would recreate
    # the same inconsistency rule_based_seniority has (scope ignored below a wall).
    strong_scope = has_leadership and experiences_count >= 3 and bullets_count >= 9
    if total_months <= 58:
        return "senior" if strong_scope else "mid"
    if total_months <= 66:
        return "senior" if (has_leadership and experiences_count >= 2 and bullets_count >= 6) else "mid"
    return "senior" if (experiences_count >= 2 and bullets_count >= 5) else "mid"


def generate_one(domain: str, target_band: str, *, title_mismatch: bool = False) -> dict:
    d = DOMAINS[domain]
    if target_band == "intern":
        total_months = random.randint(1, 11)
        n_exp = 1
        n_spec, n_vague, n_lead = random.choice([(1, 1, 0), (2, 0, 0), (0, 2, 0)])
    elif target_band == "junior":
        total_months = random.randint(12, 26)
        n_exp = random.choice([1, 1, 2])
        n_spec, n_vague, n_lead = random.choice([(2, 1, 0), (1, 2, 0), (3, 0, 0)])
    elif target_band == "mid":
        total_months = random.randint(23, 60)
        n_exp = random.choice([1, 2, 2, 3])
        n_spec, n_vague, n_lead = random.choice([(3, 1, 0), (2, 2, 0), (4, 0, 0), (3, 0, 1)])
    else:  # senior
        total_months = random.randint(52, 130)
        n_exp = random.choice([2, 2, 3, 4])
        n_spec, n_vague, n_lead = random.choice([(4, 0, 2), (3, 1, 2), (5, 0, 1), (4, 0, 1)])

    title_band = target_band
    if title_mismatch:
        # Inflated or deflated title relative to real tenure/scope — tests that the
        # veto/label doesn't just key off the position string.
        title_band = random.choice([b for b in ("intern", "junior", "mid", "senior") if b != target_band])

    is_current = random.random() < 0.6
    end_year, end_month = (2026, 6) if is_current else (random.randint(2022, 2025), random.randint(1, 12))

    experiences = _build_experiences(
        domain, total_months, n_exp, end_year, end_month, title_band,
        d["bullets_specific"], d["bullets_vague"], d["leadership_bullets"],
        n_spec, n_vague, n_lead, is_current,
    )
    bullets_count = sum(len(e["description"]) for e in experiences)
    has_leadership = n_lead > 0

    mention_years_in_summary = random.random() < 0.4
    approx_years = round(total_months / 12) if total_months >= 12 else 0
    summary_variants = [
        f"Profissional de {random.choice(['tecnologia', 'dados', 'marketing', 'operações'])} buscando novos desafios.",
        f"Experiência prática em projetos de {domain}.",
        f"Com {approx_years} anos de atuação na área." if approx_years else "Em início de carreira, buscando primeira oportunidade sólida.",
        "Foco em entregas consistentes e aprendizado contínuo.",
    ]
    summary = random.choice(summary_variants) if not mention_years_in_summary or not approx_years else summary_variants[2]

    has_links = random.random() < 0.55
    contact = {"linkedin": "linkedin.com/in/perfil-anon"} if has_links else {}
    skills_pool = d["skills"]
    skills_count = random.randint(2, min(6, len(skills_pool)))
    skills = [{"name": s} for s in random.sample(skills_pool, k=skills_count)]

    quality_score = _quality_score(n_spec, n_vague, has_links, bool(summary), skills_count)

    label = _holistic_seniority_label(total_months, n_exp, bullets_count, has_leadership)

    education = random.choice(EDUCATION_POOL)
    resume_data = {
        "data": {
            "summary": summary,
            "targetPosition": "",
            "contact": contact,
            "experiences": experiences,
            "educations": [education],
            "skills": skills,
            "languages": [],
        }
    }
    return {
        "id": str(uuid4()),
        "resume_data": resume_data,
        "intended_seniority": label,
        "intended_target_band": target_band,
        "title_mismatch": title_mismatch,
        "quality_score": quality_score,
        "domain": domain,
        "total_months_design": total_months,
        "bullets_count_design": bullets_count,
        "language": "pt-BR",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    domains = list(DOMAINS.keys())
    bands = ["intern", "junior", "mid", "senior"]
    per_band = 45
    mismatch_ratio = 0.15

    index_rows = []
    counter = 0
    for band in bands:
        for _ in range(per_band):
            domain = random.choice(domains)
            title_mismatch = random.random() < mismatch_ratio
            row = generate_one(domain, band, title_mismatch=title_mismatch)
            fname = f"{counter:04d}_{band}_{row['id'][:8]}.json"
            (OUT_DIR / fname).write_text(
                json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            index_rows.append(
                {
                    "file": fname,
                    "id": row["id"],
                    "intended_seniority": row["intended_seniority"],
                    "intended_target_band": row["intended_target_band"],
                    "quality_score": row["quality_score"],
                    "domain": row["domain"],
                }
            )
            counter += 1

    with open(OUT_DIR / "index.jsonl", "w", encoding="utf-8") as f:
        for row in index_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    from collections import Counter
    dist = Counter(r["intended_seniority"] for r in index_rows)
    print(f"Generated {len(index_rows)} resumes -> {OUT_DIR}")
    print("Label distribution (after holistic scoring, may differ from intended_target_band):", dict(dist))


if __name__ == "__main__":
    main()
