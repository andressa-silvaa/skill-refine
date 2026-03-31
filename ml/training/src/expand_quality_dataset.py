"""
Append curated pt-BR quality examples focused on class balance and contrastive cases.

Usage:
  python ml/training/src/expand_quality_dataset.py
"""
from __future__ import annotations

import json
from pathlib import Path


def _normalize_quality_level(level: str, score: int | float) -> str:
    level = str(level or "").strip().lower()
    if level in {"poor", "ok", "strong"}:
        return level
    if level in {"good", "excellent"}:
        return "strong"
    score = float(score)
    if score < 40:
        return "poor"
    if score < 60:
        return "ok"
    return "strong"


DATASET: dict[str, list[dict]] = {
    "train.jsonl": [
        {"resume_id": "tr_quality_boost_pt_01", "level": "poor", "score": 26, "seniority": "senior", "text": "Engenheiro sênior com 9 anos. Experiência em sistemas, liderança, arquitetura e tecnologia. Atuação em projetos importantes, apoio ao time e participação em reuniões estratégicas."},
        {"resume_id": "tr_quality_boost_pt_02", "level": "poor", "score": 28, "seniority": "mid", "text": "Analista pleno com 5 anos. Atuação em suporte, manutenção e demandas do negócio. Conhecimentos em banco de dados, APIs e documentação. Participação em sprints e alinhamentos."},
        {"resume_id": "tr_quality_boost_pt_03", "level": "poor", "score": 30, "seniority": "junior", "text": "Desenvolvedor júnior com 2 anos. Manutenção de sistemas legados, correção de falhas e atendimento de chamados. Conhecimento em Java, SQL e versionamento."},
        {"resume_id": "tr_quality_boost_pt_04", "level": "poor", "score": 24, "seniority": "intern", "text": "Estagiária de QA com 10 meses. Testes manuais, documentação de bugs e apoio ao time. Noções de sistemas web e organização de planilhas."},
        {"resume_id": "tr_quality_boost_pt_05", "level": "poor", "score": 33, "seniority": "senior", "text": "Tech lead com 11 anos. Responsável por times, arquitetura, decisões de plataforma e relacionamento com áreas internas. Vivência em cloud, microsserviços e governança."},
        {"resume_id": "tr_quality_boost_pt_06", "level": "poor", "score": 31, "seniority": "mid", "text": "Engenheira de software pleno com 4 anos. Desenvolvimento de serviços internos, refinamentos técnicos, code review e acompanhamento de entregas com produto."},
        {"resume_id": "tr_quality_boost_pt_07", "level": "poor", "score": 29, "seniority": "junior", "text": "Analista de BI júnior com 2 anos. Construção de dashboards, consultas SQL e contato com usuários internos para ajustes de relatórios."},
        {"resume_id": "tr_quality_boost_pt_08", "level": "poor", "score": 35, "seniority": "intern", "text": "Estagiário de dados com 1 ano. Limpeza de planilhas, consultas simples e apoio ao time. Conhecimento básico em Excel, SQL e Python."},
        {"resume_id": "tr_quality_boost_pt_09", "level": "poor", "score": 37, "seniority": "senior", "text": "Arquiteta sênior com 12 anos. Liderança técnica, definição de arquitetura e apoio a múltiplos times. Participação em decisões corporativas e fóruns de tecnologia."},
        {"resume_id": "tr_quality_boost_pt_10", "level": "poor", "score": 34, "seniority": "mid", "text": "SRE pleno com 5 anos. Monitoramento, resposta a incidentes, manutenção de scripts e operação de ambientes em nuvem."},
        {"resume_id": "tr_quality_boost_pt_11", "level": "poor", "score": 27, "seniority": "junior", "text": "Desenvolvedora frontend júnior com 2 anos. Criação de telas, correções visuais e integração com APIs sob supervisão."},
        {"resume_id": "tr_quality_boost_pt_12", "level": "poor", "score": 32, "seniority": "intern", "text": "Trainee de infraestrutura com 9 meses. Atendimento de chamados, configuração inicial de acessos e documentação operacional."},
        {"resume_id": "tr_quality_boost_pt_13", "level": "ok", "score": 46, "seniority": "senior", "text": "Especialista sênior com 10 anos. Liderança técnica, arquitetura e gestão de prioridades em produtos digitais. Experiência com APIs, cloud e integração entre times."},
        {"resume_id": "tr_quality_boost_pt_14", "level": "ok", "score": 49, "seniority": "mid", "text": "Analista pleno com 4 anos. Entrega de funcionalidades, alinhamento com produto e apoio técnico ao time. Conhecimento em sistemas web e banco de dados."},
        {"resume_id": "tr_quality_boost_pt_15", "level": "ok", "score": 52, "seniority": "junior", "text": "Desenvolvedor júnior com 3 anos. Implementação de APIs, correção de bugs e participação em refinamentos. Conhecimentos em Python, Django e SQL."},
        {"resume_id": "tr_quality_boost_pt_16", "level": "ok", "score": 55, "seniority": "intern", "text": "Estagiária de produto com 1 ano. Organização de backlog, testes de funcionalidades e documentação de fluxos internos."},
        {"resume_id": "tr_quality_boost_pt_17", "level": "ok", "score": 58, "seniority": "senior", "text": "Gerente de engenharia com 12 anos. Liderança de times, planejamento técnico e comunicação com stakeholders. Background em cloud, arquitetura e delivery."},
        {"resume_id": "tr_quality_boost_pt_18", "level": "ok", "score": 50, "seniority": "mid", "text": "Engenheira de dados pleno com 5 anos. Desenvolvimento de pipelines, monitoramento de jobs e interface com áreas de negócio."},
        {"resume_id": "tr_quality_boost_pt_19", "level": "ok", "score": 47, "seniority": "junior", "text": "QA júnior com 2 anos. Execução de regressões, registro de bugs e automação inicial com Cypress."},
        {"resume_id": "tr_quality_boost_pt_20", "level": "ok", "score": 53, "seniority": "intern", "text": "Estagiário backend com 11 meses. Scripts internos em Python, pequenos ajustes em APIs e testes unitários simples."},
        {"resume_id": "tr_quality_boost_pt_21", "level": "good", "score": 66, "seniority": "senior", "text": "Arquiteto sênior com 10 anos. Defini arquitetura de integrações críticas, conduzi revisões técnicas e documentei padrões para 3 squads. Reduzi retrabalho em 17%."},
        {"resume_id": "tr_quality_boost_pt_22", "level": "good", "score": 69, "seniority": "mid", "text": "Engenheira de software pleno com 4 anos. Implementei 8 endpoints REST, automatizei testes de contrato e reduzi o tempo de deploy em 15%. GitHub: github.com/dev-marina."},
        {"resume_id": "tr_quality_boost_pt_23", "level": "good", "score": 72, "seniority": "junior", "text": "Desenvolvedor júnior com 2 anos e meio. Entreguei 11 melhorias em APIs, removi 23 bugs repetidos e mantive documentação técnica atualizada. LinkedIn: linkedin.com/in/junior-api."},
        {"resume_id": "tr_quality_boost_pt_24", "level": "good", "score": 70, "seniority": "intern", "text": "Estagiária de dados com 1 ano. Criei 9 dashboards, automatizei planilhas com Python e documentei indicadores do time. GitHub: github.com/estag-dados."},
        {"resume_id": "tr_quality_boost_pt_25", "level": "good", "score": 75, "seniority": "senior", "text": "Tech lead com 9 anos. Coordenei a entrega de uma plataforma interna, defini padrões de observabilidade e reduzi incidentes em 18%. Portfolio: portfolio.dev/leadops."},
        {"resume_id": "tr_quality_boost_pt_26", "level": "good", "score": 68, "seniority": "mid", "text": "Analista pleno com 5 anos. Organizei backlog técnico, criei indicadores operacionais e padronizei documentação para o suporte. Melhorei o SLA em 12%."},
        {"resume_id": "tr_quality_boost_pt_27", "level": "excellent", "score": 86, "seniority": "senior", "text": "Principal engineer com 13 anos. Liderei a modernização de 32 serviços, reduzi custos de infraestrutura em 29% e defini governança para 4 squads. GitHub: github.com/principal-renata | LinkedIn: linkedin.com/in/principal-renata."},
        {"resume_id": "tr_quality_boost_pt_28", "level": "excellent", "score": 90, "seniority": "mid", "text": "Engenheiro de software pleno com 5 anos. Migrei 14 pipelines para cloud, cortei 35% do tempo de processamento e conduzi mentoria técnica quinzenal. Portfolio: portfolio.dev/felipe-data."},
        {"resume_id": "tr_quality_boost_pt_29", "level": "excellent", "score": 88, "seniority": "junior", "text": "Desenvolvedora júnior com 3 anos. Implementei 16 endpoints em Django, aumentei cobertura de testes para 81% e reduzi falhas de deploy em 24%. GitHub: github.com/jr-luiza | LinkedIn: linkedin.com/in/jr-luiza."},
        {"resume_id": "tr_quality_boost_pt_30", "level": "excellent", "score": 84, "seniority": "intern", "text": "Estagiário de backend com 1 ano. Automatizei relatórios semanais, reduzi 7 horas mensais do time e criei documentação com 14 fluxos operacionais. GitHub: github.com/estag-ops | LinkedIn: linkedin.com/in/estag-ops."},
        {"resume_id": "tr_quality_focus_pt_01", "level": "poor", "score": 25, "seniority": "senior", "text": "Especialista sênior com 10 anos. Experiência em arquitetura, liderança, cloud, integrações e projetos corporativos. Atuação com times, sistemas e tecnologia em diferentes contextos."},
        {"resume_id": "tr_quality_focus_pt_02", "level": "poor", "score": 27, "seniority": "senior", "text": "Gerente de engenharia com 12 anos. Gestão de times, estratégia técnica, alinhamento com negócio e acompanhamento de entregas. Conhecimento em produto, sistemas e operações."},
        {"resume_id": "tr_quality_focus_pt_03", "level": "poor", "score": 29, "seniority": "mid", "text": "Engenheira pleno com 5 anos. APIs, integrações, code review, documentação e atuação com produto. Participação em projetos internos e sustentação de aplicações."},
        {"resume_id": "tr_quality_focus_pt_04", "level": "poor", "score": 31, "seniority": "junior", "text": "Desenvolvedor júnior com 3 anos. Implementação de funcionalidades, correção de bugs, manutenção de serviços e apoio ao time em demandas técnicas."},
        {"resume_id": "tr_quality_focus_pt_05", "level": "poor", "score": 33, "seniority": "intern", "text": "Estagiária de dados com 1 ano. Apoio em dashboards, planilhas, consultas simples e documentação de processos internos."},
        {"resume_id": "tr_quality_focus_pt_06", "level": "poor", "score": 34, "seniority": "mid", "text": "Analista pleno com 4 anos. Suporte a sistemas, relacionamento com áreas internas e manutenção de rotinas operacionais."},
        {"resume_id": "tr_quality_focus_pt_07", "level": "ok", "score": 44, "seniority": "senior", "text": "Arquiteto sênior com 9 anos. Definiu padrões técnicos e apoiou discussões de arquitetura em produtos internos."},
        {"resume_id": "tr_quality_focus_pt_08", "level": "ok", "score": 48, "seniority": "mid", "text": "Engenheira de software pleno com 5 anos. Desenvolveu APIs internas, apoiou revisões de código e manteve documentação técnica."},
        {"resume_id": "tr_quality_focus_pt_09", "level": "ok", "score": 53, "seniority": "junior", "text": "QA júnior com 2 anos. Automatizou alguns cenários, registrou regressões e organizou evidências de homologação."},
        {"resume_id": "tr_quality_focus_pt_10", "level": "ok", "score": 57, "seniority": "intern", "text": "Estagiário backend com 11 meses. Criou scripts internos, ajudou em testes unitários e documentou fluxos básicos."},
        {"resume_id": "tr_quality_focus_pt_11", "level": "good", "score": 67, "seniority": "senior", "text": "Tech lead com 8 anos. Documentei padrões técnicos, conduzi revisões de arquitetura e reduzi retrabalho em 15%, mas sem portfolio ou links públicos."},
        {"resume_id": "tr_quality_focus_pt_12", "level": "good", "score": 71, "seniority": "mid", "text": "Engenheiro pleno com 5 anos. Implementei 9 integrações, melhorei o SLA em 12% e conduzi code review recorrente, mas sem histórico forte de resultados mais amplos."},
        {"resume_id": "tr_quality_focus_pt_13", "level": "good", "score": 74, "seniority": "junior", "text": "Desenvolvedora júnior com 3 anos. Entreguei 13 melhorias em APIs, reduzi bugs repetidos em 20% e mantenho boa documentação, porém sem portfolio técnico estruturado."},
        {"resume_id": "tr_quality_focus_pt_14", "level": "good", "score": 76, "seniority": "intern", "text": "Estagiária de analytics com 1 ano. Automatizei 7 planilhas, documentei 10 indicadores e criei dashboards para o time, mas ainda com escopo limitado."},
        {"resume_id": "tr_quality_focus_pt_15", "level": "excellent", "score": 84, "seniority": "senior", "text": "Arquiteta sênior com 10 anos. Liderei a modernização de 18 serviços, reduzi incidentes em 28% e publiquei padrões técnicos usados por 4 squads. LinkedIn: linkedin.com/in/arq-maria."},
        {"resume_id": "tr_quality_focus_pt_16", "level": "excellent", "score": 87, "seniority": "mid", "text": "Engenheiro pleno com 5 anos. Migrei 12 pipelines para cloud, reduzi custo em 22% e mantive portfolio com estudos técnicos em portfolio.dev/pleno-cloud."},
        {"resume_id": "tr_quality_focus_pt_17", "level": "excellent", "score": 89, "seniority": "junior", "text": "Desenvolvedor júnior com 3 anos. Implementei 18 endpoints, aumentei cobertura de testes para 83% e reduzi tempo de deploy em 26%. GitHub: github.com/jr-carlos."},
        {"resume_id": "tr_quality_focus_pt_18", "level": "excellent", "score": 85, "seniority": "intern", "text": "Estagiário de software com 1 ano. Automatizei relatórios de operação, economizei 6 horas por semana e documentei 15 fluxos. LinkedIn: linkedin.com/in/estag-caio | GitHub: github.com/estag-caio."},
    ],
    "val.jsonl": [
        {"resume_id": "val_quality_boost_pt_01", "level": "poor", "score": 30, "seniority": "senior", "text": "Especialista sênior com 10 anos. Atuação em arquitetura, liderança e tecnologia em diferentes projetos e áreas internas."},
        {"resume_id": "val_quality_boost_pt_02", "level": "poor", "score": 34, "seniority": "junior", "text": "Desenvolvedor júnior com 2 anos. Correções em sistemas, suporte a usuários e manutenção de funcionalidades existentes."},
        {"resume_id": "val_quality_boost_pt_03", "level": "poor", "score": 28, "seniority": "intern", "text": "Estagiária de QA com 8 meses. Testes funcionais, checklist de homologação e registro de bugs."},
        {"resume_id": "val_quality_boost_pt_04", "level": "poor", "score": 36, "seniority": "mid", "text": "Analista pleno com 4 anos. Desenvolvimento de demandas, contato com áreas parceiras e sustentação de aplicações."},
        {"resume_id": "val_quality_boost_pt_05", "level": "ok", "score": 49, "seniority": "senior", "text": "Gerente de engenharia com 11 anos. Liderança de times, planejamento técnico e comunicação com stakeholders em produtos digitais."},
        {"resume_id": "val_quality_boost_pt_06", "level": "ok", "score": 54, "seniority": "junior", "text": "QA júnior com 2 anos. Automação inicial, testes de regressão e documentação de cenários."},
        {"resume_id": "val_quality_boost_pt_07", "level": "ok", "score": 51, "seniority": "intern", "text": "Estagiário de dados com 1 ano. Limpeza de bases, apoio em dashboards e documentação simples."},
        {"resume_id": "val_quality_boost_pt_08", "level": "ok", "score": 56, "seniority": "mid", "text": "Engenheira pleno com 5 anos. APIs internas, alinhamento com produto e manutenção de integrações."},
        {"resume_id": "val_quality_boost_pt_09", "level": "good", "score": 68, "seniority": "senior", "text": "Arquiteta sênior com 9 anos. Defini padrões técnicos, documentei integrações críticas e reduzi retrabalho em 16%."},
        {"resume_id": "val_quality_boost_pt_10", "level": "good", "score": 71, "seniority": "junior", "text": "Desenvolvedor júnior com 3 anos. Entreguei 10 melhorias em APIs e aumentei a cobertura de testes para 64%. GitHub: github.com/jr-val."},
        {"resume_id": "val_quality_boost_pt_11", "level": "good", "score": 73, "seniority": "intern", "text": "Estagiária de dados com 11 meses. Criei dashboards, automatizei 6 planilhas e documentei indicadores usados pelo time. LinkedIn: linkedin.com/in/estag-val."},
        {"resume_id": "val_quality_boost_pt_12", "level": "good", "score": 69, "seniority": "mid", "text": "Analista pleno com 5 anos. Organizei backlog técnico, criei indicadores de operação e melhorei o SLA em 11%."},
        {"resume_id": "val_quality_boost_pt_13", "level": "excellent", "score": 88, "seniority": "senior", "text": "Principal engineer com 12 anos. Liderei a modernização de 25 serviços, reduzi custo em 27% e defini governança para 4 squads. GitHub: github.com/principal-val."},
        {"resume_id": "val_quality_boost_pt_14", "level": "excellent", "score": 91, "seniority": "junior", "text": "Desenvolvedora júnior com 3 anos. Implementei 15 endpoints, elevei a cobertura de testes para 82% e reduzi incidentes em 21%. LinkedIn: linkedin.com/in/jr-val-2."},
        {"resume_id": "val_quality_boost_pt_15", "level": "excellent", "score": 86, "seniority": "intern", "text": "Estagiário backend com 1 ano. Automatizei relatórios mensais, economizei 6 horas do time e documentei 12 fluxos internos. GitHub: github.com/estag-val-ops."},
        {"resume_id": "val_quality_boost_pt_16", "level": "excellent", "score": 89, "seniority": "mid", "text": "Engenheiro pleno com 5 anos. Migrei pipelines para cloud, reduzi o tempo de processamento em 33% e conduzi mentoria técnica recorrente. Portfolio: portfolio.dev/pleno-val."},
        {"resume_id": "val_quality_focus_pt_01", "level": "poor", "score": 27, "seniority": "senior", "text": "Especialista sênior com 10 anos. Arquitetura, liderança, cloud e integração entre áreas em projetos diversos."},
        {"resume_id": "val_quality_focus_pt_02", "level": "poor", "score": 32, "seniority": "mid", "text": "Analista pleno com 5 anos. Sustentação de sistemas, contato com áreas internas e manutenção de rotinas."},
        {"resume_id": "val_quality_focus_pt_03", "level": "ok", "score": 47, "seniority": "senior", "text": "Gerente técnico com 11 anos. Liderança de times, planejamento e acompanhamento de entregas em produtos internos."},
        {"resume_id": "val_quality_focus_pt_04", "level": "ok", "score": 55, "seniority": "intern", "text": "Estagiária backend com 1 ano. Scripts simples, testes básicos e documentação de fluxos."},
        {"resume_id": "val_quality_focus_pt_05", "level": "good", "score": 70, "seniority": "senior", "text": "Arquiteto sênior com 9 anos. Definiu padrões técnicos, reduziu retrabalho em 13% e documentou integrações críticas."},
        {"resume_id": "val_quality_focus_pt_06", "level": "good", "score": 74, "seniority": "junior", "text": "Desenvolvedora júnior com 3 anos. Entregou 11 melhorias em APIs, reduziu bugs em 19% e manteve documentação clara."},
        {"resume_id": "val_quality_focus_pt_07", "level": "excellent", "score": 86, "seniority": "mid", "text": "Engenheira pleno com 5 anos. Migrou pipelines para cloud, reduziu custo em 24% e mantém portfolio técnico em portfolio.dev/val-focus."},
        {"resume_id": "val_quality_focus_pt_08", "level": "excellent", "score": 88, "seniority": "intern", "text": "Estagiário de analytics com 1 ano. Automatizou dashboards, economizou 5 horas semanais e documentou 11 indicadores. LinkedIn: linkedin.com/in/val-focus."},
    ],
    "test.jsonl": [
        {"resume_id": "test_quality_boost_pt_01", "level": "poor", "score": 29, "seniority": "senior", "text": "Arquiteto sênior com 10 anos. Liderança técnica, arquitetura e participação em iniciativas estratégicas para diferentes produtos."},
        {"resume_id": "test_quality_boost_pt_02", "level": "poor", "score": 35, "seniority": "junior", "text": "Desenvolvedora júnior com 2 anos. Correções, manutenção de sistemas e apoio ao time em demandas do dia a dia."},
        {"resume_id": "test_quality_boost_pt_03", "level": "poor", "score": 27, "seniority": "intern", "text": "Estagiário de suporte com 9 meses. Atendimento inicial, registro de tickets e atualização de documentação."},
        {"resume_id": "test_quality_boost_pt_04", "level": "poor", "score": 33, "seniority": "mid", "text": "Analista pleno com 4 anos. Sustentação de aplicações, alinhamento com áreas internas e manutenção de integrações."},
        {"resume_id": "test_quality_boost_pt_05", "level": "ok", "score": 48, "seniority": "senior", "text": "Gerente técnico com 11 anos. Planejamento, liderança de times e acompanhamento de entregas de software."},
        {"resume_id": "test_quality_boost_pt_06", "level": "ok", "score": 52, "seniority": "junior", "text": "QA júnior com 2 anos. Regressão, checklist de homologação e automação básica de cenários."},
        {"resume_id": "test_quality_boost_pt_07", "level": "ok", "score": 50, "seniority": "intern", "text": "Estagiária de dados com 1 ano. Apoio em dashboards, limpeza de dados e documentação simples."},
        {"resume_id": "test_quality_boost_pt_08", "level": "ok", "score": 57, "seniority": "mid", "text": "Engenheiro pleno com 5 anos. APIs internas, manutenção de jobs e apoio técnico em integrações."},
        {"resume_id": "test_quality_boost_pt_09", "level": "good", "score": 67, "seniority": "senior", "text": "Especialista sênior com 9 anos. Estruturei padrões técnicos, documentei fluxos críticos e reduzi retrabalho em 14%."},
        {"resume_id": "test_quality_boost_pt_10", "level": "good", "score": 72, "seniority": "junior", "text": "Desenvolvedor júnior com 3 anos. Entreguei 12 melhorias em APIs, reduzi erros em 18% e mantenho GitHub: github.com/jr-test."},
        {"resume_id": "test_quality_boost_pt_11", "level": "good", "score": 70, "seniority": "intern", "text": "Estagiária de analytics com 1 ano. Automatizei planilhas, criei dashboards e documentei 8 indicadores do time. LinkedIn: linkedin.com/in/estag-test."},
        {"resume_id": "test_quality_boost_pt_12", "level": "good", "score": 74, "seniority": "mid", "text": "Analista pleno com 5 anos. Organizei backlog técnico, melhorei o SLA em 13% e criei indicadores operacionais."},
        {"resume_id": "test_quality_boost_pt_13", "level": "excellent", "score": 87, "seniority": "senior", "text": "Principal engineer com 12 anos. Liderei a evolução de uma plataforma com 28 serviços, reduzi custo em 26% e defini governança para 5 squads. GitHub: github.com/principal-test."},
        {"resume_id": "test_quality_boost_pt_14", "level": "excellent", "score": 90, "seniority": "junior", "text": "Desenvolvedora júnior com 3 anos. Implementei 14 endpoints, aumentei a cobertura de testes para 80% e reduzi falhas em produção em 19%. LinkedIn: linkedin.com/in/jr-test-2."},
        {"resume_id": "test_quality_boost_pt_15", "level": "excellent", "score": 85, "seniority": "intern", "text": "Estagiário backend com 1 ano. Automatizei relatórios, economizei 5 horas por semana do time e documentei 10 fluxos internos. GitHub: github.com/estag-test-ops."},
        {"resume_id": "test_quality_boost_pt_16", "level": "excellent", "score": 89, "seniority": "mid", "text": "Engenheira pleno com 5 anos. Migrei pipelines para cloud, reduzi tempo de processamento em 31% e conduzi mentoria técnica mensal. Portfolio: portfolio.dev/pleno-test."},
        {"resume_id": "test_quality_focus_pt_01", "level": "poor", "score": 26, "seniority": "senior", "text": "Gerente de engenharia com 11 anos. Liderança de times, estratégia técnica e alinhamento com áreas de negócio em projetos diversos."},
        {"resume_id": "test_quality_focus_pt_02", "level": "poor", "score": 30, "seniority": "junior", "text": "Desenvolvedor júnior com 2 anos. Correções, manutenção de sistemas e apoio ao time em demandas operacionais."},
        {"resume_id": "test_quality_focus_pt_03", "level": "ok", "score": 46, "seniority": "senior", "text": "Arquiteta sênior com 9 anos. Definiu padrões técnicos e apoiou discussões de arquitetura em iniciativas internas."},
        {"resume_id": "test_quality_focus_pt_04", "level": "ok", "score": 54, "seniority": "intern", "text": "Estagiário de QA com 1 ano. Automatizou alguns cenários, organizou evidências e documentou testes."},
        {"resume_id": "test_quality_focus_pt_05", "level": "good", "score": 69, "seniority": "senior", "text": "Especialista sênior com 8 anos. Documentou fluxos críticos, reduziu retrabalho em 12% e definiu padrões técnicos para o time."},
        {"resume_id": "test_quality_focus_pt_06", "level": "good", "score": 73, "seniority": "junior", "text": "Desenvolvedora júnior com 3 anos. Entregou 10 melhorias, reduziu bugs em 17% e manteve documentação técnica consistente."},
        {"resume_id": "test_quality_focus_pt_07", "level": "excellent", "score": 86, "seniority": "mid", "text": "Engenheiro pleno com 5 anos. Migrou pipelines, reduziu custo em 23% e mantém portfolio com estudos técnicos em portfolio.dev/test-focus."},
        {"resume_id": "test_quality_focus_pt_08", "level": "excellent", "score": 88, "seniority": "intern", "text": "Estagiária de dados com 1 ano. Automatizou dashboards, economizou 5 horas por semana e documentou 12 indicadores. GitHub: github.com/test-focus."},
    ],
}

