# Frontend — API HTTP e sessão

## Camada única de `fetch`

**`client/src/shared/api/http.ts`**

- **`apiRequest<T>(path, init?)`**: junta `REACT_APP_API_URL` + `path`, cabeçalhos JSON, **Bearer** a partir de `getAccessToken()` (`shared/api/token.ts`).
- Em **401/403** e se o path **não** for fluxo de auth (`login`, `refresh`, `register`, `google`), tenta **um** refresh de sessão e repete o pedido.
- Erros: corpo JSON é convertido em **`ApiError`** (status, `code`, mensagem, `retryAfterSeconds` em 429).
- **`apiRequestBlob`**: downloads (PDF, etc.).

## Erros na UI

- **`getApiErrorMessage`**, **`getApiFieldErrors`**, **`asApiError`** — `shared/api/error.ts`.
- **`handleApiSaveError`** — `shared/api/handleApiSaveError.ts`: notificação toast + erros por campo em formulários (settings, perfil, etc.).

## Sessão e tokens

- **`entities/session`**: API de login/refresh/logout, estado React (contexto ou store — ver `entities/session/index.ts` e ficheiros adjacentes).
- O backend define cookies / corpo conforme implementação; o front guarda **access token** para o header (ler `token.ts`).

## Exemplos de APIs por feature

| Feature | Ficheiro típico | Prefixo URL (exemplo) |
|---------|-----------------|------------------------|
| Resumes | `features/resume/api/resumeApi.ts` | `/resumes/...` |
| Dashboard | `features/dashboard/api/dashboardApi.ts` | `/dashboard/summary` |
| Notificações | `features/notifications/api/notificationsApi.ts` | `/notifications/` |
| Conta (perfil) | `entities/session` / features auth | `/accounts/...` |

Os prefixos exatos estão no **router Django** `backend/src/config/urls.py` (não duplicar aqui de memória — sempre confirmar).

## Performance

- **`trackApiRequest`** em `http.ts` — integração com telemetria leve em `shared/lib/performance`.

---

Segue para [04-backend-arquitetura-django.md](04-backend-arquitetura-django.md).
