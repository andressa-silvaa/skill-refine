import type { Resume, ResumeData, ResumeStatus } from '@/entities/resume';
import { apiRequest, apiRequestBlob } from '@/shared/api/http';

export type ResumeDraftPayload = ResumeData & {
  name?: string;
  status?: ResumeStatus;
  lastStep?: string;
  score?: number;
};

export type ResumeListResponse = {
  items: Resume[];
};

export type ResumeListParams = {
  search?: string;
  status?: 'draft' | 'complete' | 'analyzing' | 'published' | 'archived';
  score_min?: number;
  score_max?: number;
  include_no_score?: boolean;
  updated_from?: string;
  updated_to?: string;
  sort?: 'recent' | 'oldest' | 'score' | 'name';
};

export type ResumeDetailResponse = {
  id: string;
  name: string;
  status: ResumeStatus;
  updatedAt: string;
  lastStep?: string | null;
  data: ResumeData;
};

export type AiRewriteResponse = {
  suggestedText: string;
  provider?: 'cloud';
  fromCache?: boolean;
};

export type ResumePdfExportStatus = 'pending' | 'ready' | 'failed';

export type ResumePdfExportResponse = {
  status: ResumePdfExportStatus;
  exportId: string;
  fingerprint?: string;
  filename?: string;
  downloadPath?: string;
  cacheHit?: boolean;
  retryAfterSeconds?: number;
  errorMessage?: string;
};

export const resumeApi = {
  list(params?: ResumeListParams, init?: RequestInit) {
    const searchParams = new URLSearchParams();
    if (params?.search?.trim()) searchParams.set('search', params.search.trim());
    if (params?.status) searchParams.set('status', params.status);
    if (typeof params?.score_min === 'number') searchParams.set('score_min', String(params.score_min));
    if (typeof params?.score_max === 'number') searchParams.set('score_max', String(params.score_max));
    if (params?.include_no_score) searchParams.set('include_no_score', 'true');
    if (params?.updated_from) searchParams.set('updated_from', params.updated_from);
    if (params?.updated_to) searchParams.set('updated_to', params.updated_to);
    if (params?.sort) searchParams.set('sort', params.sort);
    const query = searchParams.toString();
    return apiRequest<ResumeListResponse>(`/resumes/api/resumes${query ? `?${query}` : ''}`, init);
  },
  get(resumeId: string) {
    return apiRequest<ResumeDetailResponse>(`/resumes/api/resumes/${resumeId}`);
  },
  rewriteSummaryWithAI(text: string) {
    return apiRequest<AiRewriteResponse>('/ai/rewrite', {
      method: 'POST',
      body: JSON.stringify({
        text,
        context: 'resume_summary',
        options: {
          language: 'pt-BR',
          tone: 'professional',
          maxLength: 600,
        },
      }),
    });
  },
  create(payload: ResumeDraftPayload) {
    return apiRequest<Resume>('/resumes/api/resumes', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  update(resumeId: string, payload: ResumeDraftPayload) {
    return apiRequest<Resume>(`/resumes/api/resumes/${resumeId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },
  delete(resumeId: string) {
    return apiRequest<void>(`/resumes/api/resumes/${resumeId}`, {
      method: 'DELETE',
    });
  },
  duplicate(resumeId: string) {
    return apiRequest<Resume>(`/resumes/api/resumes/${resumeId}/duplicate`, {
      method: 'POST',
    });
  },
  downloadPdf(resumeId: string, exportId?: string) {
    const query = exportId ? `?export_id=${encodeURIComponent(exportId)}` : '';
    return apiRequestBlob(`/resumes/api/resumes/${resumeId}/pdf${query}`);
  },
  startPdfExport(resumeId: string) {
    return apiRequest<ResumePdfExportResponse>(`/resumes/api/resumes/${resumeId}/pdf/start`, {
      method: 'POST',
    });
  },
  getPdfExportStatus(resumeId: string, exportId: string) {
    return apiRequest<ResumePdfExportResponse>(`/resumes/api/resumes/${resumeId}/pdf/status/${exportId}`);
  },
  getPdfToken(resumeId: string) {
    return apiRequest<{ token: string }>(`/resumes/api/resumes/${resumeId}/pdf-token`);
  },
  getPdfData(resumeId: string, token: string) {
    const encoded = encodeURIComponent(token);
    return apiRequest<ResumeDetailResponse>(`/resumes/api/resumes/${resumeId}/pdf-data?token=${encoded}`);
  },
};
