export type AnalysisStatus = 'idle' | 'loading' | 'success' | 'error';

/** Semântica para badge de ATS/Clareza: Excelente (verde), Bom (neutro), Atenção (amarelo) */
export type MetricBadgeTone = 'excellent' | 'good' | 'attention';

export type ImprovementPriority = 'high' | 'medium' | 'low';

/** Canonical insight item: backend returns key + params, frontend translates with t(key, params). */
export type InsightItem = {
  key: string;
  params?: Record<string, string>;
};

export type ImprovementInsightItem = InsightItem & {
  priority?: ImprovementPriority;
  exampleKey?: string;
  exampleText?: string;
  actionType?: string;
  section?: string;
  fieldTarget?: string;
};

/** Legacy: text-only (mock or backward compat). */
export type ImprovementItem = {
  text: string;
  priority?: ImprovementPriority;
};

/** Target role fit / migration (optional — present when backend computed target fit). */
export type TargetFitView = {
  score: number;
  seniorityLabel: string;
  roleDomainLabel: string;
  resumeDomainLabel: string;
  evidence: {
    matchedTerms: string[];
    missingTerms: string[];
    matchedSkills: string[];
    experienceKeywordHits: number;
    educationAlignment: string;
    portfolioEvidence: boolean;
    requiredTermsHit: number;
    requiredTermsTotal: number;
    skillsHit: number;
    semanticKeywords?: string[];
  };
  clampReasonLabels: string[];
  careerSwitch: { detected: boolean; reason?: string };
};

export type AnalysisResult = {
  score: number;
  scoreLabel: string;
  /** Curta explicação do que o score principal mede (qualidade do currículo). */
  scoreQualityHint?: string;
  ats: number;
  atsBadge: MetricBadgeTone;
  clarity: number;
  clarityBadge: MetricBadgeTone;
  seniorityLabel: string;
  seniorityConfidence?: 'low' | 'medium' | 'high';
  insufficientDataHint?: string;
  /** Aderência ao cargo alvo + senioridade na área alvo (quando disponível). */
  targetFit?: TargetFitView;
  /** Canonical: list of { key, params? }. API and mock use this. */
  strengths: InsightItem[];
  /** Canonical: list of { key, priority?, params? }. API and mock use this. */
  improvements: ImprovementInsightItem[];
};

export type ResumeOption = {
  value: string;
  label: string;
};
