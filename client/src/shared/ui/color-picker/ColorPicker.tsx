import { notify } from '@/shared/lib/notify';
import './ColorPicker.css';

type Props = {
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
};

export function ColorPicker({ value, onChange, ariaLabel }: Props) {
  const handleCopy = () => {
    if (tryCopy(value)) {
      notify.success('Cor copiada.');
    } else {
      notify.error('Não foi possível copiar.');
    }
  };

  return (
    <div className="sr-color-picker">
      <input
        type="color"
        className="sr-color-picker__swatch"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={ariaLabel}
      />
      <div className="sr-color-picker__field">
        <input
          type="text"
          className="sr-color-picker__input"
          value={value}
          readOnly
          aria-label={`${ariaLabel} (hexadecimal)`}
          spellCheck={false}
          inputMode="text"
        />
        <button
          type="button"
          className="sr-color-picker__copy"
          aria-label="Copiar cor hexadecimal"
          onClick={handleCopy}
        >
          <i className="fa-regular fa-copy" aria-hidden />
        </button>
      </div>
    </div>
  );
}

function tryCopy(text: string): boolean {
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(text);
    return true;
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(textarea);
  return ok;
}
