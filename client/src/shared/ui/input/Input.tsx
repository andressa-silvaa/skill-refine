import type { InputHTMLAttributes } from 'react';

import './Input.css';

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  hint?: string;
};

export function Input(props: Props) {
  const { className = '', label, error, hint, id, ...rest } = props;
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className={`sr-input-wrapper${className ? ` ${className}` : ''}`}>
      {label ? (
        <label htmlFor={inputId} className="sr-input-label">
          {label}
        </label>
      ) : null}
      <input
        {...rest}
        id={inputId}
        className={`sr-input${error ? ' is-invalid' : ''}`}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={hintId || errorId || undefined}
      />
      {hint && !error ? (
        <p id={hintId} className="sr-input-hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="sr-input-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
