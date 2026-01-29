import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { IconButton } from '@/shared/ui';

import { SortSelect } from './SortSelect';
import './ResumesToolbar.css';

type ViewMode = 'grid' | 'list';

type SortKey = 'recent' | 'score' | 'name';

type Props = {
  query: string;
  onQueryChange: (v: string) => void;
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  sort: SortKey;
  onSortChange: (v: SortKey) => void;
  onOpenFilters: () => void;
};

export function ResumesToolbar(props: Props) {
  const { query, onQueryChange, view, onViewChange, sort, onSortChange, onOpenFilters } = props;
  const { t } = useTranslation();

  const sortOptions = useMemo(
    () => [
      { value: 'recent', label: t('resume.sortRecent') },
      { value: 'score', label: t('resume.sortScore') },
      { value: 'name', label: t('resume.sortName') },
    ],
    [t]
  );

  return (
    <div className="sr-resumes-toolbar" role="search">
      <div className="sr-resumes-toolbar__search">
        <i className="fa-solid fa-magnifying-glass" aria-hidden />
        <input
          className="sr-resumes-toolbar__input"
          value={query}
          placeholder={t('resume.searchPlaceholder')}
          onChange={(e) => onQueryChange(e.target.value)}
        />
      </div>

      <div className="sr-resumes-toolbar__right">
        <div className="sr-resumes-toolbar__filters-wrapper">
          <button type="button" className="sr-btn sr-btn--secondary" onClick={onOpenFilters} title={t('resume.filtersHint')}>
            <i className="fa-solid fa-filter" aria-hidden />
            {t('resume.filters')}
          </button>
          <span className="sr-resumes-toolbar__filters-hint">{t('resume.filtersHint')}</span>
        </div>

        <SortSelect value={sort} options={sortOptions} onChange={(v) => onSortChange(v as SortKey)} />

        <div className="sr-resumes-toolbar__toggle" aria-label={t('resume.viewGrid')}>
          <IconButton aria-label={t('resume.viewGrid')} isActive={view === 'grid'} onClick={() => onViewChange('grid')}>
            <i className="fa-solid fa-grip" aria-hidden />
          </IconButton>
          <IconButton aria-label={t('resume.viewList')} isActive={view === 'list'} onClick={() => onViewChange('list')}>
            <i className="fa-solid fa-list" aria-hidden />
          </IconButton>
        </div>
      </div>
    </div>
  );
}
