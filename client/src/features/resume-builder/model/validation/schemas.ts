import { z } from 'zod';

import type { BuilderStep } from '../types';
import {
  compareMonth,
  monthString,
  optionalHexColor,
  optionalMonthString,
  optionalTrimmedString,
  optionalTrimmedStringAllowEmpty,
  optionalTrimmedText,
  optionalUrl,
  requiredTrimmedString,
  optionalPhoneAllowEmpty,
} from './common';

type ValidationOptions = {
  showSkillLevels: boolean;
};

const themeSchema = z.object({
  themeId: z.string().min(1, 'Selecione um tema'),
  themePaletteId: z.string().min(1, 'Selecione uma paleta'),
  themeAccentOverride: optionalHexColor('Informe uma cor válida (#RRGGBB)'),
  themeSecondaryOverride: optionalHexColor('Informe uma cor válida (#RRGGBB)'),
});

const basicSchema = z.object({
  targetPosition: requiredTrimmedString(2, 80, {
    min: 'Informe o cargo alvo',
    max: 'O cargo alvo deve ter no máximo 80 caracteres',
  }),
});

const contactSchema = z.object({
  contact: z.object({
    fullName: requiredTrimmedString(3, 80, {
      min: 'Informe seu nome completo',
      max: 'O nome deve ter no máximo 80 caracteres',
    }),
    email: z.preprocess(
      (value) => (typeof value === 'string' ? value.trim() : value),
      z.string().email('Informe um e-mail válido'),
    ),
    phone: optionalPhoneAllowEmpty('Informe um telefone válido'),
    city: optionalTrimmedStringAllowEmpty(60, 'A cidade deve ter no máximo 60 caracteres'),
    country: optionalTrimmedStringAllowEmpty(60, 'O país deve ter no máximo 60 caracteres'),
    linkedin: optionalUrl('Informe uma URL válida', 'O link deve ter no máximo 255 caracteres'),
    portfolio: optionalUrl('Informe uma URL válida', 'O link deve ter no máximo 255 caracteres'),
    github: optionalUrl('Informe uma URL válida', 'O link deve ter no máximo 255 caracteres'),
    website: optionalUrl('Informe uma URL válida', 'O link deve ter no máximo 255 caracteres'),
  }),
});

const experienceItemSchema = z
  .object({
    id: z.string().min(1),
    company: requiredTrimmedString(2, 80, {
      min: 'Informe a empresa',
      max: 'A empresa deve ter no máximo 80 caracteres',
    }),
    position: requiredTrimmedString(2, 80, {
      min: 'Informe o cargo',
      max: 'O cargo deve ter no máximo 80 caracteres',
    }),
    startDate: monthString('Informe a data de início'),
    endDate: optionalMonthString(),
    isCurrent: z.boolean(),
    description: z
      .array(
        requiredTrimmedString(10, 200, {
          min: 'Descreva com pelo menos 10 caracteres',
          max: 'A descrição deve ter no máximo 200 caracteres',
        }),
      )
      .min(1, 'Adicione pelo menos 1 descrição')
      .max(8, 'Limite de 8 pontos de descrição'),
  })
  .superRefine((value, ctx) => {
    if (value.isCurrent) {
      if (value.endDate) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['endDate'],
          message: 'Informe a data de término ou marque "Trabalho atual"',
        });
      }
    } else if (!value.endDate) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['endDate'],
        message: 'Informe a data de término ou marque "Trabalho atual"',
      });
    }

    if (value.endDate && !value.isCurrent) {
      const validOrder = compareMonth(value.startDate, value.endDate);
      if (validOrder === false) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['endDate'],
          message: 'A data final não pode ser anterior à inicial',
        });
      }
    }
  });

const experienceSchema = z.object({
  experiences: z.array(experienceItemSchema),
});

