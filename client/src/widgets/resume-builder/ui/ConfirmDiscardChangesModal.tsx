import { useTranslation } from 'react-i18next';

import { Button, Modal } from '@/shared/ui';

import '@/widgets/resumes/ui/ConfirmDeleteResumeModal.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onDiscard: () => void;
};

export function ConfirmDiscardChangesModal(props: Props) {
  const { open, onClose, onDiscard } = props;
  const { t } = useTranslation();

  return (
    <Modal open={open} title={t('resume.discardModalTitle')} onClose={onClose} width={360}>
      <div className="sr-confirm-del">
        <div className="sr-confirm-del__icon" aria-hidden>
          <i className="fa-solid fa-triangle-exclamation" />
        </div>
        <p className="sr-confirm-del__text">{t('resume.discardModalMessage')}</p>
        <div className="sr-confirm-del__actions">
          <Button variant="secondary" onClick={onClose}>
            {t('resume.discardModalContinueEdit')}
          </Button>
          <Button variant="danger" onClick={onDiscard}>
            {t('resume.discardModalDiscard')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
