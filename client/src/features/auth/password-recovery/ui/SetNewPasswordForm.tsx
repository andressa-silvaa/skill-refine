import { useState, type FormEvent } from 'react';

import { PasswordInput } from '@/shared/ui';

import { setNewPasswordSchema, type SetNewPasswordValues } from '../model/schemas';

import './PasswordRecovery.css';

type Props = {
  onSubmit?: (values: SetNewPasswordValues) => void;
};

export function SetNewPasswordForm(props: Props) {
  const { onSubmit } = props;
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = setNewPasswordSchema.safeParse({ password, confirm });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Dados inválidos');
      return;
    }
    setError(null);
    onSubmit?.(parsed.data);
  };

  return (
    <form className="recovery-form" onSubmit={handleSubmit}>
      <PasswordInput
        label="Nova senha"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        autoComplete="new-password"
      />

      <PasswordInput
        label="Confirme a senha"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        autoComplete="new-password"
      />

      {error ? <p className="recovery-error">{error}</p> : null}

      <button className="recovery-btn" type="submit" disabled={!password || !confirm}>
        Redefinir senha
      </button>
    </form>
  );
}


