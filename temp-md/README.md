# Documentação de estudo — Skill Refine (`temp-md`)

Esta pasta reúne **material em português** para quem quiser estudar o projeto **de ponta a ponta**: do browser à base de dados, passando pela API, filas e IA.

> **Nota:** São guias de leitura do código e da arquitetura. A configuração oficial mínima continua nos `README.md` da raiz, `client/` e `backend/`.

## Ordem sugerida de leitura

| # | Documento | O que cobre |
|---|-----------|-------------|
| 1 | [00-visao-geral.md](00-visao-geral.md) | Monorepo, pastas, como navegar no repositório |
| 2 | [01-frontend-arquitetura-fsd.md](01-frontend-arquitetura-fsd.md) | React, camadas FSD, onde colocar código novo |
| 3 | [02-frontend-rotas-e-fluxos.md](02-frontend-rotas-e-fluxos.md) | Rotas, auth, páginas protegidas, fluxos de UI |
| 4 | [03-frontend-api-e-sessao.md](03-frontend-api-e-sessao.md) | `apiRequest`, tokens, erros, features que chamam o backend |
| 5 | [04-backend-arquitetura-django.md](04-backend-arquitetura-django.md) | Django, DRF, `config`, `shared`, padrões por app |
| 6 | [05-backend-apps-e-endpoints.md](05-backend-apps-e-endpoints.md) | URLs, responsabilidade de cada app, ficheiros-chave |
| 7 | [06-base-de-dados-e-modelos.md](06-base-de-dados-e-modelos.md) | PostgreSQL/SQLite, tabelas, relações, migrações |
| 8 | [07-ia-analise-e-ml.md](07-ia-analise-e-ml.md) | Pipeline de análise, Celery, modelos em `ml/`, rewrite |
| 9 | [08-integracao-deploy-e-ambiente.md](08-integracao-deploy-e-ambiente.md) | Docker Compose, variáveis, PDF, Redis |

## Como usar na prática

1. Abre o documento do tema (ex.: frontend).
2. No VS Code/Cursor, usa **Ir para ficheiro** (`Ctrl+P`) com os caminhos indicados.
3. Segue as **cadeias de importação** (quem importa quem) até ao fim do fluxo (ex.: botão → hook → `resumeApi` → `apiRequest` → URL Django).

---

*Documentação auxiliar — não substitui o código-fonte nem os `env.example`.*
