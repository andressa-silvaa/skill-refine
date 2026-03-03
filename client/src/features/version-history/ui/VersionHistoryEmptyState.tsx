import { useTranslation } from 'react-i18next';

import { Card } from '@/shared/ui';

import './VersionHistoryEmptyState.css';

export function VersionHistoryEmptyState() {
  const { t } = useTranslation();

  return (
    <Card className="sr-version-empty">
      <div className="sr-version-empty__icon" aria-hidden>
        <i className="fa-solid fa-clock-rotate-left" />
      </div>
      <h2 className="sr-version-empty__title">{t('versionHistory.emptyTitle')}</h2>
      <p className="sr-version-empty__subtitle">{t('versionHistory.emptySubtitle')}</p>
    </Card>
  );
}
