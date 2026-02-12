import type { ResumeTheme } from '../../model/theme';

const TECH_STACK_PALETTES = [
  { id: 'blue', name: 'Azul', nameKey: 'palette.blue', accent: '#0EA5E9', accentSoft: 'rgba(14, 165, 233, 0.12)' },
  { id: 'green', name: 'Verde', nameKey: 'palette.green', accent: '#10B981', accentSoft: 'rgba(16, 185, 129, 0.12)' },
  { id: 'mono', name: 'Monocromático', nameKey: 'palette.mono', accent: '#E2E8F0', accentSoft: 'rgba(226, 232, 240, 0.12)' },
];

export const techStackTheme: ResumeTheme = {
  id: 'tech-stack',
  name: 'Tech Stack',
  description: 'Skills e stacks em destaque lateral.',
  tag: 'Tech',
  tags: ['2 colunas', 'skills'],
  category: 'Tecnologia',
  thumbnailSpec: { type: 'two-column', sidebarPosition: 'left', mainBlocks: 3, sidebarBlocks: 4 },
  layout: {
    type: 'split',
    sidebarPosition: 'left',
    sidebarSections: ['skills', 'languages', 'contact'],
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
  palettes: TECH_STACK_PALETTES,
  defaultPaletteId: 'blue',
  styleTokens: {
    fontFamily: '"JetBrains Mono", "Inter", monospace',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    sidebarBg: '#0F172A',
    paperBg: '#0B1220',
    borderColor: '#1E293B',
    spacingLg: '22px',
    spacingMd: '14px',
    spacingSm: '8px',
    sectionGap: '14px',
    radius: '10px',
  },
};
