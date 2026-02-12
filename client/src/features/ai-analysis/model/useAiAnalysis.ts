import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';
import { notify } from '@/shared/lib/notify';
import { useResumes } from '@/features/resume';

import { ApiError } from '@/shared/api';

import { runAnalysis as runAnalysisApi, getLatestAnalysis } from '../api/analysisApi';
import { apiPayloadToResult } from './apiPayloadMapper';
import type {
  AnalysisResult,
  AnalysisStatus,
  ResumeOption,
} from './types';

const POLL_INTERVAL_MS = 2000;

export function useAiAnalysis(initialResumeId?: string) {
  const { t } = useTranslation();
  const { status: sessionStatus } = useSession();
  const resumes = useResumes();

  const [selectedResumeId, setSelectedResumeId] = useState(initialResumeId ?? '');
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [latestPayload, setLatestPayload] = useState<Awaited<ReturnType<typeof getLatestAnalysis>>['item'] | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const resumeOptions: ResumeOption[] = resumes.viewModels.map((vm) => ({
    value: vm.id,
    label: vm.name?.trim() || vm.id,
  }));

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const fetchLatest = useCallback(
    async (options?: { onDone?: () => void; onFailed?: () => void }) => {
      if (!selectedResumeId) return null;
      try {
        const res = await getLatestAnalysis(selectedResumeId);
        setLatestPayload(res.item);
        if (res.item?.status === 'done') {
          setResult(apiPayloadToResult(res.item, t));
          setStatus('success');
          stopPolling();
          options?.onDone?.();
          return res.item;
        }
        if (res.item?.status === 'failed') {
          setStatus('error');
          stopPolling();
          options?.onFailed?.();
          return res.item;
        }
        return res.item;
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          stopPolling();
        }
        return null;
      }
    },
    [selectedResumeId, t, stopPolling]
  );

  useEffect(() => {
    if (initialResumeId) setSelectedResumeId(initialResumeId);
  }, [initialResumeId]);

  useEffect(() => {
    if (sessionStatus !== 'authenticated' || !selectedResumeId) {
      if (!selectedResumeId) {
        setLatestPayload(null);
        setResult(null);
        setStatus('idle');
      }
      return;
    }
    getLatestAnalysis(selectedResumeId)
      .then((res) => {
        setLatestPayload(res.item);
        if (res.item?.status === 'done') {
          setResult(apiPayloadToResult(res.item, t));
          setStatus('success');
        } else if (res.item?.status === 'failed') {
          setStatus('error');
        } else if (res.item?.status === 'pending' || res.item?.status === 'running') {
          setStatus('loading');
          setResult(null);
        }
      })
      .catch(() => {});
  }, [sessionStatus, selectedResumeId, t]);

  const runAnalysis = useCallback(async () => {
    if (!selectedResumeId || sessionStatus !== 'authenticated') return;

    setStatus('loading');
    setResult(null);
    stopPolling();

    try {
      await runAnalysisApi(selectedResumeId);
      setLatestPayload(null);
      pollRef.current = setInterval(
        () =>
          fetchLatest({
            onDone: () => notify.success(t('analysis.toast.done')),
            onFailed: () => notify.error(t('analysis.toast.failed')),
          }),
        POLL_INTERVAL_MS
      );
    } catch {
      setStatus('error');
      notify.error(t('analysis.toast.failed'));
    }
  }, [selectedResumeId, sessionStatus, fetchLatest, stopPolling, t]);

  const retry = useCallback(() => {
    setStatus('idle');
    setResult(null);
    setLatestPayload(null);
    stopPolling();
  }, [stopPolling]);

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  const isAnalyzing = status === 'loading' || latestPayload?.status === 'pending' || latestPayload?.status === 'running';

  return {
    resumeOptions,
    selectedResumeId,
    setSelectedResumeId,
    status,
    result,
    latestPayload,
    runAnalysis,
    retry,
    isAnalyzing,
    lastAnalysisAt: latestPayload?.status === 'done' ? latestPayload.updatedAt : null,
  };
}
