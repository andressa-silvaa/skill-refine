import type { UseFormRegisterReturn } from 'react-hook-form';

type Props = {
  label: string;
  placeholder: string;
  type: 'text' | 'email';
  autoComplete?: string;
  registration: UseFormRegisterReturn;
  isInvalid: boolean;
  errorMessage?: string;
};

export function TextInputField(props: Props) {
  const { label, placeholder, type, autoComplete, registration, isInvalid, errorMessage } = props;

  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input
        {...registration}
        className={`field-input${isInvalid ? ' is-invalid' : ''}`}
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete}
        aria-invalid={isInvalid}
      />
      {isInvalid ? <p className="field-error">{errorMessage}</p> : null}
    </label>
  );
}


