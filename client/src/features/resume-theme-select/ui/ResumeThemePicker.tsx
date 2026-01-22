import type { ResumeTheme, ResumeThemeId } from '@/entities/resume';
import { resumeThemes } from '@/entities/resume';

import { ThemeCard } from './ThemeCard';
import { ThemeGrid } from './ThemeGrid';

type Props = {
  selectedId: ResumeThemeId;
  onSelect: (id: ResumeThemeId) => void;
  themes?: ResumeTheme[];
  variant?: 'grid' | 'carousel';
  cardSize?: 'default' | 'compact';
};

export function ResumeThemePicker({ selectedId, onSelect, themes = resumeThemes, variant = 'grid', cardSize = 'default' }: Props) {
  return (
    <ThemeGrid variant={variant}>
      {themes.map((theme) => (
        <ThemeCard key={theme.id} theme={theme} isSelected={selectedId === theme.id} onSelect={() => onSelect(theme.id)} size={cardSize} />
      ))}
    </ThemeGrid>
  );
}
