import { ApiError } from './http';

export function asApiError(err: unknown): ApiError | null {
  return err instanceof ApiError ? err : null;
}

export function getApiErrorMessage(err: unknown, fallbackMessage: string) {
  const apiErr = asApiError(err);
  return apiErr?.message ?? fallbackMessage;
}

export function getApiFieldErrors(err: unknown) {
  const apiErr = asApiError(err);
  const fields = apiErr?.body?.fields;
  if (!fields) return null;
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(fields)) {
    if (!k) continue;
    if (typeof v === 'string') out[k] = v;
    else if (Array.isArray(v) && typeof v[0] === 'string') out[k] = v[0];
  }
  return Object.keys(out).length ? out : null;
}


