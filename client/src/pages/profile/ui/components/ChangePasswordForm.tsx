import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';

import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { hasFormErrors } from '@/shared/lib/forms';
import { notify } from '@/shared/lib/notify';
import { LinkButton, PasswordInput } from '@/shared/ui';

import { registerSchema } from '@/features/auth/register/model/schema';

import './ChangePasswordForm.css';

type Props = {
  onCancel?: () => void;
  onSaved?: () => void;
  disabled?: boolean;
  showActions?: boolean;
};

const registerBaseSchema = (registerSchema as unknown as z.ZodEffects<z.AnyZodObject>).innerType();
const registerShape = registerBaseSchema.shape as unknown as {
  password: z.ZodTypeAny;
  confirm: z.ZodTypeAny;
};

const changePasswordSchema = z
  .object({
    current: z.string().min(1, 'Informe sua senha atual'),
    next: registerShape.password,
    confirm: registerShape.confirm,
  })
  .refine((v) => v.next === v.confirm, { message: 'As senhas não coincidem', path: ['confirm'] });

type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

export function ChangePasswordForm(props: Props) {
  const { onCancel, onSaved, disabled = false, showActions = true } = props;
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    reset,
    trigger,
    setError,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
    watch,
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current: '', next: '', confirm: '' },
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  const nextValue = watch('next');
  const confirmValue = watch('confirm');
  const confirmInteracted = Boolean(touchedFields.confirm || dirtyFields.confirm);

  useEffect(() => {
    if (!confirmInteracted) return;
    void trigger('confirm');
  }, [confirmInteracted, nextValue, trigger]);

  const showCurrentError = Boolean((touchedFields.current || dirtyFields.current) && errors.current?.message);
  const currentErrorMessage = showCurrentError && typeof errors.current?.message === 'string' ? errors.current.message : undefined;

  const showNextError = Boolean((touchedFields.next || dirtyFields.next) && errors.next?.message);
  const nextErrorMessage = showNextError && typeof errors.next?.message === 'string' ? errors.next.message : undefined;

  const confirmMismatchVisible =
    confirmInteracted && Boolean(nextValue) && Boolean(confirmValue) && nextValue !== confirmValue;
  const confirmErrorMessage =
    confirmInteracted && typeof errors.confirm?.message === 'string'
      ? errors.confirm.message
      : confirmMismatchVisible
        ? 'As senhas não coincidem'
        : undefined;
  const showConfirmError = confirmInteracted && Boolean(confirmErrorMessage);

  return (
    <form
      className="sr-change-password__form"
      onSubmit={handleSubmit(async (values) => {
        try {
          await profileApi.changePassword({
            current_password: values.current,
            new_password: values.next,
            confirm_new_password: values.confirm,
          });
          notify.success('Senha atualizada com sucesso.');
          reset({ current: '', next: '', confirm: '' });
          onSaved?.();
        } catch (e) {
          const fields = getApiFieldErrors(e);
          if (fields?.current_password) setError('current', { message: fields.current_password });
          if (fields?.new_password) setError('next', { message: fields.new_password });
          if (fields?.confirm_new_password) setError('confirm', { message: fields.confirm_new_password });
          const hasField = Boolean(fields?.current_password || fields?.new_password || fields?.confirm_new_password);
          if (!hasField) notify.error(getApiErrorMessage(e, 'Não foi possível salvar agora.'));
        }
      })}
    >
      <PasswordInput
        label="Senha atual"
        {...register('current')}
        autoComplete="current-password"
        disabled={disabled || isSubmitting}
        isInvalid={showCurrentError}
        error={currentErrorMessage}
        wrapperClassName="sr-profile-field"
        inputClassName="sr-profile-input"
        labelRight={
          <LinkButton
            type="button"
            className="sr-change-password__forgot"
            disabled={disabled}
            onClick={(e) => {
              e.preventDefault();
              navigate('/reset/email');
            }}
          >
            <i className="fa-regular fa-circle-question" aria-hidden /> Esqueceu a senha?
          </LinkButton>
        }
      />

      <div className="sr-change-password__row">
        <PasswordInput
          label="Nova senha"
          {...register('next')}
          autoComplete="new-password"
          placeholder="Crie uma nova senha"
          disabled={disabled || isSubmitting}
          isInvalid={showNextError}
          error={nextErrorMessage}
          wrapperClassName="sr-profile-field"
          inputClassName="sr-profile-input"
        />

        <PasswordInput
          label="Confirmar senha"
          {...register('confirm')}
          autoComplete="new-password"
          placeholder="Confirme a nova senha"
          disabled={disabled || isSubmitting}
          isInvalid={showConfirmError}
          error={confirmInteracted ? confirmErrorMessage : undefined}
          wrapperClassName="sr-profile-field"
          inputClassName="sr-profile-input"
        />
      </div>

      {showActions ? (
        <div className="sr-change-password__actions">
          <button className="sr-btn sr-btn--primary" type="submit" disabled={disabled || !isReady || hasFormErrors(errors) || isSubmitting}>
            {isSubmitting ? 'Salvando...' : 'Salvar'}
          </button>
          <button
            className="sr-btn sr-btn--secondary"
            type="button"
            onClick={() => {
              reset({ current: '', next: '', confirm: '' });
              onCancel?.();
            }}
            disabled={disabled || isSubmitting}
          >
            Cancelar
          </button>
        </div>
      ) : null}
    </form>
  );
}


