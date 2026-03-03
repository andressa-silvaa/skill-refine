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

function localizeInsightParams(
  params: Record<string, string> | undefined,
  t: (key: string, params?: Record<string, string>) => string
): Record<string, string> {
  const normalized = { ...(params ?? {}) };
  const rawSection = normalized.section?.trim();
  if (rawSection) {
    const key = `analysis.sections.${rawSection.toLowerCase()}`;
    const translated = t(key);
    normalized.section = translated === key ? rawSection : translated;
  }
  return normalized;
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
    params: localizeInsightParams(s.params, t),
  }));

  const recommendationsByKey = new Map(
    (payload.recommendations ?? []).map((rec) => [rec.key, rec])
  );

  const improvements: ImprovementInsightItem[] = (payload.insights?.improvements ?? []).map((i) => {
    const recommendation = recommendationsByKey.get(i.key);
    const params = localizeInsightParams(i.params ?? recommendation?.params, t);
    return {
      key: i.key,
      params,
      priority: i.priority ?? recommendation?.priority,
      section: params.section ?? recommendation?.section,
      fieldTarget: params.field_target ?? recommendation?.field_target,
      actionType: params.action_type ?? recommendation?.action_type,
      exampleKey: recommendation?.example_key,
      exampleText: recommendation?.example_params?.text,
    };
  });

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
