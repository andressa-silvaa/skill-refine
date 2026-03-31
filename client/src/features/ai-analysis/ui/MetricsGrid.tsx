import { useTranslation } from 'react-i18next';

import type { AnalysisResult } from '../model/types';
import type { MetricBadgeTone } from '../model/types';
import { MetricCard } from './MetricCard';
import { ScoreCard } from './ScoreCard';

import './MetricsGrid.css';

function badgeToneToBadge(tone: MetricBadgeTone): 'success' | 'neutral' | 'warning' {
  if (tone === 'excellent') return 'success';
  if (tone === 'attention') return 'warning';
  return 'neutral';
}

type Props = {
  result: AnalysisResult;
};

export function MetricsGrid(props: Props) {
  const { result } = props;
  const { t } = useTranslation();

  const atsBadgeLabel = result.atsBadge === 'excellent' ? t('analysis.badgeExcellent') : result.atsBadge === 'good' ? t('analysis.badgeGood') : t('analysis.badgeAttention');
  const clarityBadgeLabel = result.clarityBadge === 'excellent' ? t('analysis.badgeExcellent') : result.clarityBadge === 'good' ? t('analysis.badgeGood') : t('analysis.badgeAttention');

  return (
    <div className="sr-ai-metrics-grid" role="group" aria-label={t('analysis.metricsAria')}>
      <ScoreCard
        score={result.score}
        scoreLabel={result.scoreLabel}
        howWeCalculateLabel={t('analysis.howWeCalculate')}
      />
      <MetricCard
        icon={<i className="fa-solid fa-file-code" aria-hidden />}
        label={t('analysis.ats')}
        value={`${result.ats}%`}
        badge={atsBadgeLabel}
        badgeTone={badgeToneToBadge(result.atsBadge)}
      />
      <MetricCard
        icon={<i className="fa-solid fa-bullseye" aria-hidden />}
        label={t('analysis.clarity')}
        value={`${result.clarity}%`}
        badge={clarityBadgeLabel}
        badgeTone={badgeToneToBadge(result.clarityBadge)}
      />
      <MetricCard
        icon={<i className="fa-solid fa-chart-line" aria-hidden />}
        label={t('analysis.seniority')}
        value={result.seniorityLabel}
        valueVariant="text"
        badge={t('analysis.estimate')}
        badgeTone="neutral"
      />
    </div>
  );
}
