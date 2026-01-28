import { useEffect, useRef, useState } from 'react';

import { Button, Modal, ProgressBar, Stepper } from '@/shared/ui';
import type { Resume, ResumeData, ResumeStatus } from '@/entities/resume';
import type { ResumeDraftPayload } from '@/features/resume/api/resumeApi';
import { useResumeBuilder, type BuilderStep } from '@/features/resume-builder';
import { notify } from '@/shared/lib/notify';
import { getApiFieldErrors } from '@/shared/api';
import { ResumePreviewFullscreen } from '@/widgets/resume-preview';
import { AutoSaveIndicator } from './AutoSaveIndicator';
import { ResumeBuilderStepContent } from './ResumeBuilderStepContent';
import { ConfirmDiscardChangesModal } from './ConfirmDiscardChangesModal';

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
  const builder = useResumeBuilder();
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const builderRef = useRef(builder);
  const prevOpenRef = useRef(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const skipDiscardRef = useRef(false);
  builderRef.current = builder;

  useEffect(() => {
    if (prevOpenRef.current && !open) {
      builderRef.current.reset();
    }
    prevOpenRef.current = open;
  }, [open]);

  useEffect(() => {
    if (!open) return;
    window.setTimeout(() => {
      const title = document.querySelector<HTMLElement>('.sr-modal__title');
      title?.focus();
    }, 0);
  }, [open]);
  
  useEffect(() => {
    if (!open && isPreviewOpen) setIsPreviewOpen(false);
  }, [open, isPreviewOpen]);

  const hydratedRef = useRef<string | null>(null);

  const inferStepFromData = (data: ResumeData): BuilderStep => {
    if (!data.themeId) return 'theme';
    if (!data.targetPosition) return 'basic';
    if (!data.contact.fullName || !data.contact.email) return 'contact';
    if (!data.experiences.length) return 'experience';
    if (!data.educations.length) return 'education';
    if (!data.skills.length) return 'skills';
    if (!data.languages.length) return 'languages';
    if (!data.summary) return 'summary';
    return 'review';
  };

  useEffect(() => {
    if (!open || !initialData) return;
    const key = `${initialResumeId ?? 'new'}:${initialStatus ?? ''}:${initialLastStep ?? ''}`;
    if (hydratedRef.current === key) return;
    hydratedRef.current = key;

    let step: BuilderStep = 'theme';
    if (initialStatus === 'complete') {
      step = 'review';
    } else if (initialLastStep) {
      step = initialLastStep;
    } else {
      step = inferStepFromData(initialData);
    }

    builderRef.current.hydrate(initialData, initialResumeId ?? null, step);
  }, [open, initialData, initialResumeId, initialStatus, initialLastStep]);

  useEffect(() => {
    if (!open) {
      hydratedRef.current = null;
    }
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

  const handleClose = () => {
    if (skipDiscardRef.current) {
      skipDiscardRef.current = false;
      onClose();
      return;
    }
    if (builderRef.current.isDirty) {
      setDiscardOpen(true);
      return;
    }
    onClose();
  };

  const handleSaveDraft = async () => {
    const payload: ResumeDraftPayload = {
      ...builder.data,
      name: builder.data.targetPosition || 'Novo Currículo',
      status: 'draft',
      lastStep: builder.currentStep,
    };

    try {
      const resume = await onSaveDraft({ payload, resumeId: builder.resumeId });
      builder.setResumeId(resume.id);
      builder.saveDraft();
      skipDiscardRef.current = true;
      onClose();
    } catch (err) {
      const fields = getApiFieldErrors(err);
      if (fields) {
        builder.setServerErrors(fields);
        const step = builder.getFirstErrorStep(fields);
        if (step) {
          builder.goToStep(step);
          builder.markStepSubmitted(step);
        }
        focusFirstError();
      }
      return;
    }
  };

  const handleNext = async () => {
    if (builder.currentStep === 'review') {
      const validation = builder.validateAll();
      if (!validation.isValid) {
        const firstStep = builder.getFirstErrorStep(validation.errors);
        if (firstStep) {
          builder.goToStep(firstStep);
          builder.markStepSubmitted(firstStep);
        }
        notify.error('Revise os campos obrigatórios antes de concluir.');
        focusFirstError();
        return;
      }
      const payload: ResumeDraftPayload = {
        ...builder.data,
        name: builder.data.targetPosition || 'Novo Currículo',
        status: 'complete',
        lastStep: 'review',
      };
      try {
        const resume = await onFinish({ payload, resumeId: builder.resumeId });
        builder.setResumeId(resume.id);
        skipDiscardRef.current = true;
        onClose();
      } catch (err) {
        const fields = getApiFieldErrors(err);
        if (fields) {
          builder.setServerErrors(fields);
          const step = builder.getFirstErrorStep(fields);
          if (step) {
            builder.goToStep(step);
            builder.markStepSubmitted(step);
          }
          focusFirstError();
        }
        return;
      }
    } else {
      const currentOrder = builder.steps.find((s) => s.id === builder.currentStep)?.order ?? 0;
      const nextStep = builder.steps.find((s) => s.order === currentOrder + 1)?.id as BuilderStep | undefined;
      if (nextStep && !builder.tryNavigateToStep(nextStep)) {
        focusFirstError();
        return;
      }
    }
  };

  const handleStepEdit = (stepId: string) => {
    const stepMap: Record<string, BuilderStep> = {
      basic: 'basic',
      contact: 'contact',
      experience: 'experience',
      education: 'education',
      skills: 'skills',
      languages: 'languages',
      summary: 'summary',
    };
    const targetStep = stepMap[stepId];
    if (targetStep) {
      builder.goToStep(targetStep);
    }
  };

  const currentStepIndex = builder.steps.findIndex((s) => s.id === builder.currentStep);
  const currentStepNum = currentStepIndex + 1;
  const totalSteps = builder.steps.length;

  const focusFirstError = () => {
    window.setTimeout(() => {
      const container = containerRef.current ?? document;
      const invalidElement = container.querySelector<HTMLElement>('.is-invalid, [aria-invalid="true"]');
      if (!invalidElement) return;
      invalidElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (typeof invalidElement.focus === 'function') {
        invalidElement.focus();
      }
    }, 0);
  };

  return (
    <Modal open={open} title={title} subtitle="Preencha as informações para criar seu currículo" onClose={handleClose} width={900}>
      <div className="sr-resume-builder-wizard" ref={containerRef}>
        <div className="sr-resume-builder-wizard__progress">
          <ProgressBar
            current={currentStepNum}
            total={totalSteps}
            rightContent={
              <AutoSaveIndicator lastSaved={builder.lastSaved} hasUnsavedChanges={builder.hasUnsavedChanges} onSave={builder.saveDraft} />
            }
          />
        </div>

        <div className="sr-resume-builder-wizard__stepper">
          <Stepper
            steps={builder.steps.map((step) => ({ id: step.id, label: step.label }))}
            currentStep={currentStepNum}
            onStepClick={(stepId) => {
              const targetStep = stepId as BuilderStep;
              if (!builder.tryNavigateToStep(targetStep)) {
                focusFirstError();
              }
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
              Carregando currículo...
            </div>
          ) : (
            <ResumeBuilderStepContent builder={builder} onStepEdit={handleStepEdit} />
          )}
        </div>

        <div className="sr-resume-builder-wizard__actions">
          <div className="sr-resume-builder-wizard__actions-back">
            <Button variant="secondary" onClick={builder.currentStep === 'theme' ? handleClose : builder.prevStep} disabled={isLoading}>
              {builder.currentStep === 'theme' ? 'Cancelar' : 'Voltar'}
            </Button>
          </div>

          <div className="sr-resume-builder-wizard__actions-secondary">
            {builder.currentStep !== 'review' && builder.hasUnsavedChanges ? (
              <Button variant="ghost" onClick={handleSaveDraft} disabled={isSavingDraft || isSubmitting || isLoading}>
                {isSavingDraft ? 'Salvando...' : 'Salvar rascunho'}
              </Button>
            ) : null}
            {builder.currentStep !== 'theme' ? (
              <Button variant="ghost" onClick={() => setIsPreviewOpen(true)} disabled={isSavingDraft || isSubmitting || isLoading}>
                <i className="fa-solid fa-eye" aria-hidden />
                Visualizar
              </Button>
            ) : null}
          </div>

          <div className="sr-resume-builder-wizard__actions-primary">
            <Button variant="primary" onClick={handleNext} disabled={!builder.canGoNext || isSavingDraft || isSubmitting || isLoading}>
              {builder.currentStep === 'review' ? (isSubmitting ? 'Salvando...' : 'Concluir') : 'Próximo'}
              {builder.currentStep !== 'review' ? <i className="fa-solid fa-arrow-right" aria-hidden /> : null}
            </Button>
          </div>
        </div>
      </div>

      <ResumePreviewFullscreen
        open={isPreviewOpen}
        data={builder.data}
        onClose={() => setIsPreviewOpen(false)}
        enableStressToggle={process.env.NODE_ENV === 'development'}
        onUpdateData={builder.updateData}
      />

      <ConfirmDiscardChangesModal
        open={discardOpen}
        onClose={() => setDiscardOpen(false)}
        onDiscard={() => {
          setDiscardOpen(false);
          builder.reset();
          onClose();
        }}
      />
    </Modal>
  );
}
