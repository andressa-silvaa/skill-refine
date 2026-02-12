import type { ResumeTheme, ResumeThemePalette } from '../../model/theme';
import { FALLBACK_PALETTE } from './palettes';
import { classicOneColumnTheme } from './classic-one-column';
import { modernOneColumnTheme } from './modern-one-column';
import { twoColumnSidebarTheme } from './two-column-sidebar';
import { executiveTheme } from './executive';
import { compactDenseTheme } from './compact-dense';
import { timelineExperienceTheme } from './timeline-experience';
import { projectFirstTheme } from './project-first';
import { academicTheme } from './academic';
import { minimalCleanTheme } from './minimal-clean';
import { elegantSerifTheme } from './elegant-serif';
import { techStackTheme } from './tech-stack';
import { hybridBalancedTheme } from './hybrid-balanced';

export const resumeThemes: ResumeTheme[] = [
  classicOneColumnTheme,
  modernOneColumnTheme,
  twoColumnSidebarTheme,
  executiveTheme,
  compactDenseTheme,
  timelineExperienceTheme,
  projectFirstTheme,
  academicTheme,
  minimalCleanTheme,
  elegantSerifTheme,
  techStackTheme,
  hybridBalancedTheme,
];

export const DEFAULT_RESUME_THEME_ID: ResumeTheme['id'] = 'classic-one-column';

export const getResumeThemeById = (id: ResumeTheme['id']): ResumeTheme =>
  resumeThemes.find((theme) => theme.id === id) ?? resumeThemes[0]!;

export const getResumeThemePalette = (theme: ResumeTheme, paletteId?: string): ResumeThemePalette =>
  theme.palettes.find((palette) => palette.id === paletteId) ??
  theme.palettes.find((palette) => palette.id === theme.defaultPaletteId) ??
  theme.palettes[0] ??
  FALLBACK_PALETTE;
