import { useEffect } from 'react';

type Options = {
  open: boolean;
  onClose?: () => void;
  lockScroll?: boolean;
  closeOnEscape?: boolean;
};

export function useModalEffects(options: Options) {
  const { open, onClose, lockScroll = true, closeOnEscape = true } = options;

  useEffect(() => {
    if (!open || !lockScroll) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [lockScroll, open]);

  useEffect(() => {
    if (!open || !closeOnEscape || !onClose) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [closeOnEscape, onClose, open]);
}
