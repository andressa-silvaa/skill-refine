import type { ZodError } from 'zod';

import type { ResumeData } from '@/entities/resume';
import type { BuilderStep } from '../types';
import { BUILDER_STEPS } from '../types';
import { getResumeSchema, getStepSchema } from './schemas';

type ValidationOptions = {
  showSkillLevels: boolean;
};

export type ValidationErrors = Record<string, string>;

const toPathKey = (path: (string | number)[]) => path.join('.');

const mapZodErrors = (error: ZodError): ValidationErrors => {
  const errors: ValidationErrors = {};
  error.issues.forEach((issue) => {
    const key = toPathKey(issue.path);
    if (!errors[key]) {
      errors[key] = issue.message;
    }
  });
  return errors;
};

export const validateStep = (step: BuilderStep, data: ResumeData, options: ValidationOptions) => {
  const schema = getStepSchema(step, options);
  const parsed = schema.safeParse(data);
  if (parsed.success) {
    return { isValid: true, errors: {} as ValidationErrors, data: parsed.data };
  }
  return { isValid: false, errors: mapZodErrors(parsed.error), data };
};

export const validateResume = (data: ResumeData, options: ValidationOptions) => {
  const schema = getResumeSchema(options);
  const parsed = schema.safeParse(data);
  if (parsed.success) {
    return { isValid: true, errors: {} as ValidationErrors, data: parsed.data };
  }
  return { isValid: false, errors: mapZodErrors(parsed.error), data };
};

export const getStepForPath = (path: string): BuilderStep => {
  if (path.startsWith('theme') || path.startsWith('themePaletteId') || path.startsWith('themeAccentOverride') || path.startsWith('themeSecondaryOverride')) {
    return 'theme';
  }
  if (path.startsWith('targetPosition')) return 'basic';
  if (path.startsWith('contact.')) return 'contact';
  if (path.startsWith('experiences')) return 'experience';
  if (path.startsWith('educations')) return 'education';
  if (path.startsWith('skills')) return 'skills';
  if (path.startsWith('languages')) return 'languages';
  if (path.startsWith('summary')) return 'summary';
  return 'review';
};

export const getFirstErrorForStep = (errors: ValidationErrors, step: BuilderStep) => {
  const entries = Object.entries(errors);
  const match = entries.find(([path]) => getStepForPath(path) === step);
  return match?.[0] ?? null;
};

export const getFirstErrorStep = (errors: ValidationErrors): BuilderStep | null => {
  for (const step of BUILDER_STEPS) {
    const match = Object.keys(errors).some((path) => getStepForPath(path) === step.id);
    if (match) return step.id;
  }
  return null;
};
