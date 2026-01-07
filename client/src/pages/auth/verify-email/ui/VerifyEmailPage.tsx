import { useMemo, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { accountApi } from '@/entities/session/api/accountApi';
import { getApiErrorMessage } from '@/shared/api';
import { useAsyncRequest } from '@/shared/lib/hooks/useAsyncRequest';
import { useCooldown } from '@/shared/lib/hooks/useCooldown';
import { AlertMessage, LinkButton, PrimaryButton } from '@/shared/ui';
import { AuthLayout } from '@/widgets/auth/auth-layout';

type LocationState = { email?: string; emailConfirmationSent?: boolean } | null;

export function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();

  const email = useMemo(() => {
    const fromState = (location.state as LocationState)?.email;
    const fromQuery = params.get('email') ?? undefined;
    return fromState ?? fromQuery ?? '';
  }, [location.state, params]);

  const emailConfirmationSent = useMemo(() => {
    const fromState = (location.state as LocationState)?.emailConfirmationSent;
    return fromState ?? true;
  }, [location.state]);

  const [alert, setAlert] = useState<{ message: string; variant: 'success' | 'error' } | null>(null);

  const cooldown = useCooldown({ seconds: 60 });
  const resendReq = useAsyncRequest(accountApi.requestEmailConfirmation);

  return (
    <AuthLayout
      title="Verifique seu e-mail"
      subtitle={
        email
          ? `Enviamos um link de confirmação para ${email}. Abra seu e-mail e clique no link para ativar sua conta.`
          : 'Enviamos um link de confirmação para seu e-mail. Abra seu e-mail e clique no link para ativar sua conta.'
      }
      onBack={() => navigate(-1)}
      footer={
        <span>
          Já confirmou?{' '}
          <LinkButton type="button" onClick={() => navigate('/login')}>
            Entrar
          </LinkButton>
        </span>
      }
    >
      {!emailConfirmationSent ? (
        <AlertMessage
          message="Não conseguimos enviar o e-mail automaticamente. Você pode reenviar a confirmação abaixo."
          variant="error"
        />
      ) : null}

      {alert ? <AlertMessage message={alert.message} variant={alert.variant} /> : null}

      <PrimaryButton
        type="button"
        disabled={!email || resendReq.isLoading || cooldown.isCoolingDown}
        onClick={async () => {
          if (!email) return;
          try {
            setAlert(null);
            await resendReq.run({ email });
            cooldown.start();
            setAlert({ message: 'E-mail de confirmação reenviado.', variant: 'success' });
          } catch (e) {
            setAlert({
              message: getApiErrorMessage(e, 'Não foi possível reenviar agora. Tente novamente.'),
              variant: 'error',
            });
          }
        }}
      >
        {cooldown.isCoolingDown ? cooldown.label : 'Reenviar e-mail de confirmação'}
      </PrimaryButton>
    </AuthLayout>
  );
}


