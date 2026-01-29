import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { ResumeData } from '@/entities/resume';
import { DEFAULT_RESUME_THEME_ID } from '@/entities/resume';
import { getResumeThemeById } from '@/entities/resume';
import type { BuilderStep } from './types';
import { BUILDER_STEPS } from './types';
import { getFirstErrorForStep, getFirstErrorStep, validateResume, validateStep } from './validation/validate';

const normalizeText = (value: string | undefined) => (value ?? '').trim();

const normalizeResumeData = (input: ResumeData) => {
  const themeId = input.themeId || DEFAULT_RESUME_THEME_ID;
  const theme = getResumeThemeById(themeId);
  const themePaletteId = input.themePaletteId || theme.defaultPaletteId;

  return {
    themeId,
    themePaletteId,
    // Removido suporte a cores personalizadas: mantemos sempre undefined
    themeAccentOverride: undefined,
    themeSecondaryOverride: undefined,
    targetPosition: normalizeText(input.targetPosition),
    summary: normalizeText(input.summary),
    contact: {
      fullName: normalizeText(input.contact.fullName),
      email: normalizeText(input.contact.email),
      phone: normalizeText(input.contact.phone),
      city: normalizeText(input.contact.city),
      country: normalizeText(input.contact.country),
      linkedin: normalizeText(input.contact.linkedin),
      portfolio: normalizeText(input.contact.portfolio),
      github: normalizeText(input.contact.github),
      website: normalizeText(input.contact.website),
    },
    experiences: input.experiences.map((exp) => ({
      company: normalizeText(exp.company),
      position: normalizeText(exp.position),
      startDate: normalizeText(exp.startDate),
      endDate: normalizeText(exp.endDate),
      isCurrent: Boolean(exp.isCurrent),
      description: exp.description.map((item) => normalizeText(item)),
    })),
    educations: input.educations.map((edu) => ({
      institution: normalizeText(edu.institution),
      course: normalizeText(edu.course),
      degree: normalizeText(edu.degree),
      startDate: normalizeText(edu.startDate),
      endDate: normalizeText(edu.endDate),
      status: edu.status,
    })),
    skills: input.skills.map((skill) => ({
      name: normalizeText(skill.name),
      level: skill.level ?? '',
    })),
    languages: input.languages.map((lang) => ({
      name: normalizeText(lang.name),
      level: lang.level,
    })),
  };
};

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
  const { t } = useTranslation();
  const [currentStep, setCurrentStep] = useState<BuilderStep>('theme');
  const [data, setData] = useState<ResumeData>(INITIAL_DATA);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [touchedFields, setTouchedFields] = useState<Record<string, boolean>>({});
  const [submittedSteps, setSubmittedSteps] = useState<Partial<Record<BuilderStep, boolean>>>({});
  const [showSkillLevels, setShowSkillLevels] = useState(false);
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [initialSnapshot, setInitialSnapshot] = useState<string>(() => JSON.stringify(normalizeResumeData(INITIAL_DATA)));

  const validationOptions = useMemo(() => ({ showSkillLevels }), [showSkillLevels]);

  const currentValidation = useMemo(
    () => validateStep(currentStep, data, validationOptions, t),
    [currentStep, data, validationOptions, t],
  );

  const currentSnapshot = useMemo(() => JSON.stringify(normalizeResumeData(data)), [data]);
  const isDirty = currentSnapshot !== initialSnapshot;

  const getStepOrder = useCallback((step: BuilderStep): number => {
    return BUILDER_STEPS.find((s) => s.id === step)?.order ?? 0;
  }, []);

  const canGoNext = useCallback((): boolean => true, []);

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

  const isStepComplete = useCallback(
    (step: BuilderStep): boolean => validateStep(step, data, validationOptions, t).isValid,
    [data, validationOptions, t],
  );

  const canGoToStep = useCallback((targetStep: BuilderStep): boolean => {
    const currentOrder = getStepOrder(currentStep);
    const targetOrder = getStepOrder(targetStep);

    if (targetOrder === currentOrder) return true;

    if (targetOrder < currentOrder) return true;

    if (targetOrder === currentOrder + 1) {
      return isStepComplete(currentStep);
    }

    for (let i = currentOrder + 1; i < targetOrder; i++) {
      const step = BUILDER_STEPS.find((s) => s.order === i);
      if (step && !isStepComplete(step.id)) {
        return false;
      }
    }

    return isStepComplete(targetStep);
  }, [currentStep, getStepOrder, isStepComplete]);

  const goToStep = useCallback((step: BuilderStep) => {
    if (canGoToStep(step)) {
      setCurrentStep(step);
    }
  }, [canGoToStep]);

  const tryNavigateToStep = useCallback(
    (targetStep: BuilderStep): boolean => {
      const currentOrder = getStepOrder(currentStep);
      const targetOrder = getStepOrder(targetStep);

      if (targetOrder <= currentOrder) {
        setCurrentStep(targetStep);
        return true;
      }

      const validation = validateStep(currentStep, data, validationOptions, t);
      if (!validation.isValid) {
        setSubmittedSteps((prev) => ({ ...prev, [currentStep]: true }));
        return false;
      }
      setCurrentStep(targetStep);
      return true;
    },
    [currentStep, data, getStepOrder, validationOptions, t],
  );

  const updateData = useCallback((updates: Partial<ResumeData>) => {
    setData((prev) => ({ ...prev, ...updates }));
    setHasUnsavedChanges(true);
  }, []);

  const hydrate = useCallback((next: ResumeData, nextResumeId: string | null, initialStep: BuilderStep = 'theme') => {
    const normalizedThemeId = next.themeId || DEFAULT_RESUME_THEME_ID;
    const theme = getResumeThemeById(normalizedThemeId);
    const normalizedPaletteId = next.themePaletteId || theme.defaultPaletteId;

    const normalized = {
      ...next,
      themeId: normalizedThemeId,
      themePaletteId: normalizedPaletteId,
      themeAccentOverride: undefined,
      themeSecondaryOverride: undefined,
    };

    setCurrentStep(initialStep);
    setData(normalized);
    setResumeId(nextResumeId);
    setTouchedFields({});
    setSubmittedSteps({});
    setHasUnsavedChanges(false);
    setLastSaved(null);
    setShowSkillLevels(next.skills.some((skill) => Boolean(skill.level)));
    setServerErrors({});
    setInitialSnapshot(JSON.stringify(normalizeResumeData(normalized)));
  }, []);

  const markFieldTouched = useCallback((path: string) => {
    setTouchedFields((prev) => (prev[path] ? prev : { ...prev, [path]: true }));
  }, []);

  const markStepSubmitted = useCallback((step: BuilderStep) => {
    setSubmittedSteps((prev) => ({ ...prev, [step]: true }));
  }, []);

  const shouldShowError = useCallback(
    (path: string, step: BuilderStep = currentStep) => Boolean(submittedSteps[step] || touchedFields[path]),
    [currentStep, submittedSteps, touchedFields],
  );

  const validateCurrentStep = useCallback(() => {
    const result = validateStep(currentStep, data, validationOptions, t);
    if (!result.isValid) {
      setSubmittedSteps((prev) => ({ ...prev, [currentStep]: true }));
    } else {
      updateData(result.data as Partial<ResumeData>);
      if (Object.keys(serverErrors).length) setServerErrors({});
    }
    return result;
  }, [currentStep, data, updateData, validationOptions, serverErrors, t]);

  const validateAll = useCallback(() => {
    const result = validateResume(data, validationOptions, t);
    if (result.isValid) {
      updateData(result.data as Partial<ResumeData>);
      if (Object.keys(serverErrors).length) setServerErrors({});
    }
    return result;
  }, [data, updateData, validationOptions, serverErrors, t]);

  const saveDraft = useCallback(() => {
    setLastSaved(new Date());
    setHasUnsavedChanges(false);
    setInitialSnapshot(currentSnapshot);
  }, []);

  const reset = useCallback(() => {
    setCurrentStep('theme');
    setData(INITIAL_DATA);
    setResumeId(null);
    setLastSaved(null);
    setHasUnsavedChanges(false);
    setTouchedFields({});
    setSubmittedSteps({});
    setShowSkillLevels(false);
    setServerErrors({});
    setInitialSnapshot(JSON.stringify(normalizeResumeData(INITIAL_DATA)));
  }, []);

  return {
    currentStep,
    data,
    resumeId,
    lastSaved,
    hasUnsavedChanges,
    steps: BUILDER_STEPS,
    canGoNext: canGoNext(),
    errors: currentValidation.errors,
    serverErrors,
    hasStepErrors: !currentValidation.isValid,
    isDirty,
    touchedFields,
    submittedSteps,
    showSkillLevels,
    setShowSkillLevels,
    isStepComplete,
    canGoToStep,
    nextStep,
    prevStep,
    goToStep,
    tryNavigateToStep,
    updateData,
    hydrate,
    setResumeId,
    saveDraft,
    markFieldTouched,
    markStepSubmitted,
    shouldShowError,
    validateCurrentStep,
    validateAll,
    getFirstErrorForStep,
    getFirstErrorStep,
    setServerErrors,
    reset,
  };
}
