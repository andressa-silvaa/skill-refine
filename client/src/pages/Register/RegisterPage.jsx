import { useState } from 'react';
import DatePicker from 'react-date-picker';
import 'react-date-picker/dist/DatePicker.css';
import 'react-calendar/dist/Calendar.css';
import './RegisterPage.css';
import PasswordInput from '../../components/PasswordInput';

export default function RegisterPage({ onGoLogin }) {
  const [birthDate, setBirthDate] = useState(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');

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

              <PasswordInput
                label="Senha"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />

              <PasswordInput
                label="Confirme a senha"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
              />

              <label className="terms">
                <input type="checkbox" />
                <span>
                  Eu aceito{' '}
                  <button type="button" className="terms-link">
                    Termos
                  </button>{' '}
                  e{' '}
                  <button type="button" className="terms-link">
                    Política de Privacidade
                  </button>
                </span>
              </label>

              <button className="submit-btn" type="button">
                <span>CADASTRAR</span>
                <span className="arrow">→</span>
              </button>
            </form>

            <footer className="footer">
              <span>Você já tem uma conta?</span>
              <button className="signup-link" type="button" onClick={() => onGoLogin?.()}>
                Acesse aqui
              </button>
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

