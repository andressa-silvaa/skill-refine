import { apiRequest } from '@/shared/api';

export type AnalysisStatusApi = 'pending' | 'running' | 'done' | 'failed';

export type InsightItemApi = {
  key: string;
  params?: Record<string, string>;
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

export type AnalysisPayload = {
  id: string;
  resumeId: string;
  status: AnalysisStatusApi;
  score: number | null;
  taskScores: {
    ats?: number | null;
    clarity?: number | null;
    seniority?: number | null;
    matching?: number | null;
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
  return apiRequest<LatestResponse>(`/analysis/latest?resume_id=${encodeURIComponent(resumeId)}`);
}

export async function getLatestAnalysesBatch(resumeIds: string[]): Promise<LatestBatchResponse> {
  const ids = resumeIds.map((id) => id.trim()).filter(Boolean);
  if (ids.length === 0) return { items: {} };
  const qs = encodeURIComponent(ids.join(","));
  return apiRequest<LatestBatchResponse>(`/analysis/latest?resume_ids=${qs}`);
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
  return apiRequest<HistoryResponse>(`/analysis/history?${params}`);
}
