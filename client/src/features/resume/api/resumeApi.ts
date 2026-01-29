import type { Resume, ResumeData, ResumeStatus } from '@/entities/resume';
import { apiRequest, apiRequestBlob } from '@/shared/api/http';

export type ResumeDraftPayload = ResumeData & {
  name?: string;
  status?: ResumeStatus;
  lastStep?: string;
  /** Score de completude (0–100). Persistido ao salvar. */
  score?: number;
};

export type ResumeListResponse = {
  items: Resume[];
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

export const resumeApi = {
  list() {
    return apiRequest<ResumeListResponse>('/resumes/api/resumes');
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
  downloadPdf(resumeId: string) {
    return apiRequestBlob(`/resumes/api/resumes/${resumeId}/pdf`);
  },
  getPdfToken(resumeId: string) {
    return apiRequest<{ token: string }>(`/resumes/api/resumes/${resumeId}/pdf-token`);
  },
  getPdfData(resumeId: string, token: string) {
    const encoded = encodeURIComponent(token);
    return apiRequest<ResumeDetailResponse>(`/resumes/api/resumes/${resumeId}/pdf-data?token=${encoded}`);
  },
};
