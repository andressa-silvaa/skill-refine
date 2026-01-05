import { useNavigate } from 'react-router-dom';

import { RegisterForm } from '@/features/auth/register';

import './RegisterPage.css';

export function RegisterPage() {
  const navigate = useNavigate();

  return (
    <main className="register-page">
      <section className="register-card">
        <header className="brand-tag" aria-label="Skill Refine">
          <span className="brand-skill">Skill</span>
          <span className="brand-refine">Refine</span>
        </header>

        <div className="register-layout">
          <RegisterForm onGoLogin={() => navigate('/login')} onSubmit={() => {}} />

          <aside className="register-visual" aria-hidden="true">
            <img className="girl-img" src="/Character-working-laptop-sitting-chair.svg" alt="" />
            <img className="cactus-img" src="/cactus.svg" alt="" />
          </aside>
        </div>
      </section>
    </main>
  );
}


