import { useState } from 'react';

import { Button, Input, CustomSelect, Checkbox } from '@/shared/ui';
import type { Skill, SkillLevel } from '@/entities/resume';

import './SkillsStep.css';

type Props = {
  skills: Skill[];
  onChange: (skills: Skill[]) => void;
};

const LEVEL_OPTIONS = [
  { value: '', label: 'Sem nível' },
  { value: 'beginner', label: 'Iniciante' },
  { value: 'intermediate', label: 'Intermediário' },
  { value: 'advanced', label: 'Avançado' },
  { value: 'expert', label: 'Especialista' },
];

export function SkillsStep(props: Props) {
  const { skills, onChange } = props;
  const [showLevels, setShowLevels] = useState(false);

  const addSkill = () => {
    const newSkill: Skill = {
      id: `skill-${Date.now()}`,
      name: '',
    };
    onChange([...skills, newSkill]);
  };

  const removeSkill = (id: string) => {
    onChange(skills.filter((s) => s.id !== id));
  };

  const updateSkill = (id: string, updates: Partial<Skill>) => {
    onChange(skills.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  };

  return (
    <div className="sr-skills-step">
      <div className="sr-skills-step__header">
        <h3 className="sr-skills-step__title">Habilidades</h3>
        <p className="sr-skills-step__subtitle">Adicione suas habilidades técnicas e profissionais</p>
      </div>

      <div className="sr-skills-step__options">
        <Checkbox
          className="sr-skills-step__toggle"
          checked={showLevels}
          onChange={setShowLevels}
          label="Mostrar níveis de proficiência"
        />
      </div>

      <div className="sr-skills-step__list">
        {skills.map((skill) => (
          <SkillCard
            key={skill.id}
            skill={skill}
            showLevel={showLevels}
            onUpdate={(updates) => updateSkill(skill.id, updates)}
            onRemove={() => removeSkill(skill.id)}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addSkill}>
        <i className="fa-solid fa-plus" aria-hidden />
        Adicionar habilidade
      </Button>
    </div>
  );
}

type SkillCardProps = {
  skill: Skill;
  showLevel: boolean;
  onUpdate: (updates: Partial<Skill>) => void;
  onRemove: () => void;
};

function SkillCard(props: SkillCardProps) {
  const { skill, showLevel, onUpdate, onRemove } = props;

  return (
    <div className="sr-skill-card">
      <Input
        label="Nome da habilidade"
        placeholder="Ex.: React, Python, Gestão de Projetos"
        value={skill.name}
        onChange={(e) => onUpdate({ name: e.target.value })}
      />
      {showLevel ? (
        <CustomSelect
          label="Nível"
          options={LEVEL_OPTIONS}
          value={skill.level || ''}
          onChange={(value) => onUpdate({ level: value ? (value as SkillLevel) : undefined })}
        />
      ) : null}
      <Button variant="ghost" onClick={onRemove}>
        <i className="fa-solid fa-trash" aria-hidden />
        Remover
      </Button>
    </div>
  );
}
