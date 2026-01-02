import { useState } from 'react';
import RecoveryLayout from '../../components/RecoveryLayout';
import VerificationCodeInput from '../../components/VerificationCodeInput';

export default function ResetCodePage({ onBack, onConfirm, onResend, onGoLogin }) {
  const [code, setCode] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    onConfirm?.(code);
  };

  return (
    <RecoveryLayout
      title="Código de confirmação"
      subtitle="Insira o código de 5 dígitos enviado para seu e-mail."
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
        <VerificationCodeInput length={5} value={code} onChange={setCode} autoFocus />

        <button
          className="recovery-small-action"
          type="button"
          onClick={onResend}
          style={{ justifySelf: 'start' }}
        >
          Reenviar código
        </button>

        <button className="recovery-btn" type="submit" disabled={code.length !== 5}>
          Confirmar código
        </button>
      </form>
    </RecoveryLayout>
  );
}

