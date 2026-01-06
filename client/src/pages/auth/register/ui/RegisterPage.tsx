import { useNavigate } from 'react-router-dom';

import { useState } from 'react';

import { useSessionActions } from '@/entities/session';
import { RegisterForm } from '@/features/auth/register';

import './RegisterPage.css';

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
                const birth_date = values.birthDate ? values.birthDate.toISOString().slice(0, 10) : null;
                await register({
                  email: values.email,
                  full_name: values.fullName,
                  birth_date,
                  password: values.password,
                });
                navigate('/login');
              } catch (e) {
                setServerError('Não foi possível cadastrar. Verifique os dados e tente novamente.');
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


