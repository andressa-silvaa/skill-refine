import { Input } from '@/shared/ui';
import type { Contact } from '@/entities/resume';

import './ContactStep.css';

type Props = {
  contact: Contact;
  onChange: (contact: Contact) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function ContactStep(props: Props) {
  const { contact, onChange, getError, shouldShowError, onFieldTouched } = props;

  const updateField = (field: keyof Contact, value: string) => {
    onChange({ ...contact, [field]: value });
  };

  const fullNameError = shouldShowError('contact.fullName') ? getError('contact.fullName') : undefined;
  const emailError = shouldShowError('contact.email') ? getError('contact.email') : undefined;
  const phoneError = shouldShowError('contact.phone') ? getError('contact.phone') : undefined;
  const cityError = shouldShowError('contact.city') ? getError('contact.city') : undefined;
  const countryError = shouldShowError('contact.country') ? getError('contact.country') : undefined;
  const linkedinError = shouldShowError('contact.linkedin') ? getError('contact.linkedin') : undefined;

  const compositeValue = contact.portfolio || contact.github || contact.website || '';
  const compositeError =
    (shouldShowError('contact.github') && getError('contact.github')) ||
    (shouldShowError('contact.portfolio') && getError('contact.portfolio')) ||
    (shouldShowError('contact.website') && getError('contact.website')) ||
    undefined;

  return (
    <div className="sr-contact-step">
      <div className="sr-contact-step__header">
        <h3 className="sr-contact-step__title">Informações de contato</h3>
        <p className="sr-contact-step__subtitle">Como os recrutadores podem entrar em contato com você</p>
      </div>

      <div className="sr-contact-step__fields">
        <Input
          label="Nome completo *"
          placeholder="Seu nome completo"
          value={contact.fullName}
          onChange={(e) => updateField('fullName', e.target.value)}
          onBlur={() => onFieldTouched('contact.fullName')}
          required
          error={fullNameError}
        />
        <div className="sr-contact-step__row">
          <Input
            label="E-mail *"
            type="email"
            placeholder="seu@email.com"
            value={contact.email}
            onChange={(e) => updateField('email', e.target.value)}
            onBlur={() => onFieldTouched('contact.email')}
            required
            error={emailError}
          />
          <Input
            label="Telefone"
            type="tel"
            placeholder="(00) 00000-0000"
            value={contact.phone}
            onChange={(e) => updateField('phone', e.target.value)}
            onBlur={() => onFieldTouched('contact.phone')}
            error={phoneError}
          />
        </div>
        <div className="sr-contact-step__row">
          <Input
            label="Cidade"
            placeholder="São Paulo"
            value={contact.city}
            onChange={(e) => updateField('city', e.target.value)}
            onBlur={() => onFieldTouched('contact.city')}
            error={cityError}
          />
          <Input
            label="País"
            placeholder="Brasil"
            value={contact.country}
            onChange={(e) => updateField('country', e.target.value)}
            onBlur={() => onFieldTouched('contact.country')}
            error={countryError}
          />
        </div>
        <Input
          label="LinkedIn"
          type="url"
          placeholder="linkedin.com/in/seu-perfil"
          value={contact.linkedin || ''}
          onChange={(e) => updateField('linkedin', e.target.value)}
          onBlur={() => onFieldTouched('contact.linkedin')}
          hint="Opcional"
          error={linkedinError}
        />
        <Input
          label="Portfólio / GitHub / Site"
          type="url"
          placeholder="github.com/seu-usuario ou seuportfolio.com"
          value={compositeValue}
          onChange={(e) => {
            const url = e.target.value;
            if (url.includes('github.com')) {
              updateField('github', url);
              onFieldTouched('contact.github');
            } else if (url) {
              updateField('portfolio', url);
              onFieldTouched('contact.portfolio');
            } else {
              updateField('portfolio', '');
            }
          }}
          onBlur={() => {
            if (contact.github) {
              onFieldTouched('contact.github');
            } else if (contact.portfolio) {
              onFieldTouched('contact.portfolio');
            } else if (contact.website) {
              onFieldTouched('contact.website');
            } else {
              onFieldTouched('contact.portfolio');
            }
          }}
          hint="Opcional"
          error={compositeError}
        />
      </div>
    </div>
  );
}
