import type { ReactNode } from 'react';

import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useSessionActions } from '@/entities/session';
import { BrandLogo, IconButton } from '@/shared/ui';

import './Sidebar.css';

type NavItem = {
  key: string;
  icon: ReactNode;
  to?: string;
};

const mainNav: NavItem[] = [
  { key: 'dashboard', icon: <i className="fa-solid fa-house" aria-hidden /> },
  { key: 'curriculos', icon: <i className="fa-regular fa-file-lines" aria-hidden />, to: '/protected/resumes' },
  { key: 'analiseComIA', icon: <i className="fa-solid fa-wand-magic-sparkles" aria-hidden /> },
  { key: 'historico', icon: <i className="fa-solid fa-clock-rotate-left" aria-hidden /> },
];

const bottomNav: NavItem[] = [
  { key: 'perfil', icon: <i className="fa-regular fa-user" aria-hidden />, to: '/protected/profile' },
  { key: 'config', icon: <i className="fa-solid fa-gear" aria-hidden />, to: '/protected/settings' },
  { key: 'sair', icon: <i className="fa-solid fa-arrow-right-from-bracket" aria-hidden /> },
];

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
        <IconButton aria-label={t('appShell.openMenu')} className="sr-sidebar__hamburger">
          <i className="fa-solid fa-bars" aria-hidden />
        </IconButton>

        <div className="sr-sidebar__brand">
          <BrandLogo showLabel={!collapsed} />
        </div>

        <IconButton
          aria-label={collapsed ? t('appShell.expandMenu') : t('appShell.collapseMenu')}
          onClick={onToggleCollapsed}
          className="sr-sidebar__collapse-fab"
        >
          <i className={`fa-solid ${collapsed ? 'fa-chevron-right' : 'fa-chevron-left'}`} aria-hidden />
        </IconButton>
      </div>

      <nav className="sr-sidebar__nav" aria-label={t('appShell.sidebarNav')}>
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
