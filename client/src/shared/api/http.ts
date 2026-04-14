import { getAccessToken } from './token';
import { normalizeApiErrorCode } from './errorCodes';
import { trackApiRequest } from '@/shared/lib/performance';

export type ApiErrorBody = {
  error?: { code?: string; error_code?: string; message?: string };
  error_code?: string;
  message?: string;
  fields?: Record<string, string | string[]>;
  detail?: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly retryAfterSeconds?: number;
  readonly body?: ApiErrorBody;

  constructor(status: number, code: string | undefined, message: string, retryAfterSeconds?: number, body?: ApiErrorBody) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
    this.body = body;
  }
}

const API_BASE = (process.env.REACT_APP_API_URL ?? 'http://localhost:8000').trim().replace(/\/+$/, '');

function isAuthFlowPath(path: string): boolean {
  const p = path.startsWith('/') ? path : `/${path}`;
  return (
    p.includes('/accounts/auth/refresh') ||
    p.includes('/accounts/auth/login') ||
    p.includes('/accounts/auth/register') ||
    p.includes('/accounts/auth/google')
  );
}

async function refreshSessionOnce(): Promise<void> {
  const { sessionApi } = await import('@/entities/session/api/sessionApi');
  await sessionApi.refresh();
}

function buildHeaders(init: RequestInit): Headers {
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && typeof init.body === 'string') headers.set('Content-Type', 'application/json');
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return headers;
}

function parseApiError(res: Response, data: unknown): ApiError {
  const body = (data ?? {}) as ApiErrorBody;
  const rawCode = body.error?.error_code ?? body.error_code ?? body.error?.code;
  const code = normalizeApiErrorCode(rawCode);
  const message =
    body.error?.message ??
    body.message ??
    (typeof body.detail === 'string' ? body.detail : undefined) ??
    'Erro inesperado';
  let retryAfterSeconds: number | undefined;
  if (res.status === 429) {
    const raw = (res.headers.get('retry-after') ?? '').trim();
    if (raw) {
      const asInt = Number(raw);
      if (Number.isFinite(asInt) && asInt > 0) {
        retryAfterSeconds = Math.floor(asInt);
      } else {
        const asDate = Date.parse(raw);
        if (!Number.isNaN(asDate)) {
          const diffSeconds = Math.ceil((asDate - Date.now()) / 1000);
          if (diffSeconds > 0) retryAfterSeconds = diffSeconds;
        }
      }
    }
  }
  return new ApiError(res.status, code, message, retryAfterSeconds, body);
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  trackApiRequest(path);

  const allowRetry = !isAuthFlowPath(path);

  for (let attempt = 0; attempt < 2; attempt++) {
    const headers = buildHeaders(init);
    const res = await fetch(url, {
      ...init,
      headers,
      credentials: 'include',
    });

    const contentType = res.headers.get('content-type') ?? '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? ((await res.json()) as unknown) : undefined;

    if (res.ok) {
      return (data ?? ({} as unknown)) as T;
    }

    if ((res.status === 401 || res.status === 403) && allowRetry && attempt === 0) {
      try {
        await refreshSessionOnce();
        continue;
      } catch {
        throw parseApiError(res, data);
      }
    }

    throw parseApiError(res, data);
  }

  throw new ApiError(401, undefined, 'Sessão expirada');
}

export type ApiBlobResponse = {
  blob: Blob;
  filename?: string;
};

function parseFilename(disposition: string | null): string | undefined {
  if (!disposition) return undefined;
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) return decodeURIComponent(utfMatch[1]);
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match?.[1];
}

export async function apiRequestBlob(path: string, init: RequestInit = {}): Promise<ApiBlobResponse> {
  const url = `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  trackApiRequest(path);
  const allowRetry = !isAuthFlowPath(path);

  for (let attempt = 0; attempt < 2; attempt++) {
    const headers = buildHeaders(init);
    const res = await fetch(url, {
      ...init,
      headers,
      credentials: 'include',
    });

    if (res.ok) {
      const blob = await res.blob();
      const filename = parseFilename(res.headers.get('content-disposition'));
      return { blob, filename };
    }

    const contentType = res.headers.get('content-type') ?? '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? ((await res.json()) as unknown) : undefined;

    if ((res.status === 401 || res.status === 403) && allowRetry && attempt === 0) {
      try {
        await refreshSessionOnce();
        continue;
      } catch {
        throw parseApiError(res, data);
      }
    }

    throw parseApiError(res, data);
  }

  throw new ApiError(401, undefined, 'Sessão expirada');
}
