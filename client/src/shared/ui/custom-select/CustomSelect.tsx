import { useId } from 'react';

import { useListbox } from '@/shared/lib/hooks/useListbox';

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
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;

  const { wrapRef, open, setOpen, activeIndex, setActiveIndex, selectedLabel, onTriggerKeyDown } = useListbox({
    value,
    options,
    disabled,
  });

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
          onKeyDown={onTriggerKeyDown}
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
