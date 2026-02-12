import { useTranslation } from 'react-i18next';

import { Card } from '@/shared/ui';

import type { AnalysisResult, ImprovementInsightItem, InsightItem } from '../model/types';
import { InsightListItem } from './InsightListItem';

import './AnalysisLists.css';

type Props = {
  result: AnalysisResult;
};

export function AnalysisLists(props: Props) {
  const { result } = props;
  const { t } = useTranslation();

  return (
    <div className="sr-analysis-lists" role="region" aria-label={t('analysis.listsAria')}>
      <Card className="sr-analysis-lists__col sr-analysis-lists__col--strengths">
        <h3 className="sr-analysis-lists__title">
          <i className="fa-solid fa-circle-check sr-analysis-lists__icon sr-analysis-lists__icon--success" aria-hidden />
          {t('analysis.strengths')}
        </h3>
        <ul className="sr-analysis-lists__list">
          {result.strengths.map((insight: InsightItem, idx: number) => (
            <li key={idx} className="sr-analysis-lists__item">
              <InsightListItem variant="positive" insight={insight} />
            </li>
          ))}
        </ul>
      </Card>

      <Card className="sr-analysis-lists__col sr-analysis-lists__col--improvements">
        <h3 className="sr-analysis-lists__title">
          <i className="fa-solid fa-triangle-exclamation sr-analysis-lists__icon sr-analysis-lists__icon--warning" aria-hidden />
          {t('analysis.improvements')}
        </h3>
        <ul className="sr-analysis-lists__list">
          {result.improvements.map((item: ImprovementInsightItem, idx: number) => (
            <li key={idx} className="sr-analysis-lists__item">
              <InsightListItem variant="improvement" insight={item} />
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
