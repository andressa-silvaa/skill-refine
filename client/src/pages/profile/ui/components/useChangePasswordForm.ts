import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';

import { profileApi } from '@/entities/session';
import { handleApiSaveError } from '@/shared/api';
import { hasFormErrors } from '@/shared/lib/forms';
import { notify } from '@/shared/lib/notify';

type Props = {
  onCancel?: () => void;
  onSaved?: () => void;
  disabled?: boolean;
  showActions?: boolean;
};

type ChangePasswordValues = {
  current: string;
  next: string;
  confirm: string;
};

export function useChangePasswordForm(props: Props) {
  const { onCancel, onSaved, disabled = false, showActions = true } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();

  const schema = useMemo(
    () =>
      z
        .object({
          current: z.string().min(1, t('changePassword.requiredCurrent')),
          next: z.string().min(8, t('changePassword.passwordMin')),
          confirm: z.string().min(1, t('changePassword.confirmRequired')),
        })
        .refine((v) => v.next === v.confirm, { message: t('changePassword.mismatch'), path: ['confirm'] }),
    [t]
  );

  const {
    register,
    handleSubmit,
    reset,
    trigger,
    setError,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
    watch,
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(schema as any),
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
        ? t('changePassword.mismatch')
        : undefined;
  const showConfirmError = confirmInteracted && Boolean(confirmErrorMessage);

  const onForgotPassword = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate('/reset/email');
  };

  const onSubmit = handleSubmit(async (values) => {
    try {
      await profileApi.changePassword({
        current_password: values.current,
        new_password: values.next,
        confirm_new_password: values.confirm,
      });
      notify.success(t('changePassword.updated'));
      reset({ current: '', next: '', confirm: '' });
      onSaved?.();
    } catch (e) {
      handleApiSaveError(e, {
        fallbackMessage: t('changePassword.saveFailed'),
        onFieldErrors: (fields) => {
          if (fields.current_password) setError('current', { message: fields.current_password });
          if (fields.new_password) setError('next', { message: fields.new_password });
          if (fields.confirm_new_password) setError('confirm', { message: fields.confirm_new_password });
        },
      });
    }
  });

  const onResetAndCancel = () => {
    reset({ current: '', next: '', confirm: '' });
    onCancel?.();
  };

  return {
    t,
    register,
    onSubmit,
    isSubmitting,
    errors,
    disabled,
    showActions,
    isReady,
    hasBlockingErrors: hasFormErrors(errors),
    currentErrorMessage,
    nextErrorMessage,
    confirmErrorMessage: confirmInteracted ? confirmErrorMessage : undefined,
    showCurrentError,
    showNextError,
    showConfirmError,
    onForgotPassword,
    onResetAndCancel,
  };
}
