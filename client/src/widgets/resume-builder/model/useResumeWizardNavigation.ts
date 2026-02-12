import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { calculateCompletenessScore } from '@/entities/resume';
import type { ResumeDraftPayload } from '@/features/resume';
import { getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';

import type { BuilderStep } from '@/features/resume-builder';

type BuilderLike = {
  currentStep: BuilderStep;
  data: import('@/entities/resume').ResumeData;
  resumeId: string | null;
  steps: { id: string; order: number }[];
  tryNavigateToStep: (step: BuilderStep) => boolean;
  validateAll: () => { isValid: boolean; errors: Record<string, string> };
  getFirstErrorStep: (errors: Record<string, string>) => BuilderStep | null | undefined;
  goToStep: (step: BuilderStep) => void;
  markStepSubmitted: (step: BuilderStep) => void;
  setResumeId: (id: string) => void;
  setServerErrors: (errors: Record<string, string>) => void;
};

type Options = {
  builder: BuilderLike;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onFinish: (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => Promise<{ id: string }>;
  skipDiscardAndClose: () => void;
};

/**
 * Single source of truth for navigation: validateAndNavigate is used by both
 * the "Next" button and the stepper click. No path bypasses validation.
 */
export function useResumeWizardNavigation(options: Options) {
  const { builder, containerRef, onFinish, skipDiscardAndClose } = options;
  const { t } = useTranslation();

  const focusFirstError = useCallback(() => {
    window.setTimeout(() => {
      const container = containerRef.current ?? document;
      const invalidElement = container.querySelector<HTMLElement>(
        '.is-invalid, [aria-invalid="true"]'
      );
      if (!invalidElement) return;
      invalidElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (typeof invalidElement.focus === 'function') {
        invalidElement.focus();
      }
    }, 0);
  }, [containerRef]);

  const validateAndNavigate = useCallback(
    (targetStep: BuilderStep): boolean => {
      const ok = builder.tryNavigateToStep(targetStep);
      if (!ok) focusFirstError();
      return ok;
    },
    [builder, focusFirstError]
  );

  const handleNext = useCallback(async () => {
    if (builder.currentStep === 'review') {
      const validation = builder.validateAll();
      if (!validation.isValid) {
        const firstStep = builder.getFirstErrorStep(validation.errors);
        if (firstStep) {
          builder.goToStep(firstStep);
          builder.markStepSubmitted(firstStep);
        }
        notify.error(t('resume.builderReviewRequired'));
        focusFirstError();
        return;
      }
      const payload: ResumeDraftPayload = {
        ...builder.data,
        name: builder.data.targetPosition || t('resume.builderDefaultName'),
        status: 'complete',
        lastStep: 'review',
        score: calculateCompletenessScore(builder.data),
      };
      try {
        const resume = await onFinish({ payload, resumeId: builder.resumeId });
        builder.setResumeId(resume.id);
        skipDiscardAndClose();
        return;
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
      }
      return;
    }

    const currentOrder = builder.steps.find((s) => s.id === builder.currentStep)?.order ?? 0;
    const nextStep = builder.steps.find((s) => s.order === currentOrder + 1)?.id as
      | BuilderStep
      | undefined;
    if (nextStep && !validateAndNavigate(nextStep)) {
      focusFirstError();
    }
  }, [
    builder,
    onFinish,
    skipDiscardAndClose,
    t,
    validateAndNavigate,
    focusFirstError,
  ]);

  const handleStepEdit = useCallback(
    (stepId: string) => {
      const stepEditMap: Record<string, BuilderStep> = {
        basic: 'basic',
        contact: 'contact',
        experience: 'experience',
        education: 'education',
        skills: 'skills',
        languages: 'languages',
        summary: 'summary',
      };
      const targetStep = stepEditMap[stepId];
      if (targetStep) builder.goToStep(targetStep);
    },
    [builder]
  );

  return {
    validateAndNavigate,
    handleNext,
    focusFirstError,
    handleStepEdit,
  };
}
