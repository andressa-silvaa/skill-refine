import { useEffect, useRef, useState, type ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

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
  const desktopCollapsedRef = useRef<boolean | null>(null);

  useEffect(() => {
    if (!preferences) return;
    applyAppearancePreferences({ theme: preferences.theme, accent_color: preferences.accent_color });
  }, [preferences?.accent_color, preferences?.theme]);

  useEffect(() => {
    if (isMobile) {
      desktopCollapsedRef.current = collapsed;
      setCollapsed(true);
      return;
    }
    if (desktopCollapsedRef.current != null) {
      setCollapsed(desktopCollapsedRef.current);
      desktopCollapsedRef.current = null;
    }
  }, [isMobile, collapsed]);

  useEffect(() => {
    if (!isMobile) return;
    const expanded = !collapsed;
    document.body.style.overflow = expanded ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobile, collapsed]);

  return (
    <I18nextProvider i18n={i18n}>
      <div
        data-sr-theme-scope
        className={[
          'sr-app-shell',
          !isMobile && collapsed ? 'is-collapsed' : '',
          isMobile ? 'is-mobile' : '',
          isMobile && !collapsed ? 'is-mobile-menu-open' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <Sidebar collapsed={collapsed} onToggleCollapsed={() => setCollapsed((v) => !v)} />
        <button
          type="button"
          className="sr-app-shell__backdrop"
          aria-label={t('appShell.closeMenu')}
          onClick={() => setCollapsed(true)}
        />
        <div className="sr-app-shell__main">
          <Topbar />
          <div className="sr-app-shell__content">{children}</div>
        </div>
      </div>
    </I18nextProvider>
  );
}


