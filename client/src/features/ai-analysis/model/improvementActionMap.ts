import { resumeApi } from '@/features/resume';

import type { ImprovementInsightItem } from './types';

export type ResumeTargetStep =
  | 'basic'
  | 'contact'
  | 'experience'
  | 'education'
  | 'skills'
  | 'languages'
  | 'summary'
  | 'review';

type ImprovementApplyMode = 'guided' | 'auto_contact_links';
type ExampleMode = 'single' | 'before_after';

type ImprovementActionConfig = {
  targetStep: ResumeTargetStep;
  targetField?: string;
  applyMode: ImprovementApplyMode;
  exampleMode: ExampleMode;
  beforeExampleKey?: string;
  afterExampleKey?: string;
  singleExampleKey?: string;
};

export type ResolvedExampleContent =
  | {
      mode: 'single';
      text: string;
    }
  | {
      mode: 'before_after';
      before: string;
      after: string;
    };

const DEFAULT_ACTION: ImprovementActionConfig = {
  targetStep: 'review',
  applyMode: 'guided',
  exampleMode: 'single',
  singleExampleKey: 'analysis.improvementExamples.fallback.single',
};

function ensureTrailingPeriod(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  const lastChar = trimmed.charAt(trimmed.length - 1);
  if (lastChar === '.' || lastChar === '!' || lastChar === '?' || lastChar === '…') {
    return trimmed;
  }
  return `${trimmed}.`;
}

const IMPROVEMENT_ACTIONS: Record<string, ImprovementActionConfig> = {
  'analysis.insights.improvements.add_metrics': {
    targetStep: 'experience',
    targetField: 'experiences.description',
    applyMode: 'guided',
    exampleMode: 'before_after',
    beforeExampleKey: 'analysis.improvementExamples.addMetrics.before',
    afterExampleKey: 'analysis.improvementExamples.addMetrics.after',
  },
  'analysis.insights.improvements.use_action_verbs': {
    targetStep: 'experience',
    targetField: 'experiences.description',
    applyMode: 'guided',
    exampleMode: 'before_after',
    beforeExampleKey: 'analysis.improvementExamples.actionVerbs.before',
    afterExampleKey: 'analysis.improvementExamples.actionVerbs.after',
  },
  'analysis.insights.improvements.action_verbs': {
    targetStep: 'experience',
    targetField: 'experiences.description',
    applyMode: 'guided',
    exampleMode: 'before_after',
    beforeExampleKey: 'analysis.improvementExamples.actionVerbs.before',
    afterExampleKey: 'analysis.improvementExamples.actionVerbs.after',
  },
  'analysis.insights.improvements.improve_summary': {
    targetStep: 'summary',
    targetField: 'summary',
    applyMode: 'guided',
    exampleMode: 'before_after',
    beforeExampleKey: 'analysis.improvementExamples.improveSummary.before',
    afterExampleKey: 'analysis.improvementExamples.improveSummary.after',
  },
  'analysis.insights.improvements.executive_summary': {
    targetStep: 'summary',
    targetField: 'summary',
    applyMode: 'guided',
    exampleMode: 'before_after',
    beforeExampleKey: 'analysis.improvementExamples.executiveSummary.before',
    afterExampleKey: 'analysis.improvementExamples.executiveSummary.after',
  },
  'analysis.insights.improvements.relevant_links': {
    targetStep: 'contact',
    targetField: 'contact.linkedin',
    applyMode: 'auto_contact_links',
    exampleMode: 'single',
    singleExampleKey: 'analysis.improvementExamples.relevantLinks.single',
  },
  'analysis.insights.improvements.ats_keywords': {
    targetStep: 'skills',
    targetField: 'skills',
    applyMode: 'guided',
    exampleMode: 'single',
    singleExampleKey: 'analysis.improvementExamples.atsKeywords.single',
  },
  'analysis.insights.improvements.clarity_conciseness': {
    targetStep: 'experience',
    targetField: 'experiences.description',
    applyMode: 'guided',
    exampleMode: 'single',
    singleExampleKey: 'analysis.improvementExamples.clarity.single',
  },
};

