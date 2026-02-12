import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const compactDenseTheme: ResumeTheme = {
  id: 'compact-dense',
  name: 'Compact Dense',
  description: 'Alta densidade para maximizar conteúdo.',
  tag: 'Compacto',
  tags: ['1 página', 'denso'],
  category: 'Produtividade',
  thumbnailSpec: { type: 'compact', columns: 2, blocks: 6 },
  layout: { type: 'compact', columns: 2 },
  sectionOrder: ['summary', 'experience', 'education', 'skills', 'languages', 'contact'],
  visibilityRules: {
    summary: 'hideIfEmpty',
    experience: 'hideIfEmpty',
    education: 'hideIfEmpty',
    skills: 'hideIfEmpty',
    languages: 'hideIfEmpty',
    contact: 'hideIfEmpty',
  },
  palettes: BASE_PALETTES,
  defaultPaletteId: 'mono',
  styleTokens: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    spacingLg: '18px',
    spacingMd: '12px',
    spacingSm: '6px',
    sectionGap: '12px',
    radius: '6px',
  },
};
