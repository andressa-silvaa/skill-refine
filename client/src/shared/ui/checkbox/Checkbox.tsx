import { useId } from 'react';

import './Checkbox.css';

type Props = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
  className?: string;
};

export function Checkbox(props: Props) {
  const { checked, onChange, label, disabled = false, className = '' } = props;
  const inputId = useId();

  return (
    <label className={`sr-checkbox${className ? ` ${className}` : ''}`}>
      <input
        id={inputId}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className="sr-checkbox__box" aria-hidden />
      <span className="sr-checkbox__label">{label}</span>
    </label>
  );
}