const SECTION_TO_STEP: Record<string, ResumeTargetStep> = {
  basic: 'basic',
  contact: 'contact',
  experience: 'experience',
  education: 'education',
  skills: 'skills',
  languages: 'languages',
  summary: 'summary',
  review: 'review',
};

function toStepFromSection(section?: string): ResumeTargetStep | null {
  if (!section) return null;
  const normalized = section.trim().toLowerCase();
  return SECTION_TO_STEP[normalized] ?? null;
}

export function resolveImprovementAction(item: ImprovementInsightItem): ImprovementActionConfig {
  const mapped = IMPROVEMENT_ACTIONS[item.key];
  if (mapped) {
    return {
      ...mapped,
      targetStep: toStepFromSection(item.section) ?? mapped.targetStep,
      targetField: item.fieldTarget ?? mapped.targetField,
      applyMode:
        item.actionType === 'auto_apply_contact_links'
          ? 'auto_contact_links'
          : item.actionType === 'guided_edit'
            ? 'guided'
            : mapped.applyMode,
    };
  }

  return {
    ...DEFAULT_ACTION,
    targetStep: toStepFromSection(item.section) ?? DEFAULT_ACTION.targetStep,
    targetField: item.fieldTarget ?? DEFAULT_ACTION.targetField,
  };
}

export function resolveExampleContent(
  item: ImprovementInsightItem,
  t: (key: string, params?: Record<string, string>) => string
): ResolvedExampleContent {
  const config = resolveImprovementAction(item);

  if (config.exampleMode === 'before_after' && config.beforeExampleKey && config.afterExampleKey) {
    const beforeText = t(config.beforeExampleKey, item.params);
    const afterText = item.exampleText || t(config.afterExampleKey, item.params);
    return {
      mode: 'before_after',
      before: ensureTrailingPeriod(beforeText),
      after: ensureTrailingPeriod(afterText),
    };
  }

  const singleText = item.exampleText || t(config.singleExampleKey ?? DEFAULT_ACTION.singleExampleKey!, item.params);
  return {
    mode: 'single',
    text: ensureTrailingPeriod(singleText),
  };
}

type ContactPatch = {
  linkedin?: string;
  github?: string;
  portfolio?: string;
  website?: string;
};

function resolveDomainField(value: string): keyof ContactPatch | null {
  const normalized = value.toLowerCase();
  if (normalized.includes('github.com')) return 'github';
  if (normalized.includes('linkedin.com')) return 'linkedin';
  return null;
}

function buildContactPatch(params?: Record<string, string>): ContactPatch {
  if (!params) return {};
  const patch: ContactPatch = {};
  const directFields: Array<keyof ContactPatch> = ['linkedin', 'github', 'portfolio', 'website'];
  for (const field of directFields) {
    const value = params[field]?.trim();
    if (value) patch[field] = value;
  }

  const genericLink = params.link?.trim();
  if (genericLink) {
    const field = resolveDomainField(genericLink);
    if (field && !patch[field]) {
      patch[field] = genericLink;
    }
  }

  return patch;
}

export async function tryAutoApplyImprovement(
  resumeId: string,
  item: ImprovementInsightItem
): Promise<boolean> {
  const config = resolveImprovementAction(item);
  if (config.applyMode !== 'auto_contact_links') return false;

  const patch = buildContactPatch(item.params);
  if (Object.keys(patch).length === 0) return false;

  const detail = await resumeApi.get(resumeId);
  const current = detail.data.contact;
  const merged = { ...current, ...patch };

  const hasChanges = Object.entries(patch).some(([key, value]) => current[key as keyof typeof current] !== value);
  if (!hasChanges) return false;

  await resumeApi.update(resumeId, {
    ...detail.data,
    contact: merged,
    name: detail.name,
    status: detail.status,
    lastStep: 'contact',
  });

  return true;
}
