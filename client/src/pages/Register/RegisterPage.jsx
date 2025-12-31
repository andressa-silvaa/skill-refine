import { useState } from 'react';
import DatePicker from 'react-date-picker';
import 'react-date-picker/dist/DatePicker.css';
import 'react-calendar/dist/Calendar.css';
import './RegisterPage.css';

export default function RegisterPage({ onGoLogin }) {
  const [birthDate, setBirthDate] = useState(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <main className="register-page">
      <section className="register-card">
        <header className="brand-tag" aria-label="Skill Refine">
          <span className="brand-skill">Skill</span>
          <span className="brand-refine">Refine</span>
        </header>

        <div className="register-layout">
          <div className="register-content">
            <div className="welcome">
              <h1 className="register-title">Bem-vindo! Faça seu cadastro</h1>
            </div>

            <form className="form">
              <label className="field">
                <span className="field-label">Nome completo</span>
                <input
                  className="field-input"
                  type="text"
                  placeholder="Digite seu nome"
                />
              </label>

              <label className="field">
                <span className="field-label">Data de nascimento</span>
                <DatePicker
                  onChange={(date) => setBirthDate(date)}
                  value={birthDate}
                  format="dd/MM/y"
                  dayPlaceholder="DD"
                  monthPlaceholder="MM"
                  yearPlaceholder="YYYY"
                  clearIcon={null}
                  calendarIcon={<span className="calendar-icon">📅</span>}
                  className="date-picker"
                />
              </label>

              <label className="field">
                <span className="field-label">E-mail</span>
                <input
                  className="field-input"
                  type="email"
                  placeholder="digite seu e-mail"
                />
              </label>

              <label className="field">
                <span className="field-label">Senha</span>
                <div className="password-wrapper">
                  <input
                    className="field-input has-icon"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="*****************"
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="toggle-visibility"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>
              </label>

              <label className="field">
                <span className="field-label">Confirme a senha</span>
                <div className="password-wrapper">
                  <input
                    className="field-input has-icon"
                    type={showConfirm ? 'text' : 'password'}
                    placeholder="*****************"
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                  />
                  <button
                    type="button"
                    className="toggle-visibility"
                    onClick={() => setShowConfirm((prev) => !prev)}
                    aria-label={showConfirm ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showConfirm ? '🙈' : '👁️'}
                  </button>
                </div>
              </label>

              <label className="terms">
                <input type="checkbox" />
                <span>
                  Eu aceito{' '}
                  <a href="#" className="terms-link">
                    Termos
                  </a>{' '}
                  e{' '}
                  <a href="#" className="terms-link">
                    Política de Privacidade
                  </a>
                </span>
              </label>

              <button className="submit-btn" type="button">
                <span>CADASTRAR</span>
                <span className="arrow">→</span>
              </button>
            </form>

            <footer className="footer">
              <span>Você já tem uma conta?</span>
              <a
                className="signup-link"
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  onGoLogin?.();
                }}
              >
                Acesse aqui
              </a>
            </footer>
          </div>

          <aside className="register-visual" aria-hidden="true">
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

