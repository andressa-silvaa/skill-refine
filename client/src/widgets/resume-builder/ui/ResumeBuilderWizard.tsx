import { useEffect, useState } from 'react';

import { Button, Modal, ProgressBar, Stepper } from '@/shared/ui';
import type { ResumeThemeId } from '@/entities/resume';
import { getResumeThemeById } from '@/entities/resume';
import { useResumeBuilder, type BuilderStep } from '@/features/resume-builder';
import { useResumePreview } from '@/features/resume-preview';
import { ResumePreviewFullscreen } from '@/widgets/resume-preview';
import { ThemeSelectionStep } from './ThemeSelectionStep';
import { BasicInfoStep } from './BasicInfoStep';
import { ContactStep } from './ContactStep';
import { ExperienceStep } from './ExperienceStep';
import { EducationStep } from './EducationStep';
import { SkillsStep } from './SkillsStep';
import { LanguagesStep } from './LanguagesStep';
import { SummaryStep } from './SummaryStep';
import { ReviewStep } from './ReviewStep';
import { AutoSaveIndicator } from './AutoSaveIndicator';

import './ResumeBuilderWizard.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; themeId: ResumeThemeId }) => void;
};

const STEP_LABELS = [
  { id: 'theme', label: 'Tema' },
  { id: 'basic', label: 'Básico' },
  { id: 'contact', label: 'Contato' },
  { id: 'experience', label: 'Experiência' },
  { id: 'education', label: 'Formação' },
  { id: 'skills', label: 'Habilidades' },
  { id: 'languages', label: 'Idiomas' },
  { id: 'summary', label: 'Resumo' },
  { id: 'review', label: 'Revisão' },
];

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
      // Final step - create resume
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
    // Map section IDs to builder steps
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

  const renderStep = () => {
    switch (builder.currentStep) {
      case 'theme':
        return (
          <ThemeSelectionStep
            selectedId={builder.data.themeId}
            onSelect={(id) => {
              const theme = getResumeThemeById(id);
              builder.updateData({ themeId: id, themePaletteId: theme.defaultPaletteId });
            }}
          />
        );
      case 'basic':
        return <BasicInfoStep data={builder.data} onChange={builder.updateData} />;
      case 'contact':
        return <ContactStep contact={builder.data.contact} onChange={(contact) => builder.updateData({ contact })} />;
      case 'experience':
        return <ExperienceStep experiences={builder.data.experiences} onChange={(experiences) => builder.updateData({ experiences })} />;
      case 'education':
        return <EducationStep educations={builder.data.educations} onChange={(educations) => builder.updateData({ educations })} />;
      case 'skills':
        return <SkillsStep skills={builder.data.skills} onChange={(skills) => builder.updateData({ skills })} />;
      case 'languages':
        return <LanguagesStep languages={builder.data.languages} onChange={(languages) => builder.updateData({ languages })} />;
      case 'summary':
        return <SummaryStep summary={builder.data.summary} onChange={(summary) => builder.updateData({ summary })} />;
      case 'review':
        return <ReviewStep data={builder.data} onEdit={handleStepEdit} />;
      default:
        return null;
    }
  };

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
            steps={STEP_LABELS}
            currentStep={currentStepNum}
            onStepClick={(stepId) => {
              const targetStep = stepId as BuilderStep;
              if (builder.canGoToStep(targetStep)) {
                builder.goToStep(targetStep);
              }
            }}
            isStepClickable={(stepId, stepNum) => {
              const targetStep = stepId as BuilderStep;
              // Can click on current step or completed steps
              return stepNum <= currentStepNum || builder.canGoToStep(targetStep);
            }}
          />
        </div>

        <div className="sr-resume-builder-wizard__content">{renderStep()}</div>

        <div className="sr-resume-builder-wizard__actions">
          {/* Navegação: Voltar */}
          <div className="sr-resume-builder-wizard__actions-back">
            <Button variant="secondary" onClick={builder.currentStep === 'theme' ? handleClose : builder.prevStep}>
              {builder.currentStep === 'theme' ? 'Cancelar' : 'Voltar'}
            </Button>
          </div>

          {/* Ações secundárias: Salvar + Visualizar */}
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

          {/* CTA Principal: Próximo */}
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
