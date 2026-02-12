import { registerSchema } from '@/features/auth';

export function validateFullName(fullName: string): string | null {
  const next = fullName.trim();
  if (!next) return 'Nome inválido.';

  const registerBaseSchema = (registerSchema as any).innerType?.() ?? null;
  const fullNameSchema = registerBaseSchema?.shape?.fullName;
  const parsed = fullNameSchema?.safeParse ? fullNameSchema.safeParse(next) : { success: true };
  if (parsed.success) return null;

  return parsed.error.issues[0]?.message ?? 'Nome inválido.';
}
