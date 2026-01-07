import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { useEmailConfirmationResend } from '@/features/auth/email-confirmation';
import { asApiError, getApiErrorMessage } from '@/shared/api';
import { isValidEmail } from '@/shared/lib/forms';
import { notify } from '@/shared/lib/notify';
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

  const hasExplicitSentFlag = useMemo(() => {
    const fromState = (location.state as LocationState)?.emailConfirmationSent;
    return typeof fromState === 'boolean';
  }, [location.state]);

  const { resend, isLoading, isCoolingDown, cooldownLabel, startCooldown } = useEmailConfirmationResend({
    cooldownSeconds: 60,
  });
  const canResend = isValidEmail(email) && !isLoading && !isCoolingDown;

  useEffect(() => {
    if (!hasExplicitSentFlag) return;
    if (!emailConfirmationSent) return;
    if (!email) return;
    startCooldown(60);
  }, [email, emailConfirmationSent, hasExplicitSentFlag, startCooldown]);

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

      <PrimaryButton
        type="button"
        disabled={!canResend}
        onClick={async () => {
          if (!canResend) return;
          try {
            await resend(email.trim());
            notify.success('E-mail de confirmação reenviado.');
          } catch (e) {
            const apiErr = asApiError(e);
            if (apiErr?.status === 429) return;
            notify.error(getApiErrorMessage(e, 'Não foi possível reenviar agora. Tente novamente.'));
          }
        }}
      >
        {isCoolingDown ? cooldownLabel : isLoading ? 'Enviando...' : 'Reenviar confirmação'}
      </PrimaryButton>
    </AuthLayout>
  );
}


