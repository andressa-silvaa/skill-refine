import { useEffect, useMemo, useState, type CSSProperties } from 'react';

import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { ACCENTS, applyAppearancePreferences, type AccentKey } from '@/shared/lib/theme/appearance';

import './AccentColorSettingsCard.css';

export function AccentColorSettingsCard() {
  const [serverKey, setServerKey] = useState<AccentKey | null>(null);
  const [draftKey, setDraftKey] = useState<AccentKey>('pink');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    void profileApi
      .getPreferences()
      .then((res) => {
        const raw = (res.accent_color ?? res.accentColor ?? 'pink') as AccentKey;
        if (!isMounted) return;
        setServerKey(raw);
        setDraftKey(raw);
      })
      .catch((e) => {
        if (!isMounted) return;
        setServerKey(null);
        notify.error(getApiErrorMessage(e, 'Não foi possível carregar suas preferências.'));
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const isDirty = useMemo(() => serverKey !== null && draftKey !== serverKey, [draftKey, serverKey]);

  return (
    <section className="sr-settings__card" aria-label="Cor de destaque">
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-regular fa-star" aria-hidden /> Cor de destaque
          </h2>
          <div className="sr-settings__muted">Personalize a cor do sistema.</div>
        </div>
        <button
          type="button"
          className="sr-edit-btn"
          aria-label={isEditing ? 'Fechar edição' : 'Editar cor de destaque'}
          disabled={isSaving || serverKey === null}
          onClick={() => {
            setIsEditing((v) => {
              const next = !v;
              setFieldError(null);
              setDraftKey(serverKey ?? 'pink');
              if (!next) applyAppearancePreferences({ accent_color: serverKey ?? 'pink' });
              return next;
            });
          }}
        >
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? 'Fechar' : 'Editar'}
        </button>
      </header>

      <div className="sr-accent" role="list" aria-label="Selecionar cor de destaque">
        {ACCENTS.map((a) => {
          const isActive = draftKey === a.key;
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
              disabled={!isEditing || isSaving}
              onClick={() => {
                if (!isEditing || isSaving) return;
                setFieldError(null);
                setDraftKey(a.key);
                applyAppearancePreferences({ accent_color: a.key });
              }}
            >
              {isActive ? <i className="fa-solid fa-check" aria-hidden /> : null}
            </button>
          );
        })}
      </div>

      {fieldError ? <p className="field-error">{fieldError}</p> : null}

      {isEditing ? (
        <div className="sr-card-actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={isSaving || serverKey === null || !isDirty}
            onClick={async () => {
              setIsSaving(true);
              setFieldError(null);
              try {
                const res = await profileApi.updatePreferences({ accent_color: draftKey });
                const next = (res.accent_color ?? res.accentColor ?? draftKey) as AccentKey;
                setServerKey(next);
                setDraftKey(next);
                applyAppearancePreferences({ accent_color: next });
                setIsEditing(false);
              } catch (e) {
                const fields = getApiFieldErrors(e);
                const errMsg = fields?.accent_color;
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
              setDraftKey(serverKey ?? 'pink');
              setFieldError(null);
              applyAppearancePreferences({ accent_color: serverKey ?? 'pink' });
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


