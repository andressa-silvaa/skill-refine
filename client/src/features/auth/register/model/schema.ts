import { z } from 'zod';

export const registerSchema = z
  .object({
    fullName: z.string().trim().min(2, 'Informe seu nome completo'),
    birthDate: z.preprocess(
      (v) => (v instanceof Date ? v : undefined),
      z.date({ required_error: 'Informe sua data de nascimento' }),
    ),
    email: z.string().trim().email('Informe um e-mail válido'),
    password: z.string().min(8, 'A senha deve ter pelo menos 8 caracteres'),
    confirm: z.string().min(1, 'Confirme a senha'),
    acceptedTerms: z.boolean().refine((v) => v, 'Você precisa aceitar os termos'),
  })
  .refine((v) => v.password === v.confirm, {
    message: 'As senhas não coincidem',
    path: ['confirm'],
  });

export type RegisterFormValues = z.input<typeof registerSchema>;
export type RegisterValues = z.output<typeof registerSchema>;


