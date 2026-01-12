import type { SelectHTMLAttributes } from 'react';

import './Select.css';

type Option = {
  value: string;
  label: string;
};

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> & {
  label?: string;
  error?: string;
  hint?: string;
  options: Option[];
  placeholder?: string;
};

export function Select(props: Props) {
  const { className = '', label, error, hint, options, placeholder, id, ...rest } = props;
  const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;

  return (
    <div className={`sr-select-wrapper${className ? ` ${className}` : ''}`}>
      {label ? (
        <label htmlFor={selectId} className="sr-select-label">
          {label}
        </label>
      ) : null}
      <select
        {...rest}
        id={selectId}
        className={`sr-select${error ? ' is-invalid' : ''}`}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={hintId || errorId || undefined}
      >
        {placeholder ? (
          <option value="" disabled>
            {placeholder}
          </option>
        ) : null}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {hint && !error ? (
        <p id={hintId} className="sr-select-hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="sr-select-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
