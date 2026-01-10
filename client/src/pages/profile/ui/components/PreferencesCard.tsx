import { useEffect, useState } from 'react';

import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';

import './PreferencesCard.css';

export function PreferencesCard() {
  const [serverValue, setServerValue] = useState<boolean | null>(null);
  const [draftValue, setDraftValue] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const isDirty = serverValue !== null && draftValue !== serverValue;

  useEffect(() => {
    let isMounted = true;
    void profileApi
      .getPreferences()
      .then((res) => {
        const value = Boolean(res.email_notifications_enabled ?? res.emailNotificationsEnabled);
        if (!isMounted) return;
        setServerValue(value);
        setDraftValue(value);
      })
      .catch((e) => {
        if (!isMounted) return;
        setServerValue(null);
        setDraftValue(false);
        notify.error(getApiErrorMessage(e, 'Não foi possível carregar suas preferências.'));
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="sr-profile__card" aria-label="Preferências">
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">Preferências</h2>
          <div className="sr-profile__muted">Ajustes rápidos de comunicação.</div>
        </div>
        <button
          type="button"
          className="sr-profile-card__edit-btn"
          aria-label={isEditing ? 'Fechar edição' : 'Editar preferências'}
          disabled={isSaving || serverValue === null}
          onClick={() => {
            setIsEditing((v) => {
              const next = !v;
              setFieldError(null);
              if (next) setDraftValue(serverValue ?? false);
              else setDraftValue(serverValue ?? false);
              return next;
            });
          }}
        >
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? 'Fechar' : 'Editar'}
        </button>
      </header>

      <div className="sr-pref__row" aria-label="Notificações por e-mail">
        <div className="sr-pref__left">
          <span className="sr-pref__icon" aria-hidden>
            <i className="fa-fw fa-regular fa-envelope" />
          </span>
          <div className="sr-pref__text">
            <div className="sr-pref__label">Notificações por e-mail</div>
            <div className="sr-pref__desc">Receba avisos importantes e lembretes.</div>
          </div>
        </div>
        <button
          type="button"
          className={`sr-pref__switch${draftValue ? ' is-on' : ''}`}
          role="switch"
          aria-checked={draftValue}
          disabled={!isEditing || isSaving || serverValue === null}
          onClick={() => {
            if (!isEditing || isSaving) return;
            setFieldError(null);
            setDraftValue((v) => !v);
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
            disabled={isSaving || serverValue === null || !isDirty}
            onClick={async () => {
              setIsSaving(true);
              setFieldError(null);
              try {
                const res = await profileApi.updatePreferences({ email_notifications_enabled: draftValue });
                const value = Boolean(res.email_notifications_enabled ?? res.emailNotificationsEnabled);
                setServerValue(value);
                setDraftValue(value);
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
            {isSaving ? 'Salvando...' : 'Salvar'}
          </button>
          <button
            type="button"
            className="sr-btn sr-btn--secondary"
            disabled={isSaving}
            onClick={() => {
              setDraftValue(serverValue ?? false);
              setFieldError(null);
              setIsEditing(false);
            }}
          >
            Cancelar
          </button>
        </div>
      ) : null}
    </section>
  );
}


