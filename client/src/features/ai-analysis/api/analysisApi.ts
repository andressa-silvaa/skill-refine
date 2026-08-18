import { apiRequest } from '@/shared/api';

/** Avoid stale GET responses for polling / latest (browser HTTP cache). */
const NO_BROWSER_CACHE: RequestInit = { cache: 'no-store' };

export type AnalysisStatusApi = 'pending' | 'running' | 'done' | 'failed';

export type InsightItemApi = {
  key: string;
  params?: Record<string, string>;
  evidence?: Record<string, string | number | boolean>;
};

export type ImprovementItemApi = InsightItemApi & {
  priority?: 'high' | 'medium' | 'low';
};

export type RecommendationItemApi = ImprovementItemApi & {
  example_key?: string;
  example_params?: Record<string, string>;
  action_type?: string;
  section?: string;
  field_target?: string;
};

export type AnalysisCompletenessApi = {
  score?: number | null;
  level?: string | null;
  confidence?: 'high' | 'low' | string | null;
};

export type TargetRoleDomainApi = {
  category?: string | null;
  confidence?: string | null;
  evidenceTokens?: string[] | null;
};

export type TargetFitEvidenceApi = {
  matchedTerms?: string[] | null;
  missingTerms?: string[] | null;
  matchedSkills?: string[] | null;
  experienceKeywordHits?: number | null;
  educationAlignment?: string | null;
  portfolioEvidence?: boolean | null;
  requiredTermsHit?: number | null;
  requiredTermsTotal?: number | null;
  skillsHit?: number | null;
  semanticEvidence?: { keywords?: string[] | null } | null;
};

export type CareerSwitchApi = {
  detected?: boolean | null;
  reasonKey?: string | null;
};

export type AnalysisPayload = {
  id: string;
  resumeId: string;
  status: AnalysisStatusApi;
  score: number | null;
  completeness?: AnalysisCompletenessApi | null;
  /** Backend class: intern | junior | mid | senior */
  seniorityLabel?: string | null;
  seniorityConfidence?: 'low' | 'medium' | 'high' | null;
  scoreMeaning?: string | null;
  insufficientData?: boolean | null;
  gatingReasons?: string[] | null;
  targetFitScore?: number | null;
  targetRoleDomain?: TargetRoleDomainApi | null;
  resumeDomain?: TargetRoleDomainApi | null;
  targetFitEvidence?: TargetFitEvidenceApi | null;
  careerSwitch?: CareerSwitchApi | null;
  /** Audit: policy vs sklearn (for dev / TCC). */
  targetFitProvider?: string | null;
  targetFitModelVersion?: string | null;
  targetFitDatasetVersion?: string | null;
  taskScores: {
    ats?: number | null;
    clarity?: number | null;
    seniority?: number | null;
    matching?: number | null;
    targetFit?: number | null;
  };
  insights: {
    strengths: InsightItemApi[];
    improvements: ImprovementItemApi[];
  };
  recommendations?: RecommendationItemApi[];
  metadata: {
    modelName: string;
    modelVersion: string;
    provider: string;
  };
  aiFeedback?: string | null;
  createdAt: string;
  updatedAt: string;
  errorMessage?: string;
};

export type LatestResponse = {
  item: AnalysisPayload | null;
};

export type LatestBatchResponse = {
  items: Record<string, AnalysisPayload>;
};

export type HistoryResponse = {
  items: AnalysisPayload[];
  limit: number;
  offset: number;
  total: number;
  hasNext: boolean;
  nextOffset: number | null;
};

export async function runAnalysis(resumeId: string, jobText?: string): Promise<AnalysisPayload> {
  const body: Record<string, unknown> = { resume_id: resumeId };
  if (jobText?.trim()) {
    body.job_description_text = jobText.trim();
  }
  return apiRequest<AnalysisPayload>('/analysis/run', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getLatestAnalysis(resumeId: string): Promise<LatestResponse> {
  return apiRequest<LatestResponse>(
    `/analysis/latest?resume_id=${encodeURIComponent(resumeId)}`,
    NO_BROWSER_CACHE
  );
}

export async function getLatestAnalysesBatch(resumeIds: string[]): Promise<LatestBatchResponse> {
  const ids = resumeIds.map((id) => id.trim()).filter(Boolean);
  if (ids.length === 0) return { items: {} };
  const qs = encodeURIComponent(ids.join(","));
  return apiRequest<LatestBatchResponse>(`/analysis/latest?resume_ids=${qs}`, NO_BROWSER_CACHE);
}

export async function getAnalysisHistory(
  resumeId: string,
  limit = 20,
  offset = 0
): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    resume_id: resumeId,
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest<HistoryResponse>(`/analysis/history?${params}`, NO_BROWSER_CACHE);
}
