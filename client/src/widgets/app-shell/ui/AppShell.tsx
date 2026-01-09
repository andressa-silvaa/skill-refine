import { useEffect, useRef, useState, type ReactNode } from 'react';

import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

import './AppShell.css';
import { useMediaQuery } from '@/shared/lib/hooks/useMediaQuery';

type Props = {
  children?: ReactNode;
  defaultCollapsed?: boolean;
};

export function AppShell(props: Props) {
  const { children, defaultCollapsed = false } = props;
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const isMobile = useMediaQuery('(max-width: 900px)');
  const desktopCollapsedRef = useRef<boolean | null>(null);

  useEffect(() => {
    if (isMobile) {
      desktopCollapsedRef.current = collapsed;
      setCollapsed(true); // mobile inicia encolhido (ícones visíveis)
      return;
    }
    if (desktopCollapsedRef.current != null) {
      setCollapsed(desktopCollapsedRef.current);
      desktopCollapsedRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMobile]);

  useEffect(() => {
    if (!isMobile) return;
    const expanded = !collapsed;
    document.body.style.overflow = expanded ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobile, collapsed]);

  return (
    <div
      className={[
        'sr-app-shell',
        !isMobile && collapsed ? 'is-collapsed' : '',
        isMobile ? 'is-mobile' : '',
        isMobile && !collapsed ? 'is-mobile-menu-open' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((v) => !v)}
      />
      <button
        type="button"
        className="sr-app-shell__backdrop"
        aria-label="Fechar menu"
        onClick={() => setCollapsed(true)}
      />
      <div className="sr-app-shell__main">
        <Topbar />
        <div className="sr-app-shell__content">{children}</div>
      </div>
    </div>
  );
}


