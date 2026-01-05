import { useState, type FormEvent } from 'react';

import { VerificationCodeInput } from '@/shared/ui';

import { verifyCodeSchema, type VerifyCodeValues } from '../model/schemas';

import './PasswordRecovery.css';

type Props = {
  onSubmit?: (values: VerifyCodeValues) => void;
  onResend?: () => void;
};

export function VerifyCodeForm(props: Props) {
  const { onSubmit, onResend } = props;
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = verifyCodeSchema.safeParse({ code });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Código inválido');
      return;
    }
    setError(null);
    onSubmit?.(parsed.data);
  };

  return (
    <form className="recovery-form" onSubmit={handleSubmit}>
      <VerificationCodeInput length={5} value={code} onChange={setCode} autoFocus />

      {error ? <p className="recovery-error">{error}</p> : null}

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
  );
}


