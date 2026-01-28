import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { IconButton } from '@/shared/ui';

import './Topbar.css';

type Action = {
  key: string;
  ariaLabel: string;
  iconClass: string;
  badgeClass?: string;
  onClick?: () => void;
};

type Props = {
  showHamburger?: boolean;
  isMenuOpen?: boolean;
  onToggleMenu?: () => void;
  menuControlsId?: string;
};

export function Topbar(props: Props) {
  const { showHamburger = false, isMenuOpen = false, onToggleMenu, menuControlsId = 'sr-mobile-menu' } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();

  const actions: Action[] = [
    { key: 'search', ariaLabel: t('nav.search'), iconClass: 'fa-solid fa-magnifying-glass' },
    {
      key: 'notifications',
      ariaLabel: t('nav.notifications'),
      iconClass: 'fa-regular fa-bell',
      badgeClass: 'sr-topbar__badge--danger',
    },
    {
      key: 'profile',
      ariaLabel: t('nav.profile'),
      iconClass: 'fa-regular fa-user',
      badgeClass: 'sr-topbar__badge--success',
      onClick: () => navigate('/protected/profile'),
    },
  ];

  return (
    <header className="sr-topbar">
      <div className="sr-topbar__left" aria-hidden={!showHamburger}>
        {showHamburger ? (
          <IconButton
            aria-label={isMenuOpen ? t('appShell.closeMenu') : t('appShell.openMenu')}
            aria-expanded={isMenuOpen}
            aria-controls={menuControlsId}
            onClick={onToggleMenu}
            className="sr-topbar__icon-btn"
          >
            <i className="fa-solid fa-bars" aria-hidden />
          </IconButton>
        ) : null}
      </div>
      <div className="sr-topbar__right" aria-label={t('appShell.userActions')}>
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


