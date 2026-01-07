import { ApiError } from './http';

export function asApiError(err: unknown): ApiError | null {
  return err instanceof ApiError ? err : null;
}

export function getApiErrorMessage(err: unknown, fallbackMessage: string) {
  const apiErr = asApiError(err);
  return apiErr?.message ?? fallbackMessage;
}


