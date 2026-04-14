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

  const seniorityBadgeParts = [t('analysis.estimate')];
  if (result.seniorityConfidence === 'low') {
    seniorityBadgeParts.push(t('analysis.seniorityConfidenceLow'));
  }
  const seniorityBadge = seniorityBadgeParts.join(' · ');

  return (
    <div className="sr-ai-metrics-grid" role="group" aria-label={t('analysis.metricsAria')}>
      <ScoreCard
        score={result.score}
        scoreLabel={result.scoreLabel}
        howWeCalculateLabel={t('analysis.howWeCalculate')}
        qualityHint={result.scoreQualityHint}
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
        label={t('analysis.seniorityGeneral')}
        value={
          <>
            {result.seniorityLabel}
            {result.seniorityConfidence === 'low' || result.insufficientDataHint ? (
              <div className="sr-ai-metrics-grid__seniority-notes">
                {result.seniorityConfidence === 'low' ? (
                  <p className="sr-ai-metrics-grid__seniority-hint sr-ai-metrics-grid__seniority-hint--primary">
                    {t('analysis.seniorityConservativeDetail')}
                  </p>
                ) : null}
                {result.insufficientDataHint ? (
                  <p className="sr-ai-metrics-grid__seniority-hint sr-ai-metrics-grid__seniority-hint--tip">
                    {result.insufficientDataHint}
                  </p>
                ) : null}
              </div>
            ) : null}
          </>
        }
        valueVariant="text"
        badge={seniorityBadge}
        badgeTone={result.seniorityConfidence === 'low' ? 'warning' : 'neutral'}
      />
    </div>
  );
}
