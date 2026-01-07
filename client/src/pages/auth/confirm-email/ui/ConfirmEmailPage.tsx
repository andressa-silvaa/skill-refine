import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { accountApi } from '@/entities/session/api/accountApi';
import { getApiErrorMessage } from '@/shared/api';
import { useAsyncRequest } from '@/shared/lib/hooks/useAsyncRequest';
import { useCooldown } from '@/shared/lib/hooks/useCooldown';
import { AlertMessage, AuthForm, Field, LinkButton, PrimaryButton, Spinner } from '@/shared/ui';
import { AuthLayout } from '@/widgets/auth/auth-layout';

export function ConfirmEmailPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = useMemo(() => params.get('token') ?? '', [params]);

  const [emailForResend, setEmailForResend] = useState('');
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverSuccess, setServerSuccess] = useState<string | null>(null);

  const {
    run: confirmEmail,
    isLoading: isConfirming,
    isSuccess: isConfirmed,
    isError: isConfirmError,
  } = useAsyncRequest(accountApi.confirmEmail);
  const { run: resendEmail, isLoading: isResending } = useAsyncRequest(accountApi.requestEmailConfirmation);
  const cooldown = useCooldown({ seconds: 60 });

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        setServerError(null);
        setServerSuccess(null);
        await confirmEmail({ token });
        setServerSuccess('E-mail confirmado com sucesso.');
      } catch (e) {
        setServerError(getApiErrorMessage(e, 'Não foi possível confirmar seu e-mail.'));
      }
    })();
  }, [token, confirmEmail]);

  return (
    <AuthLayout
      title="Confirmação de e-mail"
      subtitle={
        !token
          ? 'Token ausente. Solicite um novo e-mail de confirmação.'
          : isConfirming
            ? 'Estamos confirmando seu e-mail. Aguarde um instante.'
            : isConfirmed
              ? 'Tudo certo! Sua conta está pronta para uso.'
              : 'Não foi possível confirmar automaticamente. Você pode reenviar a confirmação abaixo.'
      }
      onBack={() => navigate(-1)}
      footer={
        <span>
          Voltar para{' '}
          <LinkButton type="button" onClick={() => navigate('/login')}>
            login
          </LinkButton>
        </span>
      }
    >
      {isConfirming ? (
        <div style={{ display: 'grid', placeItems: 'center', padding: '8px 0' }}>
          <Spinner />
        </div>
      ) : null}

      {isConfirmed ? (
        <>
          <div className="auth-success">
            <div className="auth-success-icon">✔</div>
            <p className="auth-success-text">Seu e-mail foi confirmado.</p>
          </div>
          <PrimaryButton type="button" onClick={() => navigate('/login')}>
            Entrar
          </PrimaryButton>
        </>
      ) : null}

      {isConfirmError || !token ? (
        <>
          {serverError ? <AlertMessage message={serverError} variant="error" /> : null}
          {serverSuccess ? <AlertMessage message={serverSuccess} variant="success" /> : null}

          <AuthForm
            onSubmit={(e) => {
              e.preventDefault();
              void (async () => {
                if (!emailForResend) return;
                try {
                  setServerError(null);
                  setServerSuccess(null);
                  await resendEmail({ email: emailForResend });
                  cooldown.start();
                  setServerSuccess('E-mail de confirmação reenviado.');
                } catch (err) {
                    setServerError(getApiErrorMessage(err, 'Não foi possível reenviar agora. Tente novamente.'));
                }
              })();
            }}
          >
            <Field
              label="E-mail"
              type="email"
              placeholder="Insira seu e-mail"
              autoComplete="email"
              value={emailForResend}
              onChange={(e) => setEmailForResend(e.target.value)}
            />

            <PrimaryButton type="submit" disabled={isResending || cooldown.isCoolingDown || !emailForResend}>
              {cooldown.isCoolingDown ? cooldown.label : 'Reenviar e-mail de confirmação'}
            </PrimaryButton>
          </AuthForm>
        </>
      ) : null}
    </AuthLayout>
  );
}


