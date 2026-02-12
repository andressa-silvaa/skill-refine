import { useTranslation } from 'react-i18next';

import { Button } from '@/shared/ui';
import { calculateCompletenessScore, type ResumeData } from '@/entities/resume';

import './ReviewStep.css';

type Props = {
  data: ResumeData;
  onEdit: (step: string) => void;
};

const SECTION_LABEL_KEYS = [
  'resume.reviewStepSectionBasic',
  'resume.reviewStepSectionContact',
  'resume.reviewStepSectionExperience',
  'resume.reviewStepSectionEducation',
  'resume.reviewStepSectionSkills',
  'resume.reviewStepSectionLanguages',
  'resume.reviewStepSectionSummary',
] as const;

const SECTION_IDS = ['basic', 'contact', 'experience', 'education', 'skills', 'languages', 'summary'] as const;

export function ReviewStep(props: Props) {
  const { data, onEdit } = props;
  const { t } = useTranslation();
  const score = calculateCompletenessScore(data);

  const sections: { id: string; labelKey: string; complete: boolean }[] = [
    { id: SECTION_IDS[0], labelKey: SECTION_LABEL_KEYS[0], complete: Boolean(data.targetPosition) },
    { id: SECTION_IDS[1], labelKey: SECTION_LABEL_KEYS[1], complete: Boolean(data.contact.fullName && data.contact.email) },
    { id: SECTION_IDS[2], labelKey: SECTION_LABEL_KEYS[2], complete: data.experiences.length > 0 },
    { id: SECTION_IDS[3], labelKey: SECTION_LABEL_KEYS[3], complete: data.educations.length > 0 },
    { id: SECTION_IDS[4], labelKey: SECTION_LABEL_KEYS[4], complete: data.skills.length > 0 },
    { id: SECTION_IDS[5], labelKey: SECTION_LABEL_KEYS[5], complete: data.languages.length > 0 },
    { id: SECTION_IDS[6], labelKey: SECTION_LABEL_KEYS[6], complete: Boolean(data.summary) },
  ];

  return (
    <div className="sr-review-step">
      <div className="sr-review-step__header">
        <h3 className="sr-review-step__title">{t('resume.reviewStepTitle')}</h3>
        <p className="sr-review-step__subtitle">{t('resume.reviewStepSubtitle')}</p>
      </div>

      <div className="sr-review-step__score">
        <div className="sr-review-step__score-circle">
          <span className="sr-review-step__score-value">{score}</span>
          <span className="sr-review-step__score-total">/100</span>
        </div>
        <p className="sr-review-step__score-label">{t('resume.reviewStepScoreLabel')}</p>
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
              <span className="sr-review-step__section-label">{t(section.labelKey)}</span>
            </div>
            <Button variant="ghost" onClick={() => onEdit(section.id)}>
              {t('resume.reviewStepEdit')}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
