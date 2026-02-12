import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const modernOneColumnTheme: ResumeTheme = {
  id: 'modern-one-column',
  name: 'Modern One-Column',
  description: 'Visual moderno com leitura direta.',
  tag: 'Moderno',
  tags: ['ATS-friendly', '1 coluna'],
  category: 'Moderno',
  thumbnailSpec: { type: 'one-column', blocks: 6, header: 'hero' },
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
  defaultPaletteId: 'blue',
  styleTokens: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    spacingLg: '26px',
    spacingMd: '16px',
    spacingSm: '8px',
    sectionGap: '16px',
    radius: '10px',
  },
};
