import { useNavigate } from 'react-router-dom';

import { PasswordRecoveryFooter, VerifyCodeForm } from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetCodePage() {
  const navigate = useNavigate();

  return (
    <RecoveryLayout
      title="Código de confirmação"
      subtitle="Insira o código de 5 dígitos enviado para seu e-mail."
      onBack={() => navigate('/reset/email')}
      footer={<PasswordRecoveryFooter onGoLogin={() => navigate('/login')} />}
    >
      <VerifyCodeForm onSubmit={() => navigate('/reset/new')} onResend={() => {}} />
    </RecoveryLayout>
  );
}


