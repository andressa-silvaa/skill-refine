import type { ReactElement, ReactNode } from 'react';

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
} from '@/entities/resume/ui';

type Props = {
  data: ResumeData;
  theme: ResumeTheme;
};

export type ThemeBlock = {
  key: string;
  node: ReactNode;
  kind?: 'header' | 'section';
  breakable?: boolean;
};

export type ThemeLayoutData =
  | {
      type: 'single';
      blocks: ThemeBlock[];
      variant?: string;
    }
  | {
      type: 'two-column';
      main: ThemeBlock[];
      sidebar: ThemeBlock[];
      variant: 'split' | 'tech' | 'compact';
      headerPlacement?: 'full';
    };

const sectionTitles: Record<ResumeSectionId, string> = {
  summary: 'Resumo',
  experience: 'Experiência Profissional',
  education: 'Formação Acadêmica',
  skills: 'Habilidades',
  languages: 'Idiomas',
  contact: 'Contato',
};

const sectionBlocks: Record<ResumeSectionId, (data: ResumeData) => ReactNode> = {
  summary: (data) => <ResumeSummary summary={data.summary} />,
  experience: (data) => data.experiences.map((exp) => <ResumeExperienceItem key={exp.id} experience={exp} />),
  education: (data) => data.educations.map((edu) => <ResumeEducationItem key={edu.id} education={edu} />),
  skills: (data) => <ResumeSkillTags skills={data.skills} />,
  languages: (data) => data.languages.map((lang) => <ResumeLanguageItem key={lang.id} language={lang} />),
  contact: (data) => <ResumeContactList contact={data.contact} variant="stacked" />,
};

