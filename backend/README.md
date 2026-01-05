## Backend (Django + DRF + Postgres)

Este backend usa **Django migrations como fonte da verdade** e configuração 12-factor via **`DATABASE_URL`**.

### Pré-requisitos

- Python 3.11+
- Docker Desktop (recomendado, para subir Postgres)

### 1) Criar venv e instalar dependências

No Windows (PowerShell), a partir da raiz do repo:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Subir Postgres (docker-compose)

Na raiz do repo:

```bash
docker compose up -d
```

O `docker-compose.yml` lê variáveis de `backend/env.example`. Para desenvolvimento, copie:

```bash
copy backend\env.example backend\.env
```

> Obs: Por padrão, o Django tenta ler `backend/.env` e, se não existir, tenta `.env` na raiz do repo.

### 3) Configurar `.env`

Edite `backend/.env` (copiado do `backend/env.example`) e ajuste `DJANGO_SECRET_KEY` e `DATABASE_URL` se necessário.

### 4) Rodar migrations

```bash
cd backend
python manage.py migrate
```

### 5) Subir o servidor e testar o /health

```bash
python manage.py runserver
```

Teste:
- `GET /health` -> `{"status":"ok"}`

### 6) Conectar no Beekeeper Studio

Crie uma conexão Postgres com:

- **Host**: `localhost`
- **Port**: `5433`
- **Database**: `skill_refine`
- **User**: `skill_refine`
- **Password**: `skill_refine`

Se você mudar os valores no `backend/.env`, use os mesmos no Beekeeper.


