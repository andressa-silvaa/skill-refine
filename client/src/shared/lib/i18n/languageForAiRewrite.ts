/**
 * Maps UI language to BCP-47 for /ai/rewrite (must match backend expectations).
 */
export function languageForAiRewrite(uiLanguage: string | undefined): string {
  const raw = (uiLanguage ?? 'pt-BR').trim().replace('_', '-');
  const lower = raw.toLowerCase();
  if (lower.startsWith('pt')) return 'pt-BR';
  if (lower.startsWith('en')) return 'en-US';
  if (lower.startsWith('es')) return 'es-ES';
  return 'pt-BR';
}

/**
 * Prefer saved account language (loads async after bootstrap); then document.documentElement.lang; then i18next.
 * Avoids sending pt-BR to the API while the UI is already en-US but preferences have not applied to i18n yet.
 */
export function resolveUiLanguageForAi(options: {
  preferencesLanguage?: string | null;
  i18nLanguage?: string;
  resolvedLanguage?: string;
}): string {
  const fromPrefs = (options.preferencesLanguage ?? '').trim();
  if (fromPrefs) return fromPrefs;
  if (typeof document !== 'undefined') {
    const fromHtml = document.documentElement.lang?.trim() ?? '';
    if (fromHtml.length >= 2) return fromHtml;
  }
  return (options.resolvedLanguage ?? options.i18nLanguage ?? 'pt-BR').trim() || 'pt-BR';
}
