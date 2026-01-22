import { useCallback, useState } from 'react';

import type { ResumeData } from '@/entities/resume';
import { DEFAULT_RESUME_THEME_ID } from '@/entities/resume';
import { getResumeThemeById } from '@/entities/resume';
import type { BuilderStep } from './types';
import { BUILDER_STEPS } from './types';

const INITIAL_DATA: ResumeData = {
  themeId: DEFAULT_RESUME_THEME_ID,
  themePaletteId: getResumeThemeById(DEFAULT_RESUME_THEME_ID).defaultPaletteId,
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
  const [currentStep, setCurrentStep] = useState<BuilderStep>('theme');
  const [data, setData] = useState<ResumeData>(INITIAL_DATA);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const getStepOrder = useCallback((step: BuilderStep): number => {
    return BUILDER_STEPS.find((s) => s.id === step)?.order ?? 0;
  }, []);

  const canGoNext = useCallback((): boolean => {
    switch (currentStep) {
      case 'theme':
        return Boolean(data.themeId);
      case 'basic':
        return Boolean(data.targetPosition);
      case 'contact':
        return Boolean(data.contact.fullName && data.contact.email && data.contact.phone);
      case 'experience':
        return true;
      case 'education':
        return true;
      case 'skills':
        return true;
      case 'languages':
        return true;
      case 'summary':
        return true;
      case 'review':
        return false;
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
      case 'theme':
        return Boolean(data.themeId);
      case 'basic':
        return Boolean(data.targetPosition);
      case 'contact':
        return Boolean(data.contact.fullName && data.contact.email && data.contact.phone);
      case 'experience':
        return true;
      case 'education':
        return true;
      case 'skills':
        return true;
      case 'languages':
        return true;
      case 'summary':
        return true;
      case 'review':
        return true;
      default:
        return false;
    }
  }, [data]);

  const canGoToStep = useCallback((targetStep: BuilderStep): boolean => {
    const currentOrder = getStepOrder(currentStep);
    const targetOrder = getStepOrder(targetStep);
    
    if (targetOrder === currentOrder) return true;
    
    if (targetOrder < currentOrder) return true;
    
    if (targetOrder === currentOrder + 1) {
      switch (currentStep) {
        case 'theme':
          return Boolean(data.themeId);
        case 'basic':
          return Boolean(data.targetPosition);
        case 'contact':
          return Boolean(data.contact.fullName && data.contact.email && data.contact.phone);
        default:
          return true;
      }
    }
    
    for (let i = currentOrder + 1; i < targetOrder; i++) {
      const step = BUILDER_STEPS.find((s) => s.order === i);
      if (step && !isStepComplete(step.id)) {
        return false;
      }
    }
    
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
  }, []);

  const reset = useCallback(() => {
    setCurrentStep('theme');
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
