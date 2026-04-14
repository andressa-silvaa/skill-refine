import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { MobileMenuTopSheet } from './MobileMenuTopSheet';

import './AppShell.css';
import { useMediaQuery } from '@/shared/lib/hooks/useMediaQuery';
import { i18n } from '@/shared/lib/i18n';
import { applyAppearancePreferences } from '@/shared/lib/theme/appearance';

type Props = {
  children?: ReactNode;
  defaultCollapsed?: boolean;
};

export function AppShell(props: Props) {
  const { children, defaultCollapsed = false } = props;
  const { t } = useTranslation();
  const { preferences } = useSession();
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const isMobile = useMediaQuery('(max-width: 900px)');
  const isSm = useMediaQuery('(max-width: 480px)');
  const desktopCollapsedRef = useRef<boolean | null>(null);
  const prevIsMobileRef = useRef(isMobile);
  const collapsedRef = useRef(collapsed);
  collapsedRef.current = collapsed;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useLayoutEffect(() => {
    if (!preferences) return;
    applyAppearancePreferences({ theme: preferences.theme, accent_color: preferences.accent_color });
  }, [preferences]);

  /**
   * Só ao entrar/sair do breakpoint mobile (≤900px): guardar estado de desktop e forçar menu fechado uma vez.
   * Não reagir a cada mudança de `collapsed` em mobile — senão o botão de expandir nunca funciona (efeito repunha collapsed=true).
   */
  useEffect(() => {
    const wasMobile = prevIsMobileRef.current;
    prevIsMobileRef.current = isMobile;

    if (isMobile && !wasMobile) {
      desktopCollapsedRef.current = collapsedRef.current;
      setCollapsed(true);
      return;
    }

    if (!isMobile && wasMobile && desktopCollapsedRef.current != null) {
      const previousDesktopValue = desktopCollapsedRef.current;
      desktopCollapsedRef.current = null;
      setCollapsed(previousDesktopValue);
    }
  }, [isMobile]);

  useEffect(() => {
    if (!isSm) return;
    const expanded = isMobileMenuOpen;
    document.body.style.overflow = expanded ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isSm, isMobileMenuOpen]);

  useEffect(() => {
    if (!isSm && isMobileMenuOpen) setIsMobileMenuOpen(false);
  }, [isSm, isMobileMenuOpen]);

  return (
    <I18nextProvider i18n={i18n}>
      <div
        data-sr-theme-scope
        className={[
          'sr-app-shell',
          !isMobile && collapsed ? 'is-collapsed' : '',
          isMobile ? 'is-mobile' : '',
          isMobile && !collapsed ? 'is-mobile-menu-open' : '',
          isSm ? 'is-sm' : '',
          isSm && isMobileMenuOpen ? 'is-sm-menu-open' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {isSm ? null : <Sidebar collapsed={collapsed} onToggleCollapsed={() => setCollapsed((v) => !v)} />}
        {isSm ? null : (
          <button
            type="button"
            className="sr-app-shell__backdrop"
            aria-label={t('appShell.closeMenu')}
            onClick={() => setCollapsed(true)}
          />
        )}
        <div className="sr-app-shell__main">
          <Topbar
            showHamburger={isSm}
            isMenuOpen={isMobileMenuOpen}
            onToggleMenu={() => setIsMobileMenuOpen((v) => !v)}
            menuControlsId="sr-mobile-menu"
          />
          <div className="sr-app-shell__content">{children}</div>
        </div>
        {isSm ? <MobileMenuTopSheet open={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} /> : null}
      </div>
    </I18nextProvider>
  );
}


