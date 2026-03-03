import { useEffect, useRef } from 'react';

import type { ResumeData, ResumeStatus } from '@/entities/resume';
import type { BuilderStep } from '@/features/resume-builder';

type BuilderLike = {
  hydrate: (data: ResumeData, resumeId: string | null, step: BuilderStep) => void;
  reset: () => void;
};

function inferStepFromData(data: ResumeData): BuilderStep {
  if (!data.themeId) return 'theme';
  if (!data.targetPosition) return 'basic';
  if (!data.contact.fullName || !data.contact.email) return 'contact';
  if (!data.experiences.length) return 'experience';
  if (!data.educations.length) return 'education';
  if (!data.skills.length) return 'skills';
  if (!data.languages.length) return 'languages';
  if (!data.summary) return 'summary';
  return 'review';
}

type Options = {
  open: boolean;
  initialData: ResumeData | null | undefined;
  initialResumeId: string | null | undefined;
  initialStatus: ResumeStatus | null | undefined;
  initialLastStep: BuilderStep | null | undefined;
  builder: BuilderLike;
};

export function useResumeWizardHydration(options: Options) {
  const {
    open,
    initialData,
    initialResumeId,
    initialStatus,
    initialLastStep,
    builder,
  } = options;
  const hydratedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open || !initialData) return;
    const key = `${initialResumeId ?? 'new'}:${initialStatus ?? ''}:${initialLastStep ?? ''}`;
    if (hydratedRef.current === key) return;
    hydratedRef.current = key;

    let step: BuilderStep = 'theme';
    if (initialLastStep) {
      step = initialLastStep;
    } else if (initialStatus === 'complete') {
      step = 'review';
    } else {
      step = inferStepFromData(initialData);
    }

    builder.hydrate(initialData, initialResumeId ?? null, step);
  }, [open, initialData, initialResumeId, initialStatus, initialLastStep, builder]);

  const prevOpenRef = useRef(false);
  useEffect(() => {
    if (prevOpenRef.current && !open) {
      hydratedRef.current = null;
      builder.reset();
    }
    prevOpenRef.current = open;
  }, [open, builder]);
}
