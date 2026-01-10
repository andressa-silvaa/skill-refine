export type ThemeMode = 'light' | 'dark';
export type AccentKey = 'pink' | 'purple' | 'blue' | 'green' | 'orange';

export const ACCENTS: Array<{ key: AccentKey; label: string; color: string }> = [
  { key: 'pink', label: 'Rosa', color: '#c72cb8' },
  { key: 'purple', label: 'Roxo', color: '#8b2e80' },
  { key: 'blue', label: 'Azul', color: '#2f6feb' },
  { key: 'green', label: 'Verde', color: '#2bbf5a' },
  { key: 'orange', label: 'Laranja', color: '#d45a00' },
];

const ACCENT_VARS: Record<AccentKey, { primary: string; textPurple: string; rightPanel: string; rgb: string }> = {
  pink: { primary: '#c72cb8', textPurple: '#c72cb8', rightPanel: '#d62bc3', rgb: '199,44,184' },
  purple: { primary: '#8b2e80', textPurple: '#8b2e80', rightPanel: '#a13a96', rgb: '139,46,128' },
  blue: { primary: '#2f6feb', textPurple: '#2f6feb', rightPanel: '#2563eb', rgb: '47,111,235' },
  green: { primary: '#2bbf5a', textPurple: '#2bbf5a', rightPanel: '#22c55e', rgb: '43,191,90' },
  orange: { primary: '#d45a00', textPurple: '#d45a00', rightPanel: '#e06a00', rgb: '212,90,0' },
};

export function applyAppearancePreferences(prefs: { theme?: ThemeMode | null; accent_color?: string | null }) {
  const root = document.documentElement;
  const nextTheme = prefs.theme === 'dark' || prefs.theme === 'light' ? prefs.theme : null;
  if (nextTheme) root.dataset.theme = nextTheme;

  if (prefs.accent_color != null) {
    const key = prefs.accent_color as AccentKey;
    const accent = ACCENT_VARS[key] ?? ACCENT_VARS.pink;
    root.style.setProperty('--primary', accent.primary);
    root.style.setProperty('--text-purple', accent.textPurple);
    root.style.setProperty('--right-panel', accent.rightPanel);
    root.style.setProperty('--sr-accent', accent.primary);
    root.style.setProperty('--sr-accent-rgb', accent.rgb);
  }
}

