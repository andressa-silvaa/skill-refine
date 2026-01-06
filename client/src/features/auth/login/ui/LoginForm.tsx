import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { PasswordInput } from '@/shared/ui';
import { GENERIC_FORM_ERROR_MESSAGE, hasFormErrors } from '@/shared/lib/forms';

import { loginSchema, type LoginValues } from '../model/schema';

import './LoginForm.css';

type Props = {
  onSubmit?: (values: LoginValues) => void;
  onGoRegister?: () => void;
  onGoForgot?: () => void;
  onGoogle?: () => void;
  serverError?: string;
};

export function LoginForm(props: Props) {
  const { onSubmit, onGoRegister, onGoForgot, onGoogle, serverError } = props;

  const {
    register,
    handleSubmit,
    trigger,
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
  const showGenericError = showEmailError || showPasswordError;

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

        {showGenericError ? <p className="form-error">{GENERIC_FORM_ERROR_MESSAGE}</p> : null}
        {serverError ? <p className="form-error">{serverError}</p> : null}

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


