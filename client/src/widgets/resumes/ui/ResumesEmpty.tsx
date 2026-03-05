import { useTranslation } from 'react-i18next';

import { Button, Card } from '@/shared/ui';

import './ResumesEmpty.css';

type Props = {
  onCreate: () => void;
  hasActiveFilters?: boolean;
  onClearFilters?: () => void;
};

export function ResumesEmpty(props: Props) {
  const { onCreate, hasActiveFilters = false, onClearFilters } = props;
  const { t } = useTranslation();

  const title = hasActiveFilters ? t('resume.emptyFilteredTitle') : t('resume.emptyTitle');
  const subtitle = hasActiveFilters ? t('resume.emptyFilteredSubtitle') : t('resume.emptySubtitle');

  return (
    <Card className="sr-resumes-empty">
      <div className="sr-resumes-empty__icon" aria-hidden>
        <i className="fa-regular fa-file-lines" />
      </div>
      <h3 className="sr-resumes-empty__title">{title}</h3>
      <p className="sr-resumes-empty__text">{subtitle}</p>
      {hasActiveFilters ? (
        <Button variant="secondary" onClick={onClearFilters}>
          {t('resume.filtersClear')}
        </Button>
      ) : (
        <Button variant="primary" onClick={onCreate}>
          <i className="fa-solid fa-plus" aria-hidden />
          {t('resume.emptyCta')}
        </Button>
      )}
    </Card>
  );
}
