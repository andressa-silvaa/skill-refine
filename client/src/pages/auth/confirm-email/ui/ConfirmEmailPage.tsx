import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { accountApi } from '@/entities/session/api/accountApi';
import { useEmailConfirmationResend } from '@/features/auth/email-confirmation';
import { getApiErrorMessage } from '@/shared/api';
import { isValidEmail } from '@/shared/lib/forms';
import { useAsyncRequest } from '@/shared/lib/hooks/useAsyncRequest';
import { AlertMessage, AuthForm, Field, PrimaryButton, Spinner } from '@/shared/ui';
import { AuthLayout } from '@/widgets/auth/auth-layout';

type LocationState = { email?: string; emailConfirmationSent?: boolean } | null;

export function ConfirmEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const token = useMemo(() => params.get('token') ?? '', [params]);
  const emailFromQuery = useMemo(() => params.get('email') ?? '', [params]);
  const emailFromState = useMemo(() => (location.state as LocationState)?.email ?? '', [location.state]);
  const resendSentFromState = useMemo(
    () => Boolean((location.state as LocationState)?.emailConfirmationSent),
    [location.state]
  );

  const [emailForResend, setEmailForResend] = useState('');
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverSuccess, setServerSuccess] = useState<string | null>(null);

  const {
    run: confirmEmail,
    isLoading: isConfirming,
    isSuccess: isConfirmed,
    isError: isConfirmError,
  } = useAsyncRequest(accountApi.confirmEmail);
  const resend = useEmailConfirmationResend({ cooldownSeconds: 60 });

  const canResend = isValidEmail(emailForResend) && !resend.isLoading && !resend.isCoolingDown;

  useEffect(() => {
    const initial = (emailFromState || emailFromQuery || '').trim();
    if (!initial) return;
    setEmailForResend(initial);
  }, [emailFromQuery, emailFromState]);

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
        token
          ? isConfirming
            ? 'Estamos confirmando seu e-mail. Aguarde um instante.'
            : isConfirmed
              ? 'Tudo certo! Sua conta está pronta para uso.'
              : 'Não foi possível confirmar automaticamente. Você pode reenviar a confirmação abaixo.'
          : emailForResend
            ? `Vamos reenviar o link de confirmação para ${emailForResend}.`
            : 'Informe seu e-mail para reenviar o link de confirmação.'
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
          {resendSentFromState ? (
            <AlertMessage message="E-mail de confirmação enviado. Verifique sua caixa de entrada." variant="success" />
          ) : null}

          <AuthForm
            onSubmit={(e) => {
              e.preventDefault();
              void (async () => {
                if (!canResend) return;
                try {
                  setServerError(null);
                  setServerSuccess(null);
                  await resend.resend(emailForResend.trim());
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

            <PrimaryButton type="submit" disabled={!canResend}>
              {resend.isCoolingDown ? resend.cooldownLabel : resend.isLoading ? 'Enviando...' : 'Reenviar confirmação'}
            </PrimaryButton>
          </AuthForm>
        </>
      ) : null}
    </AuthLayout>
  );
}