SENIORITY_META = {
    "intern": {"title": "Estagiário de tecnologia", "years": "1 ano"},
    "junior": {"title": "Desenvolvedor júnior", "years": "2 anos"},
    "mid": {"title": "Engenheiro pleno", "years": "5 anos"},
    "senior": {"title": "Especialista sênior", "years": "9 anos"},
}

DOMAIN_TEMPLATES = [
    {
        "slug": "backend",
        "area": "APIs internas e integrações entre serviços",
        "skills": "Python, Django, PostgreSQL e Docker",
        "artifact": "documentação técnica de serviços",
        "impact": "latência de APIs",
        "initiative": "padronização de endpoints e observabilidade",
    },
    {
        "slug": "frontend",
        "area": "interfaces web e design system",
        "skills": "React, TypeScript, testes e CSS",
        "artifact": "componentes reutilizáveis",
        "impact": "bugs de interface",
        "initiative": "biblioteca de componentes e acessibilidade",
    },
    {
        "slug": "data",
        "area": "pipelines analíticos e modelagem de dados",
        "skills": "SQL, Python, Airflow e dbt",
        "artifact": "catálogo de indicadores",
        "impact": "tempo de atualização de dados",
        "initiative": "padronização de pipelines e qualidade analítica",
    },
    {
        "slug": "ml",
        "area": "treino de modelos e serving de inferência",
        "skills": "PyTorch, NLP, avaliação offline e MLflow",
        "artifact": "relatórios de experimento",
        "impact": "tempo de inferência",
        "initiative": "versionamento de datasets e monitoramento de modelos",
    },
    {
        "slug": "devops",
        "area": "plataforma, CI/CD e ambientes em nuvem",
        "skills": "AWS, Kubernetes, Terraform e observabilidade",
        "artifact": "runbooks operacionais",
        "impact": "tempo de deploy",
        "initiative": "governança de ambientes e automação de infraestrutura",
    },
    {
        "slug": "qa",
        "area": "automação de testes e qualidade de entrega",
        "skills": "Cypress, Playwright, testes de API e qualidade",
        "artifact": "planos de regressão",
        "impact": "bugs críticos",
        "initiative": "estratégia de testes e rastreabilidade de defeitos",
    },
]

