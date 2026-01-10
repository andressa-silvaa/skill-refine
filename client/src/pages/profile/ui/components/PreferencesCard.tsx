import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession, useSessionActions } from '@/entities/session';
import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { useDirtyState } from '@/shared/lib/hooks/useDirtyState';
import { notify } from '@/shared/lib/notify';

import './PreferencesCard.css';

export function PreferencesCard() {
  const { t } = useTranslation();
  const { preferences } = useSession();
  const { updatePreferences } = useSessionActions();
  const emailNotifications = useDirtyState<boolean>(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    if (!preferences) return;
    if (isEditing) return;
    emailNotifications.acceptServer(preferences.email_notifications_enabled);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing, preferences?.email_notifications_enabled]);

  const isDirty = emailNotifications.server !== null && emailNotifications.isDirty;

  return (
    <section className="sr-profile__card" aria-label={t('profile.preferences')}>
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">{t('profile.preferences')}</h2>
          <div className="sr-profile__muted">{t('profile.preferencesMuted')}</div>
        </div>
        <button
          type="button"
          className="sr-profile-card__edit-btn"
          aria-label={isEditing ? t('common.close') : t('common.edit')}
          disabled={isSaving || emailNotifications.server === null}
          onClick={() => {
            setIsEditing((v) => {
              const next = !v;
              setFieldError(null);
              emailNotifications.resetDraft();
              return next;
            });
          }}
        >
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? t('common.close') : t('common.edit')}
        </button>
      </header>

      <div className="sr-pref__row" aria-label={t('profile.emailNotifications')}>
        <div className="sr-pref__left">
          <span className="sr-pref__icon" aria-hidden>
            <i className="fa-fw fa-regular fa-envelope" />
          </span>
          <div className="sr-pref__text">
            <div className="sr-pref__label">{t('profile.emailNotifications')}</div>
            <div className="sr-pref__desc">{t('profile.emailNotificationsDesc')}</div>
          </div>
        </div>
        <button
          type="button"
          className={`sr-pref__switch${emailNotifications.draft ? ' is-on' : ''}`}
          role="switch"
          aria-checked={emailNotifications.draft}
          disabled={!isEditing || isSaving || emailNotifications.server === null}
          onClick={() => {
            if (!isEditing || isSaving) return;
            setFieldError(null);
            emailNotifications.setDraft(!emailNotifications.draft);
          }}
        >
          <span className="sr-pref__thumb" aria-hidden />
        </button>
      </div>

      {fieldError ? <p className="field-error">{fieldError}</p> : null}

      {isEditing ? (
        <div className="sr-profile-card__actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={!isEditing || isSaving || emailNotifications.server === null || !isDirty}
            onClick={async () => {
              setIsSaving(true);
              setFieldError(null);
              try {
                const res = await profileApi.updatePreferences({ email_notifications_enabled: emailNotifications.draft });
                const value = Boolean(res.email_notifications_enabled ?? res.emailNotificationsEnabled);
                emailNotifications.acceptServer(value);
                updatePreferences({ email_notifications_enabled: value });
                setIsEditing(false);
              } catch (e) {
                const fields = getApiFieldErrors(e);
                const errMsg = fields?.email_notifications_enabled;
                if (errMsg) setFieldError(errMsg);
                else notify.error(getApiErrorMessage(e, 'Não foi possível salvar agora.'));
              } finally {
                setIsSaving(false);
              }
            }}
          >
            {isSaving ? t('common.saving') : t('common.save')}
          </button>
          <button
            type="button"
            className="sr-btn sr-btn--secondary"
            disabled={isSaving}
            onClick={() => {
              emailNotifications.resetDraft();
              setFieldError(null);
              setIsEditing(false);
            }}
          >
            {t('common.cancel')}
          </button>
        </div>
      ) : null}
    </section>
  );
}


