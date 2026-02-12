# Backend (Django + DRF + Postgres + Celery)

- Python 3.11+, venv: `python -m venv .venv` e `pip install -r requirements.txt`.
- Postgres: na raiz, `docker compose up -d`. Copiar `backend/env.example` para `backend/.env` e configurar `DATABASE_URL`, `DJANGO_SECRET_KEY`; opcional: SendGrid (email), AI (rewrite), Playwright (PDF).
- Migrations: `python manage.py migrate`. Servidor: `python manage.py runserver`. Health: `GET /health`.

## Celery (análise de currículo em background)

- **Broker:** Redis. Com docker-compose: `docker compose up -d redis` (Redis na porta 6379).
- **Worker:** `celery -A config.celery worker -l info` (em outro terminal).
- Com docker-compose completo: o serviço `celery` sobe automaticamente.
- Se Redis não estiver disponível, a análise cai para threading (fallback).
