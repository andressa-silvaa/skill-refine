import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const hybridBalancedTheme: ResumeTheme = {
  id: 'hybrid-balanced',
  name: 'Hybrid Balanced',
  description: 'Resumo, competências e experiência equilibrados.',
  tag: 'Híbrido',
  tags: ['ATS-friendly', 'equilíbrio'],
  category: 'Versátil',
  thumbnailSpec: { type: 'one-column', blocks: 6, header: 'simple' },
  layout: { type: 'single' },
  sectionOrder: ['summary', 'skills', 'experience', 'education', 'languages', 'contact'],
  visibilityRules: {
    summary: 'hideIfEmpty',
    experience: 'hideIfEmpty',
    education: 'hideIfEmpty',
    skills: 'hideIfEmpty',
    languages: 'hideIfEmpty',
    contact: 'hideIfEmpty',
  },
  palettes: BASE_PALETTES,
  defaultPaletteId: 'purple',
  styleTokens: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    spacingLg: '24px',
    spacingMd: '16px',
    spacingSm: '8px',
    sectionGap: '16px',
    radius: '8px',
  },
};
