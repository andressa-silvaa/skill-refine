import type { AnalysisPayload } from '../api/analysisApi';
import type {
  AnalysisResult,
  ImprovementInsightItem,
  InsightItem,
  MetricBadgeTone,
  TargetFitView,
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

const SENIORITY_CLASS_TO_KEY = {
  intern: 'analysis.seniorityIntern',
  junior: 'analysis.seniorityJunior',
  mid: 'analysis.seniorityMid',
  senior: 'analysis.senioritySenior',
} as const;

type SeniorityClassKey = keyof typeof SENIORITY_CLASS_TO_KEY;

function seniorityLabelToI18nKey(raw: string): string | null {
  const c = raw.trim().toLowerCase();
  if (c === 'intern' || c === 'junior' || c === 'mid' || c === 'senior') {
    return SENIORITY_CLASS_TO_KEY[c as SeniorityClassKey];
  }
  return null;
}

function seniorityScoreToKey(score: number | null | undefined): string {
  if (score == null) return 'analysis.seniorityJunior';
  if (score <= 25) return 'analysis.seniorityIntern';
  if (score <= 50) return 'analysis.seniorityJunior';
  if (score <= 75) return 'analysis.seniorityMid';
  return 'analysis.senioritySenior';
}

function domainCategoryLabel(
  category: string | null | undefined,
  t: (key: string, params?: Record<string, string>) => string
): string {
  const c = (category || 'general').trim().toLowerCase() || 'general';
  const key = `analysis.domainCategory.${c}`;
  const out = t(key);
  return out === key ? c : out;
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
  const rawClass = (payload.seniorityLabel || '').trim().toLowerCase();
  const seniorityKey =
    seniorityLabelToI18nKey(rawClass) ?? seniorityScoreToKey(seniorityScore);

  const strengths: InsightItem[] = (payload.insights?.strengths ?? []).map((s) => {
    if (
      s.key === 'analysis.insights.strengths.career_switch_context' &&
      s.params &&
      typeof s.params.reasonKey === 'string' &&
      s.params.reasonKey.length > 0
    ) {
      return {
        key: s.key,
        params: { context: t(s.params.reasonKey) },
      };
    }
    return {
      key: s.key,
      params: localizeInsightParams(s.params, t),
    };
  });

  const recommendationsByKey = new Map(
    (payload.recommendations ?? []).map((rec) => [rec.key, rec])
  );

  const improvements: ImprovementInsightItem[] = (payload.insights?.improvements ?? []).map((i) => {
    const recommendation = recommendationsByKey.get(i.key);
    const rawParams = i.params ?? recommendation?.params;
    const params = localizeInsightParams(rawParams, t);
    return {
      key: i.key,
      params,
      priority: i.priority ?? recommendation?.priority,
      section: rawParams?.section ?? recommendation?.section,
      fieldTarget: params.field_target ?? recommendation?.field_target,
      actionType: params.action_type ?? recommendation?.action_type,
      exampleKey: recommendation?.example_key,
      exampleText: recommendation?.example_params?.text,
    };
  });

  const scoreMeaningKey = (payload.scoreMeaning || '').trim();
  const scoreQualityHint = scoreMeaningKey ? t(scoreMeaningKey) : undefined;
  const sc = payload.seniorityConfidence;
  const seniorityConfidence =
    sc === 'low' || sc === 'medium' || sc === 'high' ? sc : undefined;
  const insufficientDataHint =
    payload.insufficientData === true ? t('analysis.insufficientDataHint') : undefined;

  let targetFit: TargetFitView | undefined;
  if (payload.targetFitScore != null && typeof payload.targetFitScore === 'number') {
    const ev = payload.targetFitEvidence ?? {};
    const cs = payload.careerSwitch ?? {};
    const rawTsl = (payload.targetSeniorityLabel || '').trim().toLowerCase();
    const tslKey =
      seniorityLabelToI18nKey(rawTsl) ??
      seniorityScoreToKey(
        typeof payload.taskScores?.targetSeniority === 'number'
          ? payload.taskScores.targetSeniority
          : undefined
      );
    const align = (ev.educationAlignment || 'weak').toLowerCase();
    const alignKey =
      align === 'strong'
        ? 'analysis.targetFit.eduStrong'
        : align === 'medium'
          ? 'analysis.targetFit.eduMedium'
          : 'analysis.targetFit.eduWeak';
    const sem = ev.semanticEvidence as { keywords?: unknown } | undefined;
    const semKeywords = sem?.keywords;
    const semKw = Array.isArray(semKeywords)
      ? semKeywords.filter((k): k is string => typeof k === 'string' && k.length > 0)
      : [];
    targetFit = {
      score: Math.round(payload.targetFitScore),
      seniorityLabel: t(tslKey),
      roleDomainLabel: domainCategoryLabel(payload.targetRoleDomain?.category, t),
      resumeDomainLabel: domainCategoryLabel(payload.resumeDomain?.category, t),
      evidence: {
        matchedTerms: [...(ev.matchedTerms ?? [])],
        missingTerms: [...(ev.missingTerms ?? [])],
        matchedSkills: [...(ev.matchedSkills ?? [])],
        experienceKeywordHits: typeof ev.experienceKeywordHits === 'number' ? ev.experienceKeywordHits : 0,
        educationAlignment: t(alignKey),
        portfolioEvidence: Boolean(ev.portfolioEvidence),
        requiredTermsHit: typeof ev.requiredTermsHit === 'number' ? ev.requiredTermsHit : 0,
        requiredTermsTotal: typeof ev.requiredTermsTotal === 'number' ? ev.requiredTermsTotal : 0,
        skillsHit: typeof ev.skillsHit === 'number' ? ev.skillsHit : 0,
        ...(semKw.length > 0 ? { semanticKeywords: semKw } : {}),
      },
      clampReasonLabels: (payload.targetSeniorityClampReasons ?? [])
        .filter((k): k is string => typeof k === 'string' && k.length > 0)
        .map((k) => t(k)),
      careerSwitch: {
        detected: Boolean(cs.detected),
        reason:
          cs.detected && typeof cs.reasonKey === 'string' && cs.reasonKey
            ? t(cs.reasonKey)
            : undefined,
      },
    };
  }

  logAnalysisFlow(payload);

  return {
    score,
    scoreLabel: scoreToLabel(score),
    scoreQualityHint,
    ats: typeof ats === 'number' ? ats : 0,
    atsBadge: scoreToBadge(ats),
    clarity: typeof clarity === 'number' ? clarity : 0,
    clarityBadge: scoreToBadge(clarity),
    seniorityLabel: t(seniorityKey),
    seniorityConfidence,
    insufficientDataHint,
    targetFit,
    strengths,
    improvements,
  };
}

function logAnalysisFlow(payload: AnalysisPayload): void {
  const group = `[analysis] resume ${payload.resumeId} — analysis ${payload.id}`;
  console.groupCollapsed(group);
  console.log('core scoring provider:', payload.metadata.provider, '| model:', payload.metadata.modelName, payload.metadata.modelVersion);
  console.log('seniority:', payload.seniorityLabel, '| confidence:', payload.seniorityConfidence, '| gating reasons:', payload.gatingReasons ?? []);
  console.log(
    'target fit:',
    payload.targetFitScore,
    '| provider:',
    payload.targetFitProvider ?? 'n/a',
    '| model version:',
    payload.targetFitModelVersion ?? 'n/a'
  );
  console.log('task scores:', payload.taskScores);
  if (payload.aiFeedback) {
    console.log('LLM feedback (cloud): generated —', payload.aiFeedback);
  } else {
    console.log('LLM feedback (cloud): not present (disabled, unavailable, or call failed — scoring is unaffected either way)');
  }
  console.groupEnd();
}
