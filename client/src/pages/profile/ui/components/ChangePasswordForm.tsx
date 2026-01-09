import { useState } from 'react';

import { LinkButton, PasswordInput } from '@/shared/ui';

import './ChangePasswordForm.css';

type Props = {
  onCancel?: () => void;
  onSaved?: () => void;
  disabled?: boolean;
  showActions?: boolean;
};

export function ChangePasswordForm(props: Props) {
  const { onCancel, onSaved, disabled = false, showActions = true } = props;
  const [values, setValues] = useState({ current: '', next: '', confirm: '' });
  const [helper, setHelper] = useState<string | null>(null);

  return (
    <form
      className="sr-change-password__form"
      onSubmit={(e) => {
        e.preventDefault();
        setHelper('Em breve: atualização de senha com validação e integração.');
        onSaved?.();
      }}
    >
      <PasswordInput
        label="Senha atual"
        value={values.current}
        onChange={(e) => setValues((prev) => ({ ...prev, current: e.target.value }))}
        autoComplete="current-password"
        disabled={disabled}
        wrapperClassName="sr-profile-field"
        inputClassName="sr-profile-input"
        labelRight={
          <LinkButton
            type="button"
            className="sr-change-password__forgot"
            disabled={disabled}
            onClick={(e) => {
              e.preventDefault();
              setHelper('Em breve: fluxo de recuperação de senha.');
            }}
          >
            <i className="fa-regular fa-circle-question" aria-hidden /> Esqueceu a senha?
          </LinkButton>
        }
      />

      <div className="sr-change-password__row">
        <PasswordInput
          label="Nova senha"
          value={values.next}
          onChange={(e) => setValues((prev) => ({ ...prev, next: e.target.value }))}
          autoComplete="new-password"
          placeholder="Crie uma nova senha"
          disabled={disabled}
          wrapperClassName="sr-profile-field"
          inputClassName="sr-profile-input"
        />

        <PasswordInput
          label="Confirmar senha"
          value={values.confirm}
          onChange={(e) => setValues((prev) => ({ ...prev, confirm: e.target.value }))}
          autoComplete="new-password"
          placeholder="Confirme a nova senha"
          disabled={disabled}
          wrapperClassName="sr-profile-field"
          inputClassName="sr-profile-input"
        />
      </div>

      {helper ? <p className="sr-change-password__helper">{helper}</p> : null}

      {showActions ? (
        <div className="sr-change-password__actions">
          <button className="sr-btn sr-btn--primary" type="submit">
            Salvar
          </button>
          <button
            className="sr-btn sr-btn--secondary"
            type="button"
            onClick={() => {
              setValues({ current: '', next: '', confirm: '' });
              setHelper(null);
              onCancel?.();
            }}
          >
            Cancelar
          </button>
        </div>
      ) : null}
    </form>
  );
}


