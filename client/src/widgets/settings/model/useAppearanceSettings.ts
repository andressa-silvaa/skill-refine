import { useEffect, useState } from 'react';

import { useSession, useSessionActions } from '@/entities/session';
import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { useDirtyState } from '@/shared/lib/hooks/useDirtyState';
import { applyAppearancePreferences, type ThemeMode } from '@/shared/lib/theme/appearance';

export function useAppearanceSettings() {
  const { preferences } = useSession();
  const { updatePreferences } = useSessionActions();
  const theme = useDirtyState<ThemeMode>('light');
  const { acceptServer, resetDraft, setDraft } = theme;
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    if (!preferences) return;
    if (isEditing) return;
    acceptServer(preferences.theme as ThemeMode);
  }, [acceptServer, isEditing, preferences?.theme]);

  useEffect(() => {
    return () => {
      if (isSaving) return;
      if (!isEditing) return;
      applyAppearancePreferences({ theme: theme.server ?? 'light' });
    };
  }, [isEditing, isSaving, theme.server]);

  const toggleEdit = () => {
    setIsEditing((v) => {
      const next = !v;
      setFieldError(null);
      resetDraft();
      if (!next) applyAppearancePreferences({ theme: theme.server ?? 'light' });
      return next;
    });
  };

  const changeDraftTheme = (value: ThemeMode) => {
    if (!isEditing || isSaving) return;
    setFieldError(null);
    setDraft(value);
    applyAppearancePreferences({ theme: value });
  };

  const cancelEdit = () => {
    resetDraft();
    setFieldError(null);
    applyAppearancePreferences({ theme: theme.server ?? 'light' });
    setIsEditing(false);
  };

  const save = async () => {
    if (isSaving) return;
    if (theme.server === null) return;
    if (!theme.isDirty) return;

    setIsSaving(true);
    setFieldError(null);
    try {
      const res = await profileApi.updatePreferences({ theme: theme.draft });
      const next = (res.theme === 'dark' ? 'dark' : 'light') as ThemeMode;
      theme.acceptServer(next);
      applyAppearancePreferences({ theme: next });
      updatePreferences({ theme: next });
      setIsEditing(false);
    } catch (e) {
      const fields = getApiFieldErrors(e);
      const errMsg = fields?.theme;
      if (errMsg) setFieldError(errMsg);
      else notify.error(getApiErrorMessage(e, 'Não foi possível salvar agora.'));
    } finally {
      setIsSaving(false);
    }
  };

  return {
    serverTheme: theme.server,
    draftTheme: theme.draft,
    isDirty: theme.isDirty,
    isEditing,
    isSaving,
    fieldError,
    toggleEdit,
    changeDraftTheme,
    cancelEdit,
    save,
  };
}
