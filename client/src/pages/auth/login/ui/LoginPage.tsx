import { useNavigate } from 'react-router-dom';

import { useState } from 'react';

import { useSessionActions } from '@/entities/session';
import { LoginForm } from '@/features/auth/login';
import { ApiError } from '@/shared/api';

import './LoginPage.css';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useSessionActions();
  const [serverError, setServerError] = useState<string | null>(null);

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
                await login(values);
                navigate('/protected');
              } catch (e) {
                if (e instanceof ApiError) {
                  setServerError(e.message);
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

          <aside className="login-visual" aria-hidden="true">
            <img className="girl-img" src="/Character-working-laptop-sitting-chair.svg" alt="" />
            <img className="cactus-img" src="/cactus.svg" alt="" />
          </aside>
        </div>
      </section>
    </main>
  );
}


