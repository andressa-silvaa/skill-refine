import type { InputHTMLAttributes } from 'react';

import './AuthStyles.css';

type Props = {
  label: string;
  error?: string;
} & InputHTMLAttributes<HTMLInputElement>;

export function Field(props: Props) {
  const { label, error, className = '', ...inputProps } = props;
  return (
    <label className="auth-field">
      <span className="auth-label">{label}</span>
      <input
        {...inputProps}
        className={`auth-input${className ? ` ${className}` : ''}${error ? ' is-invalid' : ''}`}
        aria-invalid={Boolean(error)}
      />
      {error ? <p className="field-error">{error}</p> : null}
    </label>
  );
}