const educationItemSchema = z
  .object({
    id: z.string().min(1),
    institution: requiredTrimmedString(2, 100, {
      min: 'Informe a instituição',
      max: 'A instituição deve ter no máximo 100 caracteres',
    }),
    course: requiredTrimmedString(2, 100, {
      min: 'Informe o curso',
      max: 'O curso deve ter no máximo 100 caracteres',
    }),
    degree: optionalTrimmedStringAllowEmpty(60, 'O grau deve ter no máximo 60 caracteres'),
    startDate: monthString('Informe a data de início'),
    endDate: optionalMonthString(),
    status: z.enum(['completed', 'in_progress']),
  })
  .superRefine((value, ctx) => {
    if (value.status === 'completed' && !value.endDate) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['endDate'],
        message: 'Informe a data de conclusão',
      });
    }

    if (value.endDate) {
      const validOrder = compareMonth(value.startDate, value.endDate);
      if (validOrder === false) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['endDate'],
          message: 'A data final não pode ser anterior à inicial',
        });
      }
    }
  });

const educationSchema = z.object({
  educations: z.array(educationItemSchema),
});

const createSkillSchema = (showSkillLevels: boolean) =>
  z.object({
    id: z.string().min(1),
    name: requiredTrimmedString(2, 40, {
      min: 'Informe a habilidade',
      max: 'A habilidade deve ter no máximo 40 caracteres',
    }),
    level: showSkillLevels
      ? z.enum(['beginner', 'intermediate', 'advanced', 'expert'], {
          required_error: 'Informe o nível',
        })
      : z.enum(['beginner', 'intermediate', 'advanced', 'expert']).optional(),
  });

const createSkillsSchema = (showSkillLevels: boolean) =>
  z
    .array(createSkillSchema(showSkillLevels))
    .min(1, 'Adicione pelo menos uma habilidade')
    .superRefine((skills, ctx) => {
      const seen = new Map<string, number>();
      skills.forEach((skill, idx) => {
        const key = skill.name.trim().toLowerCase();
        if (!key) return;
        const existing = seen.get(key);
        if (existing !== undefined) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: [idx, 'name'],
            message: 'Habilidade duplicada',
          });
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: [existing, 'name'],
            message: 'Habilidade duplicada',
          });
        } else {
          seen.set(key, idx);
        }
      });
    });

const createSkillsStepSchema = (options: ValidationOptions) =>
  z.object({
    skills: createSkillsSchema(options.showSkillLevels),
  });

const languageItemSchema = z.object({
  id: z.string().min(1),
  name: requiredTrimmedString(2, 40, {
    min: 'Informe o idioma',
    max: 'O idioma deve ter no máximo 40 caracteres',
  }),
  level: z.enum(['basic', 'intermediate', 'advanced', 'fluent', 'native']),
});

const languagesSchema = z
  .array(languageItemSchema)
  .superRefine((languages, ctx) => {
    const seen = new Map<string, number>();
    languages.forEach((lang, idx) => {
      const key = lang.name.trim().toLowerCase();
      if (!key) return;
      const existing = seen.get(key);
      if (existing !== undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: [idx, 'name'],
          message: 'Idioma duplicado',
        });
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: [existing, 'name'],
          message: 'Idioma duplicado',
        });
      } else {
        seen.set(key, idx);
      }
    });
  });

const languagesStepSchema = z.object({
  languages: languagesSchema,
});

const summarySchema = z.object({
  summary: optionalTrimmedText(30, 500, {
    min: 'O resumo deve ter pelo menos 30 caracteres',
    max: 'O resumo deve ter no máximo 500 caracteres',
  }),
});

const reviewSchema = z.object({});

export const getStepSchema = (step: BuilderStep, options: ValidationOptions) => {
  switch (step) {
    case 'theme':
      return themeSchema;
    case 'basic':
      return basicSchema;
    case 'contact':
      return contactSchema;
    case 'experience':
      return experienceSchema;
    case 'education':
      return educationSchema;
    case 'skills':
      return createSkillsStepSchema(options);
    case 'languages':
      return languagesStepSchema;
    case 'summary':
      return summarySchema;
    case 'review':
      return reviewSchema;
    default:
      return reviewSchema;
  }
};

export const getResumeSchema = (options: ValidationOptions) =>
  z.object({
    ...themeSchema.shape,
    ...basicSchema.shape,
    ...contactSchema.shape,
    ...experienceSchema.shape,
    ...educationSchema.shape,
    ...createSkillsStepSchema(options).shape,
    ...languagesStepSchema.shape,
    ...summarySchema.shape,
  });
