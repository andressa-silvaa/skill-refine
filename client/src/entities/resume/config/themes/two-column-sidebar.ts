import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const twoColumnSidebarTheme: ResumeTheme = {
  id: 'two-column-sidebar',
  name: 'Two-Column Sidebar',
  description: 'Sidebar para contato e skills (atenção ao ATS).',
  tag: '2 colunas',
  tags: ['2 colunas', 'ATS atenção'],
  category: 'Moderno',
  thumbnailSpec: { type: 'two-column', sidebarPosition: 'right', mainBlocks: 4, sidebarBlocks: 3 },
  layout: {
    type: 'split',
    sidebarPosition: 'right',
    sidebarSections: ['contact', 'skills', 'languages'],
    mainSections: ['summary', 'experience', 'education'],
  },
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
  defaultPaletteId: 'green',
  styleTokens: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    sidebarBg: '#F1F5F9',
    spacingLg: '24px',
    spacingMd: '16px',
    spacingSm: '8px',
    sectionGap: '16px',
    radius: '12px',
  },
};
