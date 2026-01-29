import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button, Modal } from '@/shared/ui';
import { ResumeThemePicker } from '@/features/resume-theme-select';
import { DEFAULT_RESUME_THEME_ID, resumeThemes, type ResumeThemeId } from '@/entities/resume';

import './NewResumeModal.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; themeId: ResumeThemeId }) => void;
};

export function NewResumeModal(props: Props) {
  const { open, onClose, onCreate } = props;
  const { t } = useTranslation();

  const [step, setStep] = useState(1);
  const [themeId, setThemeId] = useState<ResumeThemeId>(resumeThemes[0]?.id ?? DEFAULT_RESUME_THEME_ID);
  const [name, setName] = useState('');

  const canNext = useMemo(() => {
    if (step === 1) return Boolean(themeId);
    if (step === 2) return name.trim().length >= 3;
    return true;
  }, [name, step, themeId]);

  const close = () => {
    onClose();
    window.setTimeout(() => {
      setStep(1);
      setThemeId(resumeThemes[0]?.id ?? DEFAULT_RESUME_THEME_ID);
      setName('');
    }, 0);
  };

  const next = () => {
    if (!canNext) return;
    setStep((s) => Math.min(3, s + 1));
  };

  const back = () => setStep((s) => Math.max(1, s - 1));

  const finish = () => {
    if (!canNext) return;
    onCreate({ name: name.trim(), themeId });
    close();
  };

  return (
    <Modal open={open} title={t('resume.newModalTitle')} subtitle={t('resume.newModalSubtitle')} onClose={close} width={760}>
      <div className="sr-new-resume">
        <div className="sr-new-resume__steps sr-new-resume__steps--desktop" aria-label={t('resume.newModalStepsAria')}>
          {[1, 2, 3].map((n) => (
            <div key={n} className={`sr-new-resume__step${n === step ? ' is-active' : ''}${n < step ? ' is-done' : ''}`}>
              {n}
            </div>
          ))}
        </div>

        <div className="sr-new-resume__progress sr-new-resume__progress--mobile" aria-label={t('resume.newModalProgressAria')}>
          <span className="sr-new-resume__progress-text">{t('resume.newModalStep', { current: String(step) })}</span>
          <div className="sr-new-resume__progress-bar" aria-hidden>
            <div className="sr-new-resume__progress-fill" style={{ width: `${(step / 3) * 100}%` }} />
          </div>
        </div>

        <div className="sr-new-resume__content">
          {step === 1 ? (
            <div className="sr-new-resume__panel">
              <h3 className="sr-new-resume__h3">{t('resume.newModalSelectTheme')}</h3>
              <p className="sr-new-resume__muted">{t('resume.newModalThemeHint')}</p>

              <ResumeThemePicker selectedId={themeId} onSelect={setThemeId} variant="carousel" cardSize="compact" />
            </div>
          ) : step === 2 ? (
            <div className="sr-new-resume__panel">
              <h3 className="sr-new-resume__h3">{t('resume.newModalNameTitle')}</h3>
              <p className="sr-new-resume__muted">{t('resume.newModalNameExample')}</p>
              <input
                className="sr-input"
                value={name}
                placeholder={t('resume.newModalNamePlaceholder')}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          ) : (
            <div className="sr-new-resume__panel">
              <h3 className="sr-new-resume__h3">{t('resume.newModalNextSteps')}</h3>
              <p className="sr-new-resume__muted">{t('resume.newModalNextStepsHint')}</p>

              <div className="sr-new-resume__placeholder">
                <div className="sr-new-resume__placeholder-row">
                  <div className="sr-new-resume__dot is-active" />
                  <div>
                    <div className="sr-new-resume__placeholder-title">{t('resume.newModalPersonalData')}</div>
                    <div className="sr-new-resume__template-desc">{t('resume.newModalPersonalDataDesc')}</div>
                  </div>
                </div>

                <div className="sr-new-resume__placeholder-row">
                  <div className="sr-new-resume__dot" />
                  <div>
                    <div className="sr-new-resume__placeholder-title">{t('resume.newModalExperience')}</div>
                    <div className="sr-new-resume__template-desc">{t('resume.newModalExperienceDesc')}</div>
                  </div>
                </div>

                <div className="sr-new-resume__placeholder-row">
                  <div className="sr-new-resume__dot" />
                  <div>
                    <div className="sr-new-resume__placeholder-title">{t('resume.newModalSkills')}</div>
                    <div className="sr-new-resume__template-desc">{t('resume.newModalSkillsDesc')}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="sr-new-resume__footer">
          <Button variant="secondary" onClick={step === 1 ? close : back}>
            {step === 1 ? t('resume.newModalCancel') : t('resume.newModalBack')}
          </Button>

          {step < 3 ? (
            <Button variant="primary" onClick={next} disabled={!canNext}>
              {t('resume.newModalNext')}
              <i className="fa-solid fa-arrow-right" aria-hidden />
            </Button>
          ) : (
            <Button variant="primary" onClick={finish}>
              {t('resume.newModalCreate')}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
