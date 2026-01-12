import { useEffect, useId, useMemo, useRef, useState } from 'react';

import './SortSelect.css';

type Option = { value: string; label: string };

type Props = {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
};

export function SortSelect(props: Props) {
  const { value, options, onChange } = props;

  const selectId = useId();
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

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

  return (
    <div ref={wrapRef} className="sr-resumes-sort-select">
      <button
        type="button"
        className="sr-resumes-sort-select__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={selectId}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
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
        <span className="sr-resumes-sort-select__value">{label}</span>
        <span className="sr-resumes-sort-select__caret" aria-hidden />
      </button>

      {open ? (
        <div className="sr-resumes-sort-select__menu" role="listbox" id={selectId}>
          {options.map((opt, idx) => {
            const selected = opt.value === value;
            const active = idx === activeIndex;
            return (
              <button
                key={opt.value}
                type="button"
                role="option"
                aria-selected={selected}
                className={`sr-resumes-sort-select__option${selected ? ' is-selected' : ''}${active ? ' is-active' : ''}`}
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
