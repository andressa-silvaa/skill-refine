import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import type { ResumeData } from '@/entities/resume';
import { getResumeThemeById } from '@/entities/resume';
import type { ResumeDetailResponse } from '@/features/resume/api/resumeApi';
import { ResumePreviewContent } from '@/widgets/resume-preview/ui/ResumePreviewContent';

import './ResumePrintPage.css';

declare global {
  interface Window {
    __resumePdfReady?: boolean;
    __resumePdfError?: string;
  }
}

export function ResumePrintPage() {
  const { resumeId } = useParams();
  const [searchParams] = useSearchParams();
  const token = (searchParams.get('token') ?? '').trim();
  const apiUrl = (searchParams.get('apiUrl') ?? '').trim();
  const [data, setData] = useState<ResumeData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.body.dataset.srPrint = 'true';
    return () => {
      delete document.body.dataset.srPrint;
    };
  }, []);

  useEffect(() => {
    window.__resumePdfReady = false;
    window.__resumePdfError = undefined;
  }, []);

  useEffect(() => {
    if (!resumeId || !token) {
      const message = 'Token inválido para gerar o PDF.';
      setError(message);
      window.__resumePdfError = message;
      window.__resumePdfReady = true;
      return;
    }

    let cancelled = false;
    
    // Função para fazer requisição com URL customizada se disponível
    const fetchPdfData = async () => {
      const baseUrl = apiUrl || (process.env.REACT_APP_API_URL ?? 'http://localhost:8000');
      const encoded = encodeURIComponent(token);
      const url = `${baseUrl}/resumes/api/resumes/${resumeId}/pdf-data?token=${encoded}`;
      
      const response = await fetch(url, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch resume data');
      }
      
      return response.json() as Promise<ResumeDetailResponse>;
    };

    fetchPdfData()
      .then((detail) => {
        if (cancelled) return;
        const theme = getResumeThemeById(detail.data.themeId);
        setData({
          ...detail.data,
          themePaletteId: detail.data.themePaletteId || theme.defaultPaletteId,
        });
      })
      .catch(() => {
        if (cancelled) return;
        const message = 'Não foi possível carregar o currículo.';
        setError(message);
        window.__resumePdfError = message;
        window.__resumePdfReady = true;
      });

    return () => {
      cancelled = true;
    };
  }, [resumeId, token, apiUrl]);

  const handleReady = useCallback(() => {
    if (window.__resumePdfReady) return;
    window.__resumePdfReady = true;
  }, []);

  return (
    <div data-sr-theme-scope data-theme="light" className="sr-resume-print">
      {error ? <div className="sr-resume-print__error">{error}</div> : null}
      {!error && !data ? <div className="sr-resume-print__loading">Carregando pré-visualização...</div> : null}
      {data ? <ResumePreviewContent data={data} onReady={handleReady} /> : null}
    </div>
  );
}
