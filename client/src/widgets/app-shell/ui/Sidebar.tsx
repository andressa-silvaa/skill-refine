import type { ReactNode } from 'react';

import { useLocation, useNavigate } from 'react-router-dom';

import { useSessionActions } from '@/entities/session';
import { BrandLogo, IconButton } from '@/shared/ui';

import './Sidebar.css';

type NavItem = {
  key: string;
  label: string;
  icon: ReactNode;
  isActive?: boolean;
  to?: string;
};

const mainNav: NavItem[] = [
  { key: 'dashboard', label: 'Dashboard', icon: <i className="fa-solid fa-house" aria-hidden /> },
  { key: 'curriculo', label: 'Currículo', icon: <i className="fa-regular fa-file-lines" aria-hidden />, isActive: true },
  { key: 'dashboard2', label: 'Dashboard', icon: <i className="fa-regular fa-house" aria-hidden /> },
];

const bottomNav: NavItem[] = [
  { key: 'perfil', label: 'Perfil', icon: <i className="fa-regular fa-user" aria-hidden />, to: '/protected/profile' },
  { key: 'config', label: 'Configurações', icon: <i className="fa-solid fa-gear" aria-hidden />, to: '/protected/settings' },
  { key: 'sair', label: 'Sair', icon: <i className="fa-solid fa-arrow-right-from-bracket" aria-hidden /> },
];

type Props = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function Sidebar(props: Props) {
  const { collapsed, onToggleCollapsed } = props;
  const { logout } = useSessionActions();
  const navigate = useNavigate();
  const location = useLocation();

  const pathname = location.pathname;

  return (
    <aside className={`sr-sidebar${collapsed ? ' is-collapsed' : ''}`}>
      <div className="sr-sidebar__header">
        <IconButton aria-label="Abrir menu" className="sr-sidebar__hamburger">
          <i className="fa-solid fa-bars" aria-hidden />
        </IconButton>

        <div className="sr-sidebar__brand">
          <BrandLogo showLabel={!collapsed} />
        </div>

        <IconButton
          aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}
          onClick={onToggleCollapsed}
          className="sr-sidebar__collapse-fab"
        >
          <i className={`fa-solid ${collapsed ? 'fa-chevron-right' : 'fa-chevron-left'}`} aria-hidden />
        </IconButton>
      </div>

      <nav className="sr-sidebar__nav" aria-label="Menu lateral">
        <ul className="sr-sidebar__list">
          {mainNav.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                className={`sr-sidebar__item${item.isActive ? ' is-active' : ''}`}
                aria-label={collapsed ? item.label : undefined}
              >
                <span className="sr-sidebar__icon">{item.icon}</span>
                {!collapsed ? <span className="sr-sidebar__label">{item.label}</span> : null}
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
                className={`sr-sidebar__item sr-sidebar__item--muted${
                  item.to && pathname.startsWith(item.to) ? ' is-active' : ''
                }`}
                aria-label={collapsed ? item.label : undefined}
                onClick={() => {
                  if (item.key === 'sair') {
                    void logout();
                    return;
                  }
                  if (item.to) navigate(item.to);
                }}
              >
                <span className="sr-sidebar__icon">{item.icon}</span>
                {!collapsed ? <span className="sr-sidebar__label">{item.label}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
