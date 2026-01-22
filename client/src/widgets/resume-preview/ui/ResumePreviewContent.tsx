import type { CSSProperties } from 'react';

import type { ResumeData, ResumeThemeStyleTokens } from '@/entities/resume';
import { getResumeThemeById, getResumeThemePalette } from '@/entities/resume';
import { getThemeLayoutData } from '@/features/resume-preview/ui/ThemeRenderer';
import { ResumePages } from '@/features/resume-preview/ui/ResumePages';

import './ResumePreviewContent.css';

type Props = {
  data: ResumeData;
};

export function ResumePreviewContent(props: Props) {
  const { data } = props;
  const theme = getResumeThemeById(data.themeId);
  const palette = getResumeThemePalette(theme, data.themePaletteId);
  const accent = data.themeAccentOverride ?? palette.accent;
  const accentSoft = data.themeAccentOverride ? toRgba(accent, 0.12) : palette.accentSoft;
  const secondary = data.themeSecondaryOverride ?? '';
  const styleTokens = toThemeStyleVars({
    ...theme.styleTokens,
    accent,
    accentSoft,
    ...(secondary ? { secondary } : {}),
  });
  const layout = getThemeLayoutData(theme, data);

  return (
    <div className="sr-resume-preview">
      <div className={`sr-resume-preview__paper sr-resume-theme sr-resume-theme--${theme.id}`} style={styleTokens}>
        <ResumePages layout={layout} sectionGap={theme.styleTokens.sectionGap} />
      </div>
    </div>
  );
}

function toThemeStyleVars(tokens: ResumeThemeStyleTokens & { secondary?: string }): CSSProperties {
  return {
    ...(tokens.fontFamily ? { '--resume-font': tokens.fontFamily } : {}),
    ...(tokens.headingFontFamily ? { '--resume-heading-font': tokens.headingFontFamily } : {}),
    ...(tokens.accent ? { '--resume-accent': tokens.accent } : {}),
    ...(tokens.accentSoft ? { '--resume-accent-soft': tokens.accentSoft } : {}),
    ...(tokens.secondary ? { '--resume-accent-secondary': tokens.secondary } : {}),
    ...(tokens.paperBg ? { '--resume-paper-bg': tokens.paperBg } : {}),
    ...(tokens.sidebarBg ? { '--resume-sidebar-bg': tokens.sidebarBg } : {}),
    ...(tokens.borderColor ? { '--resume-border-color': tokens.borderColor } : {}),
    ...(tokens.titleWeight ? { '--resume-title-weight': tokens.titleWeight } : {}),
    ...(tokens.spacingLg ? { '--resume-spacing-lg': tokens.spacingLg } : {}),
    ...(tokens.spacingMd ? { '--resume-spacing-md': tokens.spacingMd } : {}),
    ...(tokens.spacingSm ? { '--resume-spacing-sm': tokens.spacingSm } : {}),
    ...(tokens.sectionGap ? { '--resume-section-gap': tokens.sectionGap } : {}),
    ...(tokens.radius ? { '--resume-radius': tokens.radius } : {}),
  } as React.CSSProperties;
}

function toRgba(hex: string, alpha: number): string {
  const normalized = hex.replace('#', '');
  if (normalized.length !== 6) return `rgba(0,0,0,${alpha})`;
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
