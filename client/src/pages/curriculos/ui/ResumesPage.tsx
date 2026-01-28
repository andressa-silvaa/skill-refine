import { useEffect, useMemo, useState } from 'react';

import { useResumes } from '@/features/resume';
import { getResumeThemeById, type ResumeData, type ResumeStatus } from '@/entities/resume';
import type { BuilderStep } from '@/features/resume-builder';
import { downloadBlob } from '@/shared/lib/download/download';
import type { ResumeDraftPayload } from '@/features/resume/api/resumeApi';
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

import '@/shared/ui/sr-controls/SrControls.css';
import './ResumesPage.css';

export function ResumesPage() {
  const resumes = useResumes();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editResumeId, setEditResumeId] = useState<string | null>(null);
  const [editData, setEditData] = useState<ResumeData | null>(null);
  const [editStatus, setEditStatus] = useState<ResumeStatus | null>(null);
  const [editLastStep, setEditLastStep] = useState<BuilderStep | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [duplicateLoadingId, setDuplicateLoadingId] = useState<string | null>(null);
  const [downloadLoadingId, setDownloadLoadingId] = useState<string | null>(null);
  const [pdfProgress, setPdfProgress] = useState(0);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const pdfVm = useMemo(
    () => (downloadLoadingId ? resumes.viewModels.find((item) => item.id === downloadLoadingId) : null),
    [downloadLoadingId, resumes.viewModels]
  );

  // Progresso "fake" (indeterminado) para UX durante geração do PDF.
  useEffect(() => {
    if (!downloadLoadingId) {
      setPdfProgress(0);
      return;
    }

    setPdfProgress(8);
    const interval = window.setInterval(() => {
      setPdfProgress((prev) => {
        if (prev >= 92) return prev;
        const step = 3 + Math.floor(Math.random() * 6); // 3..8
        return Math.min(92, prev + step);
      });
    }, 450);

    return () => window.clearInterval(interval);
  }, [downloadLoadingId]);

  useEffect(() => {
    if (resumes.error) {
      notify.error(getApiErrorMessage(resumes.error, 'Não foi possível carregar seus currículos.'));
    }
  }, [resumes.error]);

  const openFilters = () => notify.info('Filtros em breve.');
  const onEdit = async (id: string) => {
    setEditOpen(true);
    setEditLoading(true);
    setEditResumeId(id);
    try {
      const detail = await resumes.fetchById(id);
      const theme = getResumeThemeById(detail.data.themeId);
      setEditData({
        ...detail.data,
        themePaletteId: detail.data.themePaletteId || theme.defaultPaletteId,
      });
      setEditStatus(detail.status);
      setEditLastStep((detail.lastStep as BuilderStep) ?? null);
    } catch (err) {
      notify.error(getApiErrorMessage(err, 'Não foi possível carregar o currículo.'));
      setEditOpen(false);
      setEditResumeId(null);
      setEditData(null);
      setEditStatus(null);
      setEditLastStep(null);
    } finally {
      setEditLoading(false);
    }
  };

  const onDuplicate = (id: string) => {
    if (duplicateLoadingId === id) return;
    setDuplicateLoadingId(id);
    resumes
      .duplicateResume(id)
      .then(() => notify.success('Currículo duplicado com sucesso.'))
      .catch((err) => notify.error(getApiErrorMessage(err, 'Não foi possível duplicar o currículo.')))
      .finally(() => setDuplicateLoadingId(null));
  };

  const onExport = (id: string) => {
    if (downloadLoadingId === id) return;
    setDownloadLoadingId(id);
    const vm = resumes.viewModels.find((item) => item.id === id);
    const baseName = vm?.name?.trim() || 'Curriculo';
    const dateLabel = new Date().toISOString().slice(0, 10);
    const fallbackName = `Curriculo_${baseName}_${dateLabel}.pdf`;
    resumes
      .downloadPdf(id)
      .then(({ blob, filename }) => {
        downloadBlob(blob, filename || fallbackName);
        notify.success('Download feito com sucesso.');
        setPdfProgress(100);
      })
      .catch((err) => {
        notify.error(getApiErrorMessage(err, 'Não foi possível gerar o PDF.'));
      })
      .finally(() => {
        // deixa o usuário "ver" o 100% rapidamente antes de fechar
        window.setTimeout(() => {
          setDownloadLoadingId(null);
          setPdfProgress(0);
        }, 450);
      });
  };

  const onDelete = (id: string) => setDeleteId(id);
  const closeDelete = () => setDeleteId(null);

  const confirmDelete = () => {
    if (!deleteId) return;
    setIsDeleting(true);
    resumes
      .deleteResume(deleteId)
      .then(() => {
        setDeleteId(null);
        notify.success('Currículo excluído com sucesso.');
      })
      .catch((err) => {
        notify.error(getApiErrorMessage(err, 'Não foi possível excluir o currículo. Tente novamente.'));
      })
      .finally(() => setIsDeleting(false));
  };

  const handleSaveDraft = async (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => {
    const { payload, resumeId } = data;
    setIsSavingDraft(true);
    try {
      const resume = resumeId
        ? await resumes.updateDraft(resumeId, payload)
        : await resumes.createDraft(payload);
      notify.success('Rascunho salvo com sucesso.');
      return resume;
    } catch (err) {
      notify.error(getApiErrorMessage(err, 'Não foi possível salvar o rascunho.'));
      throw err;
    } finally {
      setIsSavingDraft(false);
    }
  };

  const handleFinish = async (data: { payload: ResumeDraftPayload; resumeId?: string | null }) => {
    const { payload, resumeId } = data;
    setIsSubmitting(true);
    try {
      const resume = resumeId
        ? await resumes.updateDraft(resumeId, payload)
        : await resumes.createDraft(payload);
      notify.success(resumeId ? 'Currículo editado com sucesso.' : 'Currículo criado com sucesso.');
      return resume;
    } catch (err) {
      notify.error(getApiErrorMessage(err, 'Não foi possível salvar o currículo.'));
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <main className="sr-resumes" aria-label="Currículos">
        <ResumesHeader onCreate={() => setNewOpen(true)} />

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
            <ResumesEmpty onCreate={() => setNewOpen(true)} />
          ) : resumes.view === 'grid' ? (
            <ResumesGrid
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
              duplicateLoadingId={duplicateLoadingId}
              downloadLoadingId={downloadLoadingId}
            />
          ) : (
            <ResumesList
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
              duplicateLoadingId={duplicateLoadingId}
              downloadLoadingId={downloadLoadingId}
            />
          )}
        </section>

        <ResumeBuilderWizard
          title="Criar Currículo"
          open={newOpen}
          onClose={() => setNewOpen(false)}
          onSaveDraft={handleSaveDraft}
          onFinish={handleFinish}
          isSavingDraft={isSavingDraft}
          isSubmitting={isSubmitting}
        />

        <ResumeBuilderWizard
          title="Editar Currículo"
          open={editOpen}
          onClose={() => {
            setEditOpen(false);
            setEditResumeId(null);
            setEditData(null);
            setEditStatus(null);
            setEditLastStep(null);
          }}
          onSaveDraft={handleSaveDraft}
          onFinish={handleFinish}
          isSavingDraft={isSavingDraft}
          isSubmitting={isSubmitting}
          isLoading={editLoading}
          initialData={editData}
          initialResumeId={editResumeId}
          initialStatus={editStatus}
          initialLastStep={editLastStep}
        />

        <ConfirmDeleteResumeModal
          open={Boolean(deleteId)}
          onClose={closeDelete}
          onConfirm={confirmDelete}
          isLoading={isDeleting}
        />

        <Modal
          open={Boolean(downloadLoadingId)}
          title="Gerando PDF"
          subtitle={pdfVm?.name ? `Preparando o PDF de “${pdfVm.name}”...` : 'Preparando seu PDF...'}
          onClose={() => {
            // Não cancelamos a request (blob), mas permitimos fechar o aviso.
            // O botão "Baixar PDF" continua bloqueado pelo loadingId.
            setDownloadLoadingId(null);
            setPdfProgress(0);
          }}
          width={520}
        >
          <div style={{ display: 'grid', gap: 12 }}>
            <ProgressBar current={pdfProgress} total={100} rightContent={<span style={{ fontWeight: 800 }}>{pdfProgress}%</span>} />
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--sr-ink-muted)' }}>
              Isso pode levar alguns segundos dependendo do tamanho do currículo.
            </div>
          </div>
        </Modal>
      </main>
    </AppShell>
  );
}
