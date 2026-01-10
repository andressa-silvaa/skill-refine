import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';

import './AccountStatusCard.css';

type Meta = {
  statusLabel: string;
  isActive: boolean;
  isEmailVerified: boolean;
  memberSince: string;
};

export function AccountStatusCard() {
  const { t, i18n } = useTranslation();
  const { user } = useSession();

  const meta = useMemo<Meta>(
    () => ({
      statusLabel:
        user?.status === 'disabled'
          ? t('profile.accountStatusDisabled')
          : user?.status === 'deleted'
            ? t('profile.accountStatusDeleted')
            : t('profile.accountStatusActive'),
      isActive: user?.status !== 'disabled' && user?.status !== 'deleted',
      isEmailVerified: Boolean(user?.email_verified),
      memberSince: user?.created_at ? new Date(user.created_at).toLocaleDateString(i18n.language) : '-',
    }),
    [i18n.language, t, user?.created_at, user?.email_verified, user?.status]
  );

  return (
    <section className="sr-profile__card" aria-label={t('profile.account')}>
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">{t('profile.account')}</h2>
        </div>
      </header>

      <div className="sr-account-status">
        <div className="sr-account-status__row">
          <span className="sr-account-status__k">{t('profile.accountStatus')}</span>
          <span className={`sr-account-status__badge${meta.isActive ? ' is-ok' : ''}`}>{meta.statusLabel}</span>
        </div>

        <div className="sr-account-status__row">
          <span className="sr-account-status__k">{t('profile.emailVerified')}</span>
          <span
            className={`sr-account-status__icon${meta.isEmailVerified ? ' is-ok' : ''}`}
            aria-label={meta.isEmailVerified ? t('profile.verified') : t('profile.notVerified')}
          >
            <i className={`fa-solid ${meta.isEmailVerified ? 'fa-circle-check' : 'fa-circle-xmark'}`} aria-hidden />
          </span>
        </div>

        <div className="sr-account-status__row">
          <span className="sr-account-status__k">{t('profile.memberSince')}</span>
          <span className="sr-account-status__v">
            <i className="fa-regular fa-calendar" aria-hidden /> {meta.memberSince}
          </span>
        </div>
      </div>
    </section>
  );
}


