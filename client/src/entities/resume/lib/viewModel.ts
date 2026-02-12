import type { Resume } from '../model/types';
import type { TFunction } from './format';
import {
  formatDatePt,
  formatScore,
  getResumeStatusLabel,
  getResumeStatusTone,
  getTopSkills,
} from './format';

const DEFAULT_MAX_SKILLS = 3;

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

export function toResumeViewModel(
  resume: Resume,
  options?: { maxTags?: number; maxSkills?: number; t?: TFunction }
): ResumeViewModel {
  const maxSkills = options?.maxSkills ?? DEFAULT_MAX_SKILLS;
  const t = options?.t ?? ((key: string) => key);
  const skillsSource = (resume.skills?.length ? resume.skills : resume.tags ?? []).filter(Boolean);
  const { visible: tagsVisible, overflow: tagsOverflow } = getTopSkills(skillsSource, maxSkills);
  const dateStr = formatDatePt(resume.updatedAt);

  return {
    id: resume.id,
    name: resume.name,
    updatedAtLabel: t('resume.updatedAt', { date: dateStr }),
    statusLabel: getResumeStatusLabel(resume.status, t),
    statusTone: getResumeStatusTone(resume.status),
    scoreValue: resume.score ?? 0,
    scoreLabel: formatScore(resume.score),
    tagsVisible,
    tagsOverflow,
  };
}
