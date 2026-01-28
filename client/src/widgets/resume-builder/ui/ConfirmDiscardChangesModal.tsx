import { Button, Modal } from '@/shared/ui';

import '@/widgets/resumes/ui/ConfirmDeleteResumeModal.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onDiscard: () => void;
};

export function ConfirmDiscardChangesModal(props: Props) {
  const { open, onClose, onDiscard } = props;

  return (
    <Modal open={open} title="Descartar alterações?" onClose={onClose} width={360}>
      <div className="sr-confirm-del">
        <div className="sr-confirm-del__icon" aria-hidden>
          <i className="fa-solid fa-triangle-exclamation" />
        </div>
        <p className="sr-confirm-del__text">Você tem alterações não salvas. Se sair agora, elas serão perdidas.</p>
        <div className="sr-confirm-del__actions">
          <Button variant="secondary" onClick={onClose}>
            Continuar editando
          </Button>
          <Button variant="danger" onClick={onDiscard}>
            Descartar
          </Button>
        </div>
      </div>
    </Modal>
  );
}
