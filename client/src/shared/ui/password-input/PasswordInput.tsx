import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from 'react';

import { usePasswordVisibility } from '@/shared/lib/hooks/usePasswordVisibility';

import './PasswordInput.css';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label?: ReactNode;
  labelRight?: ReactNode;
  isInvalid?: boolean;
  error?: ReactNode;
  wrapperClassName?: string;
  inputClassName?: string;
};

export const PasswordInput = forwardRef<HTMLInputElement, Props>(function PasswordInput(props, ref) {
  const {
    label,
    labelRight,
    isInvalid = false,
    error,
    placeholder = '*****************',
    autoComplete = 'current-password',
    name,
    id,
    wrapperClassName = '',
    className = '',
    inputClassName = '',
    ...rest
  } = props;

  const generatedId = useId();
  const { isVisible, inputType, toggleVisibility, ariaLabel } = usePasswordVisibility({
    label: typeof label === 'string' ? label : 'senha',
  });

  return (
    <div className={`field${wrapperClassName ? ` ${wrapperClassName}` : ''}`}>
      {labelRight ? (
        <div className="field-row">
          {label && (
            <label className="field-label" htmlFor={id ?? generatedId}>
              {label}
            </label>
          )}
          {labelRight}
        </div>
      ) : (
        label && (
          <label className="field-label" htmlFor={id ?? generatedId}>
            {label}
          </label>
        )
      )}

      <div className="password-wrapper">
        <input
          {...rest}
          ref={ref}
          id={id ?? generatedId}
          name={name}
          type={inputType}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-invalid={isInvalid || rest['aria-invalid']}
          className={`field-input has-icon${isInvalid ? ' is-invalid' : ''}${className ? ` ${className}` : ''}${
            inputClassName ? ` ${inputClassName}` : ''
          }`}
        />
        <button
          type="button"
          className="toggle-visibility"
          onClick={toggleVisibility}
          onMouseDown={(e) => e.preventDefault()}
          aria-label={ariaLabel}
          aria-pressed={isVisible}
        >
          <i className={`fa-solid ${isVisible ? 'fa-eye-low-vision' : 'fa-eye'}`} />
        </button>
      </div>

      {error ? <p className="field-error">{error}</p> : null}
    </div>
  );
});


