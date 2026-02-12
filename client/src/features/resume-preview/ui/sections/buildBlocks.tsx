import type { ReactNode } from 'react';

import type { ResumeData } from '@/entities/resume';
import type { ResumeSectionId, ResumeTheme } from '@/entities/resume';
import {
  ResumeContactList,
  ResumeEducationItem,
  ResumeExperienceItem,
  ResumeHeader,
  ResumeLanguageItem,
  ResumeSection,
  ResumeSkillTags,
  ResumeSummary,
} from '@/entities/resume';

import type { ThemeBlock } from '../types';

export const sectionTitles: Record<ResumeSectionId, string> = {
  summary: 'Resumo',
  experience: 'Experiência Profissional',
  education: 'Formação Acadêmica',
  skills: 'Habilidades',
  languages: 'Idiomas',
  contact: 'Contato',
};

export const sectionBlocks: Record<ResumeSectionId, (data: ResumeData) => ReactNode> = {
  summary: (data) => <ResumeSummary summary={data.summary} />,
  experience: (data) => data.experiences.map((exp) => <ResumeExperienceItem key={exp.id} experience={exp} />),
  education: (data) => data.educations.map((edu) => <ResumeEducationItem key={edu.id} education={edu} />),
  skills: (data) => <ResumeSkillTags skills={data.skills} />,
  languages: (data) => data.languages.map((lang) => <ResumeLanguageItem key={lang.id} language={lang} />),
  contact: (data) => <ResumeContactList contact={data.contact} variant="stacked" />,
};

export const hasContent: Record<ResumeSectionId, (data: ResumeData) => boolean> = {
  summary: (data) => Boolean(data.summary?.trim()),
  experience: (data) => data.experiences.length > 0,
  education: (data) => data.educations.length > 0,
  skills: (data) => data.skills.length > 0,
  languages: (data) => data.languages.length > 0,
  contact: (data) =>
    Boolean(
      data.contact.email ||
        data.contact.phone ||
        data.contact.city ||
        data.contact.country ||
        data.contact.linkedin ||
        data.contact.github ||
        data.contact.portfolio ||
        data.contact.website
    ),
};

export function renderSection(
  id: ResumeSectionId,
  data: ResumeData,
  variant?: 'default' | 'accent' | 'muted',
  visibilityRules?: ResumeTheme['visibilityRules'],
  options?: { breakable?: boolean }
): ThemeBlock | null {
  const shouldHideIfEmpty =
    visibilityRules?.[id] !== undefined ? visibilityRules[id] === 'hideIfEmpty' : true;
  if (shouldHideIfEmpty && !hasContent[id](data)) return null;
  return {
    key: `section-${id}`,
    kind: 'section',
    breakable: options?.breakable,
    node: (
      <ResumeSection title={sectionTitles[id]} variant={variant} allowBreak={options?.breakable}>
        {sectionBlocks[id](data)}
      </ResumeSection>
    ),
  };
}

export function buildSections(
  data: ResumeData,
  ids: ResumeSectionId[],
  variant?: 'default' | 'accent' | 'muted',
  visibilityRules?: ResumeTheme['visibilityRules']
): ThemeBlock[] {
  return ids
    .map((id) => renderSection(id, data, variant, visibilityRules))
    .filter((block): block is ThemeBlock => Boolean(block));
}

export function createHeaderBlock(
  data: ResumeData,
  variant: 'default' | 'compact' | 'hero',
  align: 'left' | 'center',
  showContact: boolean
): ThemeBlock {
  return {
    key: 'header',
    kind: 'header',
    node: <ResumeHeader data={data} variant={variant} align={align} showContact={showContact} />,
  };
}

export function createTimelineBlock(data: ResumeData): ThemeBlock | null {
  if (!hasContent.experience(data)) return null;
  return {
    key: 'timeline',
    kind: 'section',
    breakable: true,
    node: (
      <section className="sr-resume-theme__timeline">
        <h2 className="sr-resume-theme__timeline-title">{sectionTitles.experience}</h2>
        <div className="sr-resume-theme__timeline-items">
          {data.experiences.map((exp) => (
            <div key={exp.id} className="sr-resume-theme__timeline-item">
              <ResumeExperienceItem experience={exp} />
            </div>
          ))}
        </div>
      </section>
    ),
  };
}

export function createPortfolioBlock(data: ResumeData): ThemeBlock | null {
  if (!hasContent.experience(data)) return null;
  return {
    key: 'portfolio',
    kind: 'section',
    breakable: true,
    node: (
      <section className="sr-resume-theme__portfolio-grid">
        <h2 className="sr-resume-theme__portfolio-title">{sectionTitles.experience}</h2>
        <div className="sr-resume-theme__portfolio-items">
          {data.experiences.map((exp) => (
            <div key={exp.id} className="sr-resume-theme__portfolio-card">
              <ResumeExperienceItem experience={exp} />
            </div>
          ))}
        </div>
      </section>
    ),
  };
}
