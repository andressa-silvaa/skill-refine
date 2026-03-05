import type { TFunction } from 'i18next';

import type {
  AiInsight,
  Competency,
  DashboardData,
  RecentResume,
  ScorePoint,
} from './viewTypes';

import type { DashboardSummaryResponse } from './types';

function formatRelativeDate(dateIso: string | null, locale: string, t: TFunction): string {
  if (!dateIso) return t('dashboard.stats.never');
  const date = new Date(dateIso);
  if (Number.isNaN(date.getTime())) return t('dashboard.stats.never');

  const diffMs = date.getTime() - Date.now();
  const absMs = Math.abs(diffMs);
  const minuteMs = 60 * 1000;
  const hourMs = 60 * minuteMs;
  const dayMs = 24 * hourMs;
  const weekMs = 7 * dayMs;
  const monthMs = 30 * dayMs;
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

  if (absMs < hourMs) return rtf.format(Math.round(diffMs / minuteMs), 'minute');
  if (absMs < dayMs) return rtf.format(Math.round(diffMs / hourMs), 'hour');
  if (absMs < weekMs) return rtf.format(Math.round(diffMs / dayMs), 'day');
  if (absMs < monthMs) return rtf.format(Math.round(diffMs / weekMs), 'week');
  return rtf.format(Math.round(diffMs / monthMs), 'month');
}

function monthLabel(period: string, locale: string): string {
  const date = new Date(`${period}-01T00:00:00`);
  if (Number.isNaN(date.getTime())) return period;
  return new Intl.DateTimeFormat(locale, { month: 'short' }).format(date);
}

function iconForInsightKey(key: string): string {
  if (key.includes('ats_keywords')) return 'fa-solid fa-key';
  if (key.includes('metrics')) return 'fa-solid fa-chart-line';
  if (key.includes('summary')) return 'fa-solid fa-align-left';
  if (key.includes('action_verbs')) return 'fa-solid fa-bolt';
  if (key.includes('links')) return 'fa-solid fa-link';
  return 'fa-solid fa-lightbulb';
}

function mapScoreEvolution(
  scoreEvolution: DashboardSummaryResponse['scoreEvolution'],
  locale: string
): ScorePoint[] {
  return scoreEvolution.map((item) => ({
    month: monthLabel(item.period, locale),
    score: item.score,
  }));
}

function mapCompetencies(
  competencies: DashboardSummaryResponse['competencies'],
  t: TFunction
): Competency[] {
  return competencies.map((item) => ({
    key: item.key,
    label: t(`dashboard.competencies.${item.key}`),
    value: item.value,
  }));
}

function mapRecentResumes(
  items: DashboardSummaryResponse['recentResumes'],
  locale: string,
  t: TFunction
): RecentResume[] {
  return items.map((item) => ({
    id: item.id,
    title: item.name,
    updatedAt: item.updatedAt,
    updatedAtRelative: formatRelativeDate(item.updatedAt, locale, t),
    status: item.status,
    score: item.score,
  }));
}

function mapAiInsights(items: DashboardSummaryResponse['aiInsights'], t: TFunction): AiInsight[] {
  const localizeInsightParams = (params?: Record<string, string>) => {
    if (!params) return {};
    const normalized: Record<string, string> = { ...params };
    const section = params.section?.trim();
    if (section) {
      normalized.section = t(`analysis.sections.${section}`, {
        defaultValue: section,
      });
    }
    return normalized;
  };

  return items.map((item) => {
    const suffix = item.key.split('.').pop() || 'generic';
    return {
      id: item.id,
      key: item.key,
      priority: item.priority === 'high' || item.priority === 'low' ? item.priority : 'medium',
      icon: iconForInsightKey(item.key),
      title: t(`dashboard.insightTitles.${suffix}`, {
        defaultValue: t('dashboard.insightTitles.generic'),
      }),
      description: t(item.key, localizeInsightParams(item.params)),
      count: item.count,
      resumeId: item.resumeId,
      resumeTitle: item.resumeTitle,
    };
  });
}

export function mapDashboardResponseToViewModel(
  response: DashboardSummaryResponse,
  options: { locale: string; userName: string; t: TFunction }
): DashboardData {
  const { locale, userName, t } = options;

  return {
    summary: {
      userName,
      totalResumes: response.summary.totalResumes,
      completeResumes: response.summary.completeResumes,
      draftResumes: response.summary.draftResumes,
      lastAnalysisLabel: formatRelativeDate(response.summary.lastAnalysisAt, locale, t),
      lastAnalyzedResumeTitle: response.summary.lastAnalyzedResumeTitle || t('dashboard.stats.noAnalyzedResume'),
      averageScore: response.summary.averageScore,
      averageScoreDelta: response.summary.averageScoreDelta,
      pendingSuggestions: response.summary.pendingSuggestions,
      highPrioritySuggestions: response.summary.highPrioritySuggestions,
    },
    scoreEvolution: mapScoreEvolution(response.scoreEvolution, locale),
    competencies: mapCompetencies(response.competencies, t),
    recentResumes: mapRecentResumes(response.recentResumes, locale, t),
    aiInsights: mapAiInsights(response.aiInsights, t),
  };
}

