import { useTranslation } from 'react-i18next';

import type { DashboardSummary } from '../model/types';
import { DashboardStatCard } from './DashboardStatCard';

import './DashboardStatsGrid.css';

type Props = {
  summary: DashboardSummary;
};

export function DashboardStatsGrid({ summary }: Props) {
  const { t } = useTranslation();

  return (
    <div className="sr-dash-stats-grid">
      <DashboardStatCard
        icon="fa-regular fa-file-lines"
        label={t('dashboard.stats.totalResumes')}
        value={summary.totalResumes}
        sub={t('dashboard.stats.totalResumesSub', {
          complete: summary.completeResumes,
          draft: summary.draftResumes,
        })}
      />
      <DashboardStatCard
        icon="fa-solid fa-wand-magic-sparkles"
        iconColor="var(--sr-accent)"
        label={t('dashboard.stats.lastAnalysis')}
        value={summary.lastAnalysisLabel}
        sub={summary.lastAnalyzedResumeTitle}
      />
      <DashboardStatCard
        icon="fa-solid fa-star"
        iconColor="#f59e0b"
        label={t('dashboard.stats.averageScore')}
        value={summary.averageScore ?? '-'}
        badge={typeof summary.averageScoreDelta === 'number' ? `${summary.averageScoreDelta > 0 ? '+' : ''}${summary.averageScoreDelta}%` : undefined}
        badgeTone="success"
      />
      <DashboardStatCard
        icon="fa-solid fa-circle-exclamation"
        iconColor="#f08040"
        label={t('dashboard.stats.pendingSuggestions')}
        value={summary.pendingSuggestions}
        sub={t('dashboard.stats.pendingSuggestionsSub', {
          count: summary.highPrioritySuggestions,
        })}
        badgeTone="warning"
      />
    </div>
  );
}
