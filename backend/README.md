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

### Email (SendGrid via SMTP relay)

> Segurança: **não** comite chaves e **não** cole chaves em chat. Se uma chave vazou, revogue e gere outra no painel do SendGrid.

No `backend/.env`, configure:

```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=COLE_AQUI_SUA_SENDGRID_API_KEY
DEFAULT_FROM_EMAIL=skillrefine@skillrefine.com.br
```

Pré-requisito no SendGrid:
- O `DEFAULT_FROM_EMAIL` precisa estar **verificado** (Single Sender Verification) ou seu domínio precisa estar autenticado (Domain Authentication).

Depois de alterar o `.env`, reinicie o container do backend para carregar as variáveis:

```bash
docker compose up -d --build
```

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


