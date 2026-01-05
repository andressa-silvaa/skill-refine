import { useNavigate } from 'react-router-dom';

import { ResetSuccess } from '@/features/auth/password-recovery';
import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

export function ResetSuccessPage() {
  const navigate = useNavigate();

  return (
    <RecoveryLayout title="Senha alterada com sucesso!" footer={null}>
      <ResetSuccess onGoLogin={() => navigate('/login')} />
    </RecoveryLayout>
  );
}


