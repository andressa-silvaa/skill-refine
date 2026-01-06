import { useNavigate } from 'react-router-dom';

import { useEffect, useState } from 'react';

import {
  PasswordRecoveryFooter,
  VerifyCodeForm,
  getRecoveryEmail,
  passwordRecoveryApi,
  setRecoveryResetToken,
} from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetCodePage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    if (!getRecoveryEmail()) navigate('/reset/email', { replace: true });
  }, [navigate]);

  return (
    <RecoveryLayout
      title="Código de confirmação"
      subtitle="Insira o código de 5 dígitos enviado para seu e-mail."
      onBack={() => navigate('/reset/email')}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <VerifyCodeForm
        serverError={serverError ?? undefined}
        onSubmit={async (values) => {
          try {
            setServerError(null);
            const email = getRecoveryEmail();
            if (!email) {
              navigate('/reset/email', { replace: true });
              return;
            }
            const res = await passwordRecoveryApi.verifyCode({ email, code: values.code });
            setRecoveryResetToken(res.reset_token);
            navigate('/reset/new');
          } catch (e) {
            setServerError('Código inválido ou expirado.');
          }
        }}
        onResend={async () => {
          const email = getRecoveryEmail();
          if (!email) return;
          await passwordRecoveryApi.requestReset({ email });
        }}
      />
    </RecoveryLayout>
  );
}


