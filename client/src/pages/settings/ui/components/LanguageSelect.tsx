import { useEffect, useId, useMemo, useRef, useState } from 'react';

type Option = { value: string; label: string };

type Props = {
  value: string;
  options: Option[];
  disabled?: boolean;
  onChange: (value: string) => void;
  onOpenChange?: (open: boolean) => void;
};

export function LanguageSelect(props: Props) {
  const { value, options, disabled, onChange, onOpenChange } = props;

  const selectId = useId();
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    onOpenChange?.(open);
  }, [onOpenChange, open]);

  const label = useMemo(() => {
    return options.find((o) => o.value === value)?.label ?? '';
  }, [options, value]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const el = wrapRef.current;
      if (!el) return;
      if (e.target instanceof Node && el.contains(e.target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const idx = Math.max(0, options.findIndex((o) => o.value === value));
    setActiveIndex(idx);
  }, [open, options, value]);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  return (
    <div ref={wrapRef} className="sr-settings-general__select">
      <button
        type="button"
        className="sr-input sr-settings-general__select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={selectId}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === 'Escape') {
            setOpen(false);
            return;
          }
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen(true);
            return;
          }
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setOpen(true);
            setActiveIndex((i) => Math.min(options.length - 1, i + 1));
            return;
          }
          if (e.key === 'ArrowUp') {
            e.preventDefault();
            setOpen(true);
            setActiveIndex((i) => Math.max(0, i - 1));
          }
        }}
      >
        <span className="sr-settings-general__select-value">{label}</span>
        <span className="sr-settings-general__select-caret" aria-hidden />
      </button>

      {open ? (
        <div className="sr-settings-general__select-menu" role="listbox" id={selectId}>
          {options.map((opt, idx) => {
            const selected = opt.value === value;
            const active = idx === activeIndex;
            return (
              <button
                key={opt.value}
                type="button"
                role="option"
                aria-selected={selected}
                disabled={disabled}
                className={`sr-settings-general__select-option${selected ? ' is-selected' : ''}${active ? ' is-active' : ''}`}
                onMouseEnter={() => setActiveIndex(idx)}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
