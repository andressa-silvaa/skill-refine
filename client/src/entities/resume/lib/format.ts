import type { ResumeStatus } from '../model/types';

export function formatDatePt(dateIso: string) {
  const d = new Date(dateIso);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = String(d.getFullYear());
  return `${dd}/${mm}/${yyyy}`;
}

export function getResumeStatusLabel(status: ResumeStatus) {
  if (status === 'draft') return 'Rascunho';
  if (status === 'complete') return 'Completo';
  return 'Analisando';
}

export function getResumeStatusTone(status: ResumeStatus) {
  if (status === 'complete') return 'success';
  if (status === 'analyzing') return 'warning';
  return 'neutral';
}

export function formatMonthYear(dateStr: string): string {
  if (!dateStr) return '';
  const [year, month] = dateStr.split('-');
  if (!year || !month) return dateStr;
  const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  const monthIndex = parseInt(month, 10) - 1;
  if (monthIndex < 0 || monthIndex >= monthNames.length) return dateStr;
  return `${monthNames[monthIndex]} ${year}`;
}
