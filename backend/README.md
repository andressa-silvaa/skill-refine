# ⚙️ Skill Refine — Backend

Django + DRF + PostgreSQL backend for the Skill Refine resume builder and analysis platform.

---

## 📋 Prerequisites

- **Python** 3.11+
- **PostgreSQL** 15+ (or use Docker)
- **Redis** (optional, for Celery background tasks)
- **Playwright** (for PDF export)

---

## 🚀 Quick Start

### 1. Create virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL (Docker)

From project root:

```bash
docker compose up -d postgres
```

### 4. Configure environment

```bash
cp env.example .env
```

Edit `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgres://skill_refine:skill_refine@localhost:5433/skill_refine` |
| `DJANGO_SECRET_KEY` | Django secret key | `change-me-in-dev` |
| `JWT_SECRET` | JWT signing secret | `change-me-too` |
| `REFRESH_TOKEN_PEPPER` | Refresh token pepper | `change-me-too` |
| `FRONTEND_URL` | Frontend URL (CORS + PDF) | `http://localhost:3000` |

Optional: `CLOUDINARY_URL`, `GOOGLE_OAUTH_CLIENT_ID`, `EMAIL_HOST`, etc.

### 5. Run migrations

```bash
cd src
python manage.py migrate
```

### 6. Start server

```bash
python manage.py runserver
```

API runs at [http://localhost:8000](http://localhost:8000). Health check: `GET /health`.

---

## 🐳 Docker Compose (Full Stack)

From project root:

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, Django, Celery worker, and the frontend.

---

## 🧪 Celery (Background Tasks)

Used for AI analysis and other async jobs.

### Start Redis

```bash
docker compose up -d redis
```

### Start Celery worker

```bash
celery -A config.celery worker -l info
```

If Redis is unavailable, analysis falls back to in-process threading.

---

## 📄 PDF Export

Requires **Playwright**:

```bash
playwright install chromium
```

The backend must be able to reach the frontend URL for PDF generation. Configure `FRONTEND_URL` in `.env` (e.g. `http://host.docker.internal:3000` if backend runs in Docker).

---

## 📧 Email (Optional)

Configure SMTP in `.env`:

- **Gmail:** `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`
- **SendGrid:** `EMAIL_HOST=smtp.sendgrid.net`, `EMAIL_HOST_USER=apikey`, `EMAIL_HOST_PASSWORD=<API_KEY>`
- **Brevo:** `EMAIL_HOST=smtp-relay.brevo.com`

---

## 🔐 Google OAuth (Optional)

1. Create OAuth credentials in Google Cloud Console
2. Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in `.env`
3. Use the same Client ID in the frontend `REACT_APP_GOOGLE_CLIENT_ID`

---

## 🧪 Testing

```bash
cd src
python manage.py test apps.accounts.tests
python manage.py test apps.analysis.tests
python manage.py test apps.resumes.tests
python manage.py test apps.dashboard.tests
python manage.py test apps.notifications.tests
```

---

## 📁 Project Structure

```
backend/src/
├── config/           # settings, urls, wsgi
├── apps/
│   ├── accounts/     # auth, profile, privacy
│   ├── resumes/     # CRUD, PDF, versions
│   ├── analysis/    # AI analysis, rewrite
│   ├── dashboard/   # summary, cache
│   ├── audit/       # logging
│   ├── notifications/
│   └── search/
└── shared/           # auth, api, utils
```

---

## 📄 Author

**Andressa Silva**
