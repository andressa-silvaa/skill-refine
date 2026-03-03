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

export type AnalysisResult = {
  score: number;
  scoreLabel: string;
  ats: number;
  atsBadge: MetricBadgeTone;
  clarity: number;
  clarityBadge: MetricBadgeTone;
  seniorityLabel: string;
  /** Canonical: list of { key, params? }. API and mock use this. */
  strengths: InsightItem[];
  /** Canonical: list of { key, priority?, params? }. API and mock use this. */
  improvements: ImprovementInsightItem[];
};

export type ResumeOption = {
  value: string;
  label: string;
};
