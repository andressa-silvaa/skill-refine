export type ResumeStatus = 'draft' | 'complete' | 'analyzing';
export type ResumeThemeId =
  | 'classic-one-column'
  | 'modern-one-column'
  | 'two-column-sidebar'
  | 'executive'
  | 'compact-dense'
  | 'timeline-experience'
  | 'project-first'
  | 'academic'
  | 'minimal-clean'
  | 'elegant-serif'
  | 'tech-stack'
  | 'hybrid-balanced';
export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type LanguageLevel = 'basic' | 'intermediate' | 'advanced' | 'fluent' | 'native';
export type EducationStatus = 'completed' | 'in_progress';

export type Contact = {
  fullName: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  linkedin?: string;
  portfolio?: string;
  github?: string;
  website?: string;
};

export type Experience = {
  id: string;
  company: string;
  position: string;
  startDate: string;
  endDate?: string;
  isCurrent: boolean;
  description: string[];
};

export type Education = {
  id: string;
  institution: string;
  course: string;
  degree: string;
  startDate: string;
  endDate?: string;
  status: EducationStatus;
};

export type Skill = {
  id: string;
  name: string;
  level?: SkillLevel;
};

export type Language = {
  id: string;
  name: string;
  level: LanguageLevel;
};

export type ResumeData = {
  themeId: ResumeThemeId;
  themePaletteId?: string;
  themeAccentOverride?: string;
  themeSecondaryOverride?: string;
  targetPosition: string;
  contact: Contact;
  experiences: Experience[];
  educations: Education[];
  skills: Skill[];
  languages: Language[];
  summary: string;
};

export type Resume = {
  id: string;
  name: string;
  updatedAt: string;
  status: ResumeStatus;
  score: number;
  tags: string[];
  data?: ResumeData;
};
