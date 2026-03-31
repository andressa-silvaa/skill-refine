import DatePickerLib from 'react-date-picker';

import { formatResumeDate, parseResumeDateToDate } from '@/shared/lib/date/resumeDate';

import 'react-date-picker/dist/DatePicker.css';
import './DatePicker.css';

type Props = {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  error?: string;
  hint?: string;
  className?: string;
};

type DatePickerValue = Date | null | [Date | null, Date | null];

function normalizeDatePickerValue(value: DatePickerValue): Date | null {
  if (value instanceof Date) return value;
  if (Array.isArray(value)) return value[0] instanceof Date ? value[0] : null;
  return null;
}

export function DatePicker(props: Props) {
  const { value, onChange, label, error, hint, className = '' } = props;
  const inputId = `date-picker-${Math.random().toString(36).substr(2, 9)}`;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className={`sr-date-picker-wrapper${className ? ` ${className}` : ''}`}>
      {label ? (
        <label htmlFor={inputId} className="sr-date-picker-label">
          {label}
        </label>
      ) : null}
      <DatePickerLib
        onChange={(val: DatePickerValue) => {
          const normalized = normalizeDatePickerValue(val);
          onChange(formatResumeDate(normalized));
        }}
        value={parseResumeDateToDate(value)}
        format="dd/MM/y"
        dayPlaceholder="dd"
        monthPlaceholder="MM"
        yearPlaceholder="YYYY"
        clearIcon={null}
        calendarIcon={<span className="sr-date-picker-icon">📅</span>}
        className={`sr-date-picker${error ? ' is-invalid' : ''}`}
      />
      <div className="sr-date-picker-messages" aria-live="polite">
        {error ? (
          <p id={errorId} className="sr-date-picker-error">
            {error}
          </p>
        ) : hint ? (
          <p id={hintId} className="sr-date-picker-hint">
            {hint}
          </p>
        ) : null}
      </div>
    </div>
  );
}