const hasContent: Record<ResumeSectionId, (data: ResumeData) => boolean> = {
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

const renderSection = (
  id: ResumeSectionId,
  data: ResumeData,
  variant?: 'default' | 'accent' | 'muted',
  visibilityRules?: ResumeTheme['visibilityRules'],
  options?: { breakable?: boolean }
): ThemeBlock | null => {
  const shouldHideIfEmpty =
    visibilityRules?.[id] !== undefined ? visibilityRules[id] === 'hideIfEmpty' : true;
  if (shouldHideIfEmpty && !hasContent[id](data)) return null;
  return (
    {
      key: `section-${id}`,
      kind: 'section',
      breakable: options?.breakable,
      node: (
        <ResumeSection title={sectionTitles[id]} variant={variant} allowBreak={options?.breakable}>
          {sectionBlocks[id](data)}
        </ResumeSection>
      ),
    }
  );
};

const buildSections = (
  data: ResumeData,
  ids: ResumeSectionId[],
  variant?: 'default' | 'accent' | 'muted',
  visibilityRules?: ResumeTheme['visibilityRules']
): ThemeBlock[] =>
  ids
    .map((id) => renderSection(id, data, variant, visibilityRules))
    .filter((block): block is ThemeBlock => Boolean(block));

const createHeaderBlock = (data: ResumeData, variant: 'default' | 'compact' | 'hero', align: 'left' | 'center', showContact: boolean): ThemeBlock => ({
  key: 'header',
  kind: 'header',
  node: <ResumeHeader data={data} variant={variant} align={align} showContact={showContact} />,
});

const createTimelineBlock = (data: ResumeData): ThemeBlock | null => {
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
};

const createPortfolioBlock = (data: ResumeData): ThemeBlock | null => {
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
};

export function getThemeLayoutData(theme: ResumeTheme, data: ResumeData): ThemeLayoutData {
  switch (theme.id) {
    case 'two-column-sidebar':
      return {
        type: 'two-column',
        variant: 'split',
        main: [createHeaderBlock(data, 'default', 'left', false), ...buildSections(data, theme.layout.type === 'split' ? theme.layout.mainSections : theme.sectionOrder, undefined, theme.visibilityRules)],
        sidebar: buildSections(data, theme.layout.type === 'split' ? theme.layout.sidebarSections : [], undefined, theme.visibilityRules),
      };
    case 'tech-stack':
      return {
        type: 'two-column',
        variant: 'tech',
        main: buildSections(data, theme.layout.type === 'split' ? theme.layout.mainSections : theme.sectionOrder, undefined, theme.visibilityRules),
        sidebar: [createHeaderBlock(data, 'compact', 'left', false), ...buildSections(data, theme.layout.type === 'split' ? theme.layout.sidebarSections : [], undefined, theme.visibilityRules)],
      };
    case 'compact-dense':
      return {
        type: 'two-column',
        variant: 'compact',
        headerPlacement: 'full',
        main: [
          createHeaderBlock(data, 'compact', 'left', true),
          ...buildSections(data, ['summary', 'experience', 'education'], undefined, theme.visibilityRules),
        ],
        sidebar: buildSections(data, ['skills', 'languages', 'contact'], 'accent', theme.visibilityRules),
      };
    case 'timeline-experience': {
      const blocks = [
        createHeaderBlock(data, 'default', 'left', false),
        renderSection('summary', data, undefined, theme.visibilityRules),
        createTimelineBlock(data),
        ...buildSections(data, ['education', 'skills', 'languages', 'contact'], undefined, theme.visibilityRules),
      ].filter((block): block is ThemeBlock => Boolean(block));
      return { type: 'single', blocks, variant: 'timeline' };
    }
    case 'project-first': {
      const blocks = [
        createHeaderBlock(data, 'default', 'left', false),
        renderSection('summary', data, undefined, theme.visibilityRules),
        createPortfolioBlock(data),
        ...buildSections(data, ['skills', 'education', 'languages', 'contact'], undefined, theme.visibilityRules),
      ].filter((block): block is ThemeBlock => Boolean(block));
      return { type: 'single', blocks, variant: 'portfolio' };
    }
    case 'academic':
      return {
        type: 'single',
        variant: 'academic',
        blocks: [createHeaderBlock(data, 'hero', 'left', true), ...buildSections(data, theme.sectionOrder, 'accent', theme.visibilityRules)],
      };
    case 'classic-one-column':
    case 'modern-one-column':
    case 'hybrid-balanced':
      return {
        type: 'single',
        variant: 'single',
        blocks: [createHeaderBlock(data, 'default', 'left', true), ...buildSections(data, theme.sectionOrder, undefined, theme.visibilityRules)],
      };
    case 'executive':
      return {
        type: 'single',
        variant: 'executive',
        blocks: [createHeaderBlock(data, 'hero', 'left', true), ...buildSections(data, theme.sectionOrder, 'accent', theme.visibilityRules)],
      };
    case 'elegant-serif':
      return {
        type: 'single',
        variant: 'elegant',
        blocks: [createHeaderBlock(data, 'hero', 'center', true), ...buildSections(data, theme.sectionOrder, undefined, theme.visibilityRules)],
      };
    case 'minimal-clean':
    default:
      return {
        type: 'single',
        variant: 'single',
        blocks: [createHeaderBlock(data, 'default', 'left', true), ...buildSections(data, theme.sectionOrder, undefined, theme.visibilityRules)],
      };
  }
}

type ThemePageProps = {
  layout: ThemeLayoutData;
  mainBlocks: ThemeBlock[];
  sidebarBlocks?: ThemeBlock[];
};

export function ThemePageLayout({ layout, mainBlocks, sidebarBlocks }: ThemePageProps) {
  if (layout.type === 'two-column') {
    const headerBlocks =
      layout.headerPlacement === 'full' ? mainBlocks.filter((block) => block.kind === 'header') : [];
    const mainContent = layout.headerPlacement === 'full' ? mainBlocks.filter((block) => block.kind !== 'header') : mainBlocks;

    return (
      <div className={`sr-resume-theme__layout sr-resume-theme__layout--${layout.variant}`}>
        {headerBlocks.length ? (
          <div className="sr-resume-theme__header-blocks">
            {headerBlocks.map((block) => (
              <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
                {block.node}
              </div>
            ))}
          </div>
        ) : null}
        <div className="sr-resume-theme__columns">
          <div className="sr-resume-theme__column sr-resume-theme__main">
            {mainContent.map((block) => (
              <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
                {block.node}
              </div>
            ))}
          </div>
          <aside className="sr-resume-theme__column sr-resume-theme__sidebar">
            {(sidebarBlocks ?? []).map((block) => (
              <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
                {block.node}
              </div>
            ))}
          </aside>
        </div>
      </div>
    );
  }

  return (
    <div className={`sr-resume-theme__layout sr-resume-theme__layout--${layout.variant ?? 'single'}`}>
      {mainBlocks.map((block) => (
        <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
          {block.node}
        </div>
      ))}
    </div>
  );
}
