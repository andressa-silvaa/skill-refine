import { useEffect, useState } from 'react';

import { Button, Modal, ProgressBar, Stepper } from '@/shared/ui';
import type { ResumeThemeId } from '@/entities/resume';
import { useResumeBuilder, type BuilderStep } from '@/features/resume-builder';
import { useResumePreview } from '@/features/resume-preview';
import { ResumePreviewFullscreen } from '@/widgets/resume-preview';
import { AutoSaveIndicator } from './AutoSaveIndicator';
import { ResumeBuilderStepContent } from './ResumeBuilderStepContent';

import './ResumeBuilderWizard.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; themeId: ResumeThemeId }) => void;
};

export function ResumeBuilderWizard(props: Props) {
  const { open, onClose, onCreate } = props;
  const builder = useResumeBuilder();
  const preview = useResumePreview();

  useEffect(() => {
    if (!open) {
      builder.reset();
    }
  }, [open, builder]);

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
    if (builder.hasUnsavedChanges) {
      if (!window.confirm('Você tem alterações não salvas. Deseja realmente sair?')) {
        return;
      }
    }
    onClose();
  };

  const handleSaveDraft = () => {
    builder.saveDraft();
    onCreate({
      name: builder.data.targetPosition || 'Novo Currículo',
      themeId: builder.data.themeId,
    });
    handleClose();
  };

  const handleNext = () => {
    if (builder.currentStep === 'review') {
      onCreate({
        name: builder.data.targetPosition || 'Novo Currículo',
        themeId: builder.data.themeId,
      });
      handleClose();
    } else {
      builder.nextStep();
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

  return (
    <Modal open={open} title="Criar Currículo" subtitle="Preencha as informações para criar seu currículo" onClose={handleClose} width={900}>
      <div className="sr-resume-builder-wizard">
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
              if (builder.canGoToStep(targetStep)) {
                builder.goToStep(targetStep);
              }
            }}
            isStepClickable={(stepId, stepNum) => {
              const targetStep = stepId as BuilderStep;
              return stepNum <= currentStepNum || builder.canGoToStep(targetStep);
            }}
          />
        </div>

        <div className="sr-resume-builder-wizard__content">
          <ResumeBuilderStepContent builder={builder} onStepEdit={handleStepEdit} />
        </div>

        <div className="sr-resume-builder-wizard__actions">
          <div className="sr-resume-builder-wizard__actions-back">
            <Button variant="secondary" onClick={builder.currentStep === 'theme' ? handleClose : builder.prevStep}>
              {builder.currentStep === 'theme' ? 'Cancelar' : 'Voltar'}
            </Button>
          </div>

          <div className="sr-resume-builder-wizard__actions-secondary">
            {builder.currentStep !== 'review' && builder.hasUnsavedChanges ? (
              <Button variant="ghost" onClick={handleSaveDraft}>
                Salvar rascunho
              </Button>
            ) : null}
            {builder.currentStep !== 'theme' ? (
              <Button variant="ghost" onClick={() => preview.openPreview(builder.data)}>
                <i className="fa-solid fa-eye" aria-hidden />
                Visualizar
              </Button>
            ) : null}
          </div>

          <div className="sr-resume-builder-wizard__actions-primary">
            <Button variant="primary" onClick={handleNext} disabled={!builder.canGoNext}>
              {builder.currentStep === 'review' ? 'Concluir' : 'Próximo'}
              {builder.currentStep !== 'review' ? <i className="fa-solid fa-arrow-right" aria-hidden /> : null}
            </Button>
          </div>
        </div>
      </div>

      <ResumePreviewFullscreen
        open={preview.isOpen}
        data={builder.data}
        onClose={preview.closePreview}
        enableStressToggle={process.env.NODE_ENV === 'development'}
        onUpdateData={builder.updateData}
      />
    </Modal>
  );
}
