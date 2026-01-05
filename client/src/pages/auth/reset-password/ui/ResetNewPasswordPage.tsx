import { useNavigate } from 'react-router-dom';

import { PasswordRecoveryFooter, SetNewPasswordForm } from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetNewPasswordPage() {
  const navigate = useNavigate();

  return (
    <RecoveryLayout
      title="Redefinição de senha"
      subtitle="Insira abaixo sua nova senha."
      onBack={() => navigate('/reset/code')}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <SetNewPasswordForm onSubmit={() => navigate('/reset/success')} />
    </RecoveryLayout>
  );
}


