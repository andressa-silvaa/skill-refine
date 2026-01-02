import './VerificationCodeInput.css';
import { useEffect, useRef, useState } from 'react';

export default function VerificationCodeInput({
  length = 5,
  value,
  onChange,
  autoFocus = false,
  className = '',
}) {
  const inputsRef = useRef([]);
  const [digits, setDigits] = useState(() => toArray(value, length));

  useEffect(() => {
    setDigits(toArray(value, length));
  }, [value, length]);

  useEffect(() => {
    if (autoFocus && inputsRef.current[0]) {
      inputsRef.current[0].focus();
    }
  }, [autoFocus]);

  const update = (nextDigits) => {
    setDigits(nextDigits);
    onChange?.(nextDigits.join(''));
  };

  const handleChange = (index, raw) => {
    const char = raw.slice(-1).replace(/[^0-9]/g, '');
    const next = [...digits];
    next[index] = char;
    update(next);
    if (char && inputsRef.current[index + 1]) {
      inputsRef.current[index + 1].focus();
    }
  };

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !digits[index] && inputsRef.current[index - 1]) {
      inputsRef.current[index - 1].focus();
    }
  };

  const handlePaste = (event) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    if (!pasted) return;
    const next = toArray(pasted, length);
    update(next);
    const targetIndex = Math.min(pasted.length, length - 1);
    if (inputsRef.current[targetIndex]) {
      inputsRef.current[targetIndex].focus();
    }
    event.preventDefault();
  };

  return (
    <div className={`code-input-row${className ? ` ${className}` : ''}`} onPaste={handlePaste}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => (inputsRef.current[index] = el)}
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

function toArray(value, length) {
  const str = (value ?? '').toString().replace(/\D/g, '').slice(0, length);
  const arr = Array.from({ length }, (_, i) => str[i] ?? '');
  return arr;
}

