"""
Presets de domínio e pool de skills para o seed sintético.

Tabela, não lógica: as combinações de alvo e história de currículo que o `--domain-mix balanced`
usa para gerar alinhamento e desalinhamento propositais.
"""
from __future__ import annotations

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

BULLET_BANK: tuple[str, ...] = (
    "Implementou melhorias com impacto mensurável em indicadores de equipe.",
    "Colaborou com squads multidisciplinares em ciclos curtos de entrega.",
    "Automatizou rotinas reduzindo retrabalho operacional.",
    "Documentou processos e padrões para onboarding mais rápido.",
    "Participou de revisões técnicas e definição de arquitetura.",
    "Integrou serviços internos com APIs REST e filas assíncronas.",
    "Monitorou métricas de confiabilidade e performance.",
    "Apoiou mentoria de pares em boas práticas de código.",
)
