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

### 7) AI Rewrite (cloud)

O "Aprimorar com IA" no resumo do currículo usa **cloud** (API OpenAI‑compatível, ex. Groq, OpenAI). Configure `AI_CLOUD_BASE_URL`, `AI_CLOUD_API_KEY` e `AI_CLOUD_MODEL` no `backend/.env`. Ver `backend/env.example` (bloco "AI Rewrite").

### 8) Geração de PDF (Playwright)

A geração de PDF usa Playwright (Chromium headless) rodando dentro do container do backend. O backend precisa acessar o frontend para renderizar o currículo antes de gerar o PDF.

**Configuração necessária:**

Se você estiver rodando o backend em Docker e o frontend localmente (fora do Docker), o backend precisa conseguir acessar o frontend. Por padrão, o sistema tenta usar `host.docker.internal`, mas se isso não funcionar:

1. **Opção 1 (Recomendada)**: Habilitar `host.docker.internal` no Docker Desktop:
   - Abra Docker Desktop > Settings > Resources > Network
   - Certifique-se de que "Enable host networking" está ativado

2. **Opção 2**: Configurar o IP manualmente no `.env`:
   ```env
   FRONTEND_URL=http://192.168.1.X:3000  # Substitua pelo IP da sua máquina
   ```
   
   Para descobrir seu IP no Windows:
   ```bash
   ipconfig | findstr IPv4
   ```

3. **Opção 3**: Rodar o frontend também em Docker (adicionar ao `docker-compose.yml`)

**Testando a conectividade:**

Dentro do container do backend, teste se consegue acessar o frontend:
```bash
docker exec skill-refine-backend python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:3000').read()[:100])"
```

Se der timeout, use a Opção 2 acima.

