import { useEffect, useMemo, useState } from 'react';

import { useSession } from '@/entities/session';

import { getLatestAnalysis } from '../api/analysisApi';
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

  const ids = useMemo(() => resumeIds.slice(), [resumeIds]);

  useEffect(() => {
    if (sessionStatus !== 'authenticated' || ids.length === 0) {
      setMap(new Map());
      return;
    }

    const fetchAll = async () => {
      const results = await Promise.all(
        ids.map(async (id) => {
          try {
            const res = await getLatestAnalysis(id);
            if (!res.item) return { id, info: null };
            return {
              id,
              info: {
                status: res.item.status,
                score: res.item.score,
                updatedAt: res.item.updatedAt,
              } as LatestAnalysisInfo,
            };
          } catch {
            return { id, info: null };
          }
        })
      );

      const next = new Map<string, LatestAnalysisInfo>();
      for (const { id, info } of results) {
        if (info) next.set(id, info);
      }
      setMap(next);
    };

    void fetchAll();
  }, [sessionStatus, ids]);

  return map;
}
