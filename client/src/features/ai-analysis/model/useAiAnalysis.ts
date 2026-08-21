import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';
import { notify } from '@/shared/lib/notify';
import {
  analysisSyncStorageKey,
  readResumeSaveMarker,
  RESUME_SAVE_STORAGE_KEY,
} from '@/shared/lib/resumeSaveMarker';
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
  const [jobDescription, setJobDescription] = useState('');
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [latestPayload, setLatestPayload] = useState<Awaited<ReturnType<typeof getLatestAnalysis>>['item'] | null>(null);
  /** Bumps when este currículo é salvo (evento ou outra aba) para o efeito de sync voltar a correr. */
  const [resumeSaveEpoch, setResumeSaveEpoch] = useState(0);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollInFlightRef = useRef(false);
  const pollStartedAtRef = useRef<number | null>(null);
  const lastPendingUpdatedAtRef = useRef<string | null>(null);
  const stagnantPendingTicksRef = useRef(0);
  /** Invalidates in-flight GET /latest when resume content version or runAnalysis starts (avoids stale UI). */
  const fetchGenerationRef = useRef(0);
  /** True while POST/poll run is in progress — skip sync effect so list hydrate (updatedAt) não corta o polling. */
  const analysisRunActiveRef = useRef(false);
  const prevSelectedResumeIdRef = useRef<string>('');

  const resumeOptions: ResumeOption[] = resumes.viewModels.map((vm) => ({
    value: vm.id,
    label: vm.name?.trim() || vm.id,
  }));

  const selectedResumeUpdatedAt = useMemo(() => {
    if (!selectedResumeId) return null;
    return resumes.items.find((item) => item.id === selectedResumeId)?.updatedAt ?? null;
  }, [resumes.items, selectedResumeId]);

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

  const applyLatestResponse = useCallback(
    (
      res: Awaited<ReturnType<typeof getLatestAnalysis>>,
      opts?: { fromPoll?: boolean }
    ) => {
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

      setResult(null);
      // Durante o poll, /latest pode ainda devolver item null ou pending — não voltar a 'idle'
      // senão apaga o loading e parece que "não há análise / não há request".
      if (!opts?.fromPoll) {
        setStatus('idle');
      }
      return { state: 'pending' as const, updatedAt: res.item?.updatedAt ?? null };
    },
    [t]
  );

  const fetchLatest = useCallback(
    async (resumeId: string, generation?: number, fromPoll = false) => {
      const res = await getLatestAnalysis(resumeId);
      if (generation !== undefined && generation !== fetchGenerationRef.current) {
        return { state: 'pending' as const, updatedAt: null as string | null };
      }
      return applyLatestResponse(res, { fromPoll });
    },
    [applyLatestResponse]
  );

  useEffect(() => {
    if (initialResumeId) setSelectedResumeId(initialResumeId);
  }, [initialResumeId]);

  useEffect(() => {
    const onSaved = (e: Event) => {
      const id = (e as CustomEvent<{ resumeId?: string }>).detail?.resumeId;
      if (id && id === selectedResumeId) setResumeSaveEpoch((n) => n + 1);
    };
    const onStorage = (ev: StorageEvent) => {
      if (ev.key !== RESUME_SAVE_STORAGE_KEY || !ev.newValue) return;
      try {
        const m = JSON.parse(ev.newValue) as { resumeId?: string };
        if (m.resumeId === selectedResumeId) setResumeSaveEpoch((n) => n + 1);
      } catch {
        /* ignore */
      }
    };
    window.addEventListener('skill-refine:resume-saved', onSaved);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('skill-refine:resume-saved', onSaved);
      window.removeEventListener('storage', onStorage);
    };
  }, [selectedResumeId]);

  // Re-sync com GET /analysis/latest quando muda o currículo, o updatedAt na lista, sessão, ou marcador de save.
  // A lista em useResumes() desta página pode estar em cache / desatualizada face ao builder — por isso usamos
  // markResumeContentSaved + sessionStorage para forçar novo GET após salvar.
  useEffect(() => {
    const idChanged = prevSelectedResumeIdRef.current !== selectedResumeId;
    prevSelectedResumeIdRef.current = selectedResumeId;

    if (idChanged) {
      analysisRunActiveRef.current = false;
    }

    let lastSyncedSaveAt = 0;
    try {
      lastSyncedSaveAt = Number(sessionStorage.getItem(analysisSyncStorageKey(selectedResumeId)) || '0');
    } catch {
      lastSyncedSaveAt = 0;
    }
    const marker = readResumeSaveMarker();
    const saveRequiresRefetch =
      Boolean(selectedResumeId) &&
      marker != null &&
      marker.resumeId === selectedResumeId &&
      marker.at > lastSyncedSaveAt;

    if (saveRequiresRefetch) {
      analysisRunActiveRef.current = false;
    } else if (analysisRunActiveRef.current && !idChanged) {
      return;
    }

    stopPolling();

    if (!selectedResumeId || sessionStatus !== 'authenticated') {
      setStatus('idle');
      setResult(null);
      setLatestPayload(null);
      return;
    }

    const generation = ++fetchGenerationRef.current;

    void (async () => {
      try {
        const res = await getLatestAnalysis(selectedResumeId);
        if (generation !== fetchGenerationRef.current) {
          return;
        }
        applyLatestResponse(res);
        const m = readResumeSaveMarker();
        const sk = analysisSyncStorageKey(selectedResumeId);
        if (m && m.resumeId === selectedResumeId) {
          const prev = Number(sessionStorage.getItem(sk) || '0');
          sessionStorage.setItem(sk, String(Math.max(prev, m.at)));
        }
      } catch {
        if (generation !== fetchGenerationRef.current) return;
        setResult(null);
        setLatestPayload(null);
        setStatus('idle');
      }
    })();
  }, [
    selectedResumeId,
    selectedResumeUpdatedAt,
    sessionStatus,
    stopPolling,
    applyLatestResponse,
    resumeSaveEpoch,
  ]);

  useEffect(() => {
    const onPageShow = (e: PageTransitionEvent) => {
      if (!e.persisted || !selectedResumeId || sessionStatus !== 'authenticated') return;
      if (analysisRunActiveRef.current) return;
      const generation = ++fetchGenerationRef.current;
      void (async () => {
        try {
          const res = await getLatestAnalysis(selectedResumeId);
          if (generation !== fetchGenerationRef.current) return;
          applyLatestResponse(res);
        } catch {
          if (generation !== fetchGenerationRef.current) return;
          setResult(null);
          setLatestPayload(null);
          setStatus('idle');
        }
      })();
    };
    window.addEventListener('pageshow', onPageShow);
    return () => window.removeEventListener('pageshow', onPageShow);
  }, [selectedResumeId, sessionStatus, applyLatestResponse]);

  const runAnalysis = useCallback(async () => {
    if (!selectedResumeId || sessionStatus !== 'authenticated') {
      return;
    }

    analysisRunActiveRef.current = true;
    fetchGenerationRef.current += 1;
    const runGeneration = fetchGenerationRef.current;

    setStatus('loading');
    setResult(null);
    setLatestPayload(null);
    stopPolling();

    try {
      await runAnalysisApi(selectedResumeId, jobDescription);

      const pollResumeId = selectedResumeId;
      const tick = async (): Promise<boolean> => {
        if (pollInFlightRef.current) return false;
        if (runGeneration !== fetchGenerationRef.current) {
          analysisRunActiveRef.current = false;
          return true;
        }
        pollInFlightRef.current = true;
        try {
          const latest = await fetchLatest(pollResumeId, runGeneration, true);
          if (runGeneration !== fetchGenerationRef.current) return true;
          if (latest.state === 'done') {
            stopPolling();
            analysisRunActiveRef.current = false;
            notify.success(t('analysis.toast.done'));
            window.dispatchEvent(new CustomEvent('skill-refine:notifications-invalidate'));
            return true;
          }
          if (latest.state === 'failed') {
            stopPolling();
            analysisRunActiveRef.current = false;
            notify.error(t('analysis.toast.failed'));
            window.dispatchEvent(new CustomEvent('skill-refine:notifications-invalidate'));
            return true;
          }

          if (
            pollStartedAtRef.current &&
            Date.now() - pollStartedAtRef.current > MAX_POLL_DURATION_MS
          ) {
            stopPolling();
            analysisRunActiveRef.current = false;
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
            analysisRunActiveRef.current = false;
            setStatus('error');
            notify.error(t('analysis.toast.failed'));
            return true;
          }

          return false;
        } catch {
          stopPolling();
          analysisRunActiveRef.current = false;
          setStatus('error');
          notify.error(t('analysis.toast.failed'));
          return true;
        } finally {
          pollInFlightRef.current = false;
        }
      };

      pollStartedAtRef.current = Date.now();
      lastPendingUpdatedAtRef.current = null;
      stagnantPendingTicksRef.current = 0;
      const hasFinished = await tick();
      if (!hasFinished && !pollRef.current && runGeneration === fetchGenerationRef.current) {
        pollRef.current = setInterval(() => {
          void tick();
        }, POLL_INTERVAL_MS);
      }
    } catch {
      analysisRunActiveRef.current = false;
      setStatus('error');
      notify.error(t('analysis.toast.failed'));
    }
  }, [selectedResumeId, jobDescription, sessionStatus, fetchLatest, stopPolling, t]);

  const retry = useCallback(() => {
    analysisRunActiveRef.current = false;
    fetchGenerationRef.current += 1;
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
    jobDescription,
    setJobDescription,
    status,
    result,
    latestPayload,
    runAnalysis,
    retry,
    isAnalyzing,
    lastAnalysisAt: null,
  };
}
