import { useSession } from '@/entities/session';
import { useTranslation } from 'react-i18next';

import { ProfileAvatar } from './ProfileAvatar';
import { useProfileCardState } from './useProfileCardState';

import './ProfileCard.css';

export function ProfileCard() {
  const { t } = useTranslation();
  const { user } = useSession();
  const ui = useProfileCardState();

  return (
    <section className="sr-profile__card" aria-label={t('profile.basicInfo')}>
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">
            <i className="fa-regular fa-user" aria-hidden /> {t('profile.basicInfo')}
          </h2>
        </div>
        <button
          type="button"
          className="sr-profile-card__edit-btn"
          aria-label={ui.isEditing ? t('common.close') : t('profile.editProfile')}
          disabled={ui.isSaving}
          onClick={ui.toggleEdit}
        >
          <i className={`fa-regular ${ui.isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {ui.isEditing ? t('common.close') : t('common.edit')}
        </button>
      </header>

      <div className="sr-profile-card__top">
        <div className={`sr-profile-card__avatar${ui.isEditing ? ' is-editing' : ''}`}>
          <ProfileAvatar fullName={ui.draft.fullName || user?.full_name || 'Usuário'} src={ui.currentAvatarSrc} />

          <input
            ref={ui.fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0] ?? null;
              ui.onFileChange(file, () => {
                e.target.value = '';
              });
            }}
          />
          <button
            type="button"
            className="sr-profile-card__avatar-cta"
            disabled={!ui.isEditing || ui.isSaving}
            onClick={() => {
              ui.onPickFile();
            }}
          >
            {ui.selectedFile ? t('profile.avatarReplace') : t('profile.avatarChange')}
          </button>
        </div>

        <div className="sr-profile-card__fields" aria-label={t('profile.profileData')}>
          <div className="sr-profile-card__field">
            <div className="sr-profile-card__label">{t('profile.nameLabel')}</div>
            {ui.isEditing ? (
              <>
                <input
                  className="sr-profile-input"
                  value={ui.draft.fullName}
                  onChange={(e) => {
                    ui.onNameChange(e.target.value);
                  }}
                  autoComplete="name"
                />
                {ui.fullNameError ? <p className="field-error">{ui.fullNameError}</p> : null}
              </>
            ) : (
              <div className="sr-profile-card__value">{ui.draft.fullName}</div>
            )}
          </div>
          <div className="sr-profile-card__field">
            <div className="sr-profile-card__label">{t('profile.emailLabel')}</div>
            {ui.isEditing ? (
              <input className="sr-profile-input" value={ui.draft.email} readOnly aria-readonly="true" />
            ) : (
              <div className="sr-profile-card__value sr-profile-card__value--with-icon">
                <span className="sr-profile-card__value-text">{ui.draft.email}</span>
                <i className="fa-regular fa-envelope" aria-hidden />
              </div>
            )}
          </div>
        </div>
      </div>

      {ui.isEditing ? (
        <div className="sr-profile-card__actions">
          <button
            type="button"
            className="sr-btn sr-btn--primary"
            disabled={!ui.isEditing || ui.isSaving || !ui.hasChanges}
            onClick={ui.save}
          >
            {ui.isSaving ? t('common.saving') : t('common.save')}
          </button>
          <button
            type="button"
            className="sr-btn sr-btn--secondary"
            disabled={ui.isSaving}
            onClick={ui.cancelEdit}
          >
            {t('common.cancel')}
          </button>
        </div>
      ) : null}
    </section>
  );
}


