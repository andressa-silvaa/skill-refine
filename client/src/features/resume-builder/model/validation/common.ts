import { z } from 'zod';

const trimValue = (value: unknown) => (typeof value === 'string' ? value.trim() : value);

const emptyToUndefined = (value: unknown) => {
  if (typeof value !== 'string') return value;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : undefined;
};

export const requiredTrimmedString = (min: number, max: number, messages: { min: string; max: string }) =>
  z.preprocess(trimValue, z.string().min(min, messages.min).max(max, messages.max));

export const optionalTrimmedString = (max: number, message: string) =>
  z.preprocess(emptyToUndefined, z.string().max(max, message).optional());

export const optionalTrimmedStringAllowEmpty = (max: number, message: string) =>
  z.preprocess(trimValue, z.string().max(max, message));

export const optionalTrimmedText = (min: number, max: number, messages: { min: string; max: string }) =>
  z.preprocess(
    trimValue,
    z
      .string()
      .max(max, messages.max)
      .refine((value) => value.length === 0 || value.length >= min, messages.min),
  );

const monthRegex = /^\d{4}-(0[1-9]|1[0-2])$/;

const DEFAULT_DATE_INVALID = 'Invalid date';

export const monthString = (requiredMessage: string, dateInvalidMessage: string = DEFAULT_DATE_INVALID) =>
  z.preprocess(trimValue, z.string().min(1, requiredMessage).refine((value) => monthRegex.test(String(value)), dateInvalidMessage));

export const optionalMonthString = (dateInvalidMessage: string = DEFAULT_DATE_INVALID) =>
  z.preprocess(
    emptyToUndefined,
    z.string().refine((value) => !value || monthRegex.test(String(value)), dateInvalidMessage).optional(),
  );

export const optionalPhoneAllowEmpty = (message: string) =>
  z.preprocess(
    trimValue,
    z.string().refine((value) => value.length === 0 || /^(\+55\s?)?(\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}$/.test(value), message),
  );

const hexRegex = /^#([0-9a-fA-F]{6})$/;
export const optionalHexColor = (message: string) =>
  z.preprocess(emptyToUndefined, z.string().refine((value) => !value || hexRegex.test(value), message).optional());

const normalizeUrl = (value: string) => {
  if (!value) return value;
  if (/^https?:\/\//i.test(value)) return value;
  return `https://${value}`;
};

export const optionalUrl = (message: string, maxMessage: string) =>
  z.preprocess(
    emptyToUndefined,
    z
      .string()
      .max(255, maxMessage)
      .refine((value) => {
        if (!value) return true;
        try {
          new URL(normalizeUrl(value));
          return true;
        } catch {
          return false;
        }
      }, message)
      .transform((value) => (value ? normalizeUrl(value) : value))
      .optional(),
  );

export const compareMonth = (start?: string, end?: string) => {
  if (!start || !end || !monthRegex.test(start) || !monthRegex.test(end)) return null;
  const [startYearStr, startMonthStr] = start.split('-');
  const [endYearStr, endMonthStr] = end.split('-');
  if (!startYearStr || !startMonthStr || !endYearStr || !endMonthStr) return null;
  const startYear = Number(startYearStr);
  const startMonth = Number(startMonthStr);
  const endYear = Number(endYearStr);
  const endMonth = Number(endMonthStr);
  if ([startYear, startMonth, endYear, endMonth].some((value) => Number.isNaN(value))) return null;
  return startYear * 12 + startMonth <= endYear * 12 + endMonth;
};
