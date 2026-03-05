import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { CustomSelect, IconButton } from '@/shared/ui';
import type {
  ResumeScoreFilter,
  ResumeStatusFilter,
  ResumeUpdatedFilter,
} from '@/features/resume/model/types';

import { SortSelect } from './SortSelect';
import './ResumesToolbar.css';

type ViewMode = 'grid' | 'list';

type SortKey = 'recent' | 'oldest' | 'score' | 'name';

type Props = {
  query: string;
  onQueryChange: (v: string) => void;
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  sort: SortKey;
  onSortChange: (v: SortKey) => void;
  filtersOpen: boolean;
  onToggleFilters: () => void;
  statusFilter: ResumeStatusFilter;
  scoreFilter: ResumeScoreFilter;
  updatedFilter: ResumeUpdatedFilter;
  onStatusFilterChange: (value: ResumeStatusFilter) => void;
  onScoreFilterChange: (value: ResumeScoreFilter) => void;
  onUpdatedFilterChange: (value: ResumeUpdatedFilter) => void;
  onClearFilters: () => void;
  activeFiltersCount: number;
};

export function ResumesToolbar(props: Props) {
  const {
    query,
    onQueryChange,
    view,
    onViewChange,
    sort,
    onSortChange,
    filtersOpen,
    onToggleFilters,
    statusFilter,
    scoreFilter,
    updatedFilter,
    onStatusFilterChange,
    onScoreFilterChange,
    onUpdatedFilterChange,
    onClearFilters,
    activeFiltersCount,
  } = props;
  const { t } = useTranslation();

  const sortOptions = useMemo(
    () => [
      { value: 'recent', label: t('resume.sortRecent') },
      { value: 'oldest', label: t('resume.sortOldest') },
      { value: 'score', label: t('resume.sortScore') },
      { value: 'name', label: t('resume.sortName') },
    ],
    [t]
  );

  const statusOptions = useMemo(
    () => [
      { value: 'all', label: t('resume.filtersStatusAll') },
      { value: 'draft', label: t('resume.statusDraft') },
      { value: 'complete', label: t('resume.statusComplete') },
      { value: 'analyzing', label: t('resume.statusAnalyzing') },
    ],
    [t]
  );

  const scoreOptions = useMemo(
    () => [
      { value: 'all', label: t('resume.filtersScoreAll') },
      { value: 'none', label: t('resume.filtersScoreNone') },
      { value: '0-50', label: t('resume.filtersScore0to50') },
      { value: '51-70', label: t('resume.filtersScore51to70') },
      { value: '71-85', label: t('resume.filtersScore71to85') },
      { value: '86-100', label: t('resume.filtersScore86to100') },
    ],
    [t]
  );

  const updatedOptions = useMemo(
    () => [
      { value: 'all', label: t('resume.filtersUpdatedAll') },
      { value: '7d', label: t('resume.filtersUpdated7d') },
      { value: '30d', label: t('resume.filtersUpdated30d') },
    ],
    [t]
  );

  return (
    <div className="sr-resumes-toolbar-wrap">
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
            <button
              type="button"
              className="sr-btn sr-btn--secondary"
              onClick={onToggleFilters}
              title={t('resume.filtersHint')}
            >
              <i className="fa-solid fa-filter" aria-hidden />
              {t('resume.filters')}
              {activeFiltersCount > 0 ? (
                <span className="sr-resumes-toolbar__filters-count">{activeFiltersCount}</span>
              ) : null}
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

      {filtersOpen ? (
        <div className="sr-resumes-filters-panel" aria-label={t('resume.filters')}>
          <CustomSelect
            value={statusFilter}
            options={statusOptions}
            label={t('resume.filtersStatus')}
            onChange={(value) => onStatusFilterChange(value as ResumeStatusFilter)}
          />
          <CustomSelect
            value={scoreFilter}
            options={scoreOptions}
            label={t('resume.filtersScore')}
            onChange={(value) => onScoreFilterChange(value as ResumeScoreFilter)}
          />
          <CustomSelect
            value={updatedFilter}
            options={updatedOptions}
            label={t('resume.filtersUpdated')}
            onChange={(value) => onUpdatedFilterChange(value as ResumeUpdatedFilter)}
          />
          <button type="button" className="sr-btn sr-btn--secondary" onClick={onClearFilters}>
            {t('resume.filtersClear')}
          </button>
        </div>
      ) : null}
    </div>
  );
}
