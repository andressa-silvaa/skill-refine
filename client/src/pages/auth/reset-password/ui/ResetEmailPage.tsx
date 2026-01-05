import { useNavigate } from 'react-router-dom';

import { RequestResetForm, PasswordRecoveryFooter } from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetEmailPage() {
  const navigate = useNavigate();

  return (
    <RecoveryLayout
      title="Recuperação de senha"
      subtitle="Informe o e-mail para o qual deseja receber o envio de redefinição de senha."
      onBack={() => navigate(-1)}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <RequestResetForm onSubmit={() => navigate('/reset/code')} />
    </RecoveryLayout>
  );
}


