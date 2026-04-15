import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { markResumeContentSaved } from '@/shared/lib/resumeSaveMarker';

import { resumeApi, type ResumeDraftPayload } from '../api/resumeApi';
import { toResumeViewModel, type Resume, type ResumeViewModel } from '@/entities/resume';

import type {
  ResumeScoreFilter,
  ResumeStatusFilter,
  ResumeUpdatedFilter,
  ResumesSortKey,
  ResumesViewMode,
} from './types';
import { scoreFilterToRange, updatedFilterToRange } from './resumeListQueryParams';

const QUERY_DEBOUNCE_MS = 260;
const LIST_CACHE_TTL_MS = 15_000;

type ResumeFiltersState = {
  status: ResumeStatusFilter;
  score: ResumeScoreFilter;
  updated: ResumeUpdatedFilter;
};

type State = {
  items: Resume[];
  query: string;
  view: ResumesViewMode;
  sort: ResumesSortKey;
  filters: ResumeFiltersState;
  loading: boolean;
  error: unknown | null;
};

type UseResumesInit = {
  query?: string;
  sort?: ResumesSortKey;
  view?: ResumesViewMode;
  filters?: Partial<ResumeFiltersState>;
};

export function useResumes(init?: UseResumesInit) {
  const listCacheRef = useRef<Map<string, { at: number; items: Resume[] }>>(new Map());
  const requestSeqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const { t } = useTranslation();
  const [state, setState] = useState<State>({
    items: [],
    query: init?.query ?? '',
    view: init?.view ?? 'grid',
    sort: init?.sort ?? 'recent',
    filters: {
      status: init?.filters?.status ?? 'all',
      score: init?.filters?.score ?? 'all',
      updated: init?.filters?.updated ?? 'all',
    },
    loading: true,
    error: null,
  });
  const [listVersion, setListVersion] = useState(0);

  const viewModels = useMemo<ResumeViewModel[]>(() => {
    return state.items.map((r) => toResumeViewModel(r, { t }));
  }, [state.items, t]);

  const setQuery = (query: string) => setState((s) => ({ ...s, query }));
  const setView = (view: ResumesViewMode) => setState((s) => ({ ...s, view }));
  const setSort = (sort: ResumesSortKey) => setState((s) => ({ ...s, sort }));
  const setStatusFilter = (status: ResumeStatusFilter) =>
    setState((s) => ({ ...s, filters: { ...s.filters, status } }));
  const setScoreFilter = (score: ResumeScoreFilter) =>
    setState((s) => ({ ...s, filters: { ...s.filters, score } }));
  const setUpdatedFilter = (updated: ResumeUpdatedFilter) =>
    setState((s) => ({ ...s, filters: { ...s.filters, updated } }));
  const clearFilters = () =>
    setState((s) => ({ ...s, filters: { status: 'all', score: 'all', updated: 'all' } }));
  const setLoading = (loading: boolean) => setState((s) => ({ ...s, loading }));
  const remove = useCallback((id: string) => {
    setState((s) => ({ ...s, items: s.items.filter((r) => r.id !== id) }));
  }, []);

  const duplicate = (id: string) => {
    const src = state.items.find((r) => r.id === id);
    if (!src) return;
    const next: Resume = {
      ...src,
      id: `copy-${Date.now()}`,
      name: `${src.name} ${t('resume.copySuffix')}`,
      updatedAt: new Date().toISOString(),
      status: 'draft',
    };
    setState((s) => ({ ...s, items: [next, ...s.items] }));
  };

  const listParams = useMemo(() => {
    return {
      search: state.query.trim() || undefined,
      status: state.filters.status === 'all' ? undefined : state.filters.status,
      sort: state.sort,
      ...scoreFilterToRange(state.filters.score),
      ...updatedFilterToRange(state.filters.updated),
    };
  }, [state.filters.score, state.filters.status, state.filters.updated, state.query, state.sort]);

  const reload = useCallback(async (options?: { force?: boolean }) => {
    const cacheKey = JSON.stringify(listParams);
    const now = Date.now();
    if (!options?.force) {
      const cached = listCacheRef.current.get(cacheKey);
      if (cached && now - cached.at <= LIST_CACHE_TTL_MS) {
        setState((s) => ({ ...s, items: cached.items, loading: false, error: null }));
        return;
      }
    } else {
      listCacheRef.current.clear();
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const reqSeq = requestSeqRef.current + 1;
    requestSeqRef.current = reqSeq;

    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await resumeApi.list(listParams, { signal: controller.signal });
      if (requestSeqRef.current !== reqSeq) return;
      const items = res.items ?? [];
      listCacheRef.current.set(cacheKey, { at: now, items });
      setState((s) => ({ ...s, items, loading: false }));
      if (options?.force) {
        setListVersion((v) => v + 1);
      }
    } catch (err) {
      if ((err as { name?: string })?.name === 'AbortError') return;
      if (requestSeqRef.current !== reqSeq) return;
      setState((s) => ({ ...s, loading: false, error: err }));
      throw err;
    }
  }, [listParams]);

  const fetchById = useCallback(async (resumeId: string) => {
    return resumeApi.get(resumeId);
  }, []);

  const createDraft = useCallback(async (payload: ResumeDraftPayload) => {
    const resume = await resumeApi.create(payload);
    markResumeContentSaved(resume.id);
    await reload({ force: true });
    return resume;
  }, [reload]);

  const updateDraft = useCallback(async (resumeId: string, payload: ResumeDraftPayload) => {
    const resume = await resumeApi.update(resumeId, payload);
    markResumeContentSaved(resumeId);
    await reload({ force: true });
    return resume;
  }, [reload]);

  const deleteResume = useCallback(async (resumeId: string) => {
    await resumeApi.delete(resumeId);
    remove(resumeId);
  }, [remove]);

  const duplicateResume = useCallback(async (resumeId: string) => {
    const resume = await resumeApi.duplicate(resumeId);
    markResumeContentSaved(resume.id);
    await reload({ force: true });
    return resume;
  }, [reload]);

  const downloadPdf = useCallback(async (resumeId: string) => {
    return resumeApi.downloadPdf(resumeId);
  }, []);

  const startPdfExport = useCallback(async (resumeId: string) => {
    return resumeApi.startPdfExport(resumeId);
  }, []);

  const getPdfExportStatus = useCallback(async (resumeId: string, exportId: string) => {
    return resumeApi.getPdfExportStatus(resumeId, exportId);
  }, []);

  const downloadPdfExport = useCallback(async (resumeId: string, exportId: string) => {
    return resumeApi.downloadPdf(resumeId, exportId);
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void reload().catch(() => null);
    }, QUERY_DEBOUNCE_MS);
    return () => window.clearTimeout(id);
  }, [reload]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const hasActiveFilters =
    state.filters.status !== 'all' || state.filters.score !== 'all' || state.filters.updated !== 'all';

  return {
    items: state.items,
    query: state.query,
    view: state.view,
    sort: state.sort,
    filters: state.filters,
    loading: state.loading,
    error: state.error,
    hasActiveFilters,
    listVersion,
    viewModels,
    setQuery,
    setView,
    setSort,
    setStatusFilter,
    setScoreFilter,
    setUpdatedFilter,
    clearFilters,
    setLoading,
    duplicate,
    remove,
    reload,
    createDraft,
    updateDraft,
    fetchById,
    deleteResume,
    duplicateResume,
    downloadPdf,
    startPdfExport,
    getPdfExportStatus,
    downloadPdfExport,
  };
}
