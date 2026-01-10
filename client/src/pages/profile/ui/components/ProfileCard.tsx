import { useEffect, useMemo, useRef, useState } from 'react';

import { useSession, useSessionActions } from '@/entities/session';
import { profileApi } from '@/entities/session/api/profileApi';
import { getApiErrorMessage, getApiFieldErrors } from '@/shared/api';
import { notify } from '@/shared/lib/notify';

import { ProfileAvatar } from './ProfileAvatar';

import { registerSchema } from '@/features/auth/register/model/schema';

import './ProfileCard.css';

type ProfileDraft = {
  fullName: string;
  email: string;
};

const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);

export function ProfileCard() {
  const { user } = useSession();
  const { updateUser } = useSessionActions();

  const [draft, setDraft] = useState<ProfileDraft>(() => ({
    fullName: user?.full_name ?? '',
    email: user?.email ?? '',
  }));
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

  const currentAvatarSrc = useMemo(() => {
    if (previewUrl) return previewUrl;
    const url = user?.avatar_url ?? user?.avatarUrl ?? null;
    if (!url) return null;
    return url;
  }, [previewUrl, user?.avatar_url, user?.avatarUrl]);

  const initialDraft = initialRef.current ?? { fullName: user?.full_name ?? '', email: user?.email ?? '' };
  const hasChanges =
    Boolean(selectedFile) || draft.fullName.trim() !== (initialDraft.fullName ?? '').trim();

  return (
    <section className="sr-profile__card" aria-label="Informações básicas">
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">
            <i className="fa-regular fa-user" aria-hidden /> Informações Básicas
          </h2>
        </div>
        <button
          type="button"
          className="sr-profile-card__edit-btn"
          aria-label={isEditing ? 'Fechar edição' : 'Editar perfil'}
          disabled={isSaving}
          onClick={() => {
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
          }}
        >
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? 'Fechar' : 'Editar'}
        </button>
      </header>

      <div className="sr-profile-card__top">
        <div className={`sr-profile-card__avatar${isEditing ? ' is-editing' : ''}`}>
          <ProfileAvatar fullName={draft.fullName || user?.full_name || 'Usuário'} src={currentAvatarSrc} />

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (!isEditing) return;
              const file = e.target.files?.[0] ?? null;
              if (!file) return;

              if (!ALLOWED_TYPES.has(file.type)) {
                notify.error('Formato inválido. Envie JPG, PNG ou WEBP.');
                e.target.value = '';
                return;
              }
              if (file.size > MAX_AVATAR_BYTES) {
                notify.error('Arquivo muito grande. Tamanho máximo: 2MB.');
                e.target.value = '';
                return;
              }
              setSelectedFile(file);
            }}
          />
          <button
            type="button"
            className="sr-profile-card__avatar-cta"
            disabled={!isEditing || isSaving}
            onClick={() => {
              if (!isEditing) return;
              fileInputRef.current?.click();
            }}
          >
            {selectedFile ? 'Trocar' : 'Alterar'}
          </button>
        </div>

        <div className="sr-profile-card__fields" aria-label="Dados do perfil">
          <div className="sr-profile-card__field">
            <div className="sr-profile-card__label">Nome</div>
            {isEditing ? (
              <>
                <input
                  className="sr-profile-input"
                  value={draft.fullName}
                  onChange={(e) => {
                    setFullNameError(null);
                    setDraft((p) => ({ ...p, fullName: e.target.value }));
                  }}
                  autoComplete="name"
                />
                {fullNameError ? <p className="field-error">{fullNameError}</p> : null}
              </>
            ) : (
              <div className="sr-profile-card__value">{draft.fullName}</div>
            )}
          </div>
          <div className="sr-profile-card__field">
            <div className="sr-profile-card__label">E-mail</div>
            {isEditing ? (
              <input className="sr-profile-input" value={draft.email} readOnly aria-readonly="true" />
            ) : (
              <div className="sr-profile-card__value sr-profile-card__value--with-icon">
                <span className="sr-profile-card__value-text">{draft.email}</span>
                <i className="fa-regular fa-envelope" aria-hidden />
              </div>
            )}
          </div>
        </div>
      </div>

      {isEditing ? (
        <div className="sr-profile-card__actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={isSaving || !hasChanges}
            onClick={async () => {
              setIsSaving(true);
              setFullNameError(null);
              try {
                const updates: Array<() => Promise<void>> = [];

                const nextFullName = draft.fullName.trim();
                const currentFullName = (user?.full_name ?? '').trim();
                if (nextFullName && nextFullName !== currentFullName) {
                  const registerBaseSchema = (registerSchema as any).innerType?.() ?? null;
                  const fullNameSchema = registerBaseSchema?.shape?.fullName;
                  const parsed = fullNameSchema?.safeParse ? fullNameSchema.safeParse(nextFullName) : { success: true };
                  if (!parsed.success) {
                    setFullNameError(parsed.error.issues[0]?.message ?? 'Nome inválido.');
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
                const fields = getApiFieldErrors(e);
                const nameErr = fields?.full_name;
                if (nameErr) {
                  setFullNameError(nameErr);
                } else {
                  notify.error(getApiErrorMessage(e, 'Não foi possível salvar agora.'));
                }
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
              setSelectedFile(null);
              setPreviewUrl(null);
              if (fileInputRef.current) fileInputRef.current.value = '';
              setDraft(initialRef.current ?? { fullName: user?.full_name ?? '', email: user?.email ?? '' });
              setFullNameError(null);
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


