import { useEffect, useId, useMemo, useRef, useState } from 'react';

import './CustomSelect.css';

type Option = { value: string; label: string };

type Props = {
  value: string;
  options: Option[];
  label?: string;
  error?: string;
  hint?: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  className?: string;
};

export function CustomSelect(props: Props) {
  const { value, options, label, error, hint, disabled, onChange, className = '' } = props;

  const selectId = useId();
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;

  const selectedLabel = useMemo(() => {
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
    <div className={`sr-custom-select-wrapper${className ? ` ${className}` : ''}`}>
      {label ? (
        <label htmlFor={selectId} className="sr-custom-select-label">
          {label}
        </label>
      ) : null}
      <div ref={wrapRef} className="sr-custom-select">
        <button
          type="button"
          id={selectId}
          className={`sr-input sr-custom-select-trigger${error ? ' is-invalid' : ''}`}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={`${selectId}-menu`}
          aria-describedby={hintId || errorId || undefined}
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
          <span className="sr-custom-select-value">{selectedLabel || 'Selecione...'}</span>
          <span className="sr-custom-select-caret" aria-hidden />
        </button>

        {open ? (
          <div className="sr-custom-select-menu" role="listbox" id={`${selectId}-menu`}>
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
                  className={`sr-custom-select-option${selected ? ' is-selected' : ''}${active ? ' is-active' : ''}`}
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
      {hint && !error ? (
        <p id={hintId} className="sr-custom-select-hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="sr-custom-select-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
