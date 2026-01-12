import { useCallback, useState } from 'react';

import type { ResumeData, ResumeTemplateId } from '@/entities/resume';
import type { BuilderStep, StepConfig } from './types';
import { BUILDER_STEPS } from './types';

const INITIAL_DATA: ResumeData = {
  templateId: 'tech',
  targetPosition: '',
  contact: {
    fullName: '',
    email: '',
    phone: '',
    city: '',
    country: '',
  },
  experiences: [],
  educations: [],
  skills: [],
  languages: [],
  summary: '',
};

export function useResumeBuilder() {
  const [currentStep, setCurrentStep] = useState<BuilderStep>('template');
  const [data, setData] = useState<ResumeData>(INITIAL_DATA);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const getStepOrder = useCallback((step: BuilderStep): number => {
    return BUILDER_STEPS.find((s) => s.id === step)?.order ?? 0;
  }, []);

  const canGoNext = useCallback((): boolean => {
    switch (currentStep) {
      case 'template':
        return Boolean(data.templateId);
      case 'basic':
        return Boolean(data.targetPosition);
      case 'contact':
        return Boolean(data.contact.fullName && data.contact.email && data.contact.phone);
      case 'experience':
        return true; // Optional step
      case 'education':
        return true; // Optional step
      case 'skills':
        return true; // Optional step
      case 'languages':
        return true; // Optional step
      case 'summary':
        return true; // Optional step
      case 'review':
        return false; // Final step
      default:
        return false;
    }
  }, [currentStep, data]);

  const nextStep = useCallback(() => {
    if (!canGoNext()) return;
    const currentOrder = getStepOrder(currentStep);
    const next = BUILDER_STEPS.find((s) => s.order === currentOrder + 1);
    if (next) setCurrentStep(next.id);
  }, [currentStep, canGoNext, getStepOrder]);

  const prevStep = useCallback(() => {
    const currentOrder = getStepOrder(currentStep);
    const prev = BUILDER_STEPS.find((s) => s.order === currentOrder - 1);
    if (prev) setCurrentStep(prev.id);
  }, [currentStep, getStepOrder]);

  const isStepComplete = useCallback((step: BuilderStep): boolean => {
    switch (step) {
      case 'template':
        return Boolean(data.templateId);
      case 'basic':
        return Boolean(data.targetPosition);
      case 'contact':
        return Boolean(data.contact.fullName && data.contact.email && data.contact.phone);
      case 'experience':
        return true; // Optional, always accessible
      case 'education':
        return true; // Optional, always accessible
      case 'skills':
        return true; // Optional, always accessible
      case 'languages':
        return true; // Optional, always accessible
      case 'summary':
        return true; // Optional, always accessible
      case 'review':
        return true; // Can always go to review
      default:
        return false;
    }
  }, [data]);

  const canGoToStep = useCallback((targetStep: BuilderStep): boolean => {
    const currentOrder = getStepOrder(currentStep);
    const targetOrder = getStepOrder(targetStep);
    
    // Can always go to current step
    if (targetOrder === currentOrder) return true;
    
    // Can go to previous steps (already visited)
    if (targetOrder < currentOrder) return true;
    
    // Can go to next step if current is complete
    if (targetOrder === currentOrder + 1) {
      // Check if current step requirements are met
      switch (currentStep) {
        case 'template':
          return Boolean(data.templateId);
        case 'basic':
          return Boolean(data.targetPosition);
        case 'contact':
          return Boolean(data.contact.fullName && data.contact.email && data.contact.phone);
        default:
          return true; // Optional steps
      }
    }
    
    // Can go to any step if all previous steps are complete
    for (let i = currentOrder + 1; i < targetOrder; i++) {
      const step = BUILDER_STEPS.find((s) => s.order === i);
      if (step && !isStepComplete(step.id)) {
        return false;
      }
    }
    
    // Can go if target step is complete or optional
    return isStepComplete(targetStep);
  }, [currentStep, data, getStepOrder, isStepComplete]);

  const goToStep = useCallback((step: BuilderStep) => {
    if (canGoToStep(step)) {
      setCurrentStep(step);
    }
  }, [canGoToStep]);

  const updateData = useCallback((updates: Partial<ResumeData>) => {
    setData((prev) => ({ ...prev, ...updates }));
    setHasUnsavedChanges(true);
  }, []);

  const saveDraft = useCallback(() => {
    setLastSaved(new Date());
    setHasUnsavedChanges(false);
    // TODO: Save to backend
  }, []);

  const reset = useCallback(() => {
    setCurrentStep('template');
    setData(INITIAL_DATA);
    setLastSaved(null);
    setHasUnsavedChanges(false);
  }, []);

  return {
    currentStep,
    data,
    lastSaved,
    hasUnsavedChanges,
    steps: BUILDER_STEPS,
    canGoNext: canGoNext(),
    isStepComplete,
    canGoToStep,
    nextStep,
    prevStep,
    goToStep,
    updateData,
    saveDraft,
    reset,
  };
}
