export const API_ERROR_CODES = {
  EMAIL_NOT_CONFIRMED: 'EMAIL_NOT_CONFIRMED',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  EMAIL_ALREADY_IN_USE: 'EMAIL_ALREADY_IN_USE',
} as const;

export function normalizeApiErrorCode(code?: string) {
  const value = (code ?? '').trim();
  if (!value) return undefined;
  return value.toUpperCase();
}


