import { useEffect, useRef, useState, type ClipboardEvent, type KeyboardEvent } from 'react';

import './VerificationCodeInput.css';

type Props = {
  length?: number;
  value?: string;
  onChange?: (value: string) => void;
  autoFocus?: boolean;
  className?: string;
};

export function VerificationCodeInput(props: Props) {
  const { length = 5, value, onChange, autoFocus = false, className = '' } = props;

  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);
  const [digits, setDigits] = useState<string[]>(() => toArray(value, length));

  useEffect(() => {
    setDigits(toArray(value, length));
  }, [value, length]);

  useEffect(() => {
    if (!autoFocus) return;
    const first = inputsRef.current[0];
    if (first) first.focus();
  }, [autoFocus]);

  const update = (nextDigits: string[]) => {
    setDigits(nextDigits);
    onChange?.(nextDigits.join(''));
  };

  const handleChange = (index: number, raw: string) => {
    const char = raw.slice(-1).replace(/[^0-9]/g, '');
    const next = [...digits];
    next[index] = char;
    update(next);
    if (char) inputsRef.current[index + 1]?.focus();
  };

  const handleKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && !digits[index]) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (event: ClipboardEvent<HTMLDivElement>) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    if (!pasted) return;
    const next = toArray(pasted, length);
    update(next);

    const targetIndex = Math.min(pasted.length, length - 1);
    inputsRef.current[targetIndex]?.focus();
    event.preventDefault();
  };

  return (
    <div className={`code-input-row${className ? ` ${className}` : ''}`} onPaste={handlePaste}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => {
            inputsRef.current[index] = el;
          }}
          className="code-input-box"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
        />
      ))}
    </div>
  );
}

function toArray(value: string | undefined, length: number) {
  const str = (value ?? '').toString().replace(/\D/g, '').slice(0, length);
  return Array.from({ length }, (_, i) => str[i] ?? '');
}


