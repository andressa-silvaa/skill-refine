import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { LinkButton, PasswordInput } from '@/shared/ui';
import { hasFormErrors } from '@/shared/lib/forms';

import { loginSchema, type LoginValues } from '../model/schema';

import './LoginForm.css';

type Props = {
  onSubmit?: (values: LoginValues) => void;
  onGoRegister?: () => void;
  onGoForgot?: () => void;
  onGoogle?: () => void;
  serverError?: string;
  onConfirmEmail?: (email: string) => void | Promise<void>;
  confirmEmailBusy?: boolean;
  confirmEmailLabel?: string;
  confirmEmailError?: string;
  showConfirmEmailCta?: boolean;
};

export function LoginForm(props: Props) {
  const {
    onSubmit,
    onGoRegister,
    onGoForgot,
    onGoogle,
    serverError,
    onConfirmEmail,
    confirmEmailBusy,
    confirmEmailLabel,
    confirmEmailError,
    showConfirmEmailCta,
  } = props;

  const {
    register,
    handleSubmit,
    trigger,
    watch,
    formState: { errors, touchedFields, dirtyFields, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const [isReady, setIsReady] = useState(false);

  const showEmailError = (!!touchedFields.email || !!dirtyFields.email) && !!errors.email?.message;
  const showPasswordError = (!!touchedFields.password || !!dirtyFields.password) && !!errors.password?.message;

  useEffect(() => {
    void trigger().finally(() => setIsReady(true));
  }, [trigger]);

  return (
    <div className="login-content">
      <div className="welcome">
        <p className="welcome-back">Bem-vindo de volta!</p>
        <h1 className="login-title">Log In</h1>
      </div>

      <form className="form" onSubmit={handleSubmit((values) => onSubmit?.(values))}>
        <label className="field">
          <span className="field-label">E-mail</span>
          <input
            {...register('email')}
            className={`field-input${showEmailError ? ' is-invalid' : ''}`}
            type="email"
            placeholder="Digite seu email"
            autoComplete="email"
            aria-invalid={showEmailError}
          />
          {showEmailError ? <p className="field-error">{errors.email?.message}</p> : null}
        </label>

        <PasswordInput
          label="Senha"
          labelRight={
            <button
              className="forgot-link"
              type="button"
              onClick={(e) => {
                e.preventDefault();
                onGoForgot?.();
              }}
            >
              Esqueceu a senha?
            </button>
          }
          {...register('password')}
          autoComplete="current-password"
          isInvalid={showPasswordError}
          error={showPasswordError ? errors.password?.message : undefined}
        />

        <div className="secondary-actions" aria-live="polite">
          <LinkButton
            type="button"
            className="login-secondary-link"
            disabled={confirmEmailBusy}
            onClick={(e) => {
              e.preventDefault();
              void onConfirmEmail?.(watch('email') ?? '');
            }}
          >
            {confirmEmailLabel ?? 'Confirmar e-mail'}
          </LinkButton>
          {confirmEmailError ? <p className="secondary-error">{confirmEmailError}</p> : null}
        </div>

        {serverError ? (
          <div className="form-server-error">
            <p className="form-error" style={{ width: 'auto' }}>
              {serverError}
            </p>
            {showConfirmEmailCta ? (
              <LinkButton
                type="button"
                className="login-inline-cta"
                disabled={confirmEmailBusy}
                onClick={(e) => {
                  e.preventDefault();
                  void onConfirmEmail?.(watch('email') ?? '');
                }}
              >
                {confirmEmailLabel ?? 'Confirmar e-mail'}
              </LinkButton>
            ) : null}
          </div>
        ) : null}

        <button className="submit-btn" type="submit" disabled={!isReady || hasFormErrors(errors) || isSubmitting}>
          <span>ENTRAR</span>
          <span className="arrow">→</span>
        </button>
      </form>

      <p className="divider">Ou continue com o Google</p>

      <button className="google-btn" type="button" aria-label="Entrar com Google" onClick={onGoogle}>
        <img src="/google.svg" alt="Google" />
      </button>

      <footer className="footer">
        <span>Ainda não tem uma conta?</span>
        <button className="signup-link" type="button" onClick={onGoRegister}>
          Cadastre-se aqui
        </button>
      </footer>
    </div>
  );
}


