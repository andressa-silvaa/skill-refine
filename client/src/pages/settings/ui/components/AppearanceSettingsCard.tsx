import { useAppearanceSettings } from './useAppearanceSettings';
import { useTranslation } from 'react-i18next';

import './AppearanceSettingsCard.css';

export function AppearanceSettingsCard() {
  const { t } = useTranslation();
  const ui = useAppearanceSettings();

  return (
    <section className="sr-settings__card" aria-label={t('settings.appearanceTitle')}>
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-palette" aria-hidden /> {t('settings.appearanceTitle')}
          </h2>
          <div className="sr-settings__muted">{t('settings.appearanceMuted')}</div>
        </div>
        <button
          type="button"
          className="sr-edit-btn"
          aria-label={ui.isEditing ? t('common.close') : t('common.edit')}
          disabled={ui.isSaving || ui.serverTheme === null}
          onClick={ui.toggleEdit}
        >
          <i className={`fa-regular ${ui.isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {ui.isEditing ? t('common.close') : t('common.edit')}
        </button>
      </header>

      <div className="sr-appearance">
        <div className="sr-appearance__label">{t('settings.themeLabel')}</div>
        <div className="sr-appearance__grid" role="group" aria-label="Selecionar tema">
          <button
            type="button"
            className={`sr-appearance__option${ui.draftTheme === 'light' ? ' is-active' : ''}`}
            disabled={!ui.isEditing || ui.isSaving}
            onClick={() => {
              ui.changeDraftTheme('light');
            }}
          >
            <i className="fa-regular fa-sun" aria-hidden />
            <span>{t('settings.themeLight')}</span>
          </button>
          <button
            type="button"
            className={`sr-appearance__option${ui.draftTheme === 'dark' ? ' is-active' : ''}`}
            disabled={!ui.isEditing || ui.isSaving}
            onClick={() => {
              ui.changeDraftTheme('dark');
            }}
          >
            <i className="fa-regular fa-moon" aria-hidden />
            <span>{t('settings.themeDark')}</span>
          </button>
        </div>
      </div>

      {ui.fieldError ? <p className="field-error">{ui.fieldError}</p> : null}

      {ui.isEditing ? (
        <div className="sr-card-actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={!ui.isEditing || ui.isSaving || ui.serverTheme === null || !ui.isDirty}
            onClick={ui.save}
          >
            {ui.isSaving ? t('common.saving') : t('common.save')}
          </button>
          <button
            type="button"
            className="sr-btn sr-btn--secondary"
            disabled={ui.isSaving}
            onClick={ui.cancelEdit}
          >
            {t('common.cancel')}
          </button>
        </div>
      ) : null}
    </section>
  );
}


