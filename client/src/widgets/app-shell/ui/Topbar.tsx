import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { IconButton } from '@/shared/ui';
import { GlobalSearchModal } from '@/features/global-search';
import { NotificationsMenu } from '@/features/notifications';

import './Topbar.css';

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
        <GlobalSearchModal
          trigger={
            <IconButton aria-label={t('nav.search')} className="sr-topbar__icon-btn">
              <i className="fa-solid fa-magnifying-glass" aria-hidden />
            </IconButton>
          }
        />
        <NotificationsMenu />
        <IconButton
          aria-label={t('nav.profile')}
          className="sr-topbar__icon-btn sr-topbar__icon-btn--badge"
          onClick={() => navigate('/protected/profile')}
        >
          <i className="fa-regular fa-user" aria-hidden />
          <span className="sr-topbar__badge sr-topbar__badge--success" aria-hidden />
        </IconButton>
      </div>
    </header>
  );
}


