import type { ResumeData } from '@/entities/resume';

import './ResumePreviewContent.css';

type Props = {
  data: ResumeData;
};

export function ResumePreviewContent(props: Props) {
  const { data } = props;

  return (
    <div className="sr-resume-preview">
      <div className="sr-resume-preview__paper">
        <ResumeHeader data={data} />
        {data.experiences.length > 0 ? (
          <>
            <ResumeSection title="Experiência Profissional" />
            {data.experiences.map((exp) => (
              <ExperienceItem key={exp.id} experience={exp} />
            ))}
          </>
        ) : null}
        {data.educations.length > 0 ? (
          <>
            <ResumeSection title="Formação Acadêmica" />
            {data.educations.map((edu) => (
              <EducationItem key={edu.id} education={edu} />
            ))}
          </>
        ) : null}
        {data.skills.length > 0 ? (
          <>
            <ResumeSection title="Habilidades" />
            <div className="sr-resume-preview__skills">
              {data.skills.map((skill) => (
                <span key={skill.id} className="sr-resume-preview__skill-tag">
                  {skill.name}
                </span>
              ))}
            </div>
          </>
        ) : null}
        {data.languages.length > 0 ? (
          <>
            <ResumeSection title="Idiomas" />
            {data.languages.map((lang) => (
              <LanguageItem key={lang.id} language={lang} />
            ))}
          </>
        ) : null}
      </div>
    </div>
  );
}

function ResumeHeader(props: { data: ResumeData }) {
  const { data } = props;
  const { contact } = data;

  return (
    <header className="sr-resume-preview__header">
      <h1 className="sr-resume-preview__name">{contact.fullName || 'Nome completo'}</h1>
      <p className="sr-resume-preview__position">{data.targetPosition || 'Cargo alvo'}</p>
      <div className="sr-resume-preview__contact">
        {contact.email ? <span>{contact.email}</span> : null}
        {contact.phone ? <span>{contact.phone}</span> : null}
        {contact.city && contact.country ? <span>{contact.city}, {contact.country}</span> : null}
        {contact.linkedin ? <span>LinkedIn: {contact.linkedin}</span> : null}
        {contact.github ? <span>GitHub: {contact.github}</span> : null}
        {contact.portfolio ? <span>Portfólio: {contact.portfolio}</span> : null}
      </div>
    </header>
  );
}

function ResumeSection(props: { title: string }) {
  return <h2 className="sr-resume-preview__section-title">{props.title}</h2>;
}

function ExperienceItem(props: { experience: ResumeData['experiences'][0] }) {
  const { experience } = props;
  const dateRange = experience.isCurrent
    ? `${formatDate(experience.startDate)} - Atual`
    : experience.endDate
    ? `${formatDate(experience.startDate)} - ${formatDate(experience.endDate)}`
    : formatDate(experience.startDate);

  return (
    <div className="sr-resume-preview__item">
      <div className="sr-resume-preview__item-header">
        <h3 className="sr-resume-preview__item-title">{experience.position || 'Cargo'}</h3>
        <span className="sr-resume-preview__item-date">{dateRange}</span>
      </div>
      <p className="sr-resume-preview__item-company">{experience.company || 'Empresa'}</p>
      {experience.description.length > 0 ? (
        <ul className="sr-resume-preview__item-list">
          {experience.description.map((bullet, idx) => (
            <li key={idx}>{bullet}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function EducationItem(props: { education: ResumeData['educations'][0] }) {
  const { education } = props;
  const dateRange = education.status === 'completed' && education.endDate
    ? `${formatDate(education.startDate)} - ${formatDate(education.endDate)}`
    : education.status === 'in_progress'
    ? `${formatDate(education.startDate)} - Em andamento`
    : formatDate(education.startDate);

  return (
    <div className="sr-resume-preview__item">
      <div className="sr-resume-preview__item-header">
        <h3 className="sr-resume-preview__item-title">{education.course || 'Curso'}</h3>
        <span className="sr-resume-preview__item-date">{dateRange}</span>
      </div>
      <p className="sr-resume-preview__item-company">
        {education.institution || 'Instituição'} {education.degree ? `• ${education.degree}` : ''}
      </p>
    </div>
  );
}

function LanguageItem(props: { language: ResumeData['languages'][0] }) {
  const levelMap: Record<string, string> = {
    basic: 'Básico',
    intermediate: 'Intermediário',
    advanced: 'Avançado',
    fluent: 'Fluente',
    native: 'Nativo',
  };

  return (
    <div className="sr-resume-preview__item">
      <div className="sr-resume-preview__item-header">
        <span className="sr-resume-preview__item-title">{props.language.name}</span>
        <span className="sr-resume-preview__item-date">{levelMap[props.language.level] || props.language.level}</span>
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const [year, month] = dateStr.split('-');
  if (!year || !month) return dateStr;
  const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  const monthIndex = parseInt(month, 10) - 1;
  if (monthIndex < 0 || monthIndex >= monthNames.length) return dateStr;
  return `${monthNames[monthIndex]} ${year}`;
}
