import { Card } from '@/shared/ui';
import type { ResumeTheme } from '@/entities/resume';
import { ThemeThumbnail } from './ThemeThumbnail';

import './ThemeCard.css';

type Props = {
  theme: ResumeTheme;
  isSelected: boolean;
  onSelect: () => void;
  size?: 'default' | 'compact';
};

export function ThemeCard({ theme, isSelected, onSelect, size = 'default' }: Props) {
  return (
    <Card
      className={`sr-theme-card sr-theme-card--${size}${isSelected ? ' is-selected' : ''}`}
      role="listitem"
      onClick={onSelect}
    >
      <div className="sr-theme-card__preview" aria-hidden>
        <ThemeThumbnail spec={theme.thumbnailSpec} />
      </div>
      <div className="sr-theme-card__body">
        <div className="sr-theme-card__header">
          <h4 className="sr-theme-card__title">{theme.name}</h4>
          <span className="sr-theme-card__tag">{theme.tag}</span>
        </div>
        <p className="sr-theme-card__description">{theme.description}</p>
        <div className="sr-theme-card__tags">
          {theme.tags.map((tag) => (
            <span key={tag} className="sr-theme-card__pill">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}
