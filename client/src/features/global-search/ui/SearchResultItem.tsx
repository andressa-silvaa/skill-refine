import { useTranslation } from 'react-i18next';
import type { SearchResultItem as SearchResultItemType } from '../api/searchApi';

type Props = {
  item: SearchResultItemType;
  isSelected?: boolean;
  onClick: () => void;
};

const TYPE_ICONS: Record<string, string> = {
  resume: 'fa-solid fa-file-lines',
  analysis: 'fa-solid fa-chart-line',
  version: 'fa-solid fa-clock-rotate-left',
};

export function SearchResultItem({ item, isSelected, onClick }: Props) {
  const { t } = useTranslation();
  const typeLabel = t(`search.${item.type}`);
  const iconClass = TYPE_ICONS[item.type] ?? 'fa-solid fa-circle';

  return (
    <button
      type="button"
      className={`sr-search-result-item${isSelected ? ' is-selected' : ''}`}
      onClick={onClick}
    >
      <i className={iconClass} aria-hidden />
      <div className="sr-search-result-item__content">
        <span className="sr-search-result-item__title">{item.title}</span>
        {(item.subtitle || typeLabel) && (
          <span className="sr-search-result-item__subtitle">
            {item.subtitle ? `${typeLabel} · ${item.subtitle}` : typeLabel}
          </span>
        )}
      </div>
    </button>
  );
}