QUALITY_LANGUAGES = ("en-US", "es-ES")


def _localized_quality_title(language: str, seniority: str) -> str:
    titles = {
        "pt-BR": {"intern": "Estagiário de tecnologia", "junior": "Desenvolvedor júnior", "mid": "Engenheiro pleno", "senior": "Especialista sênior"},
        "en-US": {"intern": "Technology intern", "junior": "Junior engineer", "mid": "Mid-level engineer", "senior": "Senior specialist"},
        "es-ES": {"intern": "Practicante de tecnología", "junior": "Desarrollador junior", "mid": "Ingeniero semi-senior", "senior": "Especialista senior"},
    }
    return titles[language][seniority]


def _localized_years(language: str, seniority: str) -> str:
    years = {
        "pt-BR": {"intern": "1 ano", "junior": "2 anos", "mid": "5 anos", "senior": "9 anos"},
        "en-US": {"intern": "1 year", "junior": "2 years", "mid": "5 years", "senior": "9 years"},
        "es-ES": {"intern": "1 año", "junior": "2 años", "mid": "5 años", "senior": "9 años"},
    }
    return years[language][seniority]


def _score_for_level(level: str, seniority: str, variant: int) -> int:
    if level == "poor":
        base = {"intern": 26, "junior": 29, "mid": 31, "senior": 33}[seniority]
        return min(39, base + (variant % 5) * 2)
    if level == "ok":
        base = {"intern": 42, "junior": 45, "mid": 48, "senior": 50}[seniority]
        return min(59, base + (variant % 5) * 2)
    base = {"intern": 62, "junior": 66, "mid": 70, "senior": 74}[seniority]
    return min(88, base + (variant % 4) * 3)


