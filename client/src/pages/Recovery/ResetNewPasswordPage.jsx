import { useState } from 'react';
import RecoveryLayout from '../../components/RecoveryLayout';
import PasswordInput from '../../components/PasswordInput';

export default function ResetNewPasswordPage({ onBack, onSubmit, onGoLogin }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.(password, confirm);
  };

  return (
    <RecoveryLayout
      title="Redefinição de senha"
      subtitle="Insira abaixo sua nova senha."
      onBack={onBack}
      footer={
        <span>
          Você já tem uma conta?{' '}
          <button className="recovery-small-action" type="button" onClick={onGoLogin}>
            Entrar
          </button>
        </span>
      }
    >
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

        <button className="recovery-btn" type="submit" disabled={!password || !confirm}>
          Redefinir senha
        </button>
      </form>
    </RecoveryLayout>
  );
}

