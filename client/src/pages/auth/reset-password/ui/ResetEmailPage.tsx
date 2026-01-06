import { useNavigate } from 'react-router-dom';

import { useState } from 'react';

import {
  PasswordRecoveryFooter,
  RequestResetForm,
  clearRecovery,
  passwordRecoveryApi,
  setRecoveryEmail,
} from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetEmailPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  return (
    <RecoveryLayout
      title="Recuperação de senha"
      subtitle="Informe o e-mail para o qual deseja receber o envio de redefinição de senha."
      onBack={() => navigate(-1)}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <RequestResetForm
        serverError={serverError ?? undefined}
        onSubmit={async (values) => {
          try {
            setServerError(null);
            clearRecovery();
            await passwordRecoveryApi.requestReset({ email: values.email });
            setRecoveryEmail(values.email);
            navigate('/reset/code');
          } catch (e) {
            setServerError('Não foi possível enviar o código. Tente novamente.');
          }
        }}
      />
    </RecoveryLayout>
  );
}


