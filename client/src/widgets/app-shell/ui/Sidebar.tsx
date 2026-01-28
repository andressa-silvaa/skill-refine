import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useSessionActions } from '@/entities/session';
import { BrandLogo, IconButton } from '@/shared/ui';
import { bottomNav, mainNav, type NavItem } from '../model/navItems';

import './Sidebar.css';

type Props = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function Sidebar(props: Props) {
  const { collapsed, onToggleCollapsed } = props;
  const { t } = useTranslation();
  const { logout } = useSessionActions();
  const navigate = useNavigate();
  const location = useLocation();

  const pathname = location.pathname;

  const isNavItemActive = (item: NavItem) => (item.to ? pathname.startsWith(item.to) : false);

  const onNavItemClick = (item: NavItem) => {
    if (item.key === 'sair') {
      void logout();
      return;
    }
    if (item.to) navigate(item.to);
  };

  return (
    <aside className={`sr-sidebar${collapsed ? ' is-collapsed' : ''}`}>
      <div className="sr-sidebar__header">
        <div className="sr-sidebar__brand">
          <BrandLogo showLabel={!collapsed} />
        </div>

        <IconButton
          aria-label={collapsed ? t('appShell.expandMenu') : t('appShell.collapseMenu')}
          onClick={onToggleCollapsed}
          className="sr-sidebar__collapse-fab"
          aria-expanded={!collapsed}
          aria-controls="sr-sidebar-nav"
        >
          <i className={`fa-solid ${collapsed ? 'fa-chevron-right' : 'fa-chevron-left'}`} aria-hidden />
        </IconButton>
      </div>

      <nav id="sr-sidebar-nav" className="sr-sidebar__nav" aria-label={t('appShell.sidebarNav')}>
        <ul className="sr-sidebar__list">
          {mainNav.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                className={`sr-sidebar__item${isNavItemActive(item) ? ' is-active' : ''}`}
                aria-label={collapsed ? t(`nav.${item.key}`) : undefined}
                onClick={() => {
                  onNavItemClick(item);
                }}
              >
                <span className="sr-sidebar__icon">{item.icon}</span>
                {!collapsed ? <span className="sr-sidebar__label">{t(`nav.${item.key}`)}</span> : null}
              </button>
            </li>
          ))}
        </ul>

        <div className="sr-sidebar__spacer" />

        <ul className="sr-sidebar__list sr-sidebar__list--bottom">
          {bottomNav.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                className={`sr-sidebar__item sr-sidebar__item--muted${isNavItemActive(item) ? ' is-active' : ''}`}
                aria-label={collapsed ? t(`nav.${item.key}`) : undefined}
                onClick={() => {
                  onNavItemClick(item);
                }}
              >
                <span className="sr-sidebar__icon">{item.icon}</span>
                {!collapsed ? <span className="sr-sidebar__label">{t(`nav.${item.key}`)}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
