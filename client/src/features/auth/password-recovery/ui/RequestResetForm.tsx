import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { GENERIC_FORM_ERROR_MESSAGE, hasFormErrors } from '@/shared/lib/forms';

import { requestResetSchema, type RequestResetValues } from '../model/schemas';

import '@/shared/ui/auth/AuthStyles.css';

type Props = {
  onSubmit?: (values: RequestResetValues) => void | Promise<void>;
  serverError?: string;
};

export function RequestResetForm(props: Props) {
  const { onSubmit, serverError } = props;

  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
  } = useForm<RequestResetValues>({
    resolver: zodResolver(requestResetSchema),
    defaultValues: { email: '' },
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const [isReady, setIsReady] = useState(false);

  const showEmailError = (!!touchedFields.email || !!dirtyFields.email) && !!errors.email?.message;
  const showGenericError = showEmailError;

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  return (
    <form className="recovery-form" onSubmit={handleSubmit((values) => onSubmit?.(values))}>
      <label className="recovery-field">
        <span className="recovery-label">E-mail</span>
        <input
          {...register('email')}
          className={`recovery-input${showEmailError ? ' is-invalid' : ''}`}
          type="email"
          placeholder="Insira um e-mail válido"
          aria-invalid={showEmailError}
        />
        {showEmailError ? <p className="field-error">{errors.email?.message}</p> : null}
      </label>

      {showGenericError ? <p className="recovery-error">{GENERIC_FORM_ERROR_MESSAGE}</p> : null}
      {serverError ? <p className="recovery-error">{serverError}</p> : null}

      <button className="recovery-btn" type="submit" disabled={!isReady || hasFormErrors(errors) || isSubmitting}>
        Recuperar senha
      </button>
    </form>
  );
}


