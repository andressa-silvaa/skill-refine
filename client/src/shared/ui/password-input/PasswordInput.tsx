import '@fortawesome/fontawesome-free/css/all.min.css';
import { useId, type ChangeEventHandler, type InputHTMLAttributes, type ReactNode } from 'react';

import { usePasswordVisibility } from '@/shared/lib/hooks/usePasswordVisibility';

import './PasswordInput.css';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label?: ReactNode;
  labelRight?: ReactNode;
  inputClassName?: string;
  onChange?: ChangeEventHandler<HTMLInputElement>;
};

export function PasswordInput(props: Props) {
  const {
    label,
    labelRight,
    value,
    onChange,
    placeholder = '*****************',
    autoComplete = 'current-password',
    name,
    id,
    className = '',
    inputClassName = '',
    ...rest
  } = props;

  const generatedId = useId();
  const { isVisible, inputType, toggleVisibility, ariaLabel } = usePasswordVisibility({
    label: typeof label === 'string' ? label : 'senha',
  });

  return (
    <div className={`field${className ? ` ${className}` : ''}`}>
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
          id={id ?? generatedId}
          name={name}
          type={inputType}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className={`field-input has-icon${inputClassName ? ` ${inputClassName}` : ''}`}
          value={value}
          onChange={onChange}
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
    </div>
  );
}


