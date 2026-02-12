import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const elegantSerifTheme: ResumeTheme = {
  id: 'elegant-serif',
  name: 'Elegant Serif',
  description: 'Serifado com hierarquia clássica.',
  tag: 'Elegante',
  tags: ['1 coluna', 'serif'],
  category: 'Clássico',
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
  defaultPaletteId: 'mono',
  styleTokens: {
    fontFamily: '"Playfair Display", "Times New Roman", serif',
    headingFontFamily: '"Playfair Display", "Times New Roman", serif',
    spacingLg: '28px',
    spacingMd: '18px',
    spacingSm: '10px',
    sectionGap: '18px',
    radius: '6px',
  },
};