def _build_quality_text(level: str, seniority: str, domain: dict, variant: int) -> str:
    meta = SENIORITY_META[seniority]
    title = meta["title"]
    years = meta["years"]
    artifact_amount = 6 + (variant % 7)
    result_pct = 11 + ((variant * 3) % 19)
    initiative_count = 3 + (variant % 4)
    if level == "poor":
        return (
            f"{title} com {years} de experiência em {domain['area']}. "
            f"Atuação com {domain['skills']} e apoio ao time em demandas internas. "
            f"Experiência em manutenção, documentação e alinhamento com produto. "
            f"Participação em rotinas do time e suporte a entregas relacionadas a {domain['initiative']}."
        )
    if level == "ok":
        return (
            f"{title} com {years} de experiência em {domain['area']}. "
            f"Desenvolveu demandas recorrentes com {domain['skills']} e organizou {domain['artifact']} para o time. "
            f"Implementou melhorias pontuais, documentou {artifact_amount} fluxos e apoiou testes e revisões técnicas. "
            f"Boa clareza textual e repertório técnico consistente, mas ainda com poucos resultados quantificados e sem links públicos."
        )
    return (
        f"{title} com {years} de experiência em {domain['area']}. "
        f"Implementei iniciativas com {domain['skills']}, documentei {artifact_amount} entregas técnicas e conduzi {initiative_count} melhorias relevantes. "
        f"Reduzi {domain['impact']} em {result_pct}% e dei suporte à iniciativa de {domain['initiative']}. "
        f"GitHub: github.com/{domain['slug']}-quality-{seniority}-{variant} | LinkedIn: linkedin.com/in/{domain['slug']}-quality-{seniority}-{variant}"
    )


