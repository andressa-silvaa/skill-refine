import { Link } from 'react-router-dom';

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
        Eu aceito <Link to="/terms" className="terms-link">Termos</Link> e{' '}
        <Link to="/privacy" className="terms-link">Política de Privacidade</Link>
      </span>
      {isInvalid ? <p className="field-error">{errorMessage}</p> : null}
    </label>
  );
}


