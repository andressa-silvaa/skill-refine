import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const projectFirstTheme: ResumeTheme = {
  id: 'project-first',
  name: 'Project-First',
  description: 'Projetos e cases em destaque visual.',
  tag: 'Projetos',
  tags: ['visual', 'cards'],
  category: 'Criativo',
  thumbnailSpec: { type: 'project-grid', columns: 2, rows: 2 },
  layout: { type: 'grid' },
  sectionOrder: ['summary', 'experience', 'skills', 'education', 'languages', 'contact'],
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
    fontFamily: '"Manrope", "Segoe UI", sans-serif',
    headingFontFamily: '"Manrope", "Segoe UI", sans-serif',
    spacingLg: '22px',
    spacingMd: '14px',
    spacingSm: '8px',
    sectionGap: '14px',
    radius: '12px',
  },
};
