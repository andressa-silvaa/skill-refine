import { useTranslation } from 'react-i18next';

import { Card, Button } from '@/shared/ui';

import './AnalysisErrorState.css';

type Props = {
  onRetry: () => void;
};

export function AnalysisErrorState(props: Props) {
  const { onRetry } = props;
  const { t } = useTranslation();

  return (
    <Card className="sr-analysis-error">
      <div className="sr-analysis-error__icon" aria-hidden>
        <i className="fa-solid fa-circle-exclamation" />
      </div>
      <h2 className="sr-analysis-error__title">{t('analysis.errorTitle')}</h2>
      <p className="sr-analysis-error__text">{t('analysis.errorSubtitle')}</p>
      <Button variant="primary" onClick={onRetry} className="sr-analysis-error__btn">
        {t('analysis.retryButton')}
      </Button>
    </Card>
  );
}
