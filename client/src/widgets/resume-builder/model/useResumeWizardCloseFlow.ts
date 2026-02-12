import { useCallback, useRef, useState } from 'react';

type BuilderLike = { isDirty: boolean; reset: () => void };

type Options = {
  onClose: () => void;
  builder: BuilderLike;
};

export function useResumeWizardCloseFlow(options: Options) {
  const { onClose, builder } = options;
  const [discardOpen, setDiscardOpen] = useState(false);
  const skipDiscardRef = useRef(false);

  const skipDiscardAndClose = useCallback(() => {
    skipDiscardRef.current = true;
    onClose();
  }, [onClose]);

  const handleClose = useCallback(() => {
    if (skipDiscardRef.current) {
      skipDiscardRef.current = false;
      onClose();
      return;
    }
    if (builder.isDirty) {
      setDiscardOpen(true);
      return;
    }
    onClose();
  }, [builder.isDirty, onClose]);

  const closeDiscard = useCallback(() => setDiscardOpen(false), []);

  const confirmDiscard = useCallback(() => {
    setDiscardOpen(false);
    builder.reset();
    onClose();
  }, [builder, onClose]);

  return {
    discardOpen,
    handleClose,
    closeDiscard,
    confirmDiscard,
    skipDiscardAndClose,
  };
}
