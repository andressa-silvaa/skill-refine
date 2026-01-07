import type { UseFormRegisterReturn } from 'react-hook-form';

type Props = {
  registration: UseFormRegisterReturn;
  isInvalid: boolean;
  errorMessage?: string;
};

export function TermsField(props: Props) {
  const { registration, isInvalid, errorMessage } = props;

  return (
    <label className={`terms${isInvalid ? ' is-invalid' : ''}`}>
      <input type="checkbox" {...registration} aria-invalid={isInvalid} />
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
      {isInvalid ? <p className="field-error">{errorMessage}</p> : null}
    </label>
  );
}


