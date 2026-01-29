import { useTranslation } from 'react-i18next';

import { Button, Input, DatePicker, Checkbox } from '@/shared/ui';
import type { Experience } from '@/entities/resume';

import './ExperienceStep.css';

type Props = {
  experiences: Experience[];
  onChange: (experiences: Experience[]) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function ExperienceStep(props: Props) {
  const { experiences, onChange, getError, shouldShowError, onFieldTouched } = props;

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

  const { t } = useTranslation();

  return (
    <div className="sr-experience-step">
      <div className="sr-experience-step__header">
        <h3 className="sr-experience-step__title">{t('resume.experienceStepTitle')}</h3>
        <p className="sr-experience-step__subtitle">{t('resume.experienceStepSubtitle')}</p>
      </div>

      <div className="sr-experience-step__list">
        {experiences.map((exp, index) => (
          <ExperienceCard
            key={exp.id}
            experience={exp}
            index={index}
            onUpdate={(updates) => updateExperience(exp.id, updates)}
            onRemove={() => removeExperience(exp.id)}
            onUpdateDescription={updateDescription}
            onAddBullet={addBullet}
            onRemoveBullet={removeBullet}
            getError={getError}
            shouldShowError={shouldShowError}
            onFieldTouched={onFieldTouched}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addExperience}>
        <i className="fa-solid fa-plus" aria-hidden />
        {t('resume.experienceStepAdd')}
      </Button>
    </div>
  );
}

type ExperienceCardProps = {
  experience: Experience;
  index: number;
  onUpdate: (updates: Partial<Experience>) => void;
  onRemove: () => void;
  onUpdateDescription: (id: string, index: number, value: string) => void;
  onAddBullet: (id: string) => void;
  onRemoveBullet: (id: string, index: number) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

function ExperienceCard(props: ExperienceCardProps) {
  const { experience, index, onUpdate, onRemove, onUpdateDescription, onAddBullet, onRemoveBullet, getError, shouldShowError, onFieldTouched } = props;
  const { t } = useTranslation();
  const basePath = `experiences.${index}`;
  const companyError = shouldShowError(`${basePath}.company`) ? getError(`${basePath}.company`) : undefined;
  const positionError = shouldShowError(`${basePath}.position`) ? getError(`${basePath}.position`) : undefined;
  const startDateError = shouldShowError(`${basePath}.startDate`) ? getError(`${basePath}.startDate`) : undefined;
  const endDateError = shouldShowError(`${basePath}.endDate`) ? getError(`${basePath}.endDate`) : undefined;
  const descriptionError = shouldShowError(`${basePath}.description`) ? getError(`${basePath}.description`) : undefined;

  return (
    <div className="sr-experience-card">
      <div className="sr-experience-card__header">
        <h4 className="sr-experience-card__title">{t('resume.experienceStepTitle')}</h4>
        <Button variant="ghost" onClick={onRemove}>
          <i className="fa-solid fa-trash" aria-hidden />
        </Button>
      </div>

      <div className="sr-experience-card__fields">
        <Input
          label={t('resume.experienceStepCompany')}
          placeholder={t('resume.experienceStepCompanyPlaceholder')}
          value={experience.company}
          onChange={(e) => onUpdate({ company: e.target.value })}
          onBlur={() => onFieldTouched(`${basePath}.company`)}
          error={companyError}
        />
        <Input
          label={t('resume.experienceStepPosition')}
          placeholder={t('resume.experienceStepPositionPlaceholder')}
          value={experience.position}
          onChange={(e) => onUpdate({ position: e.target.value })}
          onBlur={() => onFieldTouched(`${basePath}.position`)}
          error={positionError}
        />
        <div className="sr-experience-card__row">
          <DatePicker
            label={t('resume.experienceStepStartDateLabel')}
            value={experience.startDate}
            onChange={(value) => {
              onUpdate({ startDate: value });
              onFieldTouched(`${basePath}.startDate`);
            }}
            error={startDateError}
          />
          {!experience.isCurrent ? (
            <DatePicker
              label={t('resume.experienceStepEndDateLabel')}
              value={experience.endDate || ''}
              onChange={(value) => {
                onUpdate({ endDate: value });
                onFieldTouched(`${basePath}.endDate`);
              }}
              error={endDateError}
            />
          ) : null}
        </div>
        <Checkbox
          className="sr-experience-card__checkbox"
          checked={experience.isCurrent}
          onChange={(checked) => onUpdate({ isCurrent: checked, endDate: checked ? undefined : experience.endDate })}
          label={t('resume.experienceStepCurrent')}
        />
        <div className={`sr-experience-card__bullets${descriptionError ? ' is-invalid' : ''}`} tabIndex={descriptionError ? -1 : undefined}>
          <label className="sr-experience-card__bullets-label">{t('resume.experienceStepDescriptionLabel')}</label>
          {descriptionError ? <p className="sr-input-error">{descriptionError}</p> : null}
          {experience.description.map((bullet, idx) => (
            <div key={idx} className="sr-experience-card__bullet">
              <Input
                placeholder={t('resume.experienceStepBulletPlaceholder')}
                value={bullet}
                onChange={(e) => onUpdateDescription(experience.id, idx, e.target.value)}
                onBlur={() => onFieldTouched(`${basePath}.description.${idx}`)}
                error={shouldShowError(`${basePath}.description.${idx}`) ? getError(`${basePath}.description.${idx}`) : undefined}
              />
              <Button variant="ghost" onClick={() => onRemoveBullet(experience.id, idx)}>
                <i className="fa-solid fa-times" aria-hidden />
              </Button>
            </div>
          ))}
          <Button variant="secondary" onClick={() => onAddBullet(experience.id)}>
            <i className="fa-solid fa-plus" aria-hidden />
            {t('resume.experienceStepAddBullet')}
          </Button>
        </div>
      </div>
    </div>
  );
}
