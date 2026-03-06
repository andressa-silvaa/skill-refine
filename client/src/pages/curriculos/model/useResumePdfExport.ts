import { useCallback } from 'react';

import { downloadBlob } from '@/shared/lib/download/download';
import { getApiErrorMessage } from '@/shared/api';
import { notify } from '@/shared/lib/notify';

type Translator = (key: string, params?: Record<string, unknown>) => string;

type Params = {
  downloadLoadingId: string | null;
  startDownload: (id: string) => void;
  finishDownload: () => void;
  setPdfStage: (stage: 'preparing' | 'downloading') => void;
  setPdfProgress: (value: number) => void;
  viewModels: Array<{ id: string; name: string }>;
  startPdfExport: (resumeId: string) => Promise<{
    status: 'pending' | 'ready' | 'failed';
    exportId: string;
    retryAfterSeconds?: number;
    errorMessage?: string;
    filename?: string;
  }>;
  getPdfExportStatus: (
    resumeId: string,
    exportId: string
  ) => Promise<{
    status: 'pending' | 'ready' | 'failed';
    exportId: string;
    retryAfterSeconds?: number;
    errorMessage?: string;
    filename?: string;
  }>;
  downloadPdfExport: (resumeId: string, exportId: string) => Promise<{ blob: Blob; filename?: string }>;
  t: Translator;
};

export function useResumePdfExport(params: Params) {
  const {
    downloadLoadingId,
    startDownload,
    finishDownload,
    setPdfStage,
    setPdfProgress,
    viewModels,
    startPdfExport,
    getPdfExportStatus,
    downloadPdfExport,
    t,
  } = params;

  const onExport = useCallback(
    async (id: string) => {
      if (downloadLoadingId === id) return;
      startDownload(id);
      setPdfStage('preparing');
      const vm = viewModels.find((item) => item.id === id);
      const baseName = vm?.name?.trim() || 'Curriculo';
      const dateLabel = new Date().toISOString().slice(0, 10);
      const fallbackName = `Curriculo_${baseName}_${dateLabel}.pdf`;
      try {
        const first = await startPdfExport(id);
        let finalStatus = first;
        let guard = 0;
        while (finalStatus.status === 'pending') {
          guard += 1;
          if (guard > 90) {
            throw new Error('Timeout waiting for PDF generation');
          }
          const waitSeconds = Math.max(1, Number(finalStatus.retryAfterSeconds ?? 2));
          await new Promise((resolve) => window.setTimeout(resolve, waitSeconds * 1000));
          finalStatus = await getPdfExportStatus(id, finalStatus.exportId);
        }
        if (finalStatus.status === 'failed') {
          throw new Error(finalStatus.errorMessage || t('resume.errorPdfFailed'));
        }

        setPdfStage('downloading');
        setPdfProgress(96);
        const { blob, filename } = await downloadPdfExport(id, finalStatus.exportId);
        downloadBlob(blob, filename || finalStatus.filename || fallbackName);
        notify.success(t('resume.toastDownloadDone'));
        setPdfProgress(100);
      } catch (err) {
        notify.error(getApiErrorMessage(err, t('resume.errorPdfFailed')));
      } finally {
        window.setTimeout(() => finishDownload(), 450);
      }
    },
    [
      downloadLoadingId,
      downloadPdfExport,
      finishDownload,
      getPdfExportStatus,
      setPdfProgress,
      setPdfStage,
      startDownload,
      startPdfExport,
      t,
      viewModels,
    ]
  );

  return { onExport };
}
