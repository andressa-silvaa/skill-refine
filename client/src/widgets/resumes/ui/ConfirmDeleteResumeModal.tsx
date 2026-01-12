import { Button, Modal } from '@/shared/ui';

import './ConfirmDeleteResumeModal.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export function ConfirmDeleteResumeModal(props: Props) {
  const { open, onClose, onConfirm } = props;

  return (
    <Modal open={open} title="Excluir currículo" onClose={onClose} width={360}>
      <div className="sr-confirm-del">
        <div className="sr-confirm-del__icon" aria-hidden>
          <i className="fa-solid fa-triangle-exclamation" />
        </div>
        <p className="sr-confirm-del__text">Essa ação é permanente.</p>
        <p className="sr-confirm-del__text">Você pode recriar depois, mas o conteúdo será perdido.</p>
        <div className="sr-confirm-del__actions">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            Excluir
          </Button>
        </div>
      </div>
    </Modal>
  );
}
