export function monthLabel(period: string, locale: string): string {
  const date = new Date(`${period}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) return period;
  return new Intl.DateTimeFormat(locale, { month: 'short' }).format(date);
}

export function iconForInsightKey(key: string): string {
  if (key.includes('ats_keywords')) return 'fa-solid fa-key';
  if (key.includes('metrics')) return 'fa-solid fa-chart-line';
  if (key.includes('summary')) return 'fa-solid fa-align-left';
  if (key.includes('action_verbs')) return 'fa-solid fa-bolt';
  if (key.includes('links')) return 'fa-solid fa-link';
  return 'fa-solid fa-lightbulb';
}

export function firstNameFromUserFullName(fullName: string | null | undefined, fallback: string): string {
  const raw = (fullName || '').trim();
  if (!raw) return fallback;
  return raw.split(/\s+/)[0] || fallback;
}
