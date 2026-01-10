import type { SessionPreferences } from './types';

export function normalizePreferences(raw: any): SessionPreferences {
  const theme = raw?.theme === 'dark' ? 'dark' : 'light';
  const accent_color = String(raw?.accent_color ?? raw?.accentColor ?? 'pink');
  const language = String(raw?.language ?? 'pt-BR');
  const email_notifications_enabled = Boolean(raw?.email_notifications_enabled ?? raw?.emailNotificationsEnabled);
  return { theme, accent_color, language, email_notifications_enabled };
}
