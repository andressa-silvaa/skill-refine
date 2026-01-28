import { cloneElement, isValidElement, useCallback, useEffect, useRef, useState, type ReactElement, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import './DropdownMenu.css';

export type DropdownItem = {
  key: string;
  label: string;
  iconClass?: string;
  danger?: boolean;
  onClick: () => void;
};

type Props = {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
};

export function DropdownMenu(props: Props) {
  const { trigger, items, align = 'right' } = props;
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const anchorRef = useRef<DOMRect | null>(null);

  useEffect(() => {
    if (!open) return;
    
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current || !menuRef.current) return;
      if (rootRef.current.contains(e.target as Node) || menuRef.current.contains(e.target as Node)) return;
      setOpen(false);
      setPosition(null);
      anchorRef.current = null;
    };
    
    window.addEventListener('pointerdown', onPointerDown);
    return () => window.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  const calculatePosition = useCallback(() => {
    if (!anchorRef.current || !menuRef.current) return;

    const anchor = anchorRef.current;
    const menu = menuRef.current;
    
    const menuRect = menu.getBoundingClientRect();
    
    if (menuRect.width === 0 || menuRect.height === 0 || menuRect.width > 1000 || menuRect.height > 1000) {
      setTimeout(() => calculatePosition(), 30);
      return;
    }

    const menuWidth = menuRect.width;
    const menuHeight = menuRect.height;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const padding = 8;

    let left = align === 'right' 
      ? anchor.right - menuWidth 
      : anchor.left;
    
    left = Math.max(padding, Math.min(left, viewportWidth - menuWidth - padding));

    let top: number;
    const spaceBelow = viewportHeight - anchor.bottom;
    
    if (spaceBelow >= menuHeight + padding) {
      top = anchor.bottom + padding;
    } else {
      top = anchor.top - menuHeight - padding;
      if (top < padding) {
        top = anchor.bottom + padding;
        menu.style.maxHeight = `${Math.max(100, spaceBelow - padding)}px`;
        menu.style.overflowY = 'auto';
      } else {
        menu.style.maxHeight = '';
        menu.style.overflowY = '';
      }
    }

    top = Math.max(padding, Math.min(top, viewportHeight - menuHeight - padding));
    left = Math.max(padding, Math.min(left, viewportWidth - menuWidth - padding));

    setPosition({ top, left });
  }, [align]);

  useEffect(() => {
    if (!open || !anchorRef.current) return;

    let retryCount = 0;
    const maxRetries = 5;
    
    const tryCalculate = () => {
      if (menuRef.current) {
        const menuRect = menuRef.current.getBoundingClientRect();
        if (menuRect.width > 0 && menuRect.height > 0 && menuRect.width < 1000) {
          calculatePosition();
        } else if (retryCount < maxRetries) {
          retryCount++;
          setTimeout(tryCalculate, 20);
        }
      }
    };

    setTimeout(tryCalculate, 10);

    const handleUpdate = () => {
      if (anchorRef.current && menuRef.current) {
        calculatePosition();
      }
    };
    
    window.addEventListener('resize', handleUpdate);

    return () => {
      window.removeEventListener('resize', handleUpdate);
    };
  }, [open, calculatePosition]);

  useEffect(() => {
    if (!open) return;

    const handleScroll = () => {
      setOpen(false);
      setPosition(null);
      anchorRef.current = null;
    };

    window.addEventListener('scroll', handleScroll, true);
    return () => window.removeEventListener('scroll', handleScroll, true);
  }, [open]);

  useEffect(() => {
    if (!open) {
      setPosition(null);
      anchorRef.current = null;
    }
  }, [open]);

  const handleTriggerClick = useCallback((e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation();
    
    const clickedElement = e.currentTarget;
    const rect = clickedElement.getBoundingClientRect();
    
    if (rect.width > 0 && rect.height > 0) {
      anchorRef.current = rect;
      setOpen((v) => !v);
    }
    
    if (isValidElement(trigger)) {
      const triggerEl = trigger as ReactElement<any>;
      const originalOnClick = triggerEl.props?.onClick;
      if (typeof originalOnClick === 'function') {
        originalOnClick(e);
      }
    }
  }, [trigger]);

  const triggerElement = isValidElement(trigger) 
    ? cloneElement(trigger as ReactElement<any>, {
        onClick: handleTriggerClick,
        'aria-haspopup': 'menu',
        'aria-expanded': open,
      })
    : trigger;

  const menuContent = open ? (
    <div
      ref={menuRef}
      className="sr-dd__menu sr-dd__menu--portal"
      style={{
        position: 'fixed',
        top: position ? `${position.top}px` : '-9999px',
        left: position ? `${position.left}px` : '-9999px',
        visibility: position ? 'visible' : 'hidden',
        opacity: position ? 1 : 0,
        transition: position ? 'opacity 0.12s ease' : 'none',
      }}
    >
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          className={`sr-dd__item${item.danger ? ' is-danger' : ''}`}
          onClick={() => {
            setOpen(false);
            setPosition(null);
            anchorRef.current = null;
            item.onClick();
          }}
        >
          {item.iconClass ? <i className={item.iconClass} aria-hidden /> : null}
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  ) : null;

  const portalRoot =
    typeof document !== 'undefined'
      ? document.querySelector('[data-sr-theme-scope]') ?? document.body
      : null;

  return (
    <div ref={rootRef} className="sr-dd">
      {triggerElement}
      {portalRoot && menuContent ? createPortal(menuContent, portalRoot) : null}
    </div>
  );
}
