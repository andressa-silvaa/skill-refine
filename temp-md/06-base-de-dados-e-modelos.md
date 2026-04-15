# Base de dados e modelos

## Motor e configuração

- **Produção / Docker:** **PostgreSQL** (serviço `postgres` no `docker-compose.yml`, porta host típica `5433`).
- **Desenvolvimento sem URL:** se `DATABASE_URL` estiver vazio, Django usa **SQLite** (`backend/db.sqlite3` relativo à pasta backend — ver settings).

Variáveis relacionadas: `DATABASE_URL`, credenciais em `backend/env.example` e `docker-compose.yml` (serviço `backend` sobrescreve URL para o host `postgres`).

## Migrações

- Cada app Django tem **`migrations/`**.
- Comando: `python manage.py migrate` (a partir de `backend/src`).
- **Não editar migrações antigas** em equipa; criar novas com `makemigrations`.

## Modelos principais (onde encontrar)

| Conceito | App | Ficheiros típicos |
|----------|-----|-------------------|
| Utilizador, sessão, identidades | `accounts` | `apps/accounts/infrastructure/models.py` |
| Currículo e anexos | `resumes` | `apps/resumes/infrastructure/models.py` |
| Execução de análise IA | `analysis` | `apps/analysis/models.py` → tabela `resume_analyses` |
| Notificações | `notifications` | `apps/notifications/models.py` |
| Auditoria | `audit` | `apps/audit/models.py` |

## Exemplo: `ResumeAnalysis`

Define uma linha por **corrida** de análise:

- FK para `User` e `Resume`
- `status`: `pending` → `running` → `done` ou `failed`
- `score`, `task_scores` (JSON), `payload_json` (insights)
- `resume_content_synced_at` — alinha análise à versão do currículo; se o currículo mudar, a “última” análise pode invalidar-se na lógica de negócio
- Campos de **senioridade** (regra, revisão, texto, evidência) e **target fit** (scores)

Índices em `Meta.indexes` otimizam listagens por utilizador/currículo/data.

## Relações importantes

- Um **User** tem muitos **Resume**.
- Um **Resume** tem muitos **ResumeAnalysis** (`related_name` configurado no modelo).
- **Notificações** ligam-se ao `user_id` (string/UUID conforme implementação).

## Consulta e debugging

- **Django admin** (se estiver ativo no projeto) ou cliente SQL direto no Postgres.
- Logs do worker Celery para ver falhas de modelo ou timeout.

---

Segue para [07-ia-analise-e-ml.md](07-ia-analise-e-ml.md).
