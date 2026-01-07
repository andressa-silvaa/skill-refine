import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { PasswordInput } from '@/shared/ui';
import { GENERIC_FORM_ERROR_MESSAGE, hasFormErrors } from '@/shared/lib/forms';

import { setNewPasswordSchema, type SetNewPasswordValues } from '../model/schemas';

import '@/shared/ui/auth/AuthStyles.css';

type Props = {
  onSubmit?: (values: SetNewPasswordValues) => void | Promise<void>;
  serverError?: string;
};

export function SetNewPasswordForm(props: Props) {
  const { onSubmit, serverError } = props;

  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
    watch,
  } = useForm<SetNewPasswordValues>({
    resolver: zodResolver(setNewPasswordSchema),
    defaultValues: { password: '', confirm: '' },
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const [isReady, setIsReady] = useState(false);

  const showPasswordError = (!!touchedFields.password || !!dirtyFields.password) && !!errors.password?.message;

  const passwordValue = watch('password');
  const confirmValue = watch('confirm');
  const confirmInteracted = !!touchedFields.confirm || !!dirtyFields.confirm;

  const confirmMismatchVisible =
    confirmInteracted &&
    Boolean(passwordValue) &&
    Boolean(confirmValue) &&
    passwordValue !== confirmValue;
  const confirmErrorMessage = errors.confirm?.message ?? (confirmMismatchVisible ? 'As senhas não coincidem' : undefined);
  const showConfirmError = confirmInteracted && !!confirmErrorMessage;

  const showGenericError = showPasswordError || showConfirmError;

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  useEffect(() => {
    if (!confirmInteracted) return;
    void trigger('confirm');
  }, [passwordValue, confirmInteracted, trigger]);

  return (
    <form className="recovery-form" onSubmit={handleSubmit((values) => onSubmit?.(values))}>
      <PasswordInput
        label="Nova senha"
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

      {showGenericError ? <p className="recovery-error">{GENERIC_FORM_ERROR_MESSAGE}</p> : null}
      {serverError ? <p className="recovery-error">{serverError}</p> : null}

      <button className="recovery-btn" type="submit" disabled={!isReady || hasFormErrors(errors) || isSubmitting}>
        Redefinir senha
      </button>
    </form>
  );
}


