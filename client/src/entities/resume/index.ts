export type { Resume, ResumeStatus, ResumeData, ResumeThemeId, Contact, Experience, Education, EducationStatus, Skill, SkillLevel, Language, LanguageLevel } from './model/types';
export type { ResumeTheme, ResumeThemeLayout, ResumeThemeStyleTokens, ResumeSectionId, ResumeThemeThumbnailSpec, ResumeThemePalette } from './model/theme';
export { resumesMock } from './mocks/resumes';
export { resumeThemes, getResumeThemeById, getResumeThemePalette, DEFAULT_RESUME_THEME_ID } from './config/themes';
export {
  calculateCompletenessScore,
  formatDatePt,
  formatScore,
  getResumeStatusLabel,
  getResumeStatusTone,
  getTopSkills,
} from './lib/format';
export { toResumeViewModel } from './lib/viewModel';
export type { ResumeViewModel } from './lib/viewModel';

export { stressResumeData } from './mocks/stressResume';

export {
  ResumeHeader,
  ResumeContactList,
  ResumeSection,
  ResumeSummary,
  ResumeExperienceItem,
  ResumeEducationItem,
  ResumeLanguageItem,
  ResumeSkillTags,
} from './ui';
