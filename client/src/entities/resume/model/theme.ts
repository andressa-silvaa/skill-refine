import type { ResumeThemeId } from './types';

export type ResumeSectionId = 'summary' | 'experience' | 'education' | 'skills' | 'languages' | 'contact';

export type ResumeThemeLayout =
  | {
      type: 'single';
    }
  | {
      type: 'split';
      sidebarPosition: 'left' | 'right';
      sidebarSections: ResumeSectionId[];
      mainSections: ResumeSectionId[];
    }
  | {
      type: 'timeline';
    }
  | {
      type: 'grid';
    }
  | {
      type: 'compact';
      columns: 1 | 2;
    };

export type ResumeThemeStyleTokens = Partial<{
  fontFamily: string;
  headingFontFamily: string;
  accent: string;
  accentSoft: string;
  paperBg: string;
  sidebarBg: string;
  borderColor: string;
  titleWeight: string;
  spacingLg: string;
  spacingMd: string;
  spacingSm: string;
  sectionGap: string;
  radius: string;
}>;

export type ResumeThemePalette = {
  id: string;
  name: string;
  nameKey?: string;
  accent: string;
  accentSoft: string;
};

export type ResumeThemeThumbnailSpec =
  | {
      type: 'one-column';
      blocks: number;
      header: 'simple' | 'hero';
    }
  | {
      type: 'two-column';
      sidebarPosition: 'left' | 'right';
      mainBlocks: number;
      sidebarBlocks: number;
    }
  | {
      type: 'timeline';
      items: number;
    }
  | {
      type: 'project-grid';
      columns: 2 | 3;
      rows: number;
    }
  | {
      type: 'compact';
      columns: 2;
      blocks: number;
    };

export type ResumeTheme = {
  id: ResumeThemeId;
  name: string;
  description: string;
  tag: string;
  tags: string[];
  category?: string;
  thumbnail?: string;
  thumbnailSpec: ResumeThemeThumbnailSpec;
  palettes: ResumeThemePalette[];
  defaultPaletteId: string;
  layout: ResumeThemeLayout;
  sectionOrder: ResumeSectionId[];
  visibilityRules?: Partial<Record<ResumeSectionId, 'hideIfEmpty'>>;
  styleTokens: ResumeThemeStyleTokens;
};
