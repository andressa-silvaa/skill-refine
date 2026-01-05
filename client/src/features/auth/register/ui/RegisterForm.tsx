import { useState, type FormEvent } from 'react';
import DatePicker from 'react-date-picker';
import 'react-date-picker/dist/DatePicker.css';
import 'react-calendar/dist/Calendar.css';

import { PasswordInput } from '@/shared/ui';

import { registerSchema, type RegisterValues } from '../model/schema';

import './RegisterForm.css';

type Props = {
  onSubmit?: (values: RegisterValues) => void;
  onGoLogin?: () => void;
};

type DatePickerValue = Date | null | [Date | null, Date | null];

export function RegisterForm(props: Props) {
  const { onSubmit, onGoLogin } = props;

  const [fullName, setFullName] = useState('');
  const [birthDate, setBirthDate] = useState<Date | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBirthDateChange = (value: DatePickerValue) => {
    if (value instanceof Date) {
      setBirthDate(value);
      return;
    }
    if (Array.isArray(value)) {
      const first = value[0];
      setBirthDate(first instanceof Date ? first : null);
      return;
    }
    setBirthDate(null);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!birthDate) {
      setError('Informe sua data de nascimento');
      return;
    }
    const parsed = registerSchema.safeParse({
      fullName,
      birthDate,
      email,
      password,
      confirm,
      acceptedTerms,
    });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Dados inválidos');
      return;
    }
    setError(null);
    onSubmit?.(parsed.data);
  };

  return (
    <div className="register-content">
      <div className="welcome">
        <h1 className="register-title">Bem-vindo! Faça seu cadastro</h1>
      </div>

      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field-label">Nome completo</span>
          <input
            className="field-input"
            type="text"
            placeholder="Digite seu nome"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoComplete="name"
          />
        </label>

        <label className="field">
          <span className="field-label">Data de nascimento</span>
          <DatePicker
            onChange={handleBirthDateChange}
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
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
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
          <input type="checkbox" checked={acceptedTerms} onChange={(e) => setAcceptedTerms(e.target.checked)} />
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

        {error ? <p className="form-error">{error}</p> : null}

        <button className="submit-btn" type="submit">
          <span>CADASTRAR</span>
          <span className="arrow">→</span>
        </button>
      </form>

      <footer className="footer">
        <span>Você já tem uma conta?</span>
        <button className="signup-link" type="button" onClick={onGoLogin}>
          Acesse aqui
        </button>
      </footer>
    </div>
  );
}


