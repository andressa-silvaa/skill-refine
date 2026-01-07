import { useNavigate } from 'react-router-dom';

import { useState } from 'react';

import { accountApi } from '@/entities/session/api/accountApi';
import { useSessionActions } from '@/entities/session';
import { LoginForm } from '@/features/auth/login';
import { asApiError } from '@/shared/api';
import { useAsyncRequest } from '@/shared/lib/hooks/useAsyncRequest';
import { useCooldown } from '@/shared/lib/hooks/useCooldown';
import { LinkButton } from '@/shared/ui';

import './LoginPage.css';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useSessionActions();
  const [serverError, setServerError] = useState<string | null>(null);
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [needsEmailConfirmation, setNeedsEmailConfirmation] = useState(false);

  const resendReq = useAsyncRequest(accountApi.requestEmailConfirmation);
  const cooldown = useCooldown({ seconds: 60 });

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
                setNeedsEmailConfirmation(false);
                setPendingEmail(values.email);
                await login(values);
                navigate('/protected');
              } catch (e) {
                const apiErr = asApiError(e);
                if (apiErr) {
                  setServerError(apiErr.message);
                  setNeedsEmailConfirmation(apiErr.code === 'email_not_confirmed');
                } else {
                  setServerError('E-mail ou senha inválidos.');
                }
              }
            }}
            onGoogle={async () => {
              setServerError(null);
              const rawApiUrl = process.env.REACT_APP_API_URL ?? 'http://localhost:8000';
              // Defensive: if .env is malformed, CRA can concatenate vars into one string.
              const apiUrl = (rawApiUrl.split('REACT_APP_')[0] ?? '').trim();
              const next = `${window.location.origin}/oauth/callback`;
              window.location.href = `${apiUrl}/accounts/auth/google/start?next=${encodeURIComponent(next)}`;
            }}
            serverError={serverError ?? undefined}
          />

          {needsEmailConfirmation && pendingEmail ? (
            <div style={{ padding: '0 24px 24px' }}>
              <LinkButton
                type="button"
                disabled={resendReq.isLoading || cooldown.isCoolingDown}
                onClick={async () => {
                  try {
                    setServerError(null);
                    await resendReq.run({ email: pendingEmail });
                    cooldown.start();
                    setServerError('E-mail de confirmação reenviado.');
                  } catch (err) {
                    const apiErr = asApiError(err);
                    setServerError(apiErr?.message ?? 'Não foi possível reenviar agora. Tente novamente.');
                  }
                }}
              >
                {cooldown.isCoolingDown ? cooldown.label : 'Reenviar confirmação'}
              </LinkButton>
              <span style={{ marginLeft: 10, fontSize: 12, fontWeight: 700, color: '#6d5b6d' }}>ou</span>{' '}
              <LinkButton type="button" onClick={() => navigate('/verify-email', { state: { email: pendingEmail } })}>
                Ver instruções
              </LinkButton>
            </div>
          ) : null}

          <aside className="login-visual" aria-hidden="true">
            <img className="girl-img" src="/Character-working-laptop-sitting-chair.svg" alt="" />
            <img className="cactus-img" src="/cactus.svg" alt="" />
          </aside>
        </div>
      </section>
    </main>
  );
}


