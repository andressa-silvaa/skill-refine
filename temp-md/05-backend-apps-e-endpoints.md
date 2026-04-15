# Backend — apps e endpoints (mapa)

## Raiz de URLs

Ficheiro: **`backend/src/config/urls.py`**

| Prefixo | App / módulo |
|---------|----------------|
| `health` | Health check |
| `ai/` | Inclui URLs de `apps.analysis.interfaces.api` (ex.: rewrite) |
| `accounts/` | Autenticação, perfil, recuperação de conta |
| `resumes/` | CRUD de currículos, PDF, versões |
| `analysis/` | Correr análise, última análise, histórico |
| `dashboard/` | Resumo agregado para o painel |
| `notifications/` | Lista, marcar lidas, contagem |
| `search/` | Pesquisa global |

> **Importante:** o client usa caminhos como `/resumes/api/resumes` — estes são definidos **dentro** de cada `apps.<nome>.interfaces.urls`, não só no `config/urls.py`. Para cada funcionalidade, abre o `urls.py` do app correspondente.

## Apps e responsabilidade

### `apps.accounts`

- Utilizador, sessão JWT/refresh, registo, confirmação de e-mail, reset de palavra-passe, Google OAuth.
- Modelos ORM em `infrastructure/models.py` (ou `models.py` reexport).
- Casos de uso puros em `application/use_cases/` com repositórios em `domain/ports.py`.

### `apps.resumes`

- Modelo `Resume` e relações (contacto, experiências, versões, exportações PDF).
- Views em `interfaces/api/` (`resume_views`, `version_views`, `pdf_views`).
- Serviços em `interfaces/api/service_*.py` — listagem, mutações, tokens PDF.

### `apps.analysis`

- Modelo **`ResumeAnalysis`** — uma execução de análise por utilizador/currículo (estado, scores, payload JSON, labels de senioridade, target fit…).
- **`application/inference/`** — carregamento de modelos, orquestração de tarefas (quality, matching, seniority…).
- **`application/worker.py`** / **`tasks.py`** — execução assíncrona (Celery ou thread fallback).
- Views: `analysis_views.py` (run, latest, history), `rewrite_views.py` (IA texto).

### `apps.dashboard`

- Cache e agregados para o widget do dashboard (resumos, scores, insights agregados).

### `apps.notifications`

- Modelo de notificação + API para listar / marcar lidas / apagar.

### `apps.search`

- Pesquisa global sobre entidades do utilizador.

### `apps.audit`

- Registo de ações (usado pelo domínio de contas, etc.).

## Contrato com o frontend

- Status HTTP e **formato de erro** devem alinhar com o que `shared/api/http.ts` e `handleApiSaveError` esperam (`error`, `error_code`, `message`, `fields`).
- Alterar mensagens ou códigos **sem** atualizar o client pode partir toasts ou validação.

---

Segue para [06-base-de-dados-e-modelos.md](06-base-de-dados-e-modelos.md).
