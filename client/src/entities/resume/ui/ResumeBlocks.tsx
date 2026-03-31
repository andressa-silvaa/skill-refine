import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { ResumeData } from '../model/types';
import { formatMonthYear } from '../lib/format';

import './ResumeBlocks.css';

type HeaderVariant = 'default' | 'compact' | 'hero';
type ContactVariant = 'inline' | 'stacked';
type SectionVariant = 'default' | 'accent' | 'muted';

type HeaderProps = {
  data: ResumeData;
  variant?: HeaderVariant;
  align?: 'left' | 'center';
  showContact?: boolean;
};

export function ResumeHeader({ data, variant = 'default', align = 'left', showContact = true }: HeaderProps) {
  const { t } = useTranslation();
  const { contact } = data;

  return (
    <header className={`sr-resume-block__header sr-resume-block__header--${variant} sr-resume-block__header--${align}`}>
      <div className="sr-resume-block__header-main">
        <h1 className="sr-resume-block__name">{contact.fullName || t('resume.blockFullName')}</h1>
        <p className="sr-resume-block__position">{data.targetPosition || t('resume.blockPosition')}</p>
      </div>
      {showContact ? <ResumeContactList contact={contact} variant="inline" /> : null}
    </header>
  );
}

type ContactListProps = {
  contact: ResumeData['contact'];
  variant?: ContactVariant;
};

export function ResumeContactList({ contact, variant = 'inline' }: ContactListProps) {
  const items = [
    contact.email,
    contact.phone,
    contact.city && contact.country ? `${contact.city}, ${contact.country}` : '',
    contact.linkedin ? `LinkedIn: ${contact.linkedin}` : '',
    contact.github ? `GitHub: ${contact.github}` : '',
    contact.portfolio ? `Portfólio: ${contact.portfolio}` : '',
    contact.website ? `Website: ${contact.website}` : '',
  ].filter(Boolean);

  if (items.length === 0) return null;

  return (
    <div className={`sr-resume-block__contact sr-resume-block__contact--${variant}`}>
      {items.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

type SectionProps = {
  title: string;
  variant?: SectionVariant;
  children: ReactNode;
  allowBreak?: boolean;
};

export function ResumeSection({ title, variant = 'default', children, allowBreak = false }: SectionProps) {
  return (
    <section className={`sr-resume-block__section sr-resume-block__section--${variant}${allowBreak ? ' is-breakable' : ''}`}>
      <h2 className="sr-resume-block__section-title">{title}</h2>
      <div className="sr-resume-block__section-content">{children}</div>
    </section>
  );
}

export function ResumeSummary({ summary }: { summary: string }) {
  if (!summary) return null;
  return <p className="sr-resume-block__summary">{summary}</p>;
}

export function ResumeExperienceItem({ experience, variant = 'default' }: { experience: ResumeData['experiences'][0]; variant?: SectionVariant }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const dateRange = experience.isCurrent
    ? `${formatMonthYear(experience.startDate, locale)} - ${t('resume.dateCurrent')}`
    : experience.endDate
    ? `${formatMonthYear(experience.startDate, locale)} - ${formatMonthYear(experience.endDate, locale)}`
    : formatMonthYear(experience.startDate, locale);

  return (
    <div className={`sr-resume-block__item sr-resume-block__item--${variant}`}>
      <div className="sr-resume-block__item-header">
        <h3 className="sr-resume-block__item-title">{experience.position || t('resume.experienceStepPosition').replace(' *', '')}</h3>
        <span className="sr-resume-block__item-date">{dateRange}</span>
      </div>
      <p className="sr-resume-block__item-company">{experience.company || t('resume.blockCompany')}</p>
      {experience.description.length > 0 ? (
        <ul className="sr-resume-block__item-list">
          {experience.description.map((bullet, idx) => (
            <li key={idx}>{bullet}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ResumeEducationItem({ education, variant = 'default' }: { education: ResumeData['educations'][0]; variant?: SectionVariant }) {
  const { i18n } = useTranslation();
  const locale = i18n.language;
  const dateRange = education.status === 'completed' && education.endDate
    ? `${formatMonthYear(education.startDate, locale)} - ${formatMonthYear(education.endDate, locale)}`
    : education.status === 'in_progress'
    ? `${formatMonthYear(education.startDate, locale)} - Em andamento`
    : formatMonthYear(education.startDate, locale);

  return (
    <div className={`sr-resume-block__item sr-resume-block__item--${variant}`}>
      <div className="sr-resume-block__item-header">
        <h3 className="sr-resume-block__item-title">{education.course || 'Curso'}</h3>
        <span className="sr-resume-block__item-date">{dateRange}</span>
      </div>
      <p className="sr-resume-block__item-company">
        {education.institution || 'Instituição'} {education.degree ? `• ${education.degree}` : ''}
      </p>
    </div>
  );
}

export function ResumeLanguageItem({ language, variant = 'default' }: { language: ResumeData['languages'][0]; variant?: SectionVariant }) {
  const levelMap: Record<string, string> = {
    basic: 'Básico',
    intermediate: 'Intermediário',
    advanced: 'Avançado',
    fluent: 'Fluente',
    native: 'Nativo',
  };

  return (
    <div className={`sr-resume-block__item sr-resume-block__item--${variant}`}>
      <div className="sr-resume-block__item-header">
        <span className="sr-resume-block__item-title">{language.name}</span>
        <span className="sr-resume-block__item-date">{levelMap[language.level] || language.level}</span>
      </div>
    </div>
  );
}

export function ResumeSkillTags({ skills, variant = 'default' }: { skills: ResumeData['skills']; variant?: SectionVariant }) {
  if (!skills.length) return null;
  return (
    <div className={`sr-resume-block__skills sr-resume-block__skills--${variant}`}>
      {skills.map((skill) => (
        <span key={skill.id} className="sr-resume-block__skill-tag">
          {skill.name}
        </span>
      ))}
    </div>
  );
}