def _build_quality_text_multilang(level: str, seniority: str, domain: dict, variant: int, language: str) -> str:
    title = _localized_quality_title(language, seniority)
    years = _localized_years(language, seniority)
    artifact_amount = 5 + (variant % 6)
    result_pct = 10 + ((variant * 4) % 17)
    initiative_count = 2 + (variant % 4)
    if language == "en-US":
        if level == "poor":
            return (
                f"{title} with {years} of experience in {domain['slug']}. "
                f"Worked on routine tasks, maintenance, documentation and day-to-day delivery support. "
                f"Lists technology context, but provides limited evidence of outcomes, ownership or external technical artifacts. Variant {variant}."
            )
        if level == "ok":
            return (
                f"{title} with {years} of experience in {domain['slug']}. "
                f"Implemented recurring tasks, documented {artifact_amount} workflows and supported reviews and testing. "
                f"Shows decent clarity and technical context, but still has limited quantified impact and no public links. Variant {variant}."
            )
        return (
            f"{title} with {years} of experience in {domain['slug']}. "
            f"Implemented initiatives, documented {artifact_amount} technical deliverables and drove {initiative_count} meaningful improvements. "
            f"Reduced key issues by {result_pct}% and maintains GitHub: github.com/{domain['slug']}-quality-en-{seniority}-{variant} plus LinkedIn: linkedin.com/in/{domain['slug']}-quality-en-{seniority}-{variant}."
        )
    if level == "poor":
        return (
            f"{title} con {years} de experiencia en {domain['slug']}. "
            f"Participó en tareas rutinarias, mantenimiento, documentación y apoyo operativo del equipo. "
            f"Menciona contexto técnico, pero aporta poca evidencia de resultados, ownership o artefactos públicos. Variante {variant}."
        )
    if level == "ok":
        return (
            f"{title} con {years} de experiencia en {domain['slug']}. "
            f"Implementó tareas recurrentes, documentó {artifact_amount} flujos y apoyó revisiones y pruebas. "
            f"Muestra claridad razonable y buen contexto técnico, pero todavía tiene poco impacto cuantificado y no incluye links públicos. Variante {variant}."
        )
    return (
        f"{title} con {years} de experiencia en {domain['slug']}. "
        f"Implementó iniciativas, documentó {artifact_amount} entregables técnicos y condujo {initiative_count} mejoras relevantes. "
        f"Redujo problemas clave en {result_pct}% y mantiene GitHub: github.com/{domain['slug']}-quality-es-{seniority}-{variant} junto con LinkedIn: linkedin.com/in/{domain['slug']}-quality-es-{seniority}-{variant}."
    )


