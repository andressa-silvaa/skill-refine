import { useState } from 'react';
import './LoginPage.css';
import PasswordInput from '../../components/PasswordInput';

export default function LoginPage({ onGoRegister }) {
  const [password, setPassword] = useState('');

  return (
    <main className="login-page">
      <section className="login-card">
        {/* Brand (some quando a imagem/painel some) */}
        <header className="brand-tag" aria-label="Skill Refine">
          <span className="brand-skill">Skill</span>
          <span className="brand-refine">Refine</span>
        </header>

        <div className="login-layout">
          <div className="login-content">
            <div className="welcome">
              <p className="welcome-back">Bem-vindo de volta!</p>
              <h1 className="login-title">Log In</h1>
            </div>

            <form className="form">
              <label className="field">
                <span className="field-label">E-mail</span>
                <input
                  className="field-input"
                  type="email"
                  placeholder="Digite seu email"
                />
              </label>

              <PasswordInput
                label="Senha"
                labelRight={
                  <a className="forgot-link" href="#">
                    Esqueceu a senha?
                  </a>
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />

              <button className="submit-btn" type="button">
                <span>ENTRAR</span>
                <span className="arrow">→</span>
              </button>
            </form>

            <p className="divider">Ou continue com o Google</p>

            <button className="google-btn" type="button" aria-label="Entrar com Google">
              <img src="/google.svg" alt="Google" />
            </button>

            <footer className="footer">
              <span>Ainda não tem uma conta?</span>
            <a
              className="signup-link"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                onGoRegister?.();
              }}
            >
                Cadastre-se aqui
              </a>
            </footer>
          </div>

          <aside className="login-visual" aria-hidden="true">
            <img
              className="girl-img"
              src="/Character-working-laptop-sitting-chair.svg"
              alt=""
            />
            <img className="cactus-img" src="/cactus.svg" alt="" />
          </aside>
        </div>
      </section>
    </main>
  );
}
