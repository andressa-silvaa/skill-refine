# 🎨 Skill Refine — Frontend (Client)

React + TypeScript frontend for the Skill Refine resume builder and analysis platform.

---

## 📋 Prerequisites

- **Node.js** 18+ (LTS recommended)
- **npm** 9+ (comes with Node.js)

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd client
npm install
```

### 2. Configure environment

Copy the example env file and adjust if needed:

```bash
cp env.example .env
```

Edit `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API base URL | `http://localhost:8000` |
| `REACT_APP_GOOGLE_CLIENT_ID` | Google OAuth Client ID (must match backend) | `xxx.apps.googleusercontent.com` |

### 3. Run development server

```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000).

---

## 📜 Available Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Start dev server (port 3000) |
| `npm run build` | Build for production |
| `npm test` | Run Jest tests |
| `npm run lint` | Run ESLint |
| `npm run i18n:check` | Validate i18n translation keys |
| `npm run deps:cycles` | Check for circular dependencies |
| `npm run ci:check` | Full CI check (lint + cycles + i18n) |

---

## 🏗️ Project Structure (FSD)

```
src/
├── app/           # App root, router, auth guards
├── pages/         # Page components (auth, protected, public)
├── widgets/       # AppShell, dashboard, resumes, settings
├── features/      # auth, ai-analysis, resume, version-history, etc.
├── entities/      # resume, session
└── shared/        # api, lib (i18n, theme, performance), ui (design system)
```

---

## 🌍 Internationalization (i18n)

- **Languages:** pt-BR (default), en-US, es-ES
- **Library:** i18next + react-i18next
- **Config:** `src/shared/lib/i18n/`

---

## 🎨 Theming

- **Appearance:** Light / Dark mode + accent colors (pink, purple, blue, green, orange)
- **Resume themes:** `src/entities/resume/config/themes/`
- **Config:** `src/shared/lib/theme/`

---

## 🧪 Testing

```bash
npm test
```

---

## 📦 Build for Production

```bash
npm run build
```

Output goes to `build/`.

---

## 📄 Author

**Andressa Silva**
