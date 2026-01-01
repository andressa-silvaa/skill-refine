import './PasswordInput.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import { useId } from 'react';
import { usePasswordVisibility } from '../hooks/usePasswordVisibility';

export default function PasswordInput({
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
}) {
  const generatedId = useId();
  const { isVisible, inputType, toggleVisibility, ariaLabel } = usePasswordVisibility({
    label: label ?? 'senha',
  });

  const inputProps = {
    type: inputType,
    placeholder,
    autoComplete,
    name,
    id: id ?? generatedId,
    className: `field-input has-icon${inputClassName ? ` ${inputClassName}` : ''}`,
    ...rest,
  };

  if (value !== undefined) {
    inputProps.value = value;
  }

  if (onChange) {
    inputProps.onChange = onChange;
  }

  return (
    <div className={`field${className ? ` ${className}` : ''}`}>
      {labelRight ? (
        <div className="field-row">
          {label && (
            <label className="field-label" htmlFor={inputProps.id}>
              {label}
            </label>
          )}
          {labelRight}
        </div>
      ) : (
        label && (
          <label className="field-label" htmlFor={inputProps.id}>
            {label}
          </label>
        )
      )}

      <div className="password-wrapper">
        <input {...inputProps} />
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

