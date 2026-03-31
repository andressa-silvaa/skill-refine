import { compareResumeDates, formatResumeDate, normalizeResumeDateInput, parseResumeDateToDate } from './resumeDate';

describe('resumeDate', () => {
  it('parse + format roundtrip (dia completo)', () => {
    const d = parseResumeDateToDate('2026-03-15');
    expect(d).not.toBeNull();
    expect(formatResumeDate(d)).toBe('2026-03-15');
  });

  it('legado YYYY-MM → primeiro dia do mês', () => {
    const d = parseResumeDateToDate('2026-03');
    expect(d).not.toBeNull();
    expect(formatResumeDate(d)).toBe('2026-03-01');
  });

  it('normalizeResumeDateInput expande legado', () => {
    expect(normalizeResumeDateInput('2020-01')).toBe('2020-01-01');
    expect(normalizeResumeDateInput('2020-01-15')).toBe('2020-01-15');
  });

  it('compareResumeDates por dia', () => {
    expect(compareResumeDates('2020-01-01', '2020-01-02')).toBe(true);
    expect(compareResumeDates('2020-01-10', '2020-01-02')).toBe(false);
  });

  it('parse rejeita inválidos', () => {
    expect(parseResumeDateToDate('')).toBeNull();
    expect(parseResumeDateToDate('2026-13-01')).toBeNull();
    expect(parseResumeDateToDate('2026-02-31')).toBeNull();
    expect(parseResumeDateToDate('abc')).toBeNull();
  });
});
