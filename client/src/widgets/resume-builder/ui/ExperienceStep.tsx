import { useState } from 'react';

import { Button, Input, Textarea, DatePicker } from '@/shared/ui';
import type { Experience } from '@/entities/resume';

import './ExperienceStep.css';

type Props = {
  experiences: Experience[];
  onChange: (experiences: Experience[]) => void;
};

export function ExperienceStep(props: Props) {
  const { experiences, onChange } = props;

  const addExperience = () => {
    const newExp: Experience = {
      id: `exp-${Date.now()}`,
      company: '',
      position: '',
      startDate: '',
      isCurrent: false,
      description: [],
    };
    onChange([...experiences, newExp]);
  };

  const removeExperience = (id: string) => {
    onChange(experiences.filter((e) => e.id !== id));
  };

  const updateExperience = (id: string, updates: Partial<Experience>) => {
    onChange(experiences.map((e) => (e.id === id ? { ...e, ...updates } : e)));
  };

  const updateDescription = (id: string, index: number, value: string) => {
    const exp = experiences.find((e) => e.id === id);
    if (!exp) return;
    const newDesc = [...exp.description];
    newDesc[index] = value;
    updateExperience(id, { description: newDesc });
  };

  const addBullet = (id: string) => {
    const exp = experiences.find((e) => e.id === id);
    if (!exp) return;
    updateExperience(id, { description: [...exp.description, ''] });
  };

  const removeBullet = (id: string, index: number) => {
    const exp = experiences.find((e) => e.id === id);
    if (!exp) return;
    updateExperience(id, { description: exp.description.filter((_, i) => i !== index) });
  };

  return (
    <div className="sr-experience-step">
      <div className="sr-experience-step__header">
        <h3 className="sr-experience-step__title">Experiência profissional</h3>
        <p className="sr-experience-step__subtitle">Adicione suas experiências de trabalho</p>
      </div>

      <div className="sr-experience-step__list">
        {experiences.map((exp) => (
          <ExperienceCard
            key={exp.id}
            experience={exp}
            onUpdate={(updates) => updateExperience(exp.id, updates)}
            onRemove={() => removeExperience(exp.id)}
            onUpdateDescription={updateDescription}
            onAddBullet={addBullet}
            onRemoveBullet={removeBullet}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addExperience}>
        <i className="fa-solid fa-plus" aria-hidden />
        Adicionar experiência
      </Button>
    </div>
  );
}

type ExperienceCardProps = {
  experience: Experience;
  onUpdate: (updates: Partial<Experience>) => void;
  onRemove: () => void;
  onUpdateDescription: (id: string, index: number, value: string) => void;
  onAddBullet: (id: string) => void;
  onRemoveBullet: (id: string, index: number) => void;
};

function ExperienceCard(props: ExperienceCardProps) {
  const { experience, onUpdate, onRemove, onUpdateDescription, onAddBullet, onRemoveBullet } = props;

  return (
    <div className="sr-experience-card">
      <div className="sr-experience-card__header">
        <h4 className="sr-experience-card__title">Experiência {experience.id.slice(-4)}</h4>
        <Button variant="ghost" onClick={onRemove}>
          <i className="fa-solid fa-trash" aria-hidden />
        </Button>
      </div>

      <div className="sr-experience-card__fields">
        <Input
          label="Empresa"
          placeholder="Nome da empresa"
          value={experience.company}
          onChange={(e) => onUpdate({ company: e.target.value })}
        />
        <Input
          label="Cargo"
          placeholder="Seu cargo"
          value={experience.position}
          onChange={(e) => onUpdate({ position: e.target.value })}
        />
        <div className="sr-experience-card__row">
          <DatePicker
            label="Data início"
            value={experience.startDate}
            onChange={(value) => onUpdate({ startDate: value })}
          />
          {!experience.isCurrent ? (
            <DatePicker
              label="Data fim"
              value={experience.endDate || ''}
              onChange={(value) => onUpdate({ endDate: value })}
            />
          ) : null}
        </div>
        <label className="sr-experience-card__checkbox">
          <input
            type="checkbox"
            checked={experience.isCurrent}
            onChange={(e) => onUpdate({ isCurrent: e.target.checked, endDate: e.target.checked ? undefined : experience.endDate })}
          />
          <span>Trabalho atual</span>
        </label>
        <div className="sr-experience-card__bullets">
          <label className="sr-experience-card__bullets-label">Descrição (bullet points)</label>
          {experience.description.map((bullet, idx) => (
            <div key={idx} className="sr-experience-card__bullet">
              <Input
                placeholder="Descreva uma conquista ou responsabilidade"
                value={bullet}
                onChange={(e) => onUpdateDescription(experience.id, idx, e.target.value)}
              />
              <Button variant="ghost" onClick={() => onRemoveBullet(experience.id, idx)}>
                <i className="fa-solid fa-times" aria-hidden />
              </Button>
            </div>
          ))}
          <Button variant="secondary" onClick={() => onAddBullet(experience.id)}>
            <i className="fa-solid fa-plus" aria-hidden />
            Adicionar ponto
          </Button>
        </div>
      </div>
    </div>
  );
}
