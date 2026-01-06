import { getAccessToken } from './token';

export type ApiErrorBody = {
  error?: { code?: string; message?: string };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(status: number, code: string | undefined, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const RAW_API_URL = process.env.REACT_APP_API_URL ?? 'http://localhost:8000';
// Defensive: if .env is malformed, CRA can concatenate vars into one string.
const API_URL = (RAW_API_URL.split('REACT_APP_')[0] ?? '').trim();

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();

  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include', // required for HttpOnly refresh cookie
  });

  const contentType = res.headers.get('content-type') ?? '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? ((await res.json()) as unknown) : undefined;

  if (!res.ok) {
    const body = (data ?? {}) as ApiErrorBody;
    const code = body.error?.code;
    const message = body.error?.message ?? 'Erro inesperado';
    throw new ApiError(res.status, code, message);
  }

  return (data ?? ({} as unknown)) as T;
}


