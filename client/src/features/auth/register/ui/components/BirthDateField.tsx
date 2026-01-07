import { Controller, type Control } from 'react-hook-form';
import DatePicker from 'react-date-picker';

import type { RegisterFormValues } from '../../model/schema';

type DatePickerValue = Date | null | [Date | null, Date | null];

type Props = {
  control: Control<RegisterFormValues>;
  isInvalid: boolean;
  errorMessage?: string;
};

function normalizeDatePickerValue(value: DatePickerValue): Date | null {
  if (value instanceof Date) return value;
  if (Array.isArray(value)) return value[0] instanceof Date ? value[0] : null;
  return null;
}

export function BirthDateField(props: Props) {
  const { control, isInvalid, errorMessage } = props;

  return (
    <label className="field">
      <span className="field-label">Data de nascimento</span>
      <Controller
        control={control}
        name="birthDate"
        render={({ field }) => (
          <DatePicker
            onChange={(value: DatePickerValue) => {
              field.onChange(normalizeDatePickerValue(value));
              field.onBlur();
            }}
            onBlur={() => field.onBlur()}
            onCalendarClose={() => field.onBlur()}
            value={field.value instanceof Date ? field.value : null}
            format="dd/MM/y"
            dayPlaceholder="DD"
            monthPlaceholder="MM"
            yearPlaceholder="YYYY"
            clearIcon={null}
            calendarIcon={<span className="calendar-icon">📅</span>}
            className={`date-picker${isInvalid ? ' is-invalid' : ''}`}
          />
        )}
      />
      {isInvalid ? <p className="field-error">{String(errorMessage ?? '')}</p> : null}
    </label>
  );
}


