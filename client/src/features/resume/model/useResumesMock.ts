import { useMemo, useState } from 'react';

import { resumesMock, toResumeViewModel, type Resume, type ResumeViewModel } from '@/entities/resume';

import type { ResumesSortKey, ResumesViewMode } from './types';

type State = {
  items: Resume[];
  query: string;
  view: ResumesViewMode;
  sort: ResumesSortKey;
  loading: boolean;
};

export function useResumesMock() {
  const [state, setState] = useState<State>({
    items: resumesMock,
    query: '',
    view: 'grid',
    sort: 'recent',
    loading: false,
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

    return sorted.map((r) => toResumeViewModel(r));
  }, [state.items, state.query, state.sort]);

  const setQuery = (query: string) => setState((s) => ({ ...s, query }));
  const setView = (view: ResumesViewMode) => setState((s) => ({ ...s, view }));
  const setSort = (sort: ResumesSortKey) => setState((s) => ({ ...s, sort }));
  const setLoading = (loading: boolean) => setState((s) => ({ ...s, loading }));

  const duplicate = (id: string) => {
    const src = state.items.find((r) => r.id === id);
    if (!src) return;
    const next: Resume = {
      ...src,
      id: `copy-${Date.now()}`,
      name: `${src.name} (cópia)`,
      updatedAt: new Date().toISOString(),
      status: 'draft',
    };
    setState((s) => ({ ...s, items: [next, ...s.items] }));
  };

  const remove = (id: string) => setState((s) => ({ ...s, items: s.items.filter((r) => r.id !== id) }));

  const create = (data: { name: string; templateId: string }) => {
    const next: Resume = {
      id: `r-${Date.now()}`,
      name: data.name,
      updatedAt: new Date().toISOString(),
      status: 'draft',
      score: 0,
      tags: data.templateId === 'tech' ? ['React', 'TypeScript', 'Node.js'] : ['Comunicação', 'Gestão', 'Resultados'],
    };
    setState((s) => ({ ...s, items: [next, ...s.items] }));
  };

  return {
    items: state.items,
    query: state.query,
    view: state.view,
    sort: state.sort,
    loading: state.loading,
    viewModels,
    setQuery,
    setView,
    setSort,
    setLoading,
    duplicate,
    remove,
    create,
  };
}
