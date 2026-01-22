import { Button, Input, CustomSelect, DatePicker } from '@/shared/ui';
import type { Education, EducationStatus } from '@/entities/resume';

import './EducationStep.css';

type Props = {
  educations: Education[];
  onChange: (educations: Education[]) => void;
};

const STATUS_OPTIONS = [
  { value: 'completed', label: 'Concluído' },
  { value: 'in_progress', label: 'Em andamento' },
];

export function EducationStep(props: Props) {
  const { educations, onChange } = props;

  const addEducation = () => {
    const newEdu: Education = {
      id: `edu-${Date.now()}`,
      institution: '',
      course: '',
      degree: '',
      startDate: '',
      status: 'completed',
    };
    onChange([...educations, newEdu]);
  };

  const removeEducation = (id: string) => {
    onChange(educations.filter((e) => e.id !== id));
  };

  const updateEducation = (id: string, updates: Partial<Education>) => {
    onChange(educations.map((e) => (e.id === id ? { ...e, ...updates } : e)));
  };

  return (
    <div className="sr-education-step">
      <div className="sr-education-step__header">
        <h3 className="sr-education-step__title">Formação acadêmica</h3>
        <p className="sr-education-step__subtitle">Adicione sua formação e cursos</p>
      </div>

      <div className="sr-education-step__list">
        {educations.map((edu) => (
          <EducationCard key={edu.id} education={edu} onUpdate={(updates) => updateEducation(edu.id, updates)} onRemove={() => removeEducation(edu.id)} />
        ))}
      </div>

      <Button variant="secondary" onClick={addEducation}>
        <i className="fa-solid fa-plus" aria-hidden />
        Adicionar formação
      </Button>
    </div>
  );
}

type EducationCardProps = {
  education: Education;
  onUpdate: (updates: Partial<Education>) => void;
  onRemove: () => void;
};

function EducationCard(props: EducationCardProps) {
  const { education, onUpdate, onRemove } = props;

  return (
    <div className="sr-education-card">
      <div className="sr-education-card__header">
        <h4 className="sr-education-card__title">Formação</h4>
        <Button variant="ghost" onClick={onRemove}>
          <i className="fa-solid fa-trash" aria-hidden />
        </Button>
      </div>

      <div className="sr-education-card__fields">
        <Input
          label="Instituição"
          placeholder="Nome da instituição"
          value={education.institution}
          onChange={(e) => onUpdate({ institution: e.target.value })}
        />
        <Input
          label="Curso"
          placeholder="Nome do curso"
          value={education.course}
          onChange={(e) => onUpdate({ course: e.target.value })}
        />
        <Input
          label="Grau"
          placeholder="Ex.: Bacharelado, Mestrado, Doutorado"
          value={education.degree}
          onChange={(e) => onUpdate({ degree: e.target.value })}
        />
        <div className="sr-education-card__row">
          <DatePicker
            label="Data início"
            value={education.startDate}
            onChange={(value) => onUpdate({ startDate: value })}
          />
          {education.status === 'completed' ? (
            <DatePicker
              label="Data conclusão"
              value={education.endDate || ''}
              onChange={(value) => onUpdate({ endDate: value })}
            />
          ) : null}
        </div>
        <CustomSelect
          label="Status"
          options={STATUS_OPTIONS}
          value={education.status}
          onChange={(value) => onUpdate({ status: value as EducationStatus, endDate: value === 'in_progress' ? undefined : education.endDate })}
        />
      </div>
    </div>
  );
}
