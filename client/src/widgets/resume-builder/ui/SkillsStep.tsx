import { Button, Input, CustomSelect, Checkbox } from '@/shared/ui';
import type { Skill, SkillLevel } from '@/entities/resume';

import './SkillsStep.css';

type Props = {
  skills: Skill[];
  onChange: (skills: Skill[]) => void;
  showLevels: boolean;
  onToggleShowLevels: (next: boolean) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

const LEVEL_OPTIONS = [
  { value: '', label: 'Sem nível' },
  { value: 'beginner', label: 'Iniciante' },
  { value: 'intermediate', label: 'Intermediário' },
  { value: 'advanced', label: 'Avançado' },
  { value: 'expert', label: 'Especialista' },
];

export function SkillsStep(props: Props) {
  const { skills, onChange, showLevels, onToggleShowLevels, getError, shouldShowError, onFieldTouched } = props;
  const listError = shouldShowError('skills') ? getError('skills') : undefined;

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
          onChange={onToggleShowLevels}
          label="Mostrar níveis de proficiência"
        />
      </div>

      <div className={`sr-skills-step__list${listError ? ' is-invalid' : ''}`} tabIndex={listError ? -1 : undefined}>
        {listError ? <p className="sr-input-error">{listError}</p> : null}
        {skills.map((skill, index) => (
          <SkillCard
            key={skill.id}
            skill={skill}
            index={index}
            showLevel={showLevels}
            onUpdate={(updates) => updateSkill(skill.id, updates)}
            onRemove={() => removeSkill(skill.id)}
            getError={getError}
            shouldShowError={shouldShowError}
            onFieldTouched={onFieldTouched}
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
  index: number;
  showLevel: boolean;
  onUpdate: (updates: Partial<Skill>) => void;
  onRemove: () => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

function SkillCard(props: SkillCardProps) {
  const { skill, index, showLevel, onUpdate, onRemove, getError, shouldShowError, onFieldTouched } = props;
  const basePath = `skills.${index}`;
  const nameError = shouldShowError(`${basePath}.name`) ? getError(`${basePath}.name`) : undefined;
  const levelError = shouldShowError(`${basePath}.level`) ? getError(`${basePath}.level`) : undefined;

  return (
    <div className="sr-skill-card">
      <Input
        label="Nome da habilidade *"
        placeholder="Ex.: React, Python, Gestão de Projetos"
        value={skill.name}
        onChange={(e) => onUpdate({ name: e.target.value })}
        onBlur={() => onFieldTouched(`${basePath}.name`)}
        error={nameError}
      />
      {showLevel ? (
        <CustomSelect
          label="Nível *"
          options={LEVEL_OPTIONS}
          value={skill.level || ''}
          onChange={(value) => {
            onUpdate({ level: value ? (value as SkillLevel) : undefined });
            onFieldTouched(`${basePath}.level`);
          }}
          error={levelError}
        />
      ) : null}
      <Button variant="ghost" onClick={onRemove}>
        <i className="fa-solid fa-trash" aria-hidden />
        Remover
      </Button>
    </div>
  );
}
