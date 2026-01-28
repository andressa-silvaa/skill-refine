import { getAccessToken } from './token';
import { normalizeApiErrorCode } from './errorCodes';

export type ApiErrorBody = {
  error?: { code?: string; error_code?: string; message?: string };
  error_code?: string;
  message?: string;
  fields?: Record<string, string | string[]>;
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

const RAW_API_URL = process.env.REACT_APP_API_URL ?? 'http://localhost:8000';
const API_URL = (RAW_API_URL.split('REACT_APP_')[0] ?? '').trim();

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();

  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && typeof init.body === 'string') headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  const contentType = res.headers.get('content-type') ?? '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? ((await res.json()) as unknown) : undefined;

  if (!res.ok) {
    const body = (data ?? {}) as ApiErrorBody;
    const rawCode = body.error?.error_code ?? body.error_code ?? body.error?.code;
    const code = normalizeApiErrorCode(rawCode);
    const message = body.error?.message ?? body.message ?? 'Erro inesperado';
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
    throw new ApiError(res.status, code, message, retryAfterSeconds, body);
  }

  return (data ?? ({} as unknown)) as T;
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
  const token = getAccessToken();

  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  if (!res.ok) {
    const contentType = res.headers.get('content-type') ?? '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? ((await res.json()) as unknown) : undefined;
    const body = (data ?? {}) as ApiErrorBody;
    const rawCode = body.error?.error_code ?? body.error_code ?? body.error?.code;
    const code = normalizeApiErrorCode(rawCode);
    const message = body.error?.message ?? body.message ?? 'Erro inesperado';
    throw new ApiError(res.status, code, message, undefined, body);
  }

  const blob = await res.blob();
  const filename = parseFilename(res.headers.get('content-disposition'));
  return { blob, filename };
}


