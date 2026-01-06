import { useNavigate } from 'react-router-dom';

import { useEffect, useState } from 'react';

import {
  PasswordRecoveryFooter,
  SetNewPasswordForm,
  clearRecovery,
  getRecoveryEmail,
  getRecoveryResetToken,
  passwordRecoveryApi,
} from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetNewPasswordPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    if (!getRecoveryEmail() || !getRecoveryResetToken()) navigate('/reset/email', { replace: true });
  }, [navigate]);

  return (
    <RecoveryLayout
      title="Redefinição de senha"
      subtitle="Insira abaixo sua nova senha."
      onBack={() => navigate('/reset/code')}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <SetNewPasswordForm
        serverError={serverError ?? undefined}
        onSubmit={async (values) => {
          try {
            setServerError(null);
            const email = getRecoveryEmail();
            const reset_token = getRecoveryResetToken();
            if (!email || !reset_token) {
              navigate('/reset/email', { replace: true });
              return;
            }
            await passwordRecoveryApi.confirmNewPassword({ email, reset_token, new_password: values.password });
            clearRecovery();
            navigate('/reset/success');
          } catch (e) {
            setServerError('Não foi possível redefinir a senha. Tente novamente.');
          }
        }}
      />
    </RecoveryLayout>
  );
}


