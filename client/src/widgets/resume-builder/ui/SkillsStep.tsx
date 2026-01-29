import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

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

export function SkillsStep(props: Props) {
  const { skills, onChange, showLevels, onToggleShowLevels, getError, shouldShowError, onFieldTouched } = props;
  const { t } = useTranslation();
  const listError = shouldShowError('skills') ? getError('skills') : undefined;

  const levelOptions = useMemo(
    () => [
      { value: '', label: t('resume.skillsStepLevelNone') },
      { value: 'beginner', label: t('resume.skillsStepLevelBeginner') },
      { value: 'intermediate', label: t('resume.skillsStepLevelIntermediate') },
      { value: 'advanced', label: t('resume.skillsStepLevelAdvanced') },
      { value: 'expert', label: t('resume.skillsStepLevelExpert') },
    ],
    [t]
  );

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
        <h3 className="sr-skills-step__title">{t('resume.skillsStepTitle')}</h3>
        <p className="sr-skills-step__subtitle">{t('resume.skillsStepSubtitle')}</p>
      </div>

      <div className="sr-skills-step__options">
        <Checkbox
          className="sr-skills-step__toggle"
          checked={showLevels}
          onChange={onToggleShowLevels}
          label={t('resume.skillsStepShowLevels')}
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
            levelOptions={levelOptions}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addSkill}>
        <i className="fa-solid fa-plus" aria-hidden />
        {t('resume.skillsStepAdd')}
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
  levelOptions: { value: string; label: string }[];
};

function SkillCard(props: SkillCardProps) {
  const { skill, index, showLevel, onUpdate, onRemove, getError, shouldShowError, onFieldTouched, levelOptions } = props;
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
          options={levelOptions}
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
