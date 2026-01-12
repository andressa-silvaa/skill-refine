export type ResumeStatus = 'draft' | 'complete' | 'analyzing';
export type ResumeTemplateId = 'tech' | 'business' | 'design' | 'marketing' | 'general' | 'executive' | 'creative' | 'academic' | 'sales' | 'healthcare' | 'finance' | 'education';
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
  startDate: string; // YYYY-MM
  endDate?: string; // YYYY-MM
  isCurrent: boolean;
  description: string[]; // bullet points
};

export type Education = {
  id: string;
  institution: string;
  course: string;
  degree: string;
  startDate: string; // YYYY-MM
  endDate?: string; // YYYY-MM
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
  templateId: ResumeTemplateId;
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
  updatedAt: string; // ISO
  status: ResumeStatus;
  score: number;
  tags: string[];
  data?: ResumeData;
};
