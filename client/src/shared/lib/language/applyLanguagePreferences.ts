export function applyLanguagePreferences(prefs: { language?: string | null }) {
  const root = document.documentElement;
  const next = (prefs.language || '').trim();
  if (!next) return;
  root.lang = next;
}
