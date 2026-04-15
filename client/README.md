# Skill Refine — Frontend

React 19 + TypeScript client (CRA/Craco). Architecture: **Feature-Sliced Design** (`app`, `pages`, `widgets`, `features`, `entities`, `shared`).

## Prerequisites

- **Node.js** 18+ (LTS)
- **npm** 9+

## Configure the frontend

### 1. Install dependencies

```bash
cd client
npm install
```

### 2. Environment variables

Copy the example file:

```bash
cp env.example .env
```

Edit **`.env`** in the `client` folder:

| Variable | Purpose | Example |
|----------|---------|---------|
| `REACT_APP_API_URL` | Base URL of the Django API (no trailing slash) | `http://localhost:8000` |
| `REACT_APP_GOOGLE_CLIENT_ID` | Google OAuth Web Client ID (must match backend `GOOGLE_OAUTH_CLIENT_ID`) | `xxx.apps.googleusercontent.com` |

The app reads these at **build time** (`REACT_APP_*`). After changing `.env`, restart the dev server or rebuild for production.

### 3. Run the development server

```bash
npm start
```

Opens at [http://localhost:3000](http://localhost:3000).

### 4. Useful scripts

| Command | Description |
|---------|-------------|
| `npm run build` | Production build → `build/` |
| `npm test` | Jest tests |
| `npm run lint` | ESLint |
| `npm run i18n:check` | Validate i18n keys |
| `npm run deps:cycles` | Detect circular imports |
| `npm run ci:check` | Lint + cycles + i18n |

## i18n

Default **pt-BR**; also **en-US** and **es-ES**. Config under `src/shared/lib/i18n/`.

## Author

👧 **Andressa Costa**
