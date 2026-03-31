import { z } from 'zod';

import type { BuilderStep } from '../types';
import { compareResumeDates } from '@/shared/lib/date/resumeDate';
import {
  optionalHexColor,
  optionalResumeDateString,
  optionalTrimmedStringAllowEmpty,
  optionalTrimmedText,
  optionalUrl,
  requiredTrimmedString,
  optionalPhoneAllowEmpty,
  resumeDateString,
} from './common';

export type TFunction = (key: string) => string;

type ValidationOptions = {
  showSkillLevels: boolean;
};

const createThemeSchema = (t: TFunction) =>
  z.object({
    themeId: z.string().min(1, t('validation.themeRequired')),
    themePaletteId: z.string().min(1, t('validation.paletteRequired')),
    themeAccentOverride: optionalHexColor(t('validation.hexColorInvalid')),
    themeSecondaryOverride: optionalHexColor(t('validation.hexColorInvalid')),
  });

const createBasicSchema = (t: TFunction) =>
  z.object({
    targetPosition: requiredTrimmedString(2, 80, {
      min: t('validation.targetPositionMin'),
      max: t('validation.targetPositionMax'),
    }),
  });

const createContactSchema = (t: TFunction) =>
  z.object({
    contact: z.object({
      fullName: requiredTrimmedString(3, 80, {
        min: t('validation.fullNameMin'),
        max: t('validation.fullNameMax'),
      }),
      email: z.preprocess(
        (value) => (typeof value === 'string' ? value.trim() : value),
        z.string().email(t('validation.emailInvalid'))
      ),
      phone: optionalPhoneAllowEmpty(t('validation.phoneInvalid')),
      city: optionalTrimmedStringAllowEmpty(60, t('validation.cityMax')),
      country: optionalTrimmedStringAllowEmpty(60, t('validation.countryMax')),
      linkedin: optionalUrl(t('validation.urlInvalid'), t('validation.urlMax')),
      portfolio: optionalUrl(t('validation.urlInvalid'), t('validation.urlMax')),
      github: optionalUrl(t('validation.urlInvalid'), t('validation.urlMax')),
      website: optionalUrl(t('validation.urlInvalid'), t('validation.urlMax')),
    }),
  });

const createExperienceItemSchema = (t: TFunction) =>
  z
    .object({
      id: z.string().min(1),
      company: requiredTrimmedString(2, 80, {
        min: t('validation.companyMin'),
        max: t('validation.companyMax'),
      }),
      position: requiredTrimmedString(2, 80, {
        min: t('validation.positionMin'),
        max: t('validation.positionMax'),
      }),
      startDate: resumeDateString(t('validation.startDateRequired'), t('validation.dateInvalid')),
      endDate: optionalResumeDateString(t('validation.dateInvalid')),
      isCurrent: z.boolean(),
      description: z
        .array(
          requiredTrimmedString(10, 200, {
            min: t('validation.descriptionMin'),
            max: t('validation.descriptionMax'),
          })
        )
        .min(1, t('validation.descriptionCountMin'))
        .max(8, t('validation.descriptionCountMax')),
    })
    .superRefine((value, ctx) => {
      if (value.isCurrent) {
        if (value.endDate) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['endDate'],
            message: t('validation.endDateOrCurrent'),
          });
        }
      } else if (!value.endDate) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['endDate'],
          message: t('validation.endDateOrCurrent'),
        });
      }

      if (value.endDate && !value.isCurrent) {
        const validOrder = compareResumeDates(value.startDate, value.endDate);
        if (validOrder === false) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['endDate'],
            message: t('validation.endDateAfterStart'),
          });
        }
      }
    });

const createExperienceSchema = (t: TFunction) =>
  z.object({
    experiences: z.array(createExperienceItemSchema(t)),
  });

