import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { resumeApi, type ResumeDraftPayload } from '../api/resumeApi';
import { toResumeViewModel, type Resume, type ResumeViewModel } from '@/entities/resume';

import type { ResumesSortKey, ResumesViewMode } from './types';

type State = {
  items: Resume[];
  query: string;
  view: ResumesViewMode;
  sort: ResumesSortKey;
  loading: boolean;
  error: unknown | null;
};

export function useResumes() {
  const { t } = useTranslation();
  const [state, setState] = useState<State>({
    items: [],
    query: '',
    view: 'grid',
    sort: 'recent',
    loading: true,
    error: null,
  });

  const viewModels = useMemo<ResumeViewModel[]>(() => {
    const q = state.query.trim().toLowerCase();
    const base = q
      ? state.items.filter((r) => r.name.toLowerCase().includes(q) || r.tags.join(' ').toLowerCase().includes(q))
      : state.items;

    const sorted = [...base].sort((a, b) => {
      if (state.sort === 'score') return (b.score ?? 0) - (a.score ?? 0);
      if (state.sort === 'name') return a.name.localeCompare(b.name);
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });

    return sorted.map((r) => toResumeViewModel(r, { t }));
  }, [state.items, state.query, state.sort, t]);

  const setQuery = (query: string) => setState((s) => ({ ...s, query }));
  const setView = (view: ResumesViewMode) => setState((s) => ({ ...s, view }));
  const setSort = (sort: ResumesSortKey) => setState((s) => ({ ...s, sort }));
  const setLoading = (loading: boolean) => setState((s) => ({ ...s, loading }));

  const upsert = useCallback((resume: Resume) => {
    setState((s) => ({
      ...s,
      items: [resume, ...s.items.filter((item) => item.id !== resume.id)],
    }));
  }, []);

  const remove = (id: string) => setState((s) => ({ ...s, items: s.items.filter((r) => r.id !== id) }));

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

  const reload = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await resumeApi.list();
      setState((s) => ({ ...s, items: res.items ?? [], loading: false }));
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err }));
      throw err;
    }
  }, []);

  const fetchById = useCallback(async (resumeId: string) => {
    return resumeApi.get(resumeId);
  }, []);

  const createDraft = useCallback(async (payload: ResumeDraftPayload) => {
    const resume = await resumeApi.create(payload);
    upsert(resume);
    return resume;
  }, [upsert]);

  const updateDraft = useCallback(async (resumeId: string, payload: ResumeDraftPayload) => {
    const resume = await resumeApi.update(resumeId, payload);
    upsert(resume);
    return resume;
  }, [upsert]);

  const deleteResume = useCallback(async (resumeId: string) => {
    await resumeApi.delete(resumeId);
    remove(resumeId);
  }, [remove]);

  const duplicateResume = useCallback(async (resumeId: string) => {
    const resume = await resumeApi.duplicate(resumeId);
    upsert(resume);
    return resume;
  }, [upsert]);

  const downloadPdf = useCallback(async (resumeId: string) => {
    return resumeApi.downloadPdf(resumeId);
  }, []);

  useEffect(() => {
    void reload().catch(() => null);
  }, [reload]);

  return {
    items: state.items,
    query: state.query,
    view: state.view,
    sort: state.sort,
    loading: state.loading,
    error: state.error,
    viewModels,
    setQuery,
    setView,
    setSort,
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
