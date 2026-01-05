import { z } from 'zod';

export const requestResetSchema = z.object({
  email: z.string().trim().email('Informe um e-mail válido'),
});

export const verifyCodeSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^\d{5}$/, 'O código deve ter 5 dígitos'),
});

export const setNewPasswordSchema = z
  .object({
    password: z.string().min(8, 'A senha deve ter pelo menos 8 caracteres'),
    confirm: z.string().min(1, 'Confirme a senha'),
  })
  .refine((v) => v.password === v.confirm, {
    message: 'As senhas não coincidem',
    path: ['confirm'],
  });

export type RequestResetValues = z.infer<typeof requestResetSchema>;
export type VerifyCodeValues = z.infer<typeof verifyCodeSchema>;
export type SetNewPasswordValues = z.infer<typeof setNewPasswordSchema>;


