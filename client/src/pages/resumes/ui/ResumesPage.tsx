import { useCallback, useEffect, useMemo, useState } from 'react';

import { prefetchAiAnalysisRoute } from '@/pages/ai-analysis/prefetch';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useResumes } from '@/features/resume';
import { useLatestAnalyses } from '@/features/ai-analysis';
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
import { Modal, ProgressBar } from '@/shared/ui';

import { useResumesPageState } from '../model/useResumesPageState';
import { usePdfProgressEffect } from '../model/usePdfProgressEffect';
import { useResumeCrudActions } from '../model/useResumeCrudActions';
import { useResumePdfExport } from '../model/useResumePdfExport';
import { useResumesUrlEffects } from '../model/useResumesUrlEffects';

import '@/shared/ui/sr-controls/SrControls.css';
import './ResumesPage.css';

export function ResumesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const resumes = useResumes({
    query: searchParams.get('q') ?? '',
    sort: ((searchParams.get('sort') as 'recent' | 'oldest' | 'score' | 'name' | null) ?? 'recent'),
    view: ((searchParams.get('view') as 'grid' | 'list' | null) ?? 'grid'),
    filters: {
      status: ((searchParams.get('status') as 'all' | 'draft' | 'complete' | 'analyzing' | null) ?? 'all'),
      score: ((searchParams.get('score') as 'all' | 'none' | '0-50' | '51-70' | '71-85' | '86-100' | null) ?? 'all'),
      updated: ((searchParams.get('updated') as 'all' | '7d' | '30d' | null) ?? 'all'),
    },
  });
  const { state: pageState, actions: pageActions } = useResumesPageState();
  const [filtersOpen, setFiltersOpen] = useState(false);

  const resumeIds = useMemo(() => resumes.viewModels.map((vm) => vm.id), [resumes.viewModels]);
  const analysisByResumeId = useLatestAnalyses(resumeIds, resumes.listVersion);

  useEffect(() => {
    prefetchAiAnalysisRoute();
  }, []);

  const onAnalyzeWithAI = useCallback(
    (id: string) => {
      prefetchAiAnalysisRoute();
      navigate(`/protected/ai-analysis?resumeId=${encodeURIComponent(id)}`);
    },
    [navigate]
  );

  const onResumeActionsMenuOpen = useCallback((open: boolean) => {
    if (open) prefetchAiAnalysisRoute();
  }, []);

  const pdfVm = useMemo(
    () =>
      pageState.downloadLoadingId
        ? resumes.viewModels.find((item) => item.id === pageState.downloadLoadingId)
        : null,
    [pageState.downloadLoadingId, resumes.viewModels]
  );

  usePdfProgressEffect({
    downloadLoadingId: pageState.downloadLoadingId,
    setPdfProgress: pageActions.setPdfProgress,
  });

  useEffect(() => {
    if (resumes.error) {
      notify.error(getApiErrorMessage(resumes.error, t('resume.errorLoadFailed')));
    }
  }, [resumes.error, t]);

  const {
    onEdit,
    onDuplicate,
    onDelete,
    closeDelete,
    confirmDelete,
    handleSaveDraft,
    handleFinish,
  } = useResumeCrudActions({
    duplicateLoadingId: pageState.duplicateLoadingId,
    deleteResumeId: pageState.deleteResumeId,
    pageActions,
    resumes,
    t,
  });

  useResumesUrlEffects({
    resumes,
    searchParams,
    setSearchParams,
    onOpenCreate: pageActions.openCreate,
    onEditFromQuery: (id, options) => {
      void onEdit(id, options);
    },
  });

  const { onExport } = useResumePdfExport({
    downloadLoadingId: pageState.downloadLoadingId,
    startDownload: pageActions.startDownload,
    finishDownload: pageActions.finishDownload,
    setPdfStage: pageActions.setPdfStage,
    setPdfProgress: pageActions.setPdfProgress,
    viewModels: resumes.viewModels.map((vm) => ({ id: vm.id, name: vm.name })),
    startPdfExport: resumes.startPdfExport,
    getPdfExportStatus: resumes.getPdfExportStatus,
    downloadPdfExport: resumes.downloadPdfExport,
    t,
  });

  return (
    <main className="sr-resumes" aria-label={t('resume.mainAria')}>
        <ResumesHeader onCreate={pageActions.openCreate} />

        <ResumesToolbar
          query={resumes.query}
          onQueryChange={resumes.setQuery}
          view={resumes.view}
          onViewChange={resumes.setView}
          sort={resumes.sort}
          onSortChange={resumes.setSort}
          filtersOpen={filtersOpen}
          onToggleFilters={() => setFiltersOpen((v) => !v)}
          statusFilter={resumes.filters.status}
          scoreFilter={resumes.filters.score}
          updatedFilter={resumes.filters.updated}
          onStatusFilterChange={resumes.setStatusFilter}
          onScoreFilterChange={resumes.setScoreFilter}
          onUpdatedFilterChange={resumes.setUpdatedFilter}
          onClearFilters={resumes.clearFilters}
          activeFiltersCount={
            Number(resumes.filters.status !== 'all') +
            Number(resumes.filters.score !== 'all') +
            Number(resumes.filters.updated !== 'all')
          }
        />

        <section className="sr-resumes__content">
          {resumes.loading ? (
            <ResumesSkeleton view={resumes.view} />
          ) : resumes.viewModels.length === 0 ? (
            <ResumesEmpty
              onCreate={pageActions.openCreate}
              hasActiveFilters={resumes.hasActiveFilters || resumes.query.trim().length > 0}
              onClearFilters={() => {
                resumes.clearFilters();
                resumes.setQuery('');
              }}
            />
          ) : resumes.view === 'grid' ? (
            <ResumesGrid
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
              onAnalyzeWithAI={onAnalyzeWithAI}
              onActionsMenuOpen={onResumeActionsMenuOpen}
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
              onActionsMenuOpen={onResumeActionsMenuOpen}
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
            pageState.pdfStage === 'downloading'
              ? pdfVm?.name
                ? t('resume.pdfModalDownloadingName', { name: pdfVm.name })
                : t('resume.pdfModalDownloading')
              : pdfVm?.name
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
  );
}
