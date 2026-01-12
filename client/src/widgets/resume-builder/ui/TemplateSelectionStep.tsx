import { Card } from '@/shared/ui';
import { resumeTemplates, type ResumeTemplate } from '@/entities/resume';
import type { ResumeTemplateId } from '@/entities/resume';

import './TemplateSelectionStep.css';

type Props = {
  selectedId: ResumeTemplateId;
  onSelect: (id: ResumeTemplateId) => void;
};

export function TemplateSelectionStep(props: Props) {
  const { selectedId, onSelect } = props;

  return (
    <div className="sr-template-selection">
      <div className="sr-template-selection__header">
        <h3 className="sr-template-selection__title">Selecione seu modelo</h3>
        <p className="sr-template-selection__subtitle">Escolha um modelo que melhor represente seu perfil profissional</p>
      </div>

      <div className="sr-template-selection__grid" role="list">
        {resumeTemplates.map((template) => (
          <TemplateCard key={template.id} template={template} isSelected={selectedId === template.id} onSelect={() => onSelect(template.id)} />
        ))}
      </div>
    </div>
  );
}

type TemplateCardProps = {
  template: ResumeTemplate;
  isSelected: boolean;
  onSelect: () => void;
};

function TemplateCard(props: TemplateCardProps) {
  const { template, isSelected, onSelect } = props;

  const getTemplateIcon = (id: string) => {
    const icons: Record<string, string> = {
      tech: 'fa-solid fa-code',
      business: 'fa-solid fa-chart-line',
      design: 'fa-solid fa-palette',
      marketing: 'fa-solid fa-bullhorn',
      general: 'fa-solid fa-file-lines',
      executive: 'fa-solid fa-briefcase',
      creative: 'fa-solid fa-paintbrush',
      academic: 'fa-solid fa-graduation-cap',
      sales: 'fa-solid fa-handshake',
      healthcare: 'fa-solid fa-heart-pulse',
      finance: 'fa-solid fa-dollar-sign',
      education: 'fa-solid fa-chalkboard-user',
    };
    return icons[id] || 'fa-solid fa-file';
  };

  return (
    <Card className={`sr-template-card${isSelected ? ' is-selected' : ''}`} role="listitem" onClick={onSelect}>
      <div className="sr-template-card__preview" aria-hidden>
        <i className={getTemplateIcon(template.id)} />
      </div>
      <div className="sr-template-card__body">
        <div className="sr-template-card__header">
          <h4 className="sr-template-card__title">{template.name}</h4>
          {template.recommended ? (
            <span className="sr-template-card__badge" aria-label="Recomendado">
              Recomendado
            </span>
          ) : null}
        </div>
        <p className="sr-template-card__description">{template.description}</p>
        <div className="sr-template-card__tags">
          {template.tags.map((tag) => (
            <span key={tag} className="sr-template-card__tag">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}
