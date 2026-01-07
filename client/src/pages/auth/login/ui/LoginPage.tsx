import { useNavigate } from 'react-router-dom';

import { useState } from 'react';

import { useSessionActions } from '@/entities/session';
import { useEmailConfirmationResend } from '@/features/auth/email-confirmation';
import { LoginForm } from '@/features/auth/login';
import { API_ERROR_CODES, asApiError, getApiErrorMessage } from '@/shared/api';
import { isValidEmail } from '@/shared/lib/forms';
import { notify } from '@/shared/lib/notify';

import './LoginPage.css';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useSessionActions();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverErrorCode, setServerErrorCode] = useState<string | null>(null);

  const resend = useEmailConfirmationResend({ cooldownSeconds: 60 });
  const [confirmEmailError, setConfirmEmailError] = useState<string | null>(null);

  return (
    <main className="login-page">
      <section className="login-card">
        <header className="brand-tag" aria-label="Skill Refine">
          <span className="brand-skill">Skill</span>
          <span className="brand-refine">Refine</span>
        </header>

        <div className="login-layout">
          <LoginForm
            onGoRegister={() => navigate('/register')}
            onGoForgot={() => navigate('/reset/email')}
            onSubmit={async (values) => {
              try {
                setServerError(null);
                setServerErrorCode(null);
                await login(values);
                notify.success('Login realizado com sucesso.');
                navigate('/protected');
              } catch (e) {
                const apiErr = asApiError(e);
                if (apiErr) {
                  setServerError(apiErr.message);
                  setServerErrorCode(apiErr.code ?? null);
                } else {
                  setServerError('E-mail ou senha inválidos.');
                  setServerErrorCode(API_ERROR_CODES.INVALID_CREDENTIALS);
                }
              }
            }}
            onConfirmEmail={async (email) => {
              const trimmed = email.trim();
              setConfirmEmailError(null);

              if (!isValidEmail(trimmed)) {
                navigate('/verify-email', trimmed ? { state: { email: trimmed } } : undefined);
                return;
              }

              try {
                await resend.resend(trimmed);
                navigate('/verify-email', { state: { email: trimmed, emailConfirmationSent: true } });
              } catch (err) {
                setConfirmEmailError(getApiErrorMessage(err, 'Não foi possível enviar a confirmação agora.'));
              }
            }}
            confirmEmailBusy={resend.isLoading}
            confirmEmailLabel={resend.isLoading ? 'Enviando...' : 'Confirmar e-mail'}
            confirmEmailError={confirmEmailError ?? undefined}
            showConfirmEmailCta={serverErrorCode === API_ERROR_CODES.EMAIL_NOT_CONFIRMED}
            onGoogle={async () => {
              setServerError(null);
              setServerErrorCode(null);
              const rawApiUrl = process.env.REACT_APP_API_URL ?? 'http://localhost:8000';
              const apiUrl = (rawApiUrl.split('REACT_APP_')[0] ?? '').trim();
              const next = `${window.location.origin}/oauth/callback`;
              window.location.href = `${apiUrl}/accounts/auth/google/start?next=${encodeURIComponent(next)}`;
            }}
            serverError={serverError ?? undefined}
          />

          <aside className="login-visual" aria-hidden="true">
            <img className="girl-img" src="/Character-working-laptop-sitting-chair.svg" alt="" />
            <img className="cactus-img" src="/cactus.svg" alt="" />
          </aside>
        </div>
      </section>
    </main>
  );
}


