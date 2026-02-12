import { useTranslation } from 'react-i18next';

import { Input } from '@/shared/ui';
import type { ResumeData } from '@/entities/resume';

import './BasicInfoStep.css';

type Props = {
  data: Pick<ResumeData, 'targetPosition'>;
  onChange: (updates: Partial<ResumeData>) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function BasicInfoStep(props: Props) {
  const { data, onChange, getError, shouldShowError, onFieldTouched } = props;
  const { t } = useTranslation();
  const targetError = shouldShowError('targetPosition') ? getError('targetPosition') : undefined;

  return (
    <div className="sr-basic-info-step">
      <div className="sr-basic-info-step__header">
        <h3 className="sr-basic-info-step__title">{t('resume.basicStepTitle')}</h3>
        <p className="sr-basic-info-step__subtitle">{t('resume.basicStepSubtitle')}</p>
      </div>

      <div className="sr-basic-info-step__fields">
        <Input
          label={t('resume.basicStepTargetLabel')}
          placeholder={t('resume.basicStepTargetPlaceholder')}
          value={data.targetPosition}
          onChange={(e) => onChange({ targetPosition: e.target.value })}
          onBlur={() => onFieldTouched('targetPosition')}
          hint={t('resume.basicStepTargetHint')}
          error={targetError}
        />
      </div>
    </div>
  );
}
