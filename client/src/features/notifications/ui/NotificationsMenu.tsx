import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { IconButton } from '@/shared/ui';

import type { NotificationItem } from '../api/notificationsApi';
import { useNotifications } from '../model/useNotifications';

import './NotificationsMenu.css';

type Props = {
  onOpenChange?: (open: boolean) => void;
};

const NOTIFICATION_TYPE_ICON: Record<string, string> = {
  analysis_done: 'fa-solid fa-circle-check',
  analysis_failed: 'fa-solid fa-circle-exclamation',
  pdf_ready: 'fa-solid fa-file-pdf',
  pdf_failed: 'fa-solid fa-file-circle-xmark',
  version_restored: 'fa-solid fa-clock-rotate-left',
  system: 'fa-solid fa-bell',
};

export function NotificationsMenu(props: Props) {
  const { onOpenChange } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const {
    items,
    unreadCount,
    loading,
    error,
    fetchList,
    fetchUnreadCount,
    markRead,
    markAllRead,
    deleteOne,
    clearAll,
  } = useNotifications();

  const close = useCallback(() => {
    setOpen(false);
    onOpenChange?.(false);
  }, [onOpenChange]);

  const openPanel = useCallback(() => {
    setOpen(true);
    onOpenChange?.(true);
    fetchList();
    fetchUnreadCount(true);
  }, [fetchList, fetchUnreadCount, onOpenChange]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        panelRef.current?.contains(e.target as Node) ||
        triggerRef.current?.contains(e.target as Node)
      ) {
        return;
      }
      close();
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('pointerdown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('pointerdown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, close]);

  const handleItemClick = useCallback(
    (n: NotificationItem) => {
      if (!n.isRead) markRead(n.id);
      close();
      if (n.actionUrl) navigate(n.actionUrl);
    },
    [markRead, close, navigate]
  );

  const handleDeleteOne = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      deleteOne(id);
    },
    [deleteOne]
  );

  const triggerRect = triggerRef.current?.getBoundingClientRect();
  const portalRoot =
    typeof document !== 'undefined'
      ? document.querySelector('[data-sr-theme-scope]') ?? document.body
      : null;

  const hasActions = unreadCount > 0 || items.length > 0;

  const viewportMargin = 16;
  const panelWidth = typeof window !== 'undefined' ? Math.min(360, window.innerWidth - viewportMargin * 2) : 360;
  const panelRight = triggerRect
    ? Math.max(
        viewportMargin,
        Math.min(window.innerWidth - triggerRect.right, window.innerWidth - panelWidth - viewportMargin)
      )
    : viewportMargin;

  const panel = open && portalRoot ? (
    <div
      ref={panelRef}
      className="sr-notifications-menu"
      role="dialog"
      aria-label={t('nav.notifications')}
      aria-modal="true"
      style={{
        position: 'fixed',
        top: triggerRect ? triggerRect.bottom + 8 : 0,
        right: panelRight,
        left: 'auto',
        width: panelWidth,
        zIndex: 99999,
      }}
    >
      <div className="sr-notifications-menu__header">
        <h3 className="sr-notifications-menu__title">{t('nav.notifications')}</h3>
        {hasActions && (
          <div className="sr-notifications-menu__actions">
            {unreadCount > 0 && (
              <button
                type="button"
                className="sr-notifications-menu__btn sr-notifications-menu__btn--accent"
                onClick={markAllRead}
              >
                {t('notifications.markAllRead')}
              </button>
            )}
            {items.length > 0 && (
              <button
                type="button"
                className="sr-notifications-menu__btn sr-notifications-menu__btn--muted"
                onClick={clearAll}
              >
                {t('notifications.clearAll')}
              </button>
            )}
          </div>
        )}
      </div>
      <div className="sr-notifications-menu__body">
        {loading && (
          <div className="sr-notifications-menu__state" role="status">
            <span className="sr-notifications-menu__spinner" aria-hidden />
            {t('notifications.loading')}
          </div>
        )}
        {error && !loading && (
          <div className="sr-notifications-menu__state sr-notifications-menu__state--error">
            {t('notifications.error')}
          </div>
        )}
        {!loading && !error && items.length === 0 && (
          <div className="sr-notifications-menu__empty">
            <i className="fa-regular fa-bell" aria-hidden />
            <p>{t('notifications.empty')}</p>
          </div>
        )}
        {!loading && !error && items.length > 0 && (
          <ul className="sr-notifications-menu__list">
            {items.map((n) => (
              <NotificationItemRow
                key={n.id}
                item={n}
                onClick={() => handleItemClick(n)}
                onDelete={(e) => handleDeleteOne(e, n.id)}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  ) : null;

  return (
    <>
      <div ref={triggerRef} style={{ display: 'inline-flex' }}>
        <IconButton
          aria-label={t('nav.notifications')}
          aria-expanded={open}
          aria-haspopup="dialog"
          className={`sr-topbar__icon-btn${unreadCount > 0 ? ' sr-topbar__icon-btn--badge' : ''}`}
          onClick={() => (open ? close() : openPanel())}
        >
          <i className="fa-regular fa-bell" aria-hidden />
          {unreadCount > 0 && (
            <span
              className="sr-topbar__badge sr-topbar__badge--danger sr-notifications-menu__badge"
              aria-hidden
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </IconButton>
      </div>
      {panel && portalRoot ? createPortal(panel, portalRoot) : null}
    </>
  );
}

function NotificationItemRow({
  item,
  onClick,
  onDelete,
}: {
  item: NotificationItem;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}) {
  const { t } = useTranslation();
  const title = t(item.titleKey, item.params);
  const iconClass = NOTIFICATION_TYPE_ICON[item.type] ?? 'fa-solid fa-bell';
  const typeMod = item.type.replace('_', '-');
  return (
    <li>
      <article
        className={`sr-notif-item sr-notif-item--${typeMod}${item.isRead ? ' is-read' : ''}`}
      >
        <button
          type="button"
          className="sr-notif-item__main"
          onClick={onClick}
        >
          <span className={`sr-notif-item__icon sr-notif-item__icon--${typeMod}`} aria-hidden>
            <i className={iconClass} />
          </span>
          <span className="sr-notif-item__text">{title}</span>
        </button>
        <button
          type="button"
          className="sr-notif-item__dismiss"
          onClick={onDelete}
          aria-label={t('common.close')}
        >
          <i className="fa-solid fa-xmark" aria-hidden />
        </button>
      </article>
    </li>
  );
}
