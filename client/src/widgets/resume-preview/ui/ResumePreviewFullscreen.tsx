import { useEffect } from 'react';
import { createPortal } from 'react-dom';

import type { ResumeData } from '@/entities/resume';

import { ResumePreviewContent } from './ResumePreviewContent';
import './ResumePreviewFullscreen.css';

type Props = {
  open: boolean;
  data: ResumeData;
  onClose: () => void;
};

export function ResumePreviewFullscreen(props: Props) {
  const { open, data, onClose } = props;

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const portalRoot = document.querySelector('[data-sr-theme-scope]') ?? document.body;

  return createPortal(
    <div className="sr-resume-preview-fullscreen" role="dialog" aria-modal="true" aria-label="Pré-visualização do currículo">
      <div className="sr-resume-preview-fullscreen__header">
        <div className="sr-resume-preview-fullscreen__header-left">
          <span className="sr-resume-preview-fullscreen__badge">Pré-visualização</span>
          <span className="sr-resume-preview-fullscreen__title">Visualização do currículo</span>
        </div>
        <button type="button" className="sr-resume-preview-fullscreen__close" aria-label="Fechar" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="sr-resume-preview-fullscreen__content">
        <ResumePreviewContent data={data} />
      </div>
    </div>,
    portalRoot
  );
}
