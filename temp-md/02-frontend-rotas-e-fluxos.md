# Frontend — rotas e fluxos principais

## Ficheiro central de rotas

**`client/src/app/router/AppRouter.tsx`**

- Rotas **públicas:** `/login`, `/register`, `/terms`, `/privacy`, fluxos de e-mail e reset de senha, `/oauth/callback`, `/verify-email`, etc.
- Rota **impressão PDF** (layout simples): `/resume/print/:resumeId` (lazy).
- Árvore **`/protected/*`:** envolvida por `<RequireAuth>` + `<ProtectedAppLayout>` (shell com menu).
  - `/protected` → redireciona para `dashboard`
  - `dashboard`, `profile`, `settings`, `resumes`, `ai-analysis`, `version-history` — todas **lazy** com `Suspense` + `PageLoader`.
- **Fallback `*`** → redireciona para `/login`.

## Autenticação no browser

**`client/src/app/router/RequireAuth.tsx`**

- Garante que só utilizadores autenticados entram em `/protected/...`.
- Se não houver sessão válida, tipicamente redireciona ou mostra estado de carregamento (ler implementação).

**`client/src/entities/session/`**

- Estado global da sessão (tokens, utilizador, ações de login/logout/refresh).
- O `apiRequest` em `shared/api/http.ts` chama `sessionApi.refresh()` em 401/403 (exceto em rotas de auth explícitas).

## Fluxo: lista de currículos

1. Rota: `/protected/resumes` → **`pages/resumes`**.
2. Usa **`useResumes`** (`features/resume/model/useResumes.ts`): estado da lista, filtros, debounce, cache em memória, abort de pedidos.
3. Chamadas: **`resumeApi`** (`features/resume/api/resumeApi.ts`) → `apiRequest('/resumes/api/resumes?...')`.
4. UI: widgets como **`widgets/resumes`** (grelha, toolbar, modais).

## Fluxo: wizard de edição

1. A partir da lista ou criação, abre-se **`ResumeBuilderWizard`** (`widgets/resume-builder/`).
2. Estado do passo e validação: **`features/resume-builder`** (hooks, schemas Zod).
3. Guardar: API de resume (create/update) + invalidações (ex.: marcador de conteúdo gravado).

## Fluxo: análise por IA

1. Rota: `/protected/ai-analysis` → página em **`pages/ai-analysis`**.
2. Features em **`features/ai-analysis`** (seleção de currículo, estado da última análise, etc.).
3. Endpoints backend típicos: `/analysis/run`, `/analysis/latest`, `/analysis/history` (ver doc de backend).

## Fluxo: dashboard

- Página lazy **`DashboardPage`**.
- Hook **`useDashboard`** + **`dashboardApi`** + mappers em `features/dashboard/model/`.

## Erros de carregamento de chunks

**`RouteLoadErrorBoundary.tsx`** — captura falhas ao carregar módulos lazy (rede); útil para explicar “página não abre em 4G”.

---

Segue para [03-frontend-api-e-sessao.md](03-frontend-api-e-sessao.md).
