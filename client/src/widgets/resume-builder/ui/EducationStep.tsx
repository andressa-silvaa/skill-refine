import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { Button, Input, CustomSelect, DatePicker } from '@/shared/ui';
import type { Education, EducationStatus } from '@/entities/resume';

import './EducationStep.css';

type Props = {
  educations: Education[];
  onChange: (educations: Education[]) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function EducationStep(props: Props) {
  const { educations, onChange, getError, shouldShowError, onFieldTouched } = props;
  const { t } = useTranslation();

  const statusOptions = useMemo(
    () => [
      { value: 'completed', label: t('resume.educationStepCompleted') },
      { value: 'in_progress', label: t('resume.educationStepInProgress') },
    ],
    [t]
  );

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
        <h3 className="sr-education-step__title">{t('resume.educationStepTitle')}</h3>
        <p className="sr-education-step__subtitle">{t('resume.educationStepSubtitle')}</p>
      </div>

      <div className="sr-education-step__list">
        {educations.map((edu, index) => (
          <EducationCard
            key={edu.id}
            education={edu}
            index={index}
            onUpdate={(updates) => updateEducation(edu.id, updates)}
            onRemove={() => removeEducation(edu.id)}
            getError={getError}
            shouldShowError={shouldShowError}
            onFieldTouched={onFieldTouched}
            statusOptions={statusOptions}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addEducation}>
        <i className="fa-solid fa-plus" aria-hidden />
        {t('resume.educationStepAdd')}
      </Button>
    </div>
  );
}

type EducationCardProps = {
  education: Education;
  index: number;
  onUpdate: (updates: Partial<Education>) => void;
  onRemove: () => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
  statusOptions: { value: string; label: string }[];
};

function EducationCard(props: EducationCardProps) {
  const { education, index, onUpdate, onRemove, getError, shouldShowError, onFieldTouched, statusOptions } = props;
  const { t } = useTranslation();
  const basePath = `educations.${index}`;
  const institutionError = shouldShowError(`${basePath}.institution`) ? getError(`${basePath}.institution`) : undefined;
  const courseError = shouldShowError(`${basePath}.course`) ? getError(`${basePath}.course`) : undefined;
  const degreeError = shouldShowError(`${basePath}.degree`) ? getError(`${basePath}.degree`) : undefined;
  const startDateError = shouldShowError(`${basePath}.startDate`) ? getError(`${basePath}.startDate`) : undefined;
  const endDateError = shouldShowError(`${basePath}.endDate`) ? getError(`${basePath}.endDate`) : undefined;
  const statusError = shouldShowError(`${basePath}.status`) ? getError(`${basePath}.status`) : undefined;

  return (
    <div className="sr-education-card">
      <div className="sr-education-card__header">
        <h4 className="sr-education-card__title">{t('resume.educationStepTitle')}</h4>
        <Button variant="ghost" onClick={onRemove}>
          <i className="fa-solid fa-trash" aria-hidden />
        </Button>
      </div>

      <div className="sr-education-card__fields">
        <Input
          label={t('resume.educationStepInstitution')}
          placeholder={t('resume.educationStepInstitutionPlaceholder')}
          value={education.institution}
          onChange={(e) => onUpdate({ institution: e.target.value })}
          onBlur={() => onFieldTouched(`${basePath}.institution`)}
          error={institutionError}
        />
        <Input
          label={t('resume.educationStepCourse')}
          placeholder={t('resume.educationStepCoursePlaceholder')}
          value={education.course}
          onChange={(e) => onUpdate({ course: e.target.value })}
          onBlur={() => onFieldTouched(`${basePath}.course`)}
          error={courseError}
        />
        <Input
          label={t('resume.educationStepDegree')}
          placeholder={t('resume.educationStepDegreePlaceholder')}
          value={education.degree}
          onChange={(e) => onUpdate({ degree: e.target.value })}
          onBlur={() => onFieldTouched(`${basePath}.degree`)}
          error={degreeError}
        />
        <div className="sr-education-card__row">
          <DatePicker
            label={t('resume.educationStepStartDateLabel')}
            value={education.startDate}
            onChange={(value) => {
              onUpdate({ startDate: value });
              onFieldTouched(`${basePath}.startDate`);
            }}
            error={startDateError}
          />
          {education.status === 'completed' ? (
            <DatePicker
              label={t('resume.educationStepEndDateLabel')}
              value={education.endDate || ''}
              onChange={(value) => {
                onUpdate({ endDate: value });
                onFieldTouched(`${basePath}.endDate`);
              }}
              error={endDateError}
            />
          ) : null}
        </div>
        <CustomSelect
          label={t('resume.educationStepStatusLabel')}
          options={statusOptions}
          value={education.status}
          onChange={(value) => {
            onUpdate({ status: value as EducationStatus, endDate: value === 'in_progress' ? undefined : education.endDate });
            onFieldTouched(`${basePath}.status`);
          }}
          error={statusError}
        />
      </div>
    </div>
  );
}
