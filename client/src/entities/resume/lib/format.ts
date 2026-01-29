import type { ResumeData, ResumeStatus } from '../model/types';

export type TFunction = (key: string, options?: Record<string, string>) => string;

export function formatDatePt(dateIso: string) {
  const d = new Date(dateIso);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = String(d.getFullYear());
  return `${dd}/${mm}/${yyyy}`;
}

export function getResumeStatusLabel(status: ResumeStatus, t: TFunction) {
  if (status === 'draft') return t('resume.statusDraft');
  if (status === 'complete') return t('resume.statusComplete');
  return t('resume.statusAnalyzing');
}

export function getResumeStatusTone(status: ResumeStatus) {
  if (status === 'complete') return 'success';
  if (status === 'analyzing') return 'warning';
  return 'neutral';
}

/** Format YYYY-MM to locale-aware "Mon YYYY". Pass locale (e.g. from i18n.language) for translated months. */
export function formatMonthYear(dateStr: string, locale?: string): string {
  if (!dateStr) return '';
  const [year, month] = dateStr.split('-');
  if (!year || !month) return dateStr;
  const monthIndex = parseInt(month, 10) - 1;
  if (monthIndex < 0 || monthIndex >= 12) return dateStr;
  if (locale) {
    const date = new Date(parseInt(year, 10), monthIndex, 1);
    return new Intl.DateTimeFormat(locale, { month: 'short', year: 'numeric' }).format(date);
  }
  const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  return `${monthNames[monthIndex]} ${year}`;
}

/** Formata score para exibição. null/undefined → "—"; caso contrário "N/100". */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—';
  return `${score}/100`;
}

/** Retorna as primeiras N skills e o overflow. Usado em cards/lista. */
export function getTopSkills(skills: string[], max: number): { visible: string[]; overflow: number } {
  const visible = skills.slice(0, max);
  const overflow = Math.max(0, skills.length - visible.length);
  return { visible, overflow };
}

/** Score de completude (0–100) usado na revisão e persistido no backend. Mesma lógica do ReviewStep. */
export function calculateCompletenessScore(data: ResumeData): number {
  let score = 0;
  if (data.targetPosition) score += 10;
  if (data.contact.fullName && data.contact.email) score += 15;
  if (data.experiences.length > 0) score += 20;
  if (data.educations.length > 0) score += 10;
  if (data.skills.length > 0) score += 15;
  if (data.languages.length > 0) score += 5;
  if (data.summary) score += 15;
  if (data.experiences.length >= 2) score += 10;
  return Math.min(100, score);
}