const createEducationItemSchema = (t: TFunction) =>
  z
    .object({
      id: z.string().min(1),
      institution: requiredTrimmedString(2, 100, {
        min: t('validation.institutionMin'),
        max: t('validation.institutionMax'),
      }),
      course: requiredTrimmedString(2, 100, {
        min: t('validation.courseMin'),
        max: t('validation.courseMax'),
      }),
      degree: optionalTrimmedStringAllowEmpty(60, t('validation.degreeMax')),
      startDate: resumeDateString(t('validation.startDateRequired'), t('validation.dateInvalid')),
      endDate: optionalResumeDateString(t('validation.dateInvalid')),
      status: z.enum(['completed', 'in_progress']),
    })
    .superRefine((value, ctx) => {
      if (value.status === 'completed' && !value.endDate) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['endDate'],
          message: t('validation.completionDate'),
        });
      }

      if (value.endDate) {
        const validOrder = compareResumeDates(value.startDate, value.endDate);
        if (validOrder === false) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['endDate'],
            message: t('validation.endDateAfterStart'),
          });
        }
      }
    });

const createEducationSchema = (t: TFunction) =>
  z.object({
    educations: z.array(createEducationItemSchema(t)),
  });

const createSkillSchema = (showSkillLevels: boolean, t: TFunction) =>
  z.object({
    id: z.string().min(1),
    name: requiredTrimmedString(2, 40, {
      min: t('validation.skillMin'),
      max: t('validation.skillMax'),
    }),
    level: showSkillLevels
      ? z.enum(['beginner', 'intermediate', 'advanced', 'expert'], {
          required_error: t('validation.skillLevelRequired'),
        })
      : z.enum(['beginner', 'intermediate', 'advanced', 'expert']).optional(),
  });

const createSkillsSchema = (showSkillLevels: boolean, t: TFunction) =>
  z
    .array(createSkillSchema(showSkillLevels, t))
    .min(1, t('validation.skillsMin'))
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
            message: t('validation.skillDuplicate'),
          });
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: [existing, 'name'],
            message: t('validation.skillDuplicate'),
          });
        } else {
          seen.set(key, idx);
        }
      });
    });

const createSkillsStepSchema = (options: ValidationOptions, t: TFunction) =>
  z.object({
    skills: createSkillsSchema(options.showSkillLevels, t),
  });

const createLanguageItemSchema = (t: TFunction) =>
  z.object({
    id: z.string().min(1),
    name: requiredTrimmedString(2, 40, {
      min: t('validation.languageMin'),
      max: t('validation.languageMax'),
    }),
    level: z.enum(['basic', 'intermediate', 'advanced', 'fluent', 'native']),
  });

const createLanguagesSchema = (t: TFunction) =>
  z
    .array(createLanguageItemSchema(t))
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
            message: t('validation.languageDuplicate'),
          });
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: [existing, 'name'],
            message: t('validation.languageDuplicate'),
          });
        } else {
          seen.set(key, idx);
        }
      });
    });

const createLanguagesStepSchema = (t: TFunction) =>
  z.object({
    languages: createLanguagesSchema(t),
  });

const createSummarySchema = (t: TFunction) =>
  z.object({
    summary: optionalTrimmedText(30, 500, {
      min: t('validation.summaryMin'),
      max: t('validation.summaryMax'),
    }),
  });

const reviewSchema = z.object({});

export const getStepSchema = (step: BuilderStep, options: ValidationOptions, t: TFunction) => {
  switch (step) {
    case 'theme':
      return createThemeSchema(t);
    case 'basic':
      return createBasicSchema(t);
    case 'contact':
      return createContactSchema(t);
    case 'experience':
      return createExperienceSchema(t);
    case 'education':
      return createEducationSchema(t);
    case 'skills':
      return createSkillsStepSchema(options, t);
    case 'languages':
      return createLanguagesStepSchema(t);
    case 'summary':
      return createSummarySchema(t);
    case 'review':
      return reviewSchema;
    default:
      return reviewSchema;
  }
};

export const getResumeSchema = (options: ValidationOptions, t: TFunction) =>
  z.object({
    ...createThemeSchema(t).shape,
    ...createBasicSchema(t).shape,
    ...createContactSchema(t).shape,
    ...createExperienceSchema(t).shape,
    ...createEducationSchema(t).shape,
    ...createSkillsStepSchema(options, t).shape,
    ...createLanguagesStepSchema(t).shape,
    ...createSummarySchema(t).shape,
  });
