import { useTranslation } from 'react-i18next';

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
  const { t } = useTranslation();

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
  const compositePaths = ['contact.github', 'contact.portfolio', 'contact.website'] as const;
  const compositeError = compositePaths.reduce<string | undefined>((acc, path) => {
    if (acc) return acc;
    return shouldShowError(path) ? getError(path) : undefined;
  }, undefined);

  return (
    <div className="sr-contact-step">
      <div className="sr-contact-step__header">
        <h3 className="sr-contact-step__title">{t('resume.contactStepTitle')}</h3>
        <p className="sr-contact-step__subtitle">{t('resume.contactStepSubtitle')}</p>
      </div>

      <div className="sr-contact-step__fields">
        <Input
          label={t('resume.contactStepFullName')}
          placeholder={t('resume.contactStepFullNamePlaceholder')}
          value={contact.fullName}
          onChange={(e) => updateField('fullName', e.target.value)}
          onBlur={() => onFieldTouched('contact.fullName')}
          required
          error={fullNameError}
        />
        <div className="sr-contact-step__row">
          <Input
            label={t('resume.contactStepEmail')}
            type="email"
            placeholder={t('resume.contactStepEmailPlaceholder')}
            value={contact.email}
            onChange={(e) => updateField('email', e.target.value)}
            onBlur={() => onFieldTouched('contact.email')}
            required
            error={emailError}
          />
          <Input
            label={t('resume.contactStepPhone')}
            type="tel"
            placeholder={t('resume.contactStepPhonePlaceholder')}
            value={contact.phone}
            onChange={(e) => updateField('phone', e.target.value)}
            onBlur={() => onFieldTouched('contact.phone')}
            error={phoneError}
          />
        </div>
        <div className="sr-contact-step__row">
          <Input
            label={t('resume.contactStepCity')}
            placeholder={t('resume.contactStepCityPlaceholder')}
            value={contact.city}
            onChange={(e) => updateField('city', e.target.value)}
            onBlur={() => onFieldTouched('contact.city')}
            error={cityError}
          />
          <Input
            label={t('resume.contactStepCountry')}
            placeholder={t('resume.contactStepCountryPlaceholder')}
            value={contact.country}
            onChange={(e) => updateField('country', e.target.value)}
            onBlur={() => onFieldTouched('contact.country')}
            error={countryError}
          />
        </div>
        <Input
          label={t('resume.contactStepLinkedin')}
          type="url"
          placeholder={t('resume.contactStepLinkedinPlaceholder')}
          value={contact.linkedin || ''}
          onChange={(e) => updateField('linkedin', e.target.value)}
          onBlur={() => onFieldTouched('contact.linkedin')}
          hint={t('resume.contactStepOptional')}
          error={linkedinError}
        />
        <Input
          label={t('resume.contactStepPortfolio')}
          type="url"
          placeholder={t('resume.contactStepPortfolioPlaceholder')}
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
          hint={t('resume.contactStepOptional')}
          error={compositeError}
        />
      </div>
    </div>
  );
}
