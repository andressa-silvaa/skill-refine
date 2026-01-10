import { useMemo } from 'react';

import { useSession } from '@/entities/session';

import './AccountStatusCard.css';

type Meta = {
  statusLabel: string;
  isActive: boolean;
  isEmailVerified: boolean;
  memberSince: string;
};

export function AccountStatusCard() {
  const { user } = useSession();

  const meta = useMemo<Meta>(
    () => ({
      statusLabel: user?.status === 'disabled' ? 'Desativada' : user?.status === 'deleted' ? 'Excluída' : 'Ativa',
      isActive: user?.status !== 'disabled' && user?.status !== 'deleted',
      isEmailVerified: Boolean(user?.email_verified),
      memberSince: user?.created_at ? new Date(user.created_at).toLocaleDateString('pt-BR') : '-',
    }),
    [user?.created_at, user?.email_verified, user?.status]
  );

  return (
    <section className="sr-profile__card" aria-label="Conta">
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">Conta</h2>
        </div>
      </header>

      <div className="sr-account-status">
        <div className="sr-account-status__row">
          <span className="sr-account-status__k">Status</span>
          <span className={`sr-account-status__badge${meta.isActive ? ' is-ok' : ''}`}>{meta.statusLabel}</span>
        </div>

        <div className="sr-account-status__row">
          <span className="sr-account-status__k">E-mail verificado</span>
          <span className={`sr-account-status__icon${meta.isEmailVerified ? ' is-ok' : ''}`} aria-label={meta.isEmailVerified ? 'Verificado' : 'Não verificado'}>
            <i className={`fa-solid ${meta.isEmailVerified ? 'fa-circle-check' : 'fa-circle-xmark'}`} aria-hidden />
          </span>
        </div>

        <div className="sr-account-status__row">
          <span className="sr-account-status__k">Membro desde</span>
          <span className="sr-account-status__v">
            <i className="fa-regular fa-calendar" aria-hidden /> {meta.memberSince}
          </span>
        </div>
      </div>
    </section>
  );
}


