/**
 * Datas de experiência/formação: ISO YYYY-MM-DD (timezone local no picker).
 * Aceita legado YYYY-MM (interpretado como dia 1), alinhado ao backend.
 */

const LEGACY_MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

export function parseResumeDateToDate(value: string): Date | null {
  if (!value?.trim()) return null;
  const raw = value.trim();
  const parts = raw.split('-');
  if (parts.length === 3) {
    const y = parseInt(parts[0]!, 10);
    const m = parseInt(parts[1]!, 10);
    const d = parseInt(parts[2]!, 10);
    if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) return null;
    if (m < 1 || m > 12 || d < 1 || d > 31) return null;
    const dt = new Date(y, m - 1, d);
    if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null;
    return dt;
  }
  if (parts.length === 2 && LEGACY_MONTH.test(raw)) {
    const y = parseInt(parts[0]!, 10);
    const m = parseInt(parts[1]!, 10);
    return new Date(y, m - 1, 1);
  }
  return null;
}

export function formatResumeDate(date: Date | null): string {
  if (!date) return '';
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Normaliza YYYY-MM legado para YYYY-MM-01 (ex.: ao hidratar da API). */
export function normalizeResumeDateInput(value: string): string {
  const v = value.trim();
  if (LEGACY_MONTH.test(v)) return `${v}-01`;
  return v;
}

export function compareResumeDates(start?: string, end?: string): boolean | null {
  if (!start || !end) return null;
  const d1 = parseResumeDateToDate(start);
  const d2 = parseResumeDateToDate(end);
  if (!d1 || !d2) return null;
  return d1.getTime() <= d2.getTime();
}
