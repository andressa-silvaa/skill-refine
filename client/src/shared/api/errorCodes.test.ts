import { normalizeApiErrorCode } from './errorCodes';

describe('normalizeApiErrorCode', () => {
  it('returns undefined for empty or whitespace', () => {
    expect(normalizeApiErrorCode(undefined)).toBeUndefined();
    expect(normalizeApiErrorCode('')).toBeUndefined();
    expect(normalizeApiErrorCode('   ')).toBeUndefined();
  });

  it('uppercases and trims', () => {
    expect(normalizeApiErrorCode('  email_not_confirmed  ')).toBe('EMAIL_NOT_CONFIRMED');
    expect(normalizeApiErrorCode('invalid_credentials')).toBe('INVALID_CREDENTIALS');
  });
});
