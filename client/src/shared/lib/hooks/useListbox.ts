import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';

type ListboxOption = { value: string; label: string };

type Options<T extends ListboxOption> = {
  value: string;
  options: T[];
  disabled?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export function useListbox<T extends ListboxOption>(options: Options<T>) {
  const { value, options: list, disabled, onOpenChange } = options;
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const selectedLabel = useMemo(() => {
    return list.find((opt) => opt.value === value)?.label ?? '';
  }, [list, value]);

  useEffect(() => {
    onOpenChange?.(open);
  }, [onOpenChange, open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      const el = wrapRef.current;
      if (!el) return;
      if (event.target instanceof Node && el.contains(event.target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const idx = Math.max(0, list.findIndex((opt) => opt.value === value));
    setActiveIndex(idx);
  }, [open, list, value]);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  const onTriggerKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (disabled) return;
      if (event.key === 'Escape') {
        setOpen(false);
        return;
      }
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        setOpen(true);
        return;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setOpen(true);
        setActiveIndex((idx) => Math.min(list.length - 1, idx + 1));
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setOpen(true);
        setActiveIndex((idx) => Math.max(0, idx - 1));
      }
    },
    [disabled, list.length]
  );

  return {
    wrapRef,
    open,
    setOpen,
    activeIndex,
    setActiveIndex,
    selectedLabel,
    onTriggerKeyDown,
  };
}
