import { apiRequest } from '@/shared/api/http';

export type VersionHistoryItemDto = {
  id: string;
  resumeId: string;
  resumeTitle: string;
  version: number;
  isCurrent: boolean;
  score: number | null;
  createdAt: string;
  changes: string[];
};

export type VersionDetailDto = VersionHistoryItemDto & {
  snapshot: import('@/entities/resume').ResumeData;
};

export type VersionListResponse = {
  items: VersionHistoryItemDto[];
};

export const versionHistoryApi = {
  list(resumeId?: string) {
    const qs = resumeId ? `?resume_id=${encodeURIComponent(resumeId)}` : '';
    return apiRequest<VersionListResponse>(`/resumes/api/versions${qs}`);
  },

  get(resumeId: string, versionId: string) {
    return apiRequest<VersionDetailDto>(
      `/resumes/api/resumes/${resumeId}/versions/${versionId}`
    );
  },

  restore(resumeId: string, versionId: string) {
    return apiRequest<{ id: string; name: string; updatedAt: string; status: string; score?: number | null }>(
      `/resumes/api/resumes/${resumeId}/versions/${versionId}/restore`,
      { method: 'POST' }
    );
  },
};
