# IA, análise de currículo e ML

## Visão em duas camadas

1. **API Django (`apps.analysis`)** — recebe pedidos, valida posse do currículo, cria registo `ResumeAnalysis`, enfileira trabalho.
2. **Execução do modelo** — worker (Celery ou fallback) carrega artefactos de **`ml/models/`** (montados no contentor via `docker-compose` / volume) e corre pipelines em `apps/analysis/application/inference/`.

## Fluxo típico “correr análise”

1. Cliente: `POST /analysis/run` com `resume_id` (e opcionalmente texto de vaga).
2. Backend: verifica utilizador e currículo; cria `ResumeAnalysis` em `pending`.
3. Tarefa assíncrona: passa a `running`, carrega modelos (qualidade, ATS, senioridade, matching, target fit… conforme configuração).
4. Resultado: grava `score`, `task_scores`, `payload_json`, labels; `status` = `done` ou `failed` + `error_message`.

## Onde ler o código de inferência

- **`backend/src/apps/analysis/application/inference/`** — orquestrador, `loader.py`, pastas por tipo (`predictors/`, `text_seniority/`, `target_fit/`, embeddings…).
- **`backend/src/apps/analysis/application/worker.py`** — execução segura no worker.
- **`backend/src/apps/analysis/tasks.py`** — entrada Celery.

## Variáveis de ambiente (exemplos)

No Docker, vê-se no `docker-compose.yml` referências a:

- `ANALYSIS_MODEL_ROOT` — raiz dos modelos (ex.: `/ml/models` no container)
- `ANALYSIS_MODEL_VERSION`, `ANALYSIS_MODEL_VERSION_BY_LANG`, `ANALYSIS_MODEL_VERSION_BY_TASK` — escolha de artefacto por língua/tarefa

O ficheiro **`backend/env.example`** lista o resto (heurísticas, flags de signals_ml, etc.).

## Rewrite de texto (IA)

- Endpoints sob prefixo **`/ai/`** (incluído em `config/urls.py`).
- Views em `apps/analysis/interfaces/api/rewrite_views.py` — rate limit, serializers; **contrato de erro** pode diferir de outros endpoints (tratar com cuidado no client).

## Pasta `ml/` no repositório

- **`ml/training/`** — scripts Python para treinar/avaliar.
- **`ml/models/`** — artefactos servidos ao backend (estrutura depende do que foi exportado).
- **`ml/data/`** — datasets e derivados.

Nem todo o fluxo de treino é necessário para **explicar o produto**; para TCC, basta: dados → treino → exportação → `ResumeAnalysis` preenchido.

## PDF com “browser”

- O backend pode usar **Playwright** para renderizar a pré-visualização do currículo na URL do **frontend** (`FRONTEND_URL`). Isto liga **IA/layout** ao deploy real (CORS, rede Docker).

---

Segue para [08-integracao-deploy-e-ambiente.md](08-integracao-deploy-e-ambiente.md).
