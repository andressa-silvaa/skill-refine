import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const minimalCleanTheme: ResumeTheme = {
  id: 'minimal-clean',
  name: 'Minimal Clean',
  description: 'Espaço em branco e leitura fluida.',
  tag: 'Minimal',
  tags: ['ATS-friendly', 'clean'],
  category: 'Minimal',
  thumbnailSpec: { type: 'one-column', blocks: 4, header: 'simple' },
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
    spacingLg: '32px',
    spacingMd: '20px',
    spacingSm: '10px',
    sectionGap: '22px',
    radius: '10px',
  },
};
