import { useState, type FormEvent } from 'react';

import { requestResetSchema, type RequestResetValues } from '../model/schemas';

import './PasswordRecovery.css';

type Props = {
  onSubmit?: (values: RequestResetValues) => void;
};

export function RequestResetForm(props: Props) {
  const { onSubmit } = props;
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = requestResetSchema.safeParse({ email });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Dados inválidos');
      return;
    }
    setError(null);
    onSubmit?.(parsed.data);
  };

  return (
    <form className="recovery-form" onSubmit={handleSubmit}>
      <label className="recovery-field">
        <span className="recovery-label">E-mail</span>
        <input
          className="recovery-input"
          type="email"
          placeholder="Insira um e-mail válido"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </label>

      {error ? <p className="recovery-error">{error}</p> : null}

      <button className="recovery-btn" type="submit">
        Recuperar senha
      </button>
    </form>
  );
}


