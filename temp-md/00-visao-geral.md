# Visão geral do monorepo

## O que é o Skill Refine

Plataforma de **construção de currículos** com **análise assistida por IA** (pontuações, insights, encaixe com vaga, etc.), autenticação (e-mail/senha e Google), histórico de versões, dashboard e notificações.

## Pastas na raiz do repositório

| Pasta / ficheiro | Função |
|------------------|--------|
| `client/` | Aplicação web **React + TypeScript** (interface). |
| `backend/` | API **Django + Django REST Framework**. |
| `ml/` | **Modelos treinados**, scripts de treino/avaliação e dados (não é o “core” da API, mas alimenta a análise). |
| `docker-compose.yml` | Orquestra Postgres, Redis, backend, worker, frontend (conforme serviços definidos). |
| `README.md` (raiz) | Entrada rápida em inglês + links. |

## Fluxo de dados (macro)

```
Utilizador (browser)
    → client (React): rotas, estado, chamadas HTTP
    → backend (Django/DRF): validação, regras, ORM
    → base de dados (PostgreSQL em produção; SQLite possível em dev)
    → (opcional) Redis + Celery: jobs longos de análise
    → carregamento de artefactos em ml/models (inferência no worker ou fallback)
```

## Como “explicar qualquer ficheiro”

Para cada ficheiro, responde mentalmente a:

1. **Camada FSD ou app Django?** — define regras de importação e responsabilidade.
2. **Quem chama isto?** — sobe na pilha (componente → hook → API).
3. **O que persiste ou muda estado?** — ORM, `setState`, cache.
4. **Qual o contrato HTTP ou de props?** — não inventar; ler tipos e serializers.

## Onde está o “cérebro” de cada parte

- **Regras de negócio de currículo (API):** `backend/src/apps/resumes/`.
- **Regras de análise / IA na API:** `backend/src/apps/analysis/` (tarefas, inferência, views).
- **Identidade e sessão:** `backend/src/apps/accounts/` + `client/src/entities/session/`.
- **UI de listagem / wizard:** `client/src/pages/resumes`, `widgets/resume-builder`, `features/resume*`.

---

Segue para [01-frontend-arquitetura-fsd.md](01-frontend-arquitetura-fsd.md).
