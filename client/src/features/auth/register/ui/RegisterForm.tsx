import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import DatePicker from 'react-date-picker';
import 'react-date-picker/dist/DatePicker.css';
import 'react-calendar/dist/Calendar.css';

import { GENERIC_FORM_ERROR_MESSAGE, hasFormErrors } from '@/shared/lib/forms';
import { PasswordInput } from '@/shared/ui';

import { registerSchema, type RegisterFormValues, type RegisterValues } from '../model/schema';

import './RegisterForm.css';

type Props = {
  onSubmit?: (values: RegisterValues) => void;
  onGoLogin?: () => void;
  serverError?: string;
};

type DatePickerValue = Date | null | [Date | null, Date | null];

export function RegisterForm(props: Props) {
  const { onSubmit, onGoLogin, serverError } = props;

  const {
    register,
    handleSubmit,
    control,
    trigger,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
    watch,
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: '',
      birthDate: undefined as unknown as Date,
      email: '',
      password: '',
      confirm: '',
      acceptedTerms: false,
    },
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const [isReady, setIsReady] = useState(false);

  const showFullNameError = (!!touchedFields.fullName || !!dirtyFields.fullName) && !!errors.fullName?.message;
  const showBirthDateError = (!!touchedFields.birthDate || !!dirtyFields.birthDate) && !!errors.birthDate?.message;
  const showEmailError = (!!touchedFields.email || !!dirtyFields.email) && !!errors.email?.message;
  const showPasswordError = (!!touchedFields.password || !!dirtyFields.password) && !!errors.password?.message;
  const showAcceptedTermsError =
    (!!touchedFields.acceptedTerms || !!dirtyFields.acceptedTerms) && !!errors.acceptedTerms?.message;

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  const passwordValue = watch('password');
  const confirmValue = watch('confirm');
  const confirmInteracted = !!touchedFields.confirm || !!dirtyFields.confirm;

  useEffect(() => {
    if (!confirmInteracted) return;
    void trigger('confirm');
  }, [passwordValue, confirmInteracted, trigger]);

  const confirmMismatchVisible =
    confirmInteracted &&
    Boolean(passwordValue) &&
    Boolean(confirmValue) &&
    passwordValue !== confirmValue;
  const confirmErrorMessage = errors.confirm?.message ?? (confirmMismatchVisible ? 'As senhas não coincidem' : undefined);
  const showConfirmError = confirmInteracted && !!confirmErrorMessage;

  const showGenericError =
    showFullNameError ||
    showBirthDateError ||
    showEmailError ||
    showPasswordError ||
    showConfirmError ||
    showAcceptedTermsError;

  return (
    <div className="register-content">
      <div className="welcome">
        <h1 className="register-title">Bem-vindo! Faça seu cadastro</h1>
      </div>

      <form
        className="form"
        onSubmit={handleSubmit((values) => {
          const parsed: RegisterValues = registerSchema.parse(values);
          onSubmit?.(parsed);
        })}
      >
        <label className="field">
          <span className="field-label">Nome completo</span>
          <input
            {...register('fullName')}
            className={`field-input${showFullNameError ? ' is-invalid' : ''}`}
            type="text"
            placeholder="Digite seu nome"
            autoComplete="name"
            aria-invalid={showFullNameError}
          />
          {showFullNameError ? <p className="field-error">{errors.fullName?.message}</p> : null}
        </label>

        <label className="field">
          <span className="field-label">Data de nascimento</span>
          <Controller
            control={control}
            name="birthDate"
            render={({ field }) => (
              <DatePicker
                onChange={(value: DatePickerValue) => {
                  if (value instanceof Date) {
                    field.onChange(value);
                    field.onBlur();
                    return;
                  }
                  if (Array.isArray(value)) {
                    const first = value[0];
                    field.onChange(first instanceof Date ? first : null);
                    field.onBlur();
                    return;
                  }
                  field.onChange(null);
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
                className={`date-picker${showBirthDateError ? ' is-invalid' : ''}`}
              />
            )}
          />
          {showBirthDateError ? <p className="field-error">{String(errors.birthDate?.message ?? '')}</p> : null}
        </label>

        <label className="field">
          <span className="field-label">E-mail</span>
          <input
            {...register('email')}
            className={`field-input${showEmailError ? ' is-invalid' : ''}`}
            type="email"
            placeholder="digite seu e-mail"
            autoComplete="email"
            aria-invalid={showEmailError}
          />
          {showEmailError ? <p className="field-error">{errors.email?.message}</p> : null}
        </label>

        <PasswordInput
          label="Senha"
          {...register('password')}
          autoComplete="new-password"
          isInvalid={showPasswordError}
          error={showPasswordError ? errors.password?.message : undefined}
        />

        <PasswordInput
          label="Confirme a senha"
          {...register('confirm')}
          autoComplete="new-password"
          isInvalid={showConfirmError}
          error={showConfirmError ? confirmErrorMessage : undefined}
        />

        <label className={`terms${showAcceptedTermsError ? ' is-invalid' : ''}`}>
          <input type="checkbox" {...register('acceptedTerms')} aria-invalid={showAcceptedTermsError} />
          <span>
            Eu aceito{' '}
            <button type="button" className="terms-link">
              Termos
            </button>{' '}
            e{' '}
            <button type="button" className="terms-link">
              Política de Privacidade
            </button>
          </span>
          {showAcceptedTermsError ? <p className="field-error">{errors.acceptedTerms?.message}</p> : null}
        </label>

        {showGenericError ? <p className="form-error">{GENERIC_FORM_ERROR_MESSAGE}</p> : null}
        {serverError ? <p className="form-error">{serverError}</p> : null}

        <button className="submit-btn" type="submit" disabled={!isReady || hasFormErrors(errors) || isSubmitting}>
          <span>CADASTRAR</span>
          <span className="arrow">→</span>
        </button>
      </form>

      <footer className="footer">
        <span>Você já tem uma conta?</span>
        <button className="signup-link" type="button" onClick={onGoLogin}>
          Acesse aqui
        </button>
      </footer>
    </div>
  );
}


