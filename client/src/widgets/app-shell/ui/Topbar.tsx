import { useNavigate } from 'react-router-dom';

import { IconButton } from '@/shared/ui';

import './Topbar.css';

type Action = {
  key: string;
  ariaLabel: string;
  iconClass: string;
  badgeClass?: string;
  onClick?: () => void;
};

export function Topbar() {
  const navigate = useNavigate();

  const actions: Action[] = [
    { key: 'search', ariaLabel: 'Buscar', iconClass: 'fa-solid fa-magnifying-glass' },
    {
      key: 'notifications',
      ariaLabel: 'Notificações',
      iconClass: 'fa-regular fa-bell',
      badgeClass: 'sr-topbar__badge--danger',
    },
    {
      key: 'profile',
      ariaLabel: 'Perfil',
      iconClass: 'fa-regular fa-user',
      badgeClass: 'sr-topbar__badge--success',
      onClick: () => navigate('/protected/profile'),
    },
  ];

  return (
    <header className="sr-topbar">
      <div className="sr-topbar__left" aria-hidden />
      <div className="sr-topbar__right" aria-label="Ações do usuário">
        {actions.map((a) => (
          <IconButton
            key={a.key}
            aria-label={a.ariaLabel}
            className={`sr-topbar__icon-btn${a.badgeClass ? ' sr-topbar__icon-btn--badge' : ''}`}
            onClick={a.onClick}
          >
            <i className={a.iconClass} aria-hidden />
            {a.badgeClass ? <span className={`sr-topbar__badge ${a.badgeClass}`} aria-hidden /> : null}
          </IconButton>
        ))}
      </div>
    </header>
  );
}


