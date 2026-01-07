import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import 'react-date-picker/dist/DatePicker.css';
import 'react-calendar/dist/Calendar.css';
import { hasFormErrors } from '@/shared/lib/forms';
import { PasswordInput } from '@/shared/ui';
import { registerSchema, type RegisterFormValues, type RegisterValues } from '../model/schema';
import { BirthDateField } from './components/BirthDateField';
import { RegisterFooter } from './components/RegisterFooter';
import { SubmitButton } from './components/SubmitButton';
import { TermsField } from './components/TermsField';
import { TextInputField } from './components/TextInputField';
import './RegisterForm.css';

type Props = {
  onSubmit?: (values: RegisterValues) => void;
  onGoLogin?: () => void;
  serverError?: string;
};
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

  const hasInteracted = <K extends keyof RegisterFormValues>(field: K) =>
    Boolean(touchedFields[field] || dirtyFields[field]);
  const shouldShowError = <K extends keyof RegisterFormValues>(field: K) =>
    hasInteracted(field) && Boolean(errors[field]?.message);

  const showFullNameError = shouldShowError('fullName');
  const showBirthDateError = shouldShowError('birthDate');
  const showEmailError = shouldShowError('email');
  const showPasswordError = shouldShowError('password');
  const showAcceptedTermsError = shouldShowError('acceptedTerms');

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  const passwordValue = watch('password');
  const confirmValue = watch('confirm');
  const confirmInteracted = hasInteracted('confirm');

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
        <TextInputField
          label="Nome completo"
          placeholder="Digite seu nome"
          type="text"
          autoComplete="name"
          registration={register('fullName')}
          isInvalid={showFullNameError}
          errorMessage={errors.fullName?.message}
        />

        <BirthDateField
          control={control}
          isInvalid={showBirthDateError}
          errorMessage={errors.birthDate?.message}
        />

        <TextInputField
          label="E-mail"
          placeholder="digite seu e-mail"
          type="email"
          autoComplete="email"
          registration={register('email')}
          isInvalid={showEmailError}
          errorMessage={errors.email?.message}
        />

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

        <TermsField
          registration={register('acceptedTerms')}
          isInvalid={showAcceptedTermsError}
          errorMessage={errors.acceptedTerms?.message}
        />

        {serverError ? <p className="form-error">{serverError}</p> : null}

        <SubmitButton disabled={!isReady || hasFormErrors(errors) || isSubmitting} />
      </form>

      <RegisterFooter onGoLogin={onGoLogin} />
    </div>
  );
}


