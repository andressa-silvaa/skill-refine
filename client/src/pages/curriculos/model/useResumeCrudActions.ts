import { useCallback } from 'react';

import { getResumeThemeById } from '@/entities/resume';
import type { Resume, ResumeStatus } from '@/entities/resume';
import type { ResumeDraftPayload } from '@/features/resume';
import type { BuilderStep } from '@/features/resume-builder';
import { getApiErrorMessage } from '@/shared/api';
import { notify } from '@/shared/lib/notify';

type Translator = (key: string, params?: Record<string, unknown>) => string;

type PageActions = {
  openEdit: (id: string) => void;
  setEditContext: (ctx: {
    data: ResumeDraftPayload;
    status: ResumeStatus | null;
    lastStep: BuilderStep | null;
  }) => void;
  closeEdit: () => void;
  startDuplicate: (id: string) => void;
  finishDuplicate: () => void;
  openDelete: (id: string) => void;
  closeDelete: () => void;
  startDeleting: () => void;
  finishDeleting: () => void;
  startSavingDraft: () => void;
  finishSavingDraft: () => void;
  startSubmitting: () => void;
  finishSubmitting: () => void;
};

type ResumesActions = {
  fetchById: (id: string) => Promise<{
    data: ResumeDraftPayload;
    status: ResumeStatus;
    lastStep?: string | null;
  }>;
  duplicateResume: (id: string) => Promise<unknown>;
  deleteResume: (id: string) => Promise<void>;
  updateDraft: (resumeId: string, payload: ResumeDraftPayload) => Promise<Resume>;
  createDraft: (payload: ResumeDraftPayload) => Promise<Resume>;
};

type Params = {
  duplicateLoadingId: string | null;
  deleteResumeId: string | null;
  pageActions: PageActions;
  resumes: ResumesActions;
  t: Translator;
};

export function useResumeCrudActions(params: Params) {
  const { duplicateLoadingId, deleteResumeId, pageActions, resumes, t } = params;

  const onEdit = useCallback(
    async (
      id: string,
      options?: {
        targetStep?: BuilderStep | null;
        suggestedText?: string | null;
      }
    ) => {
      pageActions.openEdit(id);
      try {
        const detail = await resumes.fetchById(id);
        const theme = getResumeThemeById(detail.data.themeId || 'classic-one-column');
        pageActions.setEditContext({
          data: {
            ...detail.data,
            themePaletteId: detail.data.themePaletteId || theme.defaultPaletteId,
          },
          status: detail.status,
          lastStep: options?.targetStep ?? ((detail.lastStep as BuilderStep) ?? null),
        });
        if (options?.suggestedText?.trim()) {
          notify.info(t('analysis.applyGuidedSuggestion', { text: options.suggestedText.trim() }));
        }
      } catch (err) {
        notify.error(getApiErrorMessage(err, t('resume.errorEditFailed')));
        pageActions.closeEdit();
      }
    },
    [pageActions, resumes, t]
  );

  const onDuplicate = useCallback(
    (id: string) => {
      if (duplicateLoadingId === id) return;
      pageActions.startDuplicate(id);
      resumes
        .duplicateResume(id)
        .then(() => notify.success(t('resume.toastDuplicated')))
        .catch((err) => notify.error(getApiErrorMessage(err, t('resume.errorDuplicateFailed'))))
        .finally(() => pageActions.finishDuplicate());
    },
    [duplicateLoadingId, pageActions, resumes, t]
  );

  const onDelete = useCallback((id: string) => pageActions.openDelete(id), [pageActions]);
  const closeDelete = useCallback(() => pageActions.closeDelete(), [pageActions]);

  const confirmDelete = useCallback(() => {
    if (!deleteResumeId) return;
    pageActions.startDeleting();
    resumes
      .deleteResume(deleteResumeId)
      .then(() => {
        pageActions.closeDelete();
        notify.success(t('resume.toastDeleted'));
      })
      .catch((err) => {
        notify.error(getApiErrorMessage(err, t('resume.errorDeleteFailed')));
      })
      .finally(() => pageActions.finishDeleting());
  }, [deleteResumeId, pageActions, resumes, t]);

  const handleSaveDraft = useCallback(
    async (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => {
      const { payload, resumeId } = data;
      pageActions.startSavingDraft();
      try {
        const resume = resumeId ? await resumes.updateDraft(resumeId, payload) : await resumes.createDraft(payload);
        notify.success(t('resume.toastDraftSaved'));
        return resume;
      } catch (err) {
        notify.error(getApiErrorMessage(err, t('resume.errorSaveDraftFailed')));
        throw err;
      } finally {
        pageActions.finishSavingDraft();
      }
    },
    [pageActions, resumes, t]
  );

  const handleFinish = useCallback(
    async (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => {
      const { payload, resumeId } = data;
      pageActions.startSubmitting();
      try {
        const resume = resumeId ? await resumes.updateDraft(resumeId, payload) : await resumes.createDraft(payload);
        notify.success(resumeId ? t('resume.toastSaved') : t('resume.toastCreated'));
        return resume;
      } catch (err) {
        notify.error(getApiErrorMessage(err, t('resume.errorSaveFailed')));
        throw err;
      } finally {
        pageActions.finishSubmitting();
      }
    },
    [pageActions, resumes, t]
  );

  return {
    onEdit,
    onDuplicate,
    onDelete,
    closeDelete,
    confirmDelete,
    handleSaveDraft,
    handleFinish,
  };
}
