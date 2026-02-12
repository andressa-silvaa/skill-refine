import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const executiveTheme: ResumeTheme = {
  id: 'executive',
  name: 'Executive',
  description: 'Hierarquia sólida e tipografia séria.',
  tag: 'Executivo',
  tags: ['ATS-friendly', '1 coluna'],
  category: 'Profissional',
  thumbnailSpec: { type: 'one-column', blocks: 5, header: 'hero' },
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
    fontFamily: '"Libre Franklin", "Segoe UI", sans-serif',
    headingFontFamily: '"Libre Franklin", "Segoe UI", sans-serif',
    borderColor: '#CBD5E0',
    spacingLg: '26px',
    spacingMd: '16px',
    spacingSm: '8px',
    sectionGap: '16px',
    radius: '8px',
  },
};
