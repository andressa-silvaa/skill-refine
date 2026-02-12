import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { Button, Modal, ProgressBar, Stepper } from '@/shared/ui';
import { calculateCompletenessScore, type Resume, type ResumeData, type ResumeStatus } from '@/entities/resume';
import type { ResumeDraftPayload } from '@/features/resume';
import { useResumeBuilder, type BuilderStep, type StepConfig } from '@/features/resume-builder';
import { getApiFieldErrors } from '@/shared/api';
import { ResumePreviewFullscreen } from '@/widgets/resume-preview';
import { AutoSaveIndicator } from './AutoSaveIndicator';
import { ResumeBuilderStepContent } from './ResumeBuilderStepContent';
import { ConfirmDiscardChangesModal } from './ConfirmDiscardChangesModal';

import { useResumeWizardCloseFlow } from '../model/useResumeWizardCloseFlow';
import { useResumeWizardHydration } from '../model/useResumeWizardHydration';
import { useResumeWizardNavigation } from '../model/useResumeWizardNavigation';
import { useResumeWizardPreview } from '../model/useResumeWizardPreview';

import './ResumeBuilderWizard.css';

type Props = {
  title: string;
  open: boolean;
  onClose: () => void;
  onSaveDraft: (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => Promise<Resume>;
  onFinish: (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => Promise<Resume>;
  isSavingDraft?: boolean;
  isSubmitting?: boolean;
  isLoading?: boolean;
  initialData?: ResumeData | null;
  initialResumeId?: string | null;
  initialStatus?: ResumeStatus | null;
  initialLastStep?: BuilderStep | null;
};

export function ResumeBuilderWizard(props: Props) {
  const {
    title,
    open,
    onClose,
    onSaveDraft,
    onFinish,
    isSavingDraft = false,
    isSubmitting = false,
    isLoading = false,
    initialData,
    initialResumeId,
    initialStatus,
    initialLastStep,
  } = props;
  const { t } = useTranslation();
  const builder = useResumeBuilder();
  const containerRef = useRef<HTMLDivElement>(null);

  const closeFlow = useResumeWizardCloseFlow({ onClose, builder });
  useResumeWizardHydration({
    open,
    initialData,
    initialResumeId,
    initialStatus,
    initialLastStep,
    builder,
  });
  const preview = useResumeWizardPreview(open);
  const navigation = useResumeWizardNavigation({
    builder,
    containerRef,
    onFinish,
    skipDiscardAndClose: closeFlow.skipDiscardAndClose,
  });

  const stepsWithLabels = useMemo(
    () =>
      builder.steps.map((step) => ({
        ...step,
        label: t(`resume.step${step.id.charAt(0).toUpperCase() + step.id.slice(1)}`),
      })),
    [builder.steps, t]
  );

  useEffect(() => {
    if (!open) return;
    window.setTimeout(() => {
      const titleEl = document.querySelector<HTMLElement>('.sr-modal__title');
      titleEl?.focus();
    }, 0);
  }, [open]);

  useEffect(() => {
    if (!open || !builder.hasUnsavedChanges) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [open, builder.hasUnsavedChanges]);

  const handleSaveDraft = useCallback(async () => {
    const payload: ResumeDraftPayload = {
      ...builder.data,
      name: builder.data.targetPosition || t('resume.builderDefaultName'),
      status: 'draft',
      lastStep: builder.currentStep,
      score: calculateCompletenessScore(builder.data),
    };

    try {
      const resume = await onSaveDraft({ payload, resumeId: builder.resumeId });
      builder.setResumeId(resume.id);
      builder.saveDraft();
      closeFlow.skipDiscardAndClose();
    } catch (err) {
      const fields = getApiFieldErrors(err);
      if (fields) {
        builder.setServerErrors(fields);
        const step = builder.getFirstErrorStep(fields);
        if (step) {
          builder.goToStep(step);
          builder.markStepSubmitted(step);
        }
        navigation.focusFirstError();
      }
    }
  }, [
    builder,
    onSaveDraft,
    closeFlow,
    navigation,
    t,
  ]);

  const currentStepIndex = builder.steps.findIndex((s) => s.id === builder.currentStep);
  const currentStepNum = currentStepIndex + 1;
  const totalSteps = builder.steps.length;

  return (
    <Modal open={open} title={title} subtitle={t('resume.builderSubtitle')} onClose={closeFlow.handleClose} width={900}>
      <div className="sr-resume-builder-wizard" ref={containerRef}>
        <div className="sr-resume-builder-wizard__progress">
          <ProgressBar
            current={currentStepNum}
            total={totalSteps}
            rightContent={
              <AutoSaveIndicator
                lastSaved={builder.lastSaved}
                hasUnsavedChanges={builder.hasUnsavedChanges}
                onSave={builder.saveDraft}
              />
            }
          />
        </div>

        <div className="sr-resume-builder-wizard__stepper">
          <Stepper
            steps={stepsWithLabels.map((step: StepConfig) => ({ id: step.id, label: step.label }))}
            currentStep={currentStepNum}
            onStepClick={(stepId) => {
              navigation.validateAndNavigate(stepId as BuilderStep);
            }}
            isStepClickable={(stepId, stepNum) => {
              const targetStep = stepId as BuilderStep;
              return stepNum <= currentStepNum || builder.canGoToStep(targetStep);
            }}
          />
        </div>

        <div className="sr-resume-builder-wizard__content">
          {isLoading ? (
            <div className="sr-resume-builder-wizard__loading" role="status" aria-live="polite">
              <i className="fa-solid fa-circle-notch" aria-hidden />
              {t('resume.builderLoading')}
            </div>
          ) : (
            <ResumeBuilderStepContent builder={builder} onStepEdit={navigation.handleStepEdit} />
          )}
        </div>

        <div className="sr-resume-builder-wizard__actions">
          <div className="sr-resume-builder-wizard__actions-back">
            <Button
              variant="secondary"
              onClick={builder.currentStep === 'theme' ? closeFlow.handleClose : builder.prevStep}
              disabled={isLoading}
            >
              {builder.currentStep === 'theme' ? t('resume.builderCancel') : t('resume.builderBack')}
            </Button>
          </div>

          <div className="sr-resume-builder-wizard__actions-secondary">
            {builder.currentStep !== 'review' && builder.hasUnsavedChanges ? (
              <Button variant="ghost" onClick={handleSaveDraft} disabled={isSavingDraft || isSubmitting || isLoading}>
                {isSavingDraft ? t('resume.builderSaving') : t('resume.builderSaveDraft')}
              </Button>
            ) : null}
            {builder.currentStep !== 'theme' ? (
              <Button variant="ghost" onClick={preview.openPreview} disabled={isSavingDraft || isSubmitting || isLoading}>
                <i className="fa-solid fa-eye" aria-hidden />
                {t('resume.builderPreview')}
              </Button>
            ) : null}
          </div>

          <div className="sr-resume-builder-wizard__actions-primary">
            <Button
              variant="primary"
              onClick={navigation.handleNext}
              disabled={!builder.canGoNext || isSavingDraft || isSubmitting || isLoading}
            >
              {builder.currentStep === 'review'
                ? isSubmitting
                  ? t('resume.builderSaving')
                  : t('resume.builderFinish')
                : t('resume.builderNext')}
              {builder.currentStep !== 'review' ? <i className="fa-solid fa-arrow-right" aria-hidden /> : null}
            </Button>
          </div>
        </div>
      </div>

      <ResumePreviewFullscreen
        open={preview.isPreviewOpen}
        data={builder.data}
        onClose={preview.closePreview}
        enableStressToggle={process.env.NODE_ENV === 'development'}
        onUpdateData={builder.updateData}
      />

      <ConfirmDiscardChangesModal
        open={closeFlow.discardOpen}
        onClose={closeFlow.closeDiscard}
        onDiscard={closeFlow.confirmDiscard}
      />
    </Modal>
  );
}
