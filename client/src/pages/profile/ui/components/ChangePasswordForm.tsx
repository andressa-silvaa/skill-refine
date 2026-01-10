import { LinkButton, PasswordInput } from '@/shared/ui';

import { useChangePasswordForm } from './useChangePasswordForm';

import './ChangePasswordForm.css';

type Props = {
  onCancel?: () => void;
  onSaved?: () => void;
  disabled?: boolean;
  showActions?: boolean;
};

export function ChangePasswordForm(props: Props) {
  const ui = useChangePasswordForm(props);

  return (
    <form
      className="sr-change-password__form"
      onSubmit={ui.onSubmit}
    >
      <PasswordInput
        label={ui.t('changePassword.current')}
        {...ui.register('current')}
        autoComplete="current-password"
        disabled={ui.disabled || ui.isSubmitting}
        isInvalid={ui.showCurrentError}
        error={ui.currentErrorMessage}
        wrapperClassName="sr-profile-field"
        inputClassName="sr-profile-input"
        labelRight={
          <LinkButton
            type="button"
            className="sr-change-password__forgot"
            disabled={ui.disabled}
            onClick={ui.onForgotPassword}
          >
            <i className="fa-regular fa-circle-question" aria-hidden /> {ui.t('changePassword.forgot')}
          </LinkButton>
        }
      />

      <div className="sr-change-password__row">
        <PasswordInput
          label={ui.t('changePassword.next')}
          {...ui.register('next')}
          autoComplete="new-password"
          placeholder={ui.t('changePassword.nextPlaceholder')}
          disabled={ui.disabled || ui.isSubmitting}
          isInvalid={ui.showNextError}
          error={ui.nextErrorMessage}
          wrapperClassName="sr-profile-field"
          inputClassName="sr-profile-input"
        />

        <PasswordInput
          label={ui.t('changePassword.confirm')}
          {...ui.register('confirm')}
          autoComplete="new-password"
          placeholder={ui.t('changePassword.confirmPlaceholder')}
          disabled={ui.disabled || ui.isSubmitting}
          isInvalid={ui.showConfirmError}
          error={ui.confirmErrorMessage}
          wrapperClassName="sr-profile-field"
          inputClassName="sr-profile-input"
        />
      </div>

      {ui.showActions ? (
        <div className="sr-change-password__actions">
          <button
            className="sr-btn sr-btn--primary"
            type="submit"
            disabled={ui.disabled || !ui.isReady || ui.hasBlockingErrors || ui.isSubmitting}
          >
            {ui.isSubmitting ? ui.t('common.saving') : ui.t('common.save')}
          </button>
          <button
            className="sr-btn sr-btn--secondary"
            type="button"
            onClick={ui.onResetAndCancel}
            disabled={ui.disabled || ui.isSubmitting}
          >
            {ui.t('common.cancel')}
          </button>
        </div>
      ) : null}
    </form>
  );
}


