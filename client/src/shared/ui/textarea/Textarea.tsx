import type { TextareaHTMLAttributes } from 'react';

import './Textarea.css';

type Props = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  error?: string;
  hint?: string;
  showCount?: boolean;
  maxLength?: number;
};

export function Textarea(props: Props) {
  const { className = '', label, error, hint, showCount, maxLength, id, value, ...rest } = props;
  const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
  const hintId = hint ? `${textareaId}-hint` : undefined;
  const errorId = error ? `${textareaId}-error` : undefined;
  const valueStr = typeof value === 'string' ? value : '';
  const charCount = valueStr.length;

  return (
    <div className={`sr-textarea-wrapper${className ? ` ${className}` : ''}`}>
      {label ? (
        <label htmlFor={textareaId} className="sr-textarea-label">
          {label}
        </label>
      ) : null}
      <textarea
        {...rest}
        id={textareaId}
        value={value}
        maxLength={maxLength}
        className={`sr-textarea${error ? ' is-invalid' : ''}`}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={hintId || errorId || undefined}
      />
      <div className="sr-textarea-footer">
        {hint && !error ? (
          <p id={hintId} className="sr-textarea-hint">
            {hint}
          </p>
        ) : null}
        {error ? (
          <p id={errorId} className="sr-textarea-error">
            {error}
          </p>
        ) : null}
        {showCount && maxLength ? (
          <span className="sr-textarea-count">
            {charCount} / {maxLength}
          </span>
        ) : null}
      </div>
    </div>
  );
}
