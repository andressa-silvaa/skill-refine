import type { ResumeThemePalette } from '../../model/theme';

export const BASE_PALETTES: ResumeThemePalette[] = [
  { id: 'neutral', name: 'Neutro', nameKey: 'palette.neutral', accent: '#1F2937', accentSoft: 'rgba(31, 41, 55, 0.08)' },
  { id: 'blue', name: 'Azul', nameKey: 'palette.blue', accent: '#2563EB', accentSoft: 'rgba(37, 99, 235, 0.12)' },
  { id: 'purple', name: 'Roxo', nameKey: 'palette.purple', accent: '#7C3AED', accentSoft: 'rgba(124, 58, 237, 0.12)' },
  { id: 'green', name: 'Verde', nameKey: 'palette.green', accent: '#0F766E', accentSoft: 'rgba(15, 118, 110, 0.12)' },
  { id: 'mono', name: 'Monocromático', nameKey: 'palette.mono', accent: '#111827', accentSoft: 'rgba(17, 24, 39, 0.12)' },
];

export const FALLBACK_PALETTE: ResumeThemePalette = {
  id: 'neutral',
  name: 'Neutro',
  accent: '#1F2937',
  accentSoft: 'rgba(31, 41, 55, 0.08)',
};
