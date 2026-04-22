# Skill Refine — Backend

Django + DRF API for resumes, authentication, AI analysis, dashboard, and notifications. Uses PostgreSQL in production; SQLite is possible for local dev if `DATABASE_URL` is unset (see settings).

## Prerequisites

- **Python** 3.11+
- **PostgreSQL** 15+ (recommended) or Docker Compose
- **Redis** (optional, for Celery)
- **Playwright** (optional, for PDF export: `playwright install chromium`)

## Configure the backend

### 1. Virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

On Linux/macOS: `source .venv/bin/activate`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment variables

```bash
cp env.example .env
```

Edit **`backend/.env`** (or a `.env` at repo root if your setup loads it — see `config/settings_modules/base.py`). Typical variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@localhost:5433/skill_refine` |
| `DJANGO_SECRET_KEY` | Django secret | strong random string |
| `JWT_SECRET` | Access JWT signing | strong random string |
| `REFRESH_TOKEN_PEPPER` | Refresh token hashing | strong random string |
| `PASSWORD_HASH_PEPPER` | Server-side pepper for password hashing (**required in production**) | strong random string |
| `FRONTEND_URL` | CORS + PDF generation (must reach the SPA) | `http://localhost:3000` |

Optional: `CELERY_BROKER_URL`, `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`, email (`RESEND_API_KEY`, SMTP), `CLOUDINARY_URL`, etc. Full list in `env.example`.

### 4. Database and runserver

From `backend` (where `manage.py` lives):

```bash
cd src
python manage.py migrate
python manage.py runserver
```

API: [http://localhost:8000](http://localhost:8000) — health: `GET /health`.

### 5. Docker (full stack)

From repository root:

```bash
docker compose up -d
```

### 6. Celery (optional)

```bash
docker compose up -d redis
celery -A config.celery worker -l info
```

If the broker is unavailable, some analysis paths may fall back to in-process behaviour depending on settings.

### 7. PDF export

Set `FRONTEND_URL` so the backend can open the resume preview (e.g. `http://host.docker.internal:3000` when Django runs in Docker on Windows).

## Password hashing: salt vs pepper

Passwords are hashed with **Argon2id** and a per-record **salt** (stored with
the hash), plus a process-wide **pepper** mixed in via HMAC-SHA256 **before**
the KDF runs (see `shared/auth/pepper_password_hasher.py`).

- **Salt** (in the DB) prevents rainbow tables and makes identical passwords
  produce different hashes.
- **Pepper** (in the env only, `PASSWORD_HASH_PEPPER`) mitigates the
  "DB-leaked + offline cracking" threat: an attacker with the database dump
  still needs the application environment secret to brute-force hashes.

Because the pepper never touches the database:

- It **must be set** when `DJANGO_DEBUG=0`. The app will refuse to start
  otherwise (fail fast).
- Rotating it invalidates every existing password hash. Pair any rotation with
  a forced password reset for all users.
- Existing users with legacy (un-peppered) hashes keep logging in normally;
  their hash is upgraded transparently on the first successful login.

## Tests

```bash
cd backend/src
python manage.py test
```

## Author

👧 **Andressa Costa**
