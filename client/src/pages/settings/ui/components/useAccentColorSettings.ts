import { useEffect, useState } from 'react';

import { useSession, useSessionActions } from '@/entities/session';
import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { useDirtyState } from '@/shared/lib/hooks/useDirtyState';
import { applyAppearancePreferences, type AccentKey } from '@/shared/lib/theme/appearance';

export function useAccentColorSettings() {
  const { preferences } = useSession();
  const { updatePreferences } = useSessionActions();
  const accent = useDirtyState<AccentKey>('pink');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    if (!preferences) return;
    if (isEditing) return;
    accent.acceptServer(preferences.accent_color as AccentKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing, preferences?.accent_color]);

  useEffect(() => {
    return () => {
      if (isSaving) return;
      if (!isEditing) return;
      applyAppearancePreferences({ accent_color: accent.server ?? 'pink' });
    };
  }, [accent.server, isEditing, isSaving]);

  const toggleEdit = () => {
    setIsEditing((v) => {
      const next = !v;
      setFieldError(null);
      accent.resetDraft();
      if (!next) applyAppearancePreferences({ accent_color: accent.server ?? 'pink' });
      return next;
    });
  };

  const changeDraftKey = (value: AccentKey) => {
    if (!isEditing || isSaving) return;
    setFieldError(null);
    accent.setDraft(value);
    applyAppearancePreferences({ accent_color: value });
  };

  const cancelEdit = () => {
    accent.resetDraft();
    setFieldError(null);
    applyAppearancePreferences({ accent_color: accent.server ?? 'pink' });
    setIsEditing(false);
  };

  const save = async () => {
    if (isSaving) return;
    if (accent.server === null) return;
    if (!accent.isDirty) return;

    setIsSaving(true);
    setFieldError(null);
    try {
      const res = await profileApi.updatePreferences({ accent_color: accent.draft });
      const next = (res.accent_color ?? res.accentColor ?? accent.draft) as AccentKey;
      accent.acceptServer(next);
      applyAppearancePreferences({ accent_color: next });
      updatePreferences({ accent_color: next });
      setIsEditing(false);
    } catch (e) {
      const fields = getApiFieldErrors(e);
      const errMsg = fields?.accent_color;
      if (errMsg) setFieldError(errMsg);
      else notify.error(getApiErrorMessage(e, 'Não foi possível salvar agora.'));
    } finally {
      setIsSaving(false);
    }
  };

  return {
    serverKey: accent.server,
    draftKey: accent.draft,
    isDirty: accent.isDirty,
    isEditing,
    isSaving,
    fieldError,
    toggleEdit,
    changeDraftKey,
    cancelEdit,
    save,
  };
}
