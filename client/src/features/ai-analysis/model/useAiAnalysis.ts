import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';
import { notify } from '@/shared/lib/notify';
import { useResumes } from '@/features/resume';

import { runAnalysis as runAnalysisApi, getLatestAnalysis } from '../api/analysisApi';
import { apiPayloadToResult } from './apiPayloadMapper';
import type {
  AnalysisResult,
  AnalysisStatus,
  ResumeOption,
} from './types';

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_DURATION_MS = 120_000;
const MAX_STAGNANT_PENDING_TICKS = 12;

export function useAiAnalysis(initialResumeId?: string) {
  const { t } = useTranslation();
  const { status: sessionStatus } = useSession();
  const resumes = useResumes();

  const [selectedResumeId, setSelectedResumeId] = useState(initialResumeId ?? '');
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [latestPayload, setLatestPayload] = useState<Awaited<ReturnType<typeof getLatestAnalysis>>['item'] | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollInFlightRef = useRef(false);
  const pollStartedAtRef = useRef<number | null>(null);
  const lastPendingUpdatedAtRef = useRef<string | null>(null);
  const stagnantPendingTicksRef = useRef(0);

  const resumeOptions: ResumeOption[] = resumes.viewModels.map((vm) => ({
    value: vm.id,
    label: vm.name?.trim() || vm.id,
  }));

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    pollInFlightRef.current = false;
    pollStartedAtRef.current = null;
    lastPendingUpdatedAtRef.current = null;
    stagnantPendingTicksRef.current = 0;
  }, []);

  const fetchLatest = useCallback(async (resumeId: string) => {
    const res = await getLatestAnalysis(resumeId);
    setLatestPayload(res.item);

    if (res.item?.status === 'done') {
      setResult(apiPayloadToResult(res.item, t));
      setStatus('success');
      return { state: 'done' as const, updatedAt: res.item.updatedAt };
    }

    if (res.item?.status === 'failed') {
      setResult(null);
      setStatus('error');
      return { state: 'failed' as const, updatedAt: res.item.updatedAt };
    }

    return { state: 'pending' as const, updatedAt: res.item?.updatedAt ?? null };
  }, [t]);

  useEffect(() => {
    if (initialResumeId) setSelectedResumeId(initialResumeId);
  }, [initialResumeId]);

  useEffect(() => {
    stopPolling();
    // Selection only updates local state; never preload previous analysis.
    setStatus('idle');
    setResult(null);
    setLatestPayload(null);
  }, [selectedResumeId, stopPolling]);

  const runAnalysis = useCallback(async () => {
    if (!selectedResumeId || sessionStatus !== 'authenticated') return;

    setStatus('loading');
    setResult(null);
    setLatestPayload(null);
    stopPolling();

    try {
      await runAnalysisApi(selectedResumeId);

      const pollResumeId = selectedResumeId;
      const tick = async (): Promise<boolean> => {
        if (pollInFlightRef.current) return false;
        pollInFlightRef.current = true;
        try {
          const latest = await fetchLatest(pollResumeId);
          if (latest.state === 'done') {
            stopPolling();
            notify.success(t('analysis.toast.done'));
            window.dispatchEvent(new CustomEvent('skill-refine:notifications-invalidate'));
            return true;
          }
          if (latest.state === 'failed') {
            stopPolling();
            notify.error(t('analysis.toast.failed'));
            window.dispatchEvent(new CustomEvent('skill-refine:notifications-invalidate'));
            return true;
          }

          if (
            pollStartedAtRef.current &&
            Date.now() - pollStartedAtRef.current > MAX_POLL_DURATION_MS
          ) {
            stopPolling();
            setStatus('error');
            notify.error(t('analysis.toast.failed'));
            return true;
          }

          if (latest.updatedAt && lastPendingUpdatedAtRef.current === latest.updatedAt) {
            stagnantPendingTicksRef.current += 1;
          } else {
            lastPendingUpdatedAtRef.current = latest.updatedAt;
            stagnantPendingTicksRef.current = 0;
          }

          if (stagnantPendingTicksRef.current >= MAX_STAGNANT_PENDING_TICKS) {
            stopPolling();
            setStatus('error');
            notify.error(t('analysis.toast.failed'));
            return true;
          }

          return false;
        } catch (err) {
          stopPolling();
          setStatus('error');
          notify.error(t('analysis.toast.failed'));
          return true;
        } finally {
          pollInFlightRef.current = false;
        }
      };

      // First check immediately after run to avoid a blind wait.
      pollStartedAtRef.current = Date.now();
      lastPendingUpdatedAtRef.current = null;
      stagnantPendingTicksRef.current = 0;
      const hasFinished = await tick();
      if (!hasFinished && !pollRef.current) {
        pollRef.current = setInterval(() => {
          void tick();
        }, POLL_INTERVAL_MS);
      }
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

  const isAnalyzing = status === 'loading';

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
    lastAnalysisAt: null,
  };
}
