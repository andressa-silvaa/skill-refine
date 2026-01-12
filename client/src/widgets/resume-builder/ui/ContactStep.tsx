import { Input } from '@/shared/ui';
import type { Contact } from '@/entities/resume';

import './ContactStep.css';

type Props = {
  contact: Contact;
  onChange: (contact: Contact) => void;
};

export function ContactStep(props: Props) {
  const { contact, onChange } = props;

  const updateField = (field: keyof Contact, value: string) => {
    onChange({ ...contact, [field]: value });
  };

  return (
    <div className="sr-contact-step">
      <div className="sr-contact-step__header">
        <h3 className="sr-contact-step__title">Informações de contato</h3>
        <p className="sr-contact-step__subtitle">Como os recrutadores podem entrar em contato com você</p>
      </div>

      <div className="sr-contact-step__fields">
        <Input
          label="Nome completo"
          placeholder="Seu nome completo"
          value={contact.fullName}
          onChange={(e) => updateField('fullName', e.target.value)}
          required
        />
        <div className="sr-contact-step__row">
          <Input
            label="E-mail"
            type="email"
            placeholder="seu@email.com"
            value={contact.email}
            onChange={(e) => updateField('email', e.target.value)}
            required
          />
          <Input
            label="Telefone"
            type="tel"
            placeholder="(00) 00000-0000"
            value={contact.phone}
            onChange={(e) => updateField('phone', e.target.value)}
            required
          />
        </div>
        <div className="sr-contact-step__row">
          <Input
            label="Cidade"
            placeholder="São Paulo"
            value={contact.city}
            onChange={(e) => updateField('city', e.target.value)}
          />
          <Input
            label="País"
            placeholder="Brasil"
            value={contact.country}
            onChange={(e) => updateField('country', e.target.value)}
          />
        </div>
        <Input
          label="LinkedIn"
          type="url"
          placeholder="linkedin.com/in/seu-perfil"
          value={contact.linkedin || ''}
          onChange={(e) => updateField('linkedin', e.target.value)}
          hint="Opcional"
        />
        <Input
          label="Portfólio / GitHub / Site"
          type="url"
          placeholder="github.com/seu-usuario ou seuportfolio.com"
          value={contact.portfolio || contact.github || contact.website || ''}
          onChange={(e) => {
            const url = e.target.value;
            if (url.includes('github.com')) {
              updateField('github', url);
            } else if (url) {
              updateField('portfolio', url);
            }
          }}
          hint="Opcional"
        />
      </div>
    </div>
  );
}
