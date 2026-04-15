# Frontend — arquitetura (FSD)

## Stack

- **React 19** + **TypeScript**
- **Create React App** com **Craco** (aliases `@/` → `src/`)
- **react-router-dom** v7
- **i18next** (pt-BR, en-US, es-ES)
- **Zod** + **react-hook-form** onde há formulários complexos

## Feature-Sliced Design (FSD)

A pasta `client/src/` segue camadas **de cima para baixo** (quem pode importar quem):

```
app/        → Arranque, router, guards, layout raiz
pages/      → Uma rota ≈ uma página; compõe widgets e features
widgets/    → Blocos grandes da UI (shell, lista de currículos, wizard)
features/   → Casos de uso (auth, resume, ai-analysis, dashboard, …)
entities/   → Modelo de domínio no front (resume, session) — tipos, temas, API de entidade
shared/     → Infra reutilizável: api, ui, hooks, i18n, theme, performance
```

### Regras práticas

- **`shared`** não importa `features` nem `widgets`.
- **`entities`** não importa `features`/`widgets`/`pages`.
- **`features`** pode usar `entities` e `shared`.
- **`widgets`** pode usar `features`, `entities`, `shared`.
- **`pages`** pode usar tudo abaixo de si.

Quebrar isto (ex.: `entities` a importar `widgets`) gera acoplamento e avisos no `npm run deps:cycles`.

## Mapa rápido de pastas

| Pasta | Exemplos de conteúdo |
|-------|----------------------|
| `app/router/` | `AppRouter.tsx`, `RequireAuth.tsx`, lazy loading de páginas |
| `pages/` | `auth/login`, `resumes`, `dashboard`, `ai-analysis`, `settings` |
| `widgets/app-shell/` | Topbar, navegação, área autenticada |
| `widgets/resume-builder/` | Passos do wizard, auto-guardar |
| `features/resume/` | `useResumes`, `resumeApi`, filtros da lista |
| `features/ai-analysis/` | Seleção de currículo, disparo de análise, insights na UI |
| `entities/resume/` | Temas (`config/themes/`), `viewModel`, tipos |
| `shared/api/` | `http.ts` (`apiRequest`), erros, `handleApiSaveError` |

## Onde procurar quando…

- **Mudar texto traduzido:** `shared/lib/i18n/locales/*`
- **Mudar cor/tema global:** `shared/lib/theme/`
- **Nova chamada HTTP:** criar ou estender `*Api.ts` no `feature` ou `entity` e usar `apiRequest` de `shared/api/http.ts`
- **Nova rota:** `AppRouter.tsx` + nova pasta em `pages/`

---

Segue para [02-frontend-rotas-e-fluxos.md](02-frontend-rotas-e-fluxos.md).
