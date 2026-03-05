import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { resumeApi, type ResumeDraftPayload } from '../api/resumeApi';
import { toResumeViewModel, type Resume, type ResumeViewModel } from '@/entities/resume';

import type {
  ResumeScoreFilter,
  ResumeStatusFilter,
  ResumeUpdatedFilter,
  ResumesSortKey,
  ResumesViewMode,
} from './types';

const QUERY_DEBOUNCE_MS = 260;

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

function scoreFilterToRange(score: ResumeScoreFilter) {
  if (score === 'none') return { include_no_score: true };
  if (score === '0-50') return { score_min: 0, score_max: 50 };
  if (score === '51-70') return { score_min: 51, score_max: 70 };
  if (score === '71-85') return { score_min: 71, score_max: 85 };
  if (score === '86-100') return { score_min: 86, score_max: 100 };
  return {};
}

function updatedFilterToRange(updated: ResumeUpdatedFilter) {
  if (updated === 'all') return {};
  const now = new Date();
  const days = updated === '7d' ? 7 : 30;
  const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  const iso = from.toISOString().slice(0, 10);
  return { updated_from: iso };
}

export function useResumes(init?: UseResumesInit) {
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

  const reload = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await resumeApi.list(listParams);
      setState((s) => ({ ...s, items: res.items ?? [], loading: false }));
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err }));
      throw err;
    }
  }, [listParams]);

  const fetchById = useCallback(async (resumeId: string) => {
    return resumeApi.get(resumeId);
  }, []);

  const createDraft = useCallback(async (payload: ResumeDraftPayload) => {
    const resume = await resumeApi.create(payload);
    await reload();
    return resume;
  }, [reload]);

  const updateDraft = useCallback(async (resumeId: string, payload: ResumeDraftPayload) => {
    const resume = await resumeApi.update(resumeId, payload);
    await reload();
    return resume;
  }, [reload]);

  const deleteResume = useCallback(async (resumeId: string) => {
    await resumeApi.delete(resumeId);
    remove(resumeId);
  }, [remove]);

  const duplicateResume = useCallback(async (resumeId: string) => {
    const resume = await resumeApi.duplicate(resumeId);
    await reload();
    return resume;
  }, [reload]);

  const downloadPdf = useCallback(async (resumeId: string) => {
    return resumeApi.downloadPdf(resumeId);
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => {
      void reload().catch(() => null);
    }, QUERY_DEBOUNCE_MS);
    return () => window.clearTimeout(id);
  }, [reload]);

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
  };
}
