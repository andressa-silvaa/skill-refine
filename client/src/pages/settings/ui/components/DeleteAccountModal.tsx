import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';

import './DeleteAccountModal.css';

type Props = {
  open: boolean;
  onConfirm: () => void;
  onClose: () => void;
  isLoading?: boolean;
};

export function DeleteAccountModal(props: Props) {
  const { t } = useTranslation();
  const { open, onClose, onConfirm, isLoading } = props;
  const cancelRef = useRef<HTMLButtonElement | null>(null);

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

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => cancelRef.current?.focus(), 0);
    return () => window.clearTimeout(id);
  }, [open]);

  if (!open) return null;

  const portalRoot = document.querySelector('[data-sr-theme-scope]') ?? document.body;

  return createPortal(
    <div className="sr-modal" role="dialog" aria-modal="true" aria-label={t('modal.deleteAccountTitle')}>
      <button type="button" className="sr-modal__backdrop" aria-label={t('common.close')} onClick={onClose} />
      <div className="sr-modal__panel">
        <div className="sr-modal__icon" aria-hidden>
          <i className="fa-solid fa-triangle-exclamation" />
        </div>
        <h3 className="sr-modal__title">{t('modal.deleteAccountTitle')}</h3>
        <p className="sr-modal__text">{t('modal.deleteAccountTextLine1')}</p>
        <p className="sr-modal__text">{t('modal.deleteAccountTextLine2')}</p>
        <div className="sr-modal__actions">
          <button
            ref={cancelRef}
            type="button"
            className="sr-btn sr-btn--secondary"
            disabled={isLoading}
            onClick={onClose}
          >
            {t('common.cancel')}
          </button>
          <button type="button" className="sr-btn sr-btn--danger" disabled={isLoading} onClick={onConfirm}>
            {isLoading ? t('modal.deleting') : t('modal.deleteAccountConfirm')}
          </button>
        </div>
      </div>
    </div>,
    portalRoot
  );
}
