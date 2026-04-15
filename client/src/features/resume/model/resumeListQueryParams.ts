import type { ResumeListParams } from '../api/resumeApi';
import type { ResumeScoreFilter, ResumeUpdatedFilter } from './types';

export function scoreFilterToRange(score: ResumeScoreFilter): Partial<ResumeListParams> {
  if (score === 'none') return { include_no_score: true };
  if (score === '0-50') return { score_min: 0, score_max: 50 };
  if (score === '51-70') return { score_min: 51, score_max: 70 };
  if (score === '71-85') return { score_min: 71, score_max: 85 };
  if (score === '86-100') return { score_min: 86, score_max: 100 };
  return {};
}

export function updatedFilterToRange(
  updated: ResumeUpdatedFilter,
  now: Date = new Date()
): Partial<ResumeListParams> {
  if (updated === 'all') return {};
  const days = updated === '7d' ? 7 : 30;
  const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  const iso = from.toISOString().slice(0, 10);
  return { updated_from: iso };
}
