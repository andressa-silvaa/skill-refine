import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const classicOneColumnTheme: ResumeTheme = {
  id: 'classic-one-column',
  name: 'Classic One-Column',
  description: 'Layout clássico e linear, ideal para ATS.',
  tag: 'ATS-first',
  tags: ['ATS-friendly', '1 coluna'],
  category: 'Clássico',
  thumbnailSpec: { type: 'one-column', blocks: 5, header: 'simple' },
  layout: { type: 'single' },
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
  defaultPaletteId: 'neutral',
  styleTokens: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    spacingLg: '28px',
    spacingMd: '18px',
    spacingSm: '10px',
    sectionGap: '18px',
    radius: '6px',
  },
};
