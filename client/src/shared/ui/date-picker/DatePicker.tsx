import DatePickerLib from 'react-date-picker';

import 'react-date-picker/dist/DatePicker.css';
import './DatePicker.css';

type Props = {
  value: string; // YYYY-MM format
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

function toDate(value: string): Date | null {
  if (!value) return null;
  const [year, month] = value.split('-');
  if (!year || !month) return null;
  return new Date(parseInt(year, 10), parseInt(month, 10) - 1, 1);
}

function toMonthString(date: Date | null): string {
  if (!date) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
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
          onChange(toMonthString(normalized));
        }}
        value={toDate(value)}
        format="MM/y"
        monthPlaceholder="MM"
        yearPlaceholder="YYYY"
        clearIcon={null}
        calendarIcon={<span className="sr-date-picker-icon">📅</span>}
        className={`sr-date-picker${error ? ' is-invalid' : ''}`}
      />
      {hint && !error ? (
        <p id={hintId} className="sr-date-picker-hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="sr-date-picker-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
