import { useTranslation } from 'react-i18next';

import { Button } from '@/shared/ui';

import type { ResumeFilterOption } from '../model/types';

import './VersionHistoryFilters.css';

type Props = {
  options: ResumeFilterOption[];
  activeId: string;
  allFilterId: string;
  onSelect: (id: string) => void;
};

export function VersionHistoryFilters({ options, activeId, allFilterId, onSelect }: Props) {
  const { t } = useTranslation();

  return (
    <div className="sr-version-filters" role="tablist" aria-label={t('versionHistory.filtersLabel')}>
      <Button
        type="button"
        role="tab"
        aria-selected={activeId === allFilterId}
        className={`sr-version-filters__chip${activeId === allFilterId ? ' is-active' : ''}`}
        onClick={() => onSelect(allFilterId)}
      >
        {t('versionHistory.filters.all')}
      </Button>
      {options.map((opt) => (
        <Button
          key={opt.id}
          type="button"
          role="tab"
          aria-selected={activeId === opt.id}
          className={`sr-version-filters__chip${activeId === opt.id ? ' is-active' : ''}`}
          onClick={() => onSelect(opt.id)}
        >
          {opt.title}
        </Button>
      ))}
    </div>
  );
}
