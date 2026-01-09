import { useState } from 'react';

import { ProfileAvatar } from './ProfileAvatar';

import './ProfileCard.css';

type ProfileDraft = {
  fullName: string;
  email: string;
  avatarUrl?: string | null;
};

export function ProfileCard() {
  const [draft, setDraft] = useState<ProfileDraft>({
    fullName: 'Andressa Silva',
    email: 'andressa.silva@email.com',
    avatarUrl: null,
  });
  const [isEditing, setIsEditing] = useState(false);

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
          onClick={() => setIsEditing((v) => !v)}
        >
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? 'Fechar' : 'Editar'}
        </button>
      </header>

      <div className="sr-profile-card__top">
        <div className="sr-profile-card__avatar">
          <ProfileAvatar fullName={draft.fullName} src={draft.avatarUrl} />
          <button type="button" className="sr-profile-card__avatar-cta" onClick={() => void 0}>
            Alterar
          </button>
        </div>

        <div className="sr-profile-card__fields" aria-label="Dados do perfil">
          <div className="sr-profile-card__field">
            <div className="sr-profile-card__label">Nome</div>
            {isEditing ? (
              <input
                className="sr-profile-input"
                value={draft.fullName}
                onChange={(e) => setDraft((p) => ({ ...p, fullName: e.target.value }))}
                autoComplete="name"
              />
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
          <button type="button" className="sr-btn sr-btn--primary" onClick={() => setIsEditing(false)}>
            Salvar
          </button>
          <button type="button" className="sr-btn sr-btn--secondary" onClick={() => setIsEditing(false)}>
            Cancelar
          </button>
        </div>
      ) : null}
    </section>
  );
}


