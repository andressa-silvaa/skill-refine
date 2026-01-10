import { useEffect, useMemo, useState } from 'react';

import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { applyAppearancePreferences, type ThemeMode } from '@/shared/lib/theme/appearance';

import './AppearanceSettingsCard.css';

export function AppearanceSettingsCard() {
  const [serverTheme, setServerTheme] = useState<ThemeMode | null>(null);
  const [draftTheme, setDraftTheme] = useState<ThemeMode>('light');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    void profileApi
      .getPreferences()
      .then((res) => {
        const raw = (res.theme === 'dark' ? 'dark' : 'light') as ThemeMode;
        if (!isMounted) return;
        setServerTheme(raw);
        setDraftTheme(raw);
      })
      .catch((e) => {
        if (!isMounted) return;
        setServerTheme(null);
        notify.error(getApiErrorMessage(e, 'Não foi possível carregar suas preferências.'));
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const isDirty = useMemo(() => serverTheme !== null && draftTheme !== serverTheme, [draftTheme, serverTheme]);

  return (
    <section className="sr-settings__card" aria-label="Aparência">
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-palette" aria-hidden /> Aparência
          </h2>
          <div className="sr-settings__muted">Escolha entre tema claro e escuro.</div>
        </div>
        <button
          type="button"
          className="sr-edit-btn"
          aria-label={isEditing ? 'Fechar edição' : 'Editar aparência'}
          disabled={isSaving || serverTheme === null}
          onClick={() => {
            setIsEditing((v) => {
              const next = !v;
              setFieldError(null);
              setDraftTheme(serverTheme ?? 'light');
              if (!next) applyAppearancePreferences({ theme: serverTheme ?? 'light' });
              return next;
            });
          }}
        >
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? 'Fechar' : 'Editar'}
        </button>
      </header>

      <div className="sr-appearance">
        <div className="sr-appearance__label">Tema</div>
        <div className="sr-appearance__grid" role="group" aria-label="Selecionar tema">
          <button
            type="button"
            className={`sr-appearance__option${draftTheme === 'light' ? ' is-active' : ''}`}
            disabled={!isEditing || isSaving}
            onClick={() => {
              if (!isEditing || isSaving) return;
              setFieldError(null);
              setDraftTheme('light');
              applyAppearancePreferences({ theme: 'light' });
            }}
          >
            <i className="fa-regular fa-sun" aria-hidden />
            <span>Claro</span>
          </button>
          <button
            type="button"
            className={`sr-appearance__option${draftTheme === 'dark' ? ' is-active' : ''}`}
            disabled={!isEditing || isSaving}
            onClick={() => {
              if (!isEditing || isSaving) return;
              setFieldError(null);
              setDraftTheme('dark');
              applyAppearancePreferences({ theme: 'dark' });
            }}
          >
            <i className="fa-regular fa-moon" aria-hidden />
            <span>Escuro</span>
          </button>
        </div>
      </div>

      {fieldError ? <p className="field-error">{fieldError}</p> : null}

      {isEditing ? (
        <div className="sr-card-actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={isSaving || serverTheme === null || !isDirty}
            onClick={async () => {
              setIsSaving(true);
              setFieldError(null);
              try {
                const res = await profileApi.updatePreferences({ theme: draftTheme });
                const next = (res.theme === 'dark' ? 'dark' : 'light') as ThemeMode;
                setServerTheme(next);
                setDraftTheme(next);
                applyAppearancePreferences({ theme: next });
                setIsEditing(false);
              } catch (e) {
                const fields = getApiFieldErrors(e);
                const errMsg = fields?.theme;
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
              setDraftTheme(serverTheme ?? 'light');
              setFieldError(null);
              applyAppearancePreferences({ theme: serverTheme ?? 'light' });
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


