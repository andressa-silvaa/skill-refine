import { useNavigate } from 'react-router-dom';

import { LoginForm } from '@/features/auth/login';

import './LoginPage.css';

export function LoginPage() {
  const navigate = useNavigate();

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
            onSubmit={() => {}}
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


