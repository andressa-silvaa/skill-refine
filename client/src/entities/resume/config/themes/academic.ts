import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const academicTheme: ResumeTheme = {
  id: 'academic',
  name: 'Academic',
  description: 'Ênfase em formação e produção acadêmica.',
  tag: 'Acadêmico',
  tags: ['1 coluna', 'rigor'],
  category: 'Acadêmico',
  thumbnailSpec: { type: 'one-column', blocks: 6, header: 'hero' },
  layout: { type: 'single' },
  sectionOrder: ['education', 'experience', 'summary', 'skills', 'languages', 'contact'],
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
    fontFamily: '"Merriweather", "Times New Roman", serif',
    headingFontFamily: '"Merriweather", "Times New Roman", serif',
    spacingLg: '26px',
    spacingMd: '16px',
    spacingSm: '8px',
    sectionGap: '16px',
    radius: '6px',
  },
};
