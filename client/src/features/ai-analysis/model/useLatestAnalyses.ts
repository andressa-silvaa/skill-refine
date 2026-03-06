import { useEffect, useMemo, useRef, useState } from 'react';

import { useSession } from '@/entities/session';

import { getLatestAnalysesBatch } from '../api/analysisApi';
import type { AnalysisPayload } from '../api/analysisApi';

export type LatestAnalysisInfo = {
  status: AnalysisPayload['status'];
  score: number | null;
  updatedAt: string;
};

/**
 * Fetches latest analysis for each resume ID.
 * Returns a map of resumeId -> { status, score, updatedAt }.
 * Used to show "Analisando…" or "Score IA: X" on resume cards.
 */
export function useLatestAnalyses(resumeIds: string[]): Map<string, LatestAnalysisInfo> {
  const { status: sessionStatus } = useSession();
  const [map, setMap] = useState<Map<string, LatestAnalysisInfo>>(new Map());
  const cacheRef = useRef<Map<string, { at: number; map: Map<string, LatestAnalysisInfo> }>>(new Map());

  const ids = useMemo(() => resumeIds.slice(), [resumeIds]);

  useEffect(() => {
    if (sessionStatus !== 'authenticated' || ids.length === 0) {
      setMap(new Map());
      return;
    }

    const key = ids.join(',');
    const now = Date.now();
    const cached = cacheRef.current.get(key);
    if (cached && now - cached.at <= 15_000) {
      setMap(new Map(cached.map));
      return;
    }

    const fetchAll = async () => {
      try {
        const res = await getLatestAnalysesBatch(ids);
        const next = new Map<string, LatestAnalysisInfo>();
        Object.entries(res.items || {}).forEach(([id, item]) => {
          if (!item) return;
          next.set(id, {
            status: item.status,
            score: item.score,
            updatedAt: item.updatedAt,
          });
        });
        cacheRef.current.set(key, { at: now, map: new Map(next) });
        setMap(next);
      } catch {
        setMap(new Map());
      }
    };

    void fetchAll();
  }, [sessionStatus, ids]);

  return map;
}
