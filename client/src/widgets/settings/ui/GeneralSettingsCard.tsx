import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import './GeneralSettingsCard.css';
import { LanguageSelect } from './LanguageSelect';
import { useGeneralSettingsLanguage } from '../model/useGeneralSettingsLanguage';

type Option = { value: string; label: string };

export function GeneralSettingsCard() {
  const { t } = useTranslation();

  const languageOptions = useMemo<Option[]>(
    () => [
      { value: 'pt-BR', label: 'Português (Brasil)' },
      { value: 'en-US', label: 'English (US)' },
      { value: 'es-ES', label: 'Español' },
    ],
    []
  );

  const [region, setRegion] = useState('BR');

  const lang = useGeneralSettingsLanguage(languageOptions);

  return (
    <section
      className="sr-settings__card"
      aria-label={t('settings.general')}
      data-lang-open={lang.langOpen ? 'true' : undefined}
    >
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-gear" aria-hidden /> {t('settings.general')}
          </h2>
          <div className="sr-settings__muted">{t('settings.subtitle')}</div>
        </div>
        <button
          type="button"
          className="sr-edit-btn"
          aria-label={lang.isEditing ? t('common.close') : t('common.edit')}
          disabled={lang.isSaving || lang.serverLanguage === null}
          onClick={lang.toggleEdit}
        >
          <i className={`fa-regular ${lang.isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {lang.isEditing ? t('common.close') : t('common.edit')}
        </button>
      </header>

      <div className="sr-settings-general__grid">
        <label className="sr-field">
          <span className="sr-label">{t('settings.language')}</span>
          <LanguageSelect
            value={lang.draftLanguage}
            options={languageOptions}
            disabled={!lang.isEditing || lang.isSaving}
            onOpenChange={(open) => lang.setLangOpen(open)}
            onChange={(value) => {
              lang.changeDraftLanguage(value);
            }}
          />
          <span className="sr-settings-general__hint">{t('settings.languageHint')}</span>
        </label>

        <label className="sr-field">
          <span className="sr-label">{t('settings.regionVisual')}</span>
          <select className="sr-input" value={region} onChange={(e) => setRegion(e.target.value)} disabled>
            <option value="BR">Brasil</option>
          </select>
          <span className="sr-settings-general__hint">{t('settings.regionHint')}</span>
        </label>
      </div>

      {lang.fieldError ? <p className="field-error">{lang.fieldError}</p> : null}

      {lang.isEditing ? (
        <div className="sr-card-actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={!lang.isEditing || lang.isSaving || lang.serverLanguage === null || !lang.isDirty}
            onClick={lang.save}
          >
            {lang.isSaving ? t('common.saving') : t('common.save')}
          </button>
          <button type="button" className="sr-btn sr-btn--secondary" disabled={lang.isSaving} onClick={lang.cancelEdit}>
            {t('common.cancel')}
          </button>
        </div>
      ) : null}
    </section>
  );
}
