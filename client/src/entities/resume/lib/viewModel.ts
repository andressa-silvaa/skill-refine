import { VERSION_CHANGE_SUMMARY_KEYS } from '@/shared/constants/versionChangeSummaryKeys';

import type { Resume } from '../model/types';
import type { TFunction } from './format';
import {
  formatDatePt,
  formatScore,
  getResumeStatusLabel,
  getResumeStatusTone,
  getTopSkills,
  isJunkResumeChipLabel,
} from './format';

function normalizeResumeSkillTags(skills: unknown, tags: unknown): string[] {
  const primary = Array.isArray(skills) && skills.length > 0 ? skills : tags;
  if (!Array.isArray(primary)) return [];
  const out: string[] = [];
  for (const item of primary) {
    if (typeof item !== 'string') continue;
    const s = item.trim();
    if (!s || VERSION_CHANGE_SUMMARY_KEYS.has(s) || isJunkResumeChipLabel(s)) continue;
    out.push(s);
  }
  return out;
}

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
  const skillsSource = normalizeResumeSkillTags(resume.skills, resume.tags);
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
