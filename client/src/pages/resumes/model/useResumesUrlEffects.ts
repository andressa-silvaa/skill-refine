import { useEffect, useRef } from 'react';
import type { SetURLSearchParams } from 'react-router-dom';

import type { BuilderStep } from '@/features/resume-builder';

type ResumesLike = {
  query: string;
  sort: 'recent' | 'oldest' | 'score' | 'name';
  view: 'grid' | 'list';
  filters: {
    status: 'all' | 'draft' | 'complete' | 'analyzing';
    score: 'all' | 'none' | '0-50' | '51-70' | '71-85' | '86-100';
    updated: 'all' | '7d' | '30d';
  };
};

type Params = {
  resumes: ResumesLike;
  searchParams: URLSearchParams;
  setSearchParams: SetURLSearchParams;
  onOpenCreate: () => void;
  onEditFromQuery: (id: string, options: { targetStep: BuilderStep | null; suggestedText: string | null }) => void;
};

export function useResumesUrlEffects(params: Params) {
  const { resumes, searchParams, setSearchParams, onOpenCreate, onEditFromQuery } = params;
  const handledApplyContextRef = useRef<string | null>(null);

  useEffect(() => {
    const currentQueryString = searchParams.toString();
    const nextParams = new URLSearchParams(searchParams);
    const setOrDelete = (key: string, value: string | null | undefined, fallback = '') => {
      const normalized = (value ?? '').trim();
      if (!normalized || normalized === fallback) {
        nextParams.delete(key);
        return;
      }
      nextParams.set(key, normalized);
    };
    setOrDelete('q', resumes.query, '');
    setOrDelete('sort', resumes.sort, 'recent');
    setOrDelete('view', resumes.view, 'grid');
    setOrDelete('status', resumes.filters.status, 'all');
    setOrDelete('score', resumes.filters.score, 'all');
    setOrDelete('updated', resumes.filters.updated, 'all');
    if (nextParams.toString() !== currentQueryString) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [
    resumes.filters.score,
    resumes.filters.status,
    resumes.filters.updated,
    resumes.query,
    resumes.sort,
    resumes.view,
    searchParams,
    setSearchParams,
  ]);

  useEffect(() => {
    const createResume = searchParams.get('create');
    if (createResume !== '1') return;

    onOpenCreate();
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('create');
    setSearchParams(nextParams, { replace: true });
  }, [onOpenCreate, searchParams, setSearchParams]);

  useEffect(() => {
    const editResumeId = searchParams.get('editResumeId');
    if (!editResumeId) return;

    const targetStepParam = searchParams.get('targetStep');
    const suggestedText = searchParams.get('suggestedText');
    const allSteps: BuilderStep[] = ['theme', 'basic', 'contact', 'experience', 'education', 'skills', 'languages', 'summary', 'review'];
    const targetStep = targetStepParam && allSteps.includes(targetStepParam as BuilderStep)
      ? (targetStepParam as BuilderStep)
      : null;

    const contextKey = `${editResumeId}:${targetStep ?? ''}:${suggestedText ?? ''}`;
    if (handledApplyContextRef.current === contextKey) return;
    handledApplyContextRef.current = contextKey;

    onEditFromQuery(editResumeId, {
      targetStep,
      suggestedText,
    });

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('editResumeId');
    nextParams.delete('targetStep');
    nextParams.delete('fieldTarget');
    nextParams.delete('improvementKey');
    nextParams.delete('suggestedText');
    setSearchParams(nextParams, { replace: true });
  }, [onEditFromQuery, searchParams, setSearchParams]);
}
