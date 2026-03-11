import { useEffect, useRef } from 'react';

import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useSessionActions } from '@/entities/session';
import { bottomNav, mainNav, type NavItem } from '../model/navItems';

import './MobileMenuTopSheet.css';

type Props = {
  open: boolean;
  onClose: () => void;
};

export function MobileMenuTopSheet(props: Props) {
  const { open, onClose } = props;
  const { t } = useTranslation();
  const { logout } = useSessionActions();
  const navigate = useNavigate();
  const location = useLocation();
  const containerRef = useRef<HTMLDivElement>(null);

  const pathname = location.pathname;
  const isNavItemActive = (item: NavItem) => (item.to ? pathname.startsWith(item.to) : false);

  const onNavItemClick = (item: NavItem) => {
    if (item.key === 'sair') {
      void logout();
      onClose();
      return;
    }
    if (item.to) {
      navigate(item.to);
      onClose();
    }
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    window.setTimeout(() => {
      const first = containerRef.current?.querySelector<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
      first?.focus?.();
    }, 0);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className={`sr-mobile-menu__backdrop${open ? ' is-open' : ''}`}
        aria-label={t('appShell.closeMenu')}
        onClick={onClose}
      />

      <div
        id="sr-mobile-menu"
        className={`sr-mobile-menu${open ? ' is-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={t('appShell.sidebarNav')}
        ref={containerRef}
      >
        <nav className="sr-mobile-menu__nav" aria-label={t('appShell.sidebarNav')}>
          <ul className="sr-mobile-menu__list">
            {mainNav.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  className={`sr-mobile-menu__item${isNavItemActive(item) ? ' is-active' : ''}`}
                  onClick={() => onNavItemClick(item)}
                >
                  <span className="sr-mobile-menu__icon">{item.icon}</span>
                  <span className="sr-mobile-menu__label">{t(`nav.${item.key}`)}</span>
                </button>
              </li>
            ))}
          </ul>

          <div className="sr-mobile-menu__divider" aria-hidden />

          <ul className="sr-mobile-menu__list sr-mobile-menu__list--bottom">
            {bottomNav.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  className={`sr-mobile-menu__item sr-mobile-menu__item--muted${isNavItemActive(item) ? ' is-active' : ''}`}
                  onClick={() => onNavItemClick(item)}
                >
                  <span className="sr-mobile-menu__icon">{item.icon}</span>
                  <span className="sr-mobile-menu__label">{t(`nav.${item.key}`)}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </>
  );
}

