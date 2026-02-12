import { useNavigate } from 'react-router-dom';

import { useState } from 'react';

import { useSessionActions } from '@/entities/session';
import { RegisterForm } from '@/features/auth';
import { API_ERROR_CODES, asApiError, getApiErrorMessage } from '@/shared/api';

import './RegisterPage.css';

function toIsoDateOrNull(date: Date | undefined) {
  return date ? date.toISOString().slice(0, 10) : null;
}

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useSessionActions();
  const [serverError, setServerError] = useState<string | null>(null);

  return (
    <main className="register-page">
      <section className="register-card">
        <header className="brand-tag" aria-label="Skill Refine">
          <span className="brand-skill">Skill</span>
          <span className="brand-refine">Refine</span>
        </header>

        <div className="register-layout">
          <RegisterForm
            onGoLogin={() => navigate('/login')}
            onSubmit={async (values) => {
              try {
                setServerError(null);
                const birth_date = toIsoDateOrNull(values.birthDate);
                const res = await register({
                  email: values.email,
                  full_name: values.fullName,
                  birth_date,
                  password: values.password,
                });
                navigate('/verify-email', {
                  state: { email: values.email, emailConfirmationSent: Boolean(res.email_confirmation_sent ?? true) },
                });
              } catch (e) {
                const apiErr = asApiError(e);

                if (apiErr?.code === API_ERROR_CODES.EMAIL_NOT_CONFIRMED) {
                  navigate('/verify-email', { state: { email: values.email } });
                  return;
                }

                setServerError(getApiErrorMessage(e, 'Não foi possível cadastrar. Verifique os dados e tente novamente.'));
              }
            }}
            serverError={serverError ?? undefined}
          />

          <aside className="register-visual" aria-hidden="true">
            <img className="girl-img" src="/Character-working-laptop-sitting-chair.svg" alt="" />
            <img className="cactus-img" src="/cactus.svg" alt="" />
          </aside>
        </div>
      </section>
    </main>
  );
}


