import { useEffect, useId, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import './Modal.css';

type Props = {
  open: boolean;
  title: string;
  subtitle?: string;
  width?: number;
  children: ReactNode;
  onClose: () => void;
};

export function Modal(props: Props) {
  const { open, title, subtitle, width = 560, children, onClose } = props;
  const labelId = useId();

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
    <div className="sr-modal" role="dialog" aria-modal="true" aria-labelledby={labelId}>
      <button type="button" className="sr-modal__backdrop" aria-label="Fechar" onClick={onClose} />
      <div className="sr-modal__panel" style={{ width: `min(${width}px, 100%)` }}>
        <div className="sr-modal__header">
          <div className="sr-modal__header-content">
            <h3 id={labelId} className="sr-modal__title">
              {title}
            </h3>
            {subtitle ? <p className="sr-modal__subtitle">{subtitle}</p> : null}
          </div>
          <button type="button" className="sr-modal__close" aria-label="Fechar" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="sr-modal__body">{children}</div>
      </div>
    </div>,
    portalRoot
  );
}
