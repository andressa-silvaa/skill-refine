import { useState } from 'react';
import RecoveryLayout from '../../components/RecoveryLayout';

export default function ResetEmailPage({ onBack, onContinue, onGoLogin }) {
  const [email, setEmail] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    onContinue?.(email);
  };

  return (
    <RecoveryLayout
      title="Recuperação de senha"
      subtitle="Informe o e-mail para o qual deseja receber o envio de redefinição de senha."
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

        <button className="recovery-btn" type="submit">
          Recuperar senha
        </button>
      </form>
    </RecoveryLayout>
  );
}

