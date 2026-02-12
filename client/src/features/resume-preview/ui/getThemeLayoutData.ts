import type { ResumeData } from '@/entities/resume';
import type { ResumeTheme } from '@/entities/resume';

import type { ThemeBlock, ThemeLayoutData } from './types';
import {
  buildSections,
  createHeaderBlock,
  createPortfolioBlock,
  createTimelineBlock,
  renderSection,
} from './sections/buildBlocks';

export function getThemeLayoutData(theme: ResumeTheme, data: ResumeData): ThemeLayoutData {
  switch (theme.id) {
    case 'two-column-sidebar':
      return {
        type: 'two-column',
        variant: 'split',
        main: [
          createHeaderBlock(data, 'default', 'left', false),
          ...buildSections(
            data,
            theme.layout.type === 'split' ? theme.layout.mainSections : theme.sectionOrder,
            undefined,
            theme.visibilityRules
          ),
        ],
        sidebar: buildSections(
          data,
          theme.layout.type === 'split' ? theme.layout.sidebarSections : [],
          undefined,
          theme.visibilityRules
        ),
      };
    case 'tech-stack':
      return {
        type: 'two-column',
        variant: 'tech',
        main: buildSections(
          data,
          theme.layout.type === 'split' ? theme.layout.mainSections : theme.sectionOrder,
          undefined,
          theme.visibilityRules
        ),
        sidebar: [
          createHeaderBlock(data, 'compact', 'left', false),
          ...buildSections(
            data,
            theme.layout.type === 'split' ? theme.layout.sidebarSections : [],
            undefined,
            theme.visibilityRules
          ),
        ],
      };
    case 'compact-dense':
      return {
        type: 'two-column',
        variant: 'compact',
        headerPlacement: 'full',
        main: [
          createHeaderBlock(data, 'compact', 'left', true),
          ...buildSections(data, ['summary', 'experience', 'education'], undefined, theme.visibilityRules),
        ],
        sidebar: buildSections(data, ['skills', 'languages', 'contact'], 'accent', theme.visibilityRules),
      };
    case 'timeline-experience': {
      const blocks = [
        createHeaderBlock(data, 'default', 'left', false),
        renderSection('summary', data, undefined, theme.visibilityRules),
        createTimelineBlock(data),
        ...buildSections(data, ['education', 'skills', 'languages', 'contact'], undefined, theme.visibilityRules),
      ].filter((block): block is ThemeBlock => Boolean(block));
      return { type: 'single', blocks, variant: 'timeline' };
    }
    case 'project-first': {
      const blocks = [
        createHeaderBlock(data, 'default', 'left', false),
        renderSection('summary', data, undefined, theme.visibilityRules),
        createPortfolioBlock(data),
        ...buildSections(data, ['skills', 'education', 'languages', 'contact'], undefined, theme.visibilityRules),
      ].filter((block): block is ThemeBlock => Boolean(block));
      return { type: 'single', blocks, variant: 'portfolio' };
    }
    case 'academic':
      return {
        type: 'single',
        variant: 'academic',
        blocks: [
          createHeaderBlock(data, 'hero', 'left', true),
          ...buildSections(data, theme.sectionOrder, 'accent', theme.visibilityRules),
        ],
      };
    case 'classic-one-column':
    case 'modern-one-column':
    case 'hybrid-balanced':
      return {
        type: 'single',
        variant: 'single',
        blocks: [
          createHeaderBlock(data, 'default', 'left', true),
          ...buildSections(data, theme.sectionOrder, undefined, theme.visibilityRules),
        ],
      };
    case 'executive':
      return {
        type: 'single',
        variant: 'executive',
        blocks: [
          createHeaderBlock(data, 'hero', 'left', true),
          ...buildSections(data, theme.sectionOrder, 'accent', theme.visibilityRules),
        ],
      };
    case 'elegant-serif':
      return {
        type: 'single',
        variant: 'elegant',
        blocks: [
          createHeaderBlock(data, 'hero', 'center', true),
          ...buildSections(data, theme.sectionOrder, undefined, theme.visibilityRules),
        ],
      };
    case 'minimal-clean':
    default:
      return {
        type: 'single',
        variant: 'single',
        blocks: [
          createHeaderBlock(data, 'default', 'left', true),
          ...buildSections(data, theme.sectionOrder, undefined, theme.visibilityRules),
        ],
      };
  }
}
