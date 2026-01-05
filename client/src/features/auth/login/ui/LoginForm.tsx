import { useState, type FormEvent } from 'react';

import { PasswordInput } from '@/shared/ui';

import { loginSchema, type LoginValues } from '../model/schema';

import './LoginForm.css';

type Props = {
  onSubmit?: (values: LoginValues) => void;
  onGoRegister?: () => void;
  onGoForgot?: () => void;
  onGoogle?: () => void;
};

export function LoginForm(props: Props) {
  const { onSubmit, onGoRegister, onGoForgot, onGoogle } = props;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Dados inválidos');
      return;
    }
    setError(null);
    onSubmit?.(parsed.data);
  };

  return (
    <div className="login-content">
      <div className="welcome">
        <p className="welcome-back">Bem-vindo de volta!</p>
        <h1 className="login-title">Log In</h1>
      </div>

      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field-label">E-mail</span>
          <input
            className="field-input"
            type="email"
            placeholder="Digite seu email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
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
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />

        {error ? <p className="form-error">{error}</p> : null}

        <button className="submit-btn" type="submit">
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


