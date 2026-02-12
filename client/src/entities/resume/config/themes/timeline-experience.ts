import type { ResumeTheme } from '../../model/theme';
import { BASE_PALETTES } from './palettes';

export const timelineExperienceTheme: ResumeTheme = {
  id: 'timeline-experience',
  name: 'Timeline Experience',
  description: 'Experiência em linha do tempo vertical.',
  tag: 'Timeline',
  tags: ['1 coluna', 'visual'],
  category: 'Moderno',
  thumbnailSpec: { type: 'timeline', items: 4 },
  layout: { type: 'timeline' },
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
  defaultPaletteId: 'blue',
  styleTokens: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    headingFontFamily: '"Inter", "Segoe UI", sans-serif',
    spacingLg: '24px',
    spacingMd: '16px',
    spacingSm: '8px',
    sectionGap: '16px',
    radius: '10px',
  },
};
