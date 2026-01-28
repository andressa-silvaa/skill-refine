import { Badge, Button } from '@/shared/ui';
import type { ResumeData } from '@/entities/resume';

import './ReviewStep.css';

type Props = {
  data: ResumeData;
  onEdit: (step: string) => void;
};

export function ReviewStep(props: Props) {
  const { data, onEdit } = props;

  const calculateScore = (): number => {
    let score = 0;
    if (data.targetPosition) score += 10;
    if (data.contact.fullName && data.contact.email) score += 15;
    if (data.experiences.length > 0) score += 20;
    if (data.educations.length > 0) score += 10;
    if (data.skills.length > 0) score += 15;
    if (data.languages.length > 0) score += 5;
    if (data.summary) score += 15;
    if (data.experiences.length >= 2) score += 10;
    return Math.min(100, score);
  };

  const score = calculateScore();

  const sections = [
    { id: 'basic', label: 'Informações básicas', complete: Boolean(data.targetPosition) },
    { id: 'contact', label: 'Contato', complete: Boolean(data.contact.fullName && data.contact.email) },
    { id: 'experience', label: 'Experiência', complete: data.experiences.length > 0 },
    { id: 'education', label: 'Formação', complete: data.educations.length > 0 },
    { id: 'skills', label: 'Habilidades', complete: data.skills.length > 0 },
    { id: 'languages', label: 'Idiomas', complete: data.languages.length > 0 },
    { id: 'summary', label: 'Resumo', complete: Boolean(data.summary) },
  ];

  return (
    <div className="sr-review-step">
      <div className="sr-review-step__header">
        <h3 className="sr-review-step__title">Revisão final</h3>
        <p className="sr-review-step__subtitle">Revise seu currículo antes de finalizar</p>
      </div>

      <div className="sr-review-step__score">
        <div className="sr-review-step__score-circle">
          <span className="sr-review-step__score-value">{score}</span>
          <span className="sr-review-step__score-total">/100</span>
        </div>
        <p className="sr-review-step__score-label">Score de completude</p>
      </div>

      <div className="sr-review-step__sections">
        {sections.map((section) => (
          <div key={section.id} className={`sr-review-step__section${section.complete ? ' is-complete' : ''}`}>
            <div className="sr-review-step__section-header">
              {section.complete ? (
                <i className="fa-solid fa-check-circle" aria-hidden />
              ) : (
                <i className="fa-regular fa-circle" aria-hidden />
              )}
              <span className="sr-review-step__section-label">{section.label}</span>
            </div>
            <Button variant="ghost" onClick={() => onEdit(section.id)}>
              Editar
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
