import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useResumes } from '@/features/resume';
import { useLatestAnalyses } from '@/features/ai-analysis';
import { getResumeThemeById } from '@/entities/resume';
import type { BuilderStep } from '@/features/resume-builder';
import { downloadBlob } from '@/shared/lib/download/download';
import type { ResumeDraftPayload } from '@/features/resume';
import { notify } from '@/shared/lib/notify';
import { getApiErrorMessage } from '@/shared/api';
import {
  ConfirmDeleteResumeModal,
  ResumesEmpty,
  ResumesGrid,
  ResumesHeader,
  ResumesList,
  ResumesSkeleton,
  ResumesToolbar,
} from '@/widgets/resumes';
import { ResumeBuilderWizard } from '@/widgets/resume-builder';
import { AppShell } from '@/widgets/app-shell';
import { Modal, ProgressBar } from '@/shared/ui';

import { useResumesPageState } from '../model/useResumesPageState';

import '@/shared/ui/sr-controls/SrControls.css';
import './ResumesPage.css';

export function ResumesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const resumes = useResumes();
  const { state: pageState, actions: pageActions } = useResumesPageState();
  const handledApplyContextRef = useRef<string | null>(null);

  const resumeIds = useMemo(() => resumes.viewModels.map((vm) => vm.id), [resumes.viewModels]);
  const analysisByResumeId = useLatestAnalyses(resumeIds);

  const onAnalyzeWithAI = useCallback(
    (id: string) => {
      navigate(`/protected/ai-analysis?resumeId=${encodeURIComponent(id)}`);
    },
    [navigate]
  );

  const pdfVm = useMemo(
    () =>
      pageState.downloadLoadingId
        ? resumes.viewModels.find((item) => item.id === pageState.downloadLoadingId)
        : null,
    [pageState.downloadLoadingId, resumes.viewModels]
  );

  const pdfProgressRef = useRef(0);
  useEffect(() => {
    if (!pageState.downloadLoadingId) {
      pageActions.setPdfProgress(0);
      pdfProgressRef.current = 0;
      return;
    }
    pageActions.setPdfProgress(8);
    pdfProgressRef.current = 8;
    const interval = window.setInterval(() => {
      if (pdfProgressRef.current >= 92) return;
      const step = 3 + Math.floor(Math.random() * 6);
      pdfProgressRef.current = Math.min(92, pdfProgressRef.current + step);
      pageActions.setPdfProgress(pdfProgressRef.current);
    }, 450);
    return () => window.clearInterval(interval);
  }, [pageState.downloadLoadingId, pageActions.setPdfProgress]);

  useEffect(() => {
    if (resumes.error) {
      notify.error(getApiErrorMessage(resumes.error, t('resume.errorLoadFailed')));
    }
  }, [resumes.error, t]);

  const openFilters = useCallback(() => {
    notify.info(t('resume.filtersComingSoon'));
  }, [t]);

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
        const theme = getResumeThemeById(detail.data.themeId);
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
    [pageActions, resumes.fetchById, t]
  );

  useEffect(() => {
    const editResumeId = searchParams.get('editResumeId');
    if (!editResumeId) return;

    const targetStepParam = searchParams.get('targetStep');
    const suggestedText = searchParams.get('suggestedText');
    const allSteps: BuilderStep[] = ['theme', 'basic', 'contact', 'experience', 'education', 'skills', 'languages', 'summary', 'review'];
    const targetStep = targetStepParam && allSteps.includes(targetStepParam as BuilderStep)
      ? (targetStepParam as BuilderStep)
      : null;

    const contextKey = `${editResumeId}:${targetStep ?? ''}:${suggestedText ?? ''}`;
    if (handledApplyContextRef.current === contextKey) return;
    handledApplyContextRef.current = contextKey;

    void onEdit(editResumeId, {
      targetStep,
      suggestedText,
    });

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('editResumeId');
    nextParams.delete('targetStep');
    nextParams.delete('fieldTarget');
    nextParams.delete('improvementKey');
    nextParams.delete('suggestedText');
    setSearchParams(nextParams, { replace: true });
  }, [onEdit, searchParams, setSearchParams]);

  const onDuplicate = useCallback(
    (id: string) => {
      if (pageState.duplicateLoadingId === id) return;
      pageActions.startDuplicate(id);
      resumes
        .duplicateResume(id)
        .then(() => notify.success(t('resume.toastDuplicated')))
        .catch((err) => notify.error(getApiErrorMessage(err, t('resume.errorDuplicateFailed'))))
        .finally(() => pageActions.finishDuplicate());
    },
    [pageState.duplicateLoadingId, pageActions, resumes.duplicateResume, t]
  );

  const onExport = useCallback(
    (id: string) => {
      if (pageState.downloadLoadingId === id) return;
      pageActions.startDownload(id);
      const vm = resumes.viewModels.find((item) => item.id === id);
      const baseName = vm?.name?.trim() || 'Curriculo';
      const dateLabel = new Date().toISOString().slice(0, 10);
      const fallbackName = `Curriculo_${baseName}_${dateLabel}.pdf`;
      resumes
        .downloadPdf(id)
        .then(({ blob, filename }) => {
          downloadBlob(blob, filename || fallbackName);
          notify.success(t('resume.toastDownloadDone'));
          pageActions.setPdfProgress(100);
        })
        .catch((err) => {
          notify.error(getApiErrorMessage(err, t('resume.errorPdfFailed')));
        })
        .finally(() => {
          window.setTimeout(() => pageActions.finishDownload(), 450);
        });
    },
    [pageState.downloadLoadingId, pageActions, resumes.downloadPdf, resumes.viewModels, t]
  );

  const onDelete = useCallback((id: string) => pageActions.openDelete(id), [pageActions]);
  const closeDelete = useCallback(() => pageActions.closeDelete(), [pageActions]);

  const confirmDelete = useCallback(() => {
    if (!pageState.deleteResumeId) return;
    pageActions.startDeleting();
    resumes
      .deleteResume(pageState.deleteResumeId)
      .then(() => {
        pageActions.closeDelete();
        notify.success(t('resume.toastDeleted'));
      })
      .catch((err) => {
        notify.error(getApiErrorMessage(err, t('resume.errorDeleteFailed')));
      })
      .finally(() => pageActions.finishDeleting());
  }, [pageState.deleteResumeId, pageActions, resumes.deleteResume, t]);

  const handleSaveDraft = useCallback(
    async (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => {
      const { payload, resumeId } = data;
      pageActions.startSavingDraft();
      try {
        const resume = resumeId
          ? await resumes.updateDraft(resumeId, payload)
          : await resumes.createDraft(payload);
        notify.success(t('resume.toastDraftSaved'));
        return resume;
      } catch (err) {
        notify.error(getApiErrorMessage(err, t('resume.errorSaveDraftFailed')));
        throw err;
      } finally {
        pageActions.finishSavingDraft();
      }
    },
    [pageActions, resumes.updateDraft, resumes.createDraft, t]
  );

  const handleFinish = useCallback(
    async (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => {
      const { payload, resumeId } = data;
      pageActions.startSubmitting();
      try {
        const resume = resumeId
          ? await resumes.updateDraft(resumeId, payload)
          : await resumes.createDraft(payload);
        notify.success(resumeId ? t('resume.toastSaved') : t('resume.toastCreated'));
        return resume;
      } catch (err) {
        notify.error(getApiErrorMessage(err, t('resume.errorSaveFailed')));
        throw err;
      } finally {
        pageActions.finishSubmitting();
      }
    },
    [pageActions, resumes.updateDraft, resumes.createDraft, t]
  );

  return (
    <AppShell>
      <main className="sr-resumes" aria-label={t('resume.mainAria')}>
        <ResumesHeader onCreate={pageActions.openCreate} />

        <ResumesToolbar
          query={resumes.query}
          onQueryChange={resumes.setQuery}
          view={resumes.view}
          onViewChange={resumes.setView}
          sort={resumes.sort}
          onSortChange={resumes.setSort}
          onOpenFilters={openFilters}
        />

        <section className="sr-resumes__content">
          {resumes.loading ? (
            <ResumesSkeleton view={resumes.view} />
          ) : resumes.viewModels.length === 0 ? (
            <ResumesEmpty onCreate={pageActions.openCreate} />
          ) : resumes.view === 'grid' ? (
            <ResumesGrid
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
              onAnalyzeWithAI={onAnalyzeWithAI}
              duplicateLoadingId={pageState.duplicateLoadingId}
              downloadLoadingId={pageState.downloadLoadingId}
              analysisByResumeId={analysisByResumeId}
            />
          ) : (
            <ResumesList
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
              onAnalyzeWithAI={onAnalyzeWithAI}
              duplicateLoadingId={pageState.duplicateLoadingId}
              downloadLoadingId={pageState.downloadLoadingId}
              analysisByResumeId={analysisByResumeId}
            />
          )}
        </section>

        <ResumeBuilderWizard
          title={t('resume.createTitle')}
          open={pageState.createOpen}
          onClose={pageActions.closeCreate}
          onSaveDraft={handleSaveDraft}
          onFinish={handleFinish}
          isSavingDraft={pageState.isSavingDraft}
          isSubmitting={pageState.isSubmitting}
        />

        <ResumeBuilderWizard
          title={t('resume.editTitle')}
          open={pageState.editOpen}
          onClose={pageActions.closeEdit}
          onSaveDraft={handleSaveDraft}
          onFinish={handleFinish}
          isSavingDraft={pageState.isSavingDraft}
          isSubmitting={pageState.isSubmitting}
          isLoading={pageState.editLoading}
          initialData={pageState.editData}
          initialResumeId={pageState.editResumeId}
          initialStatus={pageState.editStatus}
          initialLastStep={pageState.editLastStep}
        />

        <ConfirmDeleteResumeModal
          open={Boolean(pageState.deleteResumeId)}
          onClose={closeDelete}
          onConfirm={confirmDelete}
          isLoading={pageState.isDeleting}
        />

        <Modal
          open={Boolean(pageState.downloadLoadingId)}
          title={t('resume.pdfModalTitle')}
          subtitle={
            pdfVm?.name
              ? t('resume.pdfModalPreparingName', { name: pdfVm.name })
              : t('resume.pdfModalPreparing')
          }
          onClose={pageActions.finishDownload}
          width={520}
        >
          <div style={{ display: 'grid', gap: 12 }}>
            <ProgressBar
              current={pageState.pdfProgress}
              total={100}
              rightContent={
                <span style={{ fontWeight: 800 }}>{pageState.pdfProgress}%</span>
              }
            />
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--sr-ink-muted)' }}>
              {t('resume.pdfModalHint')}
            </div>
          </div>
        </Modal>
      </main>
    </AppShell>
  );
}
