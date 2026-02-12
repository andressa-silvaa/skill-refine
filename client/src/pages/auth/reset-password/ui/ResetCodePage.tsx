import { useNavigate } from 'react-router-dom';

import { useEffect, useState } from 'react';

import {
  PasswordRecoveryFooter,
  VerifyCodeForm,
  getRecoveryEmail,
  passwordRecoveryApi,
  setRecoveryResetToken,
} from '@/features/auth/password-recovery';
import { getApiErrorMessage } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { AuthLayout } from '@/widgets/auth';

export function ResetCodePage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (!getRecoveryEmail()) navigate('/reset/email', { replace: true });
  }, [navigate]);

  return (
    <AuthLayout
      title="Código de confirmação"
      subtitle="Insira o código de 5 dígitos enviado para seu e-mail."
      onBack={() => navigate(-1)}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <VerifyCodeForm
        serverError={serverError ?? undefined}
        isResending={isResending}
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
            setServerError(getApiErrorMessage(e, 'Código inválido ou expirado.'));
          }
        }}
        onResend={async () => {
          const email = getRecoveryEmail();
          if (!email) return;
          try {
            setServerError(null);
            setIsResending(true);
            await passwordRecoveryApi.requestReset({ email });
            notify.success('Código reenviado.');
          } catch (e) {
            setServerError(getApiErrorMessage(e, 'Não foi possível reenviar o código. Tente novamente.'));
          } finally {
            setIsResending(false);
          }
        }}
      />
    </AuthLayout>
  );
}


