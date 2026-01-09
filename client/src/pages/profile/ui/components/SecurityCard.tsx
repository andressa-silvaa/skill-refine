import { useState } from 'react';

import { ChangePasswordForm } from './ChangePasswordForm';

import './SecurityCard.css';

export function SecurityCard() {
  const [isEditing, setIsEditing] = useState(false);

  return (
    <section className="sr-profile__card" aria-label="Alterar senha">
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">
            <i className="fa-solid fa-shield-halved" aria-hidden /> Alterar Senha
          </h2>
        </div>
        <button type="button" className="sr-security__edit-btn" onClick={() => setIsEditing((v) => !v)}>
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? 'Fechar' : 'Editar'}
        </button>
      </header>

      <div className="sr-security__panel" role="region" aria-label="Alterar senha">
        <ChangePasswordForm
          disabled={!isEditing}
          showActions={isEditing}
          onCancel={() => setIsEditing(false)}
          onSaved={() => setIsEditing(false)}
        />
      </div>
    </section>
  );
}


