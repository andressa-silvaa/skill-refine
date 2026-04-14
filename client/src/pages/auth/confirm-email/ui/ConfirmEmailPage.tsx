import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { accountApi } from '@/entities/session';
import { useEmailConfirmationResend } from '@/features/auth';
import { getApiErrorMessage } from '@/shared/api';
import { isValidEmail } from '@/shared/lib/forms';
import { useAsyncRequest } from '@/shared/lib/hooks/useAsyncRequest';
import { AlertMessage, AuthForm, Field, PrimaryButton, Spinner } from '@/features/auth';
import { LinkButton } from '@/shared/ui';
import { AuthLayout } from '@/widgets/auth';

type LocationState = { email?: string; emailConfirmationSent?: boolean } | null;

/** Evita concorrência enquanto um POST /confirm está em andamento. */
const emailConfirmTokenInFlight = new Set<string>();
/** Tokens já confirmados com sucesso nesta sessão (evita 2º POST após remount do Strict Mode). */
const emailConfirmTokenSucceeded = new Set<string>();

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
  const confirmEmailRef = useRef(confirmEmail);
  confirmEmailRef.current = confirmEmail;
  const resend = useEmailConfirmationResend({ cooldownSeconds: 60 });

  const canResend = isValidEmail(emailForResend) && !resend.isLoading && !resend.isCoolingDown;

  useEffect(() => {
    const initial = (emailFromState || emailFromQuery || '').trim();
    if (!initial) return;
    setEmailForResend(initial);
  }, [emailFromQuery, emailFromState]);

  useEffect(() => {
    if (!token) return;

    if (emailConfirmTokenSucceeded.has(token)) {
      setServerError(null);
      setServerSuccess('E-mail confirmado com sucesso.');
      return;
    }

    if (emailConfirmTokenInFlight.has(token)) return;
    emailConfirmTokenInFlight.add(token);

    void (async () => {
      try {
        setServerError(null);
        setServerSuccess(null);
        await confirmEmailRef.current({ token });
        emailConfirmTokenSucceeded.add(token);
        setServerSuccess('E-mail confirmado com sucesso.');
      } catch (e) {
        setServerSuccess(null);
        setServerError(getApiErrorMessage(e, 'Não foi possível confirmar seu e-mail.'));
      } finally {
        emailConfirmTokenInFlight.delete(token);
      }
    })();
  }, [token]);

  const confirmedByApiOrSession =
    isConfirmed || (Boolean(token) && emailConfirmTokenSucceeded.has(token));

  return (
    <AuthLayout
      title="Confirmação de e-mail"
      footer={
        confirmedByApiOrSession ? undefined : (
          <span>
            Já confirmou?{' '}
            <LinkButton
              type="button"
              className="recovery-small-action"
              onClick={() => navigate('/login')}
            >
              Entrar
            </LinkButton>
          </span>
        )
      }
      subtitle={
        token
          ? isConfirming
            ? 'Estamos confirmando seu e-mail. Aguarde um instante.'
            : confirmedByApiOrSession
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

      {confirmedByApiOrSession ? (
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

      {(isConfirmError && !emailConfirmTokenSucceeded.has(token)) || !token ? (
        <>
          {serverError ? (
            <AlertMessage message={serverError} variant="error" />
          ) : serverSuccess ? (
            <AlertMessage message={serverSuccess} variant="success" />
          ) : null}
          {resendSentFromState && !serverError ? (
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
                  const out = await resend.resend(emailForResend.trim());
                  if (out?.already_verified) {
                    setServerSuccess('Este e-mail já está confirmado. Você pode entrar na conta.');
                  } else {
                    setServerSuccess('E-mail de confirmação reenviado.');
                  }
                } catch (err) {
                  setServerSuccess(null);
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


