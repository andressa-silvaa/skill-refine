import type { AnalysisPayload } from '../api/analysisApi';
import type {
  AnalysisResult,
  ImprovementInsightItem,
  InsightItem,
  MetricBadgeTone,
} from './types';

function scoreToBadge(score: number | null | undefined): MetricBadgeTone {
  if (score == null) return 'attention';
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  return 'attention';
}

function scoreToLabel(score: number | null | undefined): string {
  if (score == null) return '-';
  if (score >= 90) return 'Excelente';
  if (score >= 75) return 'Muito bom';
  if (score >= 60) return 'Bom';
  if (score >= 40) return 'Regular';
  return 'Atenção';
}

function seniorityScoreToKey(score: number | null | undefined): string {
  if (score == null) return 'analysis.seniorityJunior';
  if (score <= 25) return 'analysis.seniorityIntern';
  if (score <= 50) return 'analysis.seniorityJunior';
  if (score <= 75) return 'analysis.seniorityMid';
  return 'analysis.senioritySenior';
}

export function apiPayloadToResult(
  payload: AnalysisPayload,
  t: (key: string, params?: Record<string, string>) => string
): AnalysisResult {
  const score = payload.score ?? 0;
  const ats = payload.taskScores?.ats ?? 0;
  const clarity = payload.taskScores?.clarity ?? 0;
  const seniorityScore = payload.taskScores?.seniority ?? 50;
  const seniorityKey = seniorityScoreToKey(seniorityScore);

  const strengths: InsightItem[] = (payload.insights?.strengths ?? []).map((s) => ({
    key: s.key,
    params: s.params ?? {},
  }));

  const improvements: ImprovementInsightItem[] = (payload.insights?.improvements ?? []).map((i) => ({
    key: i.key,
    params: i.params ?? {},
    priority: i.priority,
  }));

  return {
    score,
    scoreLabel: scoreToLabel(score),
    ats: typeof ats === 'number' ? ats : 0,
    atsBadge: scoreToBadge(ats),
    clarity: typeof clarity === 'number' ? clarity : 0,
    clarityBadge: scoreToBadge(clarity),
    seniorityLabel: t(seniorityKey),
    strengths,
    improvements,
  };
}
