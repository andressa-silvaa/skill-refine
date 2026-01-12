import type { Resume } from '../model/types';
import { formatDatePt, getResumeStatusLabel, getResumeStatusTone } from './format';

export type ResumeViewModel = {
  id: string;
  name: string;
  updatedAtLabel: string;
  statusLabel: string;
  statusTone: 'neutral' | 'success' | 'warning';
  scoreLabel: string;
  scoreValue: number;
  tagsVisible: string[];
  tagsOverflow: number;
};

export function toResumeViewModel(resume: Resume, options?: { maxTags?: number }): ResumeViewModel {
  const maxTags = options?.maxTags ?? 3;
  const tagsVisible = resume.tags.slice(0, maxTags);
  const tagsOverflow = Math.max(0, resume.tags.length - tagsVisible.length);

  return {
    id: resume.id,
    name: resume.name,
    updatedAtLabel: `Atualizado em ${formatDatePt(resume.updatedAt)}`,
    statusLabel: getResumeStatusLabel(resume.status),
    statusTone: getResumeStatusTone(resume.status),
    scoreValue: resume.score,
    scoreLabel: resume.score > 0 ? `${resume.score}/100` : '—',
    tagsVisible,
    tagsOverflow,
  };
}
