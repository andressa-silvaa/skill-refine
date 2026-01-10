import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ChangePasswordForm } from './ChangePasswordForm';

import './SecurityCard.css';

export function SecurityCard() {
  const { t } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);

  return (
    <section className="sr-profile__card" aria-label={t('profile.changePassword')}>
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">
            <i className="fa-solid fa-shield-halved" aria-hidden /> {t('profile.changePassword')}
          </h2>
        </div>
        <button type="button" className="sr-security__edit-btn" onClick={() => setIsEditing((v) => !v)}>
          <i className={`fa-regular ${isEditing ? 'fa-circle-xmark' : 'fa-pen-to-square'}`} aria-hidden />{' '}
          {isEditing ? t('common.close') : t('common.edit')}
        </button>
      </header>

      <div className="sr-security__panel" role="region" aria-label={t('profile.changePassword')}>
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


