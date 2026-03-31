import { z } from 'zod';

import { parseResumeDateToDate } from '@/shared/lib/date/resumeDate';

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

const DEFAULT_DATE_INVALID = 'Invalid date';

export const resumeDateString = (requiredMessage: string, dateInvalidMessage: string = DEFAULT_DATE_INVALID) =>
  z.preprocess(trimValue, z.string().min(1, requiredMessage).refine((value) => parseResumeDateToDate(String(value)) !== null, dateInvalidMessage));

export const optionalResumeDateString = (dateInvalidMessage: string = DEFAULT_DATE_INVALID) =>
  z.preprocess(
    emptyToUndefined,
    z.string().refine((value) => !value || parseResumeDateToDate(String(value)) !== null, dateInvalidMessage).optional(),
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

/**
 * Host plausível para links de currículo.
 * - Evita `https://abc` (host sem TLD).
 * - Evita strings só numéricas: o construtor `URL` trata como IPv4 em notação decimal única
 *   (ex.: `69369` → hostname `0.1.14.249`), o que passava refine indevidamente.
 */
const isPlausibleHttpUrl = (raw: string) => {
  const trimmed = raw.trim();
  if (!trimmed) return false;

  const hostCandidate = trimmed
    .replace(/^https?:\/\//i, '')
    .split('/')[0]
    ?.split('?')[0]
    ?.split('#')[0]
    ?.split(':')[0];

  if (hostCandidate && /^\d+$/.test(hostCandidate)) {
    return false;
  }

  try {
    const u = new URL(normalizeUrl(trimmed));
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
    const host = u.hostname.toLowerCase();
    if (host === 'localhost' || host.endsWith('.localhost')) return true;
    if (host.startsWith('[')) return true;
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return true;
    return host.includes('.');
  } catch {
    return false;
  }
};

export const optionalUrl = (message: string, maxMessage: string) =>
  z.preprocess(
    emptyToUndefined,
    z
      .string()
      .max(255, maxMessage)
      .refine((value) => !value || isPlausibleHttpUrl(value), message)
      .transform((value) => (value ? normalizeUrl(value) : value))
      .optional(),
  );

