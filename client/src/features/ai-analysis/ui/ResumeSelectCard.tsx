import { useTranslation } from 'react-i18next';

import { Button, Card, CustomSelect } from '@/shared/ui';

import type { ResumeOption } from '../model/types';

import './ResumeSelectCard.css';

type Props = {
  options: ResumeOption[];
  value: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  loading?: boolean;
  selectPlaceholder: string;
  analyzeButtonLabel: string;
};

export function ResumeSelectCard(props: Props) {
  const {
    options,
    value,
    onChange,
    onAnalyze,
    loading = false,
    selectPlaceholder,
    analyzeButtonLabel,
  } = props;
  const { t } = useTranslation();

  const optionsWithPlaceholder: ResumeOption[] = [
    { value: '', label: selectPlaceholder },
    ...options.filter((o) => o.value !== ''),
  ];

  return (
    <Card className="sr-ai-select-card">
      <h2 className="sr-ai-select-card__title">{t('analysis.selectCardTitle')}</h2>
      <div className="sr-ai-select-card__row">
        <div className="sr-ai-select-card__select-wrap">
          <CustomSelect
            value={value}
            options={optionsWithPlaceholder}
            onChange={onChange}
            disabled={loading}
            className="sr-ai-select-card__select"
          />
        </div>
        <Button
          type="button"
          variant="primary"
          onClick={onAnalyze}
          disabled={!value || loading}
          className="sr-ai-select-card__btn"
          aria-busy={loading}
        >
          {loading ? (
            <>
              <i className="fa-solid fa-spinner fa-spin" aria-hidden />
              {t('analysis.analyzing')}
            </>
          ) : (
            <>
              <i className="fa-solid fa-wand-magic-sparkles" aria-hidden />
              {analyzeButtonLabel}
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}
