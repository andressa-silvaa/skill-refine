import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession, useSessionActions } from '@/entities/session';
import { profileApi } from '@/entities/session';
import { handleApiSaveError } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { validateAvatarFile } from './profileCardAvatarValidation';
import { validateFullName } from './profileCardFullNameValidation';

type ProfileDraft = { fullName: string; email: string };
export function useProfileCardState() {
  const { t } = useTranslation();
  const { user } = useSession();
  const { updateUser } = useSessionActions();
  const [draft, setDraft] = useState<ProfileDraft>(() => ({ fullName: user?.full_name ?? '', email: user?.email ?? '' }));
  const [isEditing, setIsEditing] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [fullNameError, setFullNameError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const initialRef = useRef<ProfileDraft | null>(null);

  useEffect(() => {
    setDraft({ fullName: user?.full_name ?? '', email: user?.email ?? '' });
  }, [user?.full_name, user?.email]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  const currentAvatarSrc = useMemo(
    () => (previewUrl ? previewUrl : ((user?.avatar_url ?? user?.avatarUrl ?? null) as string | null)),
    [previewUrl, user?.avatar_url, user?.avatarUrl]
  );

  const hasChanges = Boolean(selectedFile) || draft.fullName.trim() !== ((initialRef.current?.fullName ?? user?.full_name ?? '') as string).trim();

  const toggleEdit = () => {
    setIsEditing((v) => {
      const next = !v;
      if (next) {
        initialRef.current = { fullName: user?.full_name ?? '', email: user?.email ?? '' };
        setDraft(initialRef.current);
        setFullNameError(null);
        return next;
      }
      setSelectedFile(null);
      setPreviewUrl(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setDraft(initialRef.current ?? { fullName: user?.full_name ?? '', email: user?.email ?? '' });
      setFullNameError(null);
      return next;
    });
  };

  const onNameChange = (value: string) => {
    setFullNameError(null);
    setDraft((p) => ({ ...p, fullName: value }));
  };

  const onPickFile = () => (isEditing ? fileInputRef.current?.click() : void 0);

  const onFileChange = (file: File | null, clearInput?: () => void) => {
    if (!isEditing) return;
    if (!file) return;
    const err = validateAvatarFile(file);
    if (err) {
      notify.error(err);
      clearInput?.();
      return;
    }
    setSelectedFile(file);
  };

  const cancelEdit = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setDraft(initialRef.current ?? { fullName: user?.full_name ?? '', email: user?.email ?? '' });
    setFullNameError(null);
    setIsEditing(false);
  };

  const save = async () => {
    if (isSaving) return;
    if (!hasChanges) return;

    setIsSaving(true);
    setFullNameError(null);
    try {
      const updates: Array<() => Promise<void>> = [];
      const nextFullName = draft.fullName.trim();
      const currentFullName = (user?.full_name ?? '').trim();
      if (nextFullName && nextFullName !== currentFullName) {
        const err = validateFullName(nextFullName);
        if (err) {
          setFullNameError(err);
          return;
        }
        updates.push(async () => {
          const res = await profileApi.updateProfile({ full_name: nextFullName });
          updateUser(res.user);
        });
      }

      if (selectedFile) {
        updates.push(async () => {
          const res = await profileApi.uploadAvatar(selectedFile);
          const avatarUrl = res.avatar_url ?? res.avatarUrl ?? null;
          updateUser({ avatar_url: avatarUrl, avatarUrl });
          notify.success('Foto atualizada com sucesso.');
        });
      }
      for (const fn of updates) await fn();
      setSelectedFile(null);
      setPreviewUrl(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setIsEditing(false);
    } catch (e) {
      handleApiSaveError(e, {
        fallbackMessage: t('common.errors.saveFailed'),
        fieldKey: 'full_name',
        onFieldError: setFullNameError,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return {
    draft,
    isEditing,
    isSaving,
    fullNameError,
    fileInputRef,
    currentAvatarSrc,
    selectedFile,
    hasChanges,
    toggleEdit,
    onNameChange,
    onPickFile,
    onFileChange,
    save,
    cancelEdit,
  };
}
