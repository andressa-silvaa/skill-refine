# Backend — arquitetura Django

## Stack

- **Django** + **Django REST Framework (DRF)**
- **PostgreSQL** em produção típica; **SQLite** se `DATABASE_URL` vazio (ver `config/settings_modules/base.py`)
- **Redis** + **Celery** para trabalhos assíncronos (análise); fallback possível sem broker conforme settings

## Arranque do projeto Django

- **`backend/manage.py`** — ponto de entrada; adiciona `backend/src` ao `PYTHONPATH`.
- **`backend/src/config/`** — projeto Django:
  - `settings.py` ou módulos em `settings_modules/` (base, DRF, e-mail, Celery…)
  - `urls.py` — **mapa de todas as rotas HTTP** da API
  - `wsgi.py` / `asgi.py` — deployment
- **`backend/src/apps/`** — aplicações de domínio (cada uma com `models`, migrações, interfaces, etc.).

## Pasta `shared` (backend)

**`backend/src/shared/`** — código transversal **sem** ser uma app Django instalada como “feature”:

- `shared/api/responses.py` — formato canónico de erros JSON para o client.
- `shared/api/request_user.py` — helper DRF para `user_id` autenticado + 401.
- `shared/api/pagination.py` — parsing de `limit`/`offset` reutilizável.
- `shared/auth/` — JWT, autenticação DRF.
- `shared/db/models.py` — mixins (UUID, timestamps, soft delete).

## Padrão por app (variações)

Alguns apps seguem **camadas explícitas**:

- **`accounts`**: `domain/` (ports, erros), `application/use_cases/`, `infrastructure/` (ORM, e-mail), `interfaces/api/` (views DRF).
- **`resumes`**, **`analysis`**: mais orientados a **serviços + interfaces API**, com lógica pesada em `application/` (sobretudo `analysis`).

## Onde correr comandos

```bash
cd backend
# ativar venv
cd src
python manage.py migrate
python manage.py runserver
python manage.py test apps.resumes.tests
```

---

Segue para [05-backend-apps-e-endpoints.md](05-backend-apps-e-endpoints.md).
