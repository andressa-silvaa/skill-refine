import { type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';

import { useAccentColorSettings } from '../model/useAccentColorSettings';

import { ACCENTS } from '@/shared/lib/theme/appearance';

import './AccentColorSettingsCard.css';

export function AccentColorSettingsCard() {
  const { t } = useTranslation();
  const ui = useAccentColorSettings();

  return (
    <section className="sr-settings__card" aria-label={t('settings.accentTitle')}>
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-regular fa-star" aria-hidden /> {t('settings.accentTitle')}
          </h2>
          <div className="sr-settings__muted">{t('settings.accentMuted')}</div>
        </div>
        <button
          type="button"
          className="sr-edit-btn"
          aria-label={ui.isEditing ? t('common.close') : t('common.edit')}
          disabled={ui.isSaving || ui.serverKey === null}
          onClick={ui.toggleEdit}
        >
          <i className={`fa-regular ${ui.isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {ui.isEditing ? t('common.close') : t('common.edit')}
        </button>
      </header>

      <div className="sr-accent" role="list" aria-label={t('settings.accentTitle')}>
        {ACCENTS.map((a) => {
          const isActive = ui.draftKey === a.key;
          const style = {
            background: a.color,
            ['--sr-accent-color' as unknown as keyof CSSProperties]: a.color,
          } as CSSProperties;
          return (
            <button
              key={a.key}
              type="button"
              className={`sr-accent__dot${isActive ? ' is-active' : ''}`}
              style={style}
              aria-label={a.label}
              aria-pressed={isActive}
              disabled={!ui.isEditing || ui.isSaving}
              onClick={() => {
                ui.changeDraftKey(a.key);
              }}
            >
              {isActive ? <i className="fa-solid fa-check" aria-hidden /> : null}
            </button>
          );
        })}
      </div>

      {ui.fieldError ? <p className="field-error">{ui.fieldError}</p> : null}

      {ui.isEditing ? (
        <div className="sr-card-actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={!ui.isEditing || ui.isSaving || ui.serverKey === null || !ui.isDirty}
            onClick={ui.save}
          >
            {ui.isSaving ? t('common.saving') : t('common.save')}
          </button>
          <button type="button" className="sr-btn sr-btn--secondary" disabled={ui.isSaving} onClick={ui.cancelEdit}>
            {t('common.cancel')}
          </button>
        </div>
      ) : null}
    </section>
  );
}
