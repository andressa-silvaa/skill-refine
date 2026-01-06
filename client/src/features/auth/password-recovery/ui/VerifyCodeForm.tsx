import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';

import { VerificationCodeInput } from '@/shared/ui';
import { GENERIC_FORM_ERROR_MESSAGE, hasFormErrors } from '@/shared/lib/forms';

import { verifyCodeSchema, type VerifyCodeValues } from '../model/schemas';

import './PasswordRecovery.css';

type Props = {
  onSubmit?: (values: VerifyCodeValues) => void;
  onResend?: () => void;
  serverError?: string;
};

export function VerifyCodeForm(props: Props) {
  const { onSubmit, onResend, serverError } = props;

  const {
    control,
    handleSubmit,
    trigger,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
  } = useForm<VerifyCodeValues>({
    resolver: zodResolver(verifyCodeSchema),
    defaultValues: { code: '' },
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const [isReady, setIsReady] = useState(false);

  const showCodeError = (!!touchedFields.code || !!dirtyFields.code) && !!errors.code?.message;
  const showGenericError = showCodeError;

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  return (
    <form className="recovery-form" onSubmit={handleSubmit((values) => onSubmit?.(values))}>
      <Controller
        control={control}
        name="code"
        render={({ field }) => (
          <VerificationCodeInput
            length={5}
            value={field.value}
            onChange={field.onChange}
            onBlur={field.onBlur}
            autoFocus
            isInvalid={showCodeError}
          />
        )}
      />
      {showCodeError ? <p className="field-error">{errors.code?.message}</p> : null}

      {showGenericError ? <p className="recovery-error">{GENERIC_FORM_ERROR_MESSAGE}</p> : null}
      {serverError ? <p className="recovery-error">{serverError}</p> : null}

      <button
        className="recovery-small-action"
        type="button"
        onClick={onResend}
        style={{ justifySelf: 'start' }}
      >
        Reenviar código
      </button>

      <button className="recovery-btn" type="submit" disabled={!isReady || hasFormErrors(errors) || isSubmitting}>
        Confirmar código
      </button>
    </form>
  );
}


