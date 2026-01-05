import { loginSchema } from './schema';

describe('loginSchema', () => {
  test('accepts valid payload', () => {
    const parsed = loginSchema.safeParse({ email: 'test@example.com', password: '123' });
    expect(parsed.success).toBe(true);
  });

  test('rejects invalid email', () => {
    const parsed = loginSchema.safeParse({ email: 'nope', password: '123' });
    expect(parsed.success).toBe(false);
  });
});


