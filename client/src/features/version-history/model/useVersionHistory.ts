import { useCallback, useEffect, useMemo, useState } from 'react';

import { versionHistoryApi } from '../api/versionHistoryApi';

import type { ResumeFilterOption, VersionHistoryItem } from './types';

const ALL_FILTER_ID = '__all__';

function mapDtoToItem(dto: import('../api/versionHistoryApi').VersionHistoryItemDto): VersionHistoryItem {
  return {
    id: dto.id,
    resumeId: dto.resumeId,
    resumeTitle: dto.resumeTitle,
    version: dto.version,
    isCurrent: dto.isCurrent,
    score: dto.score ?? 0,
    createdAt: dto.createdAt,
    changes: Array.isArray(dto.changes) ? dto.changes : [],
  };
}

type UseVersionHistoryParams = {
  resumeOptions: ResumeFilterOption[];
};

export function useVersionHistory(params: UseVersionHistoryParams) {
  const { resumeOptions: sourceResumeOptions } = params;
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [versions, setVersions] = useState<VersionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const resumeOptions: ResumeFilterOption[] = useMemo(() => {
    return sourceResumeOptions;
  }, [sourceResumeOptions]);

  const fetchVersions = useCallback(async (resumeId: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const res = await versionHistoryApi.list(resumeId ?? undefined);
      const items = (res.items ?? []).map(mapDtoToItem).sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setVersions(items);
    } catch (err) {
      setError(err);
      setVersions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchVersions(selectedResumeId);
  }, [selectedResumeId, fetchVersions]);

  const activeFilterId = selectedResumeId ?? ALL_FILTER_ID;
  const setFilter = useCallback((id: string) => {
    setSelectedResumeId(id === ALL_FILTER_ID ? null : id);
  }, []);

  const refetch = useCallback(() => {
    void fetchVersions(selectedResumeId);
  }, [fetchVersions, selectedResumeId]);

  return {
    versions,
    resumeOptions,
    activeFilterId,
    setFilter,
    allFilterId: ALL_FILTER_ID,
    loading,
    error,
    refetch,
  };
}
