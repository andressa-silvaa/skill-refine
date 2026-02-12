import { useTranslation } from 'react-i18next';

import { Card } from '@/shared/ui';
import { notify } from '@/shared/lib/notify';

import type { AnalysisResult, ImprovementInsightItem, InsightItem } from '../model/types';
import { InsightListItem } from './InsightListItem';

import './InsightList.css';

type Props = {
  result: AnalysisResult;
};

export function InsightList(props: Props) {
  const { result } = props;
  const { t } = useTranslation();

  const handleSeeExample = () => {
    notify.info(t('analysis.exampleComingSoon'));
  };

  const handleApply = () => {
    notify.info(t('analysis.applyComingSoon'));
  };

  return (
    <div className="sr-insight-list" role="region" aria-label={t('analysis.listsAria')}>
      <section className="sr-insight-list__col" aria-label={t('analysis.strengths')}>
        <Card className="sr-insight-list__card">
          <h3 className="sr-insight-list__title">
            <i className="fa-solid fa-circle-check sr-insight-list__title-icon sr-insight-list__title-icon--success" aria-hidden />
            {t('analysis.strengths')}
          </h3>
          <ul className="sr-insight-list__items">
            {result.strengths.map((insight, idx) => (
              <li key={idx}>
                <InsightListItem variant="positive" insight={insight} />
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section className="sr-insight-list__col" aria-label={t('analysis.improvements')}>
        <Card className="sr-insight-list__card">
          <h3 className="sr-insight-list__title">
            <i className="fa-solid fa-triangle-exclamation sr-insight-list__title-icon sr-insight-list__title-icon--warning" aria-hidden />
            {t('analysis.improvements')}
          </h3>
          <ul className="sr-insight-list__items">
            {result.improvements.map((item: ImprovementInsightItem, idx: number) => (
              <li key={idx}>
                <InsightListItem
                  variant="improvement"
                  insight={item}
                  onSeeExample={handleSeeExample}
                  onApply={handleApply}
                />
              </li>
            ))}
          </ul>
        </Card>
      </section>
    </div>
  );
}
