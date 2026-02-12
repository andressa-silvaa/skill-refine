import { useTranslation } from 'react-i18next';

import { Card } from '@/shared/ui';

import './AnalysisEmptyState.css';

export function AnalysisEmptyState() {
  const { t } = useTranslation();

  return (
    <Card className="sr-analysis-empty">
      <div className="sr-analysis-empty__icon" aria-hidden>
        <i className="fa-solid fa-wand-magic-sparkles" />
      </div>
      <h2 className="sr-analysis-empty__title">{t('analysis.emptyTitle')}</h2>
      <p className="sr-analysis-empty__subtitle">{t('analysis.emptySubtitle')}</p>
      <ol className="sr-analysis-empty__steps">
        <li>{t('analysis.emptyStep1')}</li>
        <li>{t('analysis.emptyStep2')}</li>
        <li>{t('analysis.emptyStep3')}</li>
      </ol>
    </Card>
  );
}