def _generated_examples(filename: str) -> list[dict]:
    split = filename.replace(".jsonl", "")
    rows: list[dict] = []
    seniorities = ("intern", "junior", "mid", "senior")
    base_variants = 2 if split == "train" else 1
    extra_low_variants = 2 if split == "train" else 1
    strong_variants = 1 if split == "train" else 0

    for seniority in seniorities:
        for domain_idx, domain in enumerate(DOMAIN_TEMPLATES):
            for variant in range(base_variants):
                poor_variant = domain_idx * 10 + variant
                ok_variant = domain_idx * 10 + variant
                rows.append(
                    {
                        "resume_id": f"{split}_quality_boundary_poor_{domain['slug']}_{seniority}_{variant:02d}",
                        "level": "poor",
                        "score": _score_for_level("poor", seniority, poor_variant),
                        "seniority": seniority,
                        "text": _build_quality_text("poor", seniority, domain, poor_variant),
                    }
                )
                rows.append(
                    {
                        "resume_id": f"{split}_quality_boundary_ok_{domain['slug']}_{seniority}_{variant:02d}",
                        "level": "ok",
                        "score": _score_for_level("ok", seniority, ok_variant),
                        "seniority": seniority,
                        "text": _build_quality_text("ok", seniority, domain, ok_variant),
                    }
                )
            for variant in range(extra_low_variants):
                extra_variant = 100 + domain_idx * 10 + variant
                rows.append(
                    {
                        "resume_id": f"{split}_quality_contrast_poor_{domain['slug']}_{seniority}_{variant:02d}",
                        "level": "poor",
                        "score": _score_for_level("poor", seniority, extra_variant),
                        "seniority": seniority,
                        "text": _build_quality_text("poor", seniority, domain, extra_variant),
                    }
                )
                rows.append(
                    {
                        "resume_id": f"{split}_quality_contrast_ok_{domain['slug']}_{seniority}_{variant:02d}",
                        "level": "ok",
                        "score": _score_for_level("ok", seniority, extra_variant),
                        "seniority": seniority,
                        "text": _build_quality_text("ok", seniority, domain, extra_variant),
                    }
                )
            for variant in range(strong_variants):
                strong_variant = 200 + domain_idx * 10 + variant
                rows.append(
                    {
                        "resume_id": f"{split}_quality_boundary_strong_{domain['slug']}_{seniority}_{variant:02d}",
                        "level": "strong",
                        "score": _score_for_level("strong", seniority, strong_variant),
                        "seniority": seniority,
                        "text": _build_quality_text("strong", seniority, domain, strong_variant),
                    }
                )
    return rows


