import { useEffect, useMemo, useState } from 'react';

import { useSession, useSessionActions } from '@/entities/session';
import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { i18n } from '@/shared/lib/i18n';
import { applyLanguagePreferences } from '@/shared/lib/language/applyLanguagePreferences';
import { useDirtyState } from '@/shared/lib/hooks/useDirtyState';
import { notify } from '@/shared/lib/notify';

export function useGeneralSettingsLanguage(options: Array<{ value: string; label: string }>) {
  const { preferences } = useSession();
  const { updatePreferences } = useSessionActions();
  const language = useDirtyState<string>('pt-BR');

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  const [langOpen, setLangOpen] = useState(false);

  useEffect(() => {
    if (!preferences) return;
    if (isEditing) return;
    language.acceptServer(preferences.language);
    applyLanguagePreferences({ language: preferences.language });
    void i18n.changeLanguage(preferences.language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing, preferences?.language]);

  useEffect(() => {
    return () => {
      if (isSaving) return;
      if (!isEditing) return;
      applyLanguagePreferences({ language: language.server ?? 'pt-BR' });
      void i18n.changeLanguage(language.server ?? 'pt-BR');
    };
  }, [isEditing, isSaving, language.server]);

  const isDirty = useMemo(() => language.server !== null && language.isDirty, [language.isDirty, language.server]);

  const toggleEdit = () => {
    setIsEditing((v) => {
      const next = !v;
      setFieldError(null);
      language.resetDraft();
      if (!next) {
        applyLanguagePreferences({ language: language.server ?? 'pt-BR' });
        void i18n.changeLanguage(language.server ?? 'pt-BR');
      }
      return next;
    });
  };

  const changeDraftLanguage = (value: string) => {
    if (!isEditing || isSaving) return;
    if (!options.some((o) => o.value === value)) return;
    setFieldError(null);
    language.setDraft(value);
    applyLanguagePreferences({ language: value });
    void i18n.changeLanguage(value);
  };

  const cancelEdit = () => {
    language.resetDraft();
    setFieldError(null);
    applyLanguagePreferences({ language: language.server ?? 'pt-BR' });
    void i18n.changeLanguage(language.server ?? 'pt-BR');
    setIsEditing(false);
  };

  const save = async () => {
    if (isSaving) return;
    if (language.server === null) return;
    if (!isDirty) return;

    setIsSaving(true);
    setFieldError(null);
    try {
      const res = await profileApi.updatePreferences({ language: language.draft });
      const next = String(res.language || language.draft);
      language.acceptServer(next);
      applyLanguagePreferences({ language: next });
      void i18n.changeLanguage(next);
      updatePreferences({ language: next });
      setIsEditing(false);
    } catch (e) {
      const fields = getApiFieldErrors(e);
      const errMsg = (fields as any)?.language;
      if (errMsg) setFieldError(errMsg);
      else notify.error(getApiErrorMessage(e, 'Não foi possível salvar agora.'));
    } finally {
      setIsSaving(false);
    }
  };

  return {
    serverLanguage: language.server,
    draftLanguage: language.draft,
    isEditing,
    isSaving,
    fieldError,
    isDirty,
    langOpen,
    setLangOpen,
    toggleEdit,
    changeDraftLanguage,
    cancelEdit,
    save,
  };
}
