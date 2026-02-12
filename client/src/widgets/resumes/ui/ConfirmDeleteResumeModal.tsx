import { useTranslation } from 'react-i18next';

import { Button, Modal } from '@/shared/ui';

import './ConfirmDeleteResumeModal.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
};

export function ConfirmDeleteResumeModal(props: Props) {
  const { open, onClose, onConfirm, isLoading = false } = props;
  const { t } = useTranslation();

  return (
    <Modal open={open} title={t('resume.deleteModalTitle')} onClose={onClose} width={360}>
      <div className="sr-confirm-del">
        <div className="sr-confirm-del__icon" aria-hidden>
          <i className="fa-solid fa-triangle-exclamation" />
        </div>
        <p className="sr-confirm-del__text">{t('resume.deleteModalPermanent')}</p>
        <p className="sr-confirm-del__text">{t('resume.deleteModalRecreate')}</p>
        <div className="sr-confirm-del__actions">
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            {t('resume.deleteModalCancel')}
          </Button>
          <Button variant="danger" onClick={onConfirm} disabled={isLoading}>
            {isLoading ? t('resume.deleting') : t('resume.deleteModalDelete')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
