import { useNavigate } from 'react-router-dom';

import { ResetSuccess } from '@/features/auth/password-recovery';
import { AuthLayout } from '@/widgets/auth';

export function ResetSuccessPage() {
  const navigate = useNavigate();

  return (
    <AuthLayout title="Senha alterada com sucesso!" footer={null}>
      <ResetSuccess onGoLogin={() => navigate('/login')} />
    </AuthLayout>
  );
}


