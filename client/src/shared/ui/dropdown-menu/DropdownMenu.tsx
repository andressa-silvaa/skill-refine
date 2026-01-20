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

  // Close menu on outside click
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

  // Calculate position based on anchor
  const calculatePosition = useCallback(() => {
    if (!anchorRef.current || !menuRef.current) return;

    const anchor = anchorRef.current;
    const menu = menuRef.current;
    
    // Get actual menu dimensions from DOM
    const menuRect = menu.getBoundingClientRect();
    
    // Safety: if menu has invalid dimensions, skip calculation
    if (menuRect.width === 0 || menuRect.height === 0 || menuRect.width > 1000 || menuRect.height > 1000) {
      // Retry after a delay
      setTimeout(() => calculatePosition(), 30);
      return;
    }

    const menuWidth = menuRect.width;
    const menuHeight = menuRect.height;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const padding = 8;

    // Horizontal: align to right edge of anchor, but clamp to viewport
    let left = align === 'right' 
      ? anchor.right - menuWidth 
      : anchor.left;
    
    left = Math.max(padding, Math.min(left, viewportWidth - menuWidth - padding));

    // Vertical: prefer below, but go above if no space
    let top: number;
    const spaceBelow = viewportHeight - anchor.bottom;
    
    if (spaceBelow >= menuHeight + padding) {
      // Enough space below
      top = anchor.bottom + padding;
    } else {
      // Try above
      top = anchor.top - menuHeight - padding;
      // If not enough space above either, go below anyway and scroll
      if (top < padding) {
        top = anchor.bottom + padding;
        menu.style.maxHeight = `${Math.max(100, spaceBelow - padding)}px`;
        menu.style.overflowY = 'auto';
      } else {
        menu.style.maxHeight = '';
        menu.style.overflowY = '';
      }
    }

    // Final clamp
    top = Math.max(padding, Math.min(top, viewportHeight - menuHeight - padding));
    left = Math.max(padding, Math.min(left, viewportWidth - menuWidth - padding));

    setPosition({ top, left });
  }, [align]);

  // Update position when menu opens or on scroll/resize
  useEffect(() => {
    if (!open || !anchorRef.current) return;

    // Initial calculation with multiple retries
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

    // Start calculation after menu is in DOM
    setTimeout(tryCalculate, 10);

    // Update on scroll and resize
    const handleUpdate = () => {
      if (anchorRef.current && menuRef.current) {
        calculatePosition();
      }
    };
    
    window.addEventListener('resize', handleUpdate);
    window.addEventListener('scroll', handleUpdate, true);

    return () => {
      window.removeEventListener('resize', handleUpdate);
      window.removeEventListener('scroll', handleUpdate, true);
    };
  }, [open, calculatePosition]);

  // Reset when closing
  useEffect(() => {
    if (!open) {
      setPosition(null);
      anchorRef.current = null;
    }
  }, [open]);

  // Handle trigger click - capture position
  const handleTriggerClick = useCallback((e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation();
    
    const clickedElement = e.currentTarget;
    const rect = clickedElement.getBoundingClientRect();
    
    // Validate rect
    if (rect.width > 0 && rect.height > 0) {
      anchorRef.current = rect;
      setOpen((v) => !v);
    }
    
    // Call original onClick if exists
    if (isValidElement(trigger)) {
      const triggerEl = trigger as ReactElement<any>;
      const originalOnClick = triggerEl.props?.onClick;
      if (typeof originalOnClick === 'function') {
        originalOnClick(e);
      }
    }
  }, [trigger]);

  // Clone trigger and inject handler
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

  return (
    <div ref={rootRef} className="sr-dd">
      {triggerElement}
      {typeof document !== 'undefined' && menuContent 
        ? createPortal(menuContent, document.body) 
        : null}
    </div>
  );
}
