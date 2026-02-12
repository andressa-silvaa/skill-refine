import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button, Textarea } from '@/shared/ui';
import { resumeApi } from '@/features/resume';
import { notify } from '@/shared/lib/notify';
import { getApiErrorMessage } from '@/shared/api';

import './SummaryStep.css';

type Props = {
  summary: string;
  onChange: (summary: string) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function SummaryStep(props: Props) {
  const { summary, onChange, getError, shouldShowError, onFieldTouched } = props;
  const { t } = useTranslation();
  const summaryError = shouldShowError('summary') ? getError('summary') : undefined;
  const [isImproving, setIsImproving] = useState(false);

  return (
    <div className="sr-summary-step">
      <div className="sr-summary-step__header">
        <h3 className="sr-summary-step__title">{t('resume.summaryStepTitle')}</h3>
        <p className="sr-summary-step__subtitle">{t('resume.summaryStepSubtitle')}</p>
      </div>

      <Textarea
        label={t('resume.summaryStepLabel')}
        placeholder={t('resume.summaryStepPlaceholder')}
        value={summary}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => onFieldTouched('summary')}
        showCount
        maxLength={500}
        hint={t('resume.summaryStepHint')}
        error={summaryError}
      />

      <div className="sr-summary-step__actions">
        <Button
          variant="primary"
          className="sr-summary-step__ai-button"
          disabled={isImproving}
          onClick={async () => {
            if (!summary.trim()) {
              notify.error(t('resume.summaryStepImproveError'));
              return;
            }
            setIsImproving(true);
            try {
              const result = await resumeApi.rewriteSummaryWithAI(summary);
              onChange(result.suggestedText);
            } catch (err) {
              notify.error(getApiErrorMessage(err, t('resume.summaryStepApiError')));
            } finally {
              setIsImproving(false);
            }
          }}
        >
          {isImproving ? <i className="fa-solid fa-circle-notch fa-spin" aria-hidden /> : <i className="fa-solid fa-wand-magic-sparkles" aria-hidden />}
          {isImproving ? t('resume.summaryStepImproving') : t('resume.summaryStepImprove')}
        </Button>
      </div>
    </div>
  );
}
