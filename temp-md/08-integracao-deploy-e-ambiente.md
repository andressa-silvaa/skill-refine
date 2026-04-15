# Integração, deploy e ambiente

## Variáveis cruzadas (front + back)

| Objetivo | Backend | Frontend |
|----------|---------|----------|
| URL da API | (N/A — o servidor escuta num host/porta) | `REACT_APP_API_URL` |
| URL do site (CORS, PDF, e-mails) | `FRONTEND_URL` | `npm start` em `localhost:3000` por defeito |
| Google OAuth | `GOOGLE_OAUTH_CLIENT_ID` (+ secret no servidor) | `REACT_APP_GOOGLE_CLIENT_ID` **igual** ao Client ID |

Sempre que mudares portas ou Docker, atualiza **ambos** os lados.

## Docker Compose (raiz)

Ficheiro **`docker-compose.yml`**:

- **postgres** — base de dados persistente (volume nomeado).
- **redis** — broker/resultado Celery e caches.
- **backend** — Django; monta `ml/models` e envs de análise.
- **worker** (se definido) — Celery.
- **frontend** (se definido) — build ou dev do React.

Lê as secções `environment` e `volumes` para perceber **caminhos dentro do container** (`/ml/models` vs pasta no host).

## Ordem típica de arranque local

1. Subir Postgres (e Redis se precisares de Celery): `docker compose up -d postgres redis`
2. Configurar `backend/.env` e `client/.env`
3. Migrar: `python manage.py migrate`
4. Backend: `python manage.py runserver`
5. Frontend: `npm start` em `client/`
6. (Opcional) Worker: `celery -A config.celery worker -l info`

## Saúde e diagnóstico

- **Backend:** `GET /health` (sem auth, conforme `HealthcheckView`).
- **Logs:** consola Django + logs do worker.
- **Client:** DevTools → rede — ver 401 (refresh), 429 (retry-after), 503 (análise indisponível).

## Testes automatizados

- **Backend:** `python manage.py test` (apps específicos conforme README do backend).
- **Frontend:** `npm test` (Jest); `npm run ci:check` antes de PR.

## Segurança em desenvolvimento

- Não commits com **secrets reais**; usa `.env` local ignorado pelo Git.
- `DJANGO_DEBUG=1` só em dev; em produção hosts e CORS restritos.

---

Voltar ao [README.md](README.md) desta pasta.