def _generated_multilang_examples(filename: str) -> list[dict]:
    split = filename.replace(".jsonl", "")
    rows: list[dict] = []
    variants = 2 if split == "train" else 1
    for language in QUALITY_LANGUAGES:
        for seniority in ("intern", "junior", "mid", "senior"):
            for domain_idx, domain in enumerate(DOMAIN_TEMPLATES):
                for variant in range(variants):
                    poor_variant = domain_idx * 10 + variant
                    ok_variant = 100 + domain_idx * 10 + variant
                    strong_variant = 200 + domain_idx * 10 + variant
                    rows.append(
                        {
                            "resume_id": f"{split}_quality_multi_poor_{language}_{domain['slug']}_{seniority}_{variant:02d}",
                            "level": "poor",
                            "score": _score_for_level("poor", seniority, poor_variant),
                            "seniority": seniority,
                            "text": _build_quality_text_multilang("poor", seniority, domain, poor_variant, language),
                            "language": language,
                        }
                    )
                    rows.append(
                        {
                            "resume_id": f"{split}_quality_multi_ok_{language}_{domain['slug']}_{seniority}_{variant:02d}",
                            "level": "ok",
                            "score": _score_for_level("ok", seniority, ok_variant),
                            "seniority": seniority,
                            "text": _build_quality_text_multilang("ok", seniority, domain, ok_variant, language),
                            "language": language,
                        }
                    )
                    rows.append(
                        {
                            "resume_id": f"{split}_quality_multi_strong_{language}_{domain['slug']}_{seniority}_{variant:02d}",
                            "level": "strong",
                            "score": _score_for_level("strong", seniority, strong_variant),
                            "seniority": seniority,
                            "text": _build_quality_text_multilang("strong", seniority, domain, strong_variant, language),
                            "language": language,
                        }
                    )
    return rows


def _record(entry: dict) -> dict:
    return {
        "resume_text": entry["text"],
        "labels": {
            "seniority": entry["seniority"],
            "quality_score": entry["score"],
            "quality_level": _normalize_quality_level(entry["level"], entry["score"]),
        },
        "language": entry.get("language", "pt-BR"),
        "resume_id": entry["resume_id"],
    }


def _append_unique(path: Path, rows: list[dict]) -> tuple[int, int]:
    existing_lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    existing_ids = set()
    for line in existing_lines:
        data = json.loads(line)
        existing_ids.add(str(data.get("resume_id") or ""))

    added = 0
    for row in rows:
        if row["resume_id"] in existing_ids:
            continue
        existing_lines.append(json.dumps(_record(row), ensure_ascii=False))
        existing_ids.add(row["resume_id"])
        added += 1

    path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
    return added, len(existing_lines)


def main() -> None:
    splits_dir = Path(__file__).resolve().parents[2] / "data" / "splits"
    for filename, rows in DATASET.items():
        path = splits_dir / filename
        all_rows = rows + _generated_examples(filename) + _generated_multilang_examples(filename)
        added, total = _append_unique(path, all_rows)
        print(f"{filename}: added={added} total={total}")


if __name__ == "__main__":
    main()
