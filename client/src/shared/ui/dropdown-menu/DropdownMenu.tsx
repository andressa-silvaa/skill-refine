import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
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
  const [menuPosition, setMenuPosition] = useState<{ top?: number; left?: number; right?: number; bottom?: number } | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current || !menuRef.current) return;
      if (rootRef.current.contains(e.target as Node) || menuRef.current.contains(e.target as Node)) return;
      setOpen(false);
    };
    window.addEventListener('pointerdown', onPointerDown);
    return () => window.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  useEffect(() => {
    if (!open || !rootRef.current) {
      setMenuPosition(null);
      return;
    }

    const updatePosition = () => {
      const root = rootRef.current;
      if (!root) return;

      const rect = root.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const scrollY = window.scrollY;
      const scrollX = window.scrollX;

      // Set initial position immediately (below trigger, aligned to right)
      const initialTop = rect.bottom + scrollY + 8;
      const initialLeft = align === 'right' ? rect.right + scrollX - 180 : rect.left + scrollX;
      setMenuPosition({ top: initialTop, left: initialLeft });

      // Wait for menu to be rendered to get its dimensions, then adjust
      requestAnimationFrame(() => {
        if (!menuRef.current) return;
        const menu = menuRef.current;
        
        // Get menu dimensions
        const menuRect = menu.getBoundingClientRect();

        let left: number | undefined;
        let right: number | undefined;
        let top: number | undefined;
        let bottom: number | undefined;

        // Horizontal positioning
        if (align === 'right') {
          const spaceOnRight = viewportWidth - rect.right;
          const spaceOnLeft = rect.left;
          
          if (menuRect.width <= spaceOnRight) {
            // Enough space on right, align to right edge of trigger
            left = rect.right + scrollX - menuRect.width;
            right = undefined;
          } else if (menuRect.width <= spaceOnLeft) {
            // Not enough on right, but enough on left
            left = rect.left + scrollX - menuRect.width;
            right = undefined;
          } else {
            // Not enough space on either side, use viewport edges
            if (spaceOnRight >= spaceOnLeft) {
              left = viewportWidth + scrollX - menuRect.width - 8;
              right = undefined;
            } else {
              left = scrollX + 8;
              right = undefined;
            }
          }
        } else {
          // align === 'left'
          const spaceOnLeft = rect.left;
          const spaceOnRight = viewportWidth - rect.right;
          
          if (menuRect.width <= spaceOnLeft) {
            left = rect.left + scrollX - menuRect.width;
            right = undefined;
          } else if (menuRect.width <= spaceOnRight) {
            left = rect.right + scrollX;
            right = undefined;
          } else {
            if (spaceOnLeft >= spaceOnRight) {
              left = scrollX + 8;
              right = undefined;
            } else {
              left = viewportWidth + scrollX - menuRect.width - 8;
              right = undefined;
            }
          }
        }

        // Vertical positioning
        const spaceBelow = viewportHeight - rect.bottom;
        const spaceAbove = rect.top;
        const menuHeight = menuRect.height;

        if (menuHeight <= spaceBelow) {
          // Enough space below
          top = rect.bottom + scrollY + 8;
          bottom = undefined;
          menu.style.maxHeight = 'none';
          menu.style.overflowY = 'visible';
        } else if (menuHeight <= spaceAbove) {
          // Not enough below, but enough above
          top = undefined;
          bottom = viewportHeight - rect.top + scrollY + 8;
          menu.style.maxHeight = 'none';
          menu.style.overflowY = 'visible';
        } else {
          // Not enough space on either side, position to fit in viewport
          if (spaceBelow >= spaceAbove) {
            top = rect.bottom + scrollY + 8;
            bottom = undefined;
            menu.style.maxHeight = `${Math.max(100, spaceBelow - 16)}px`;
            menu.style.overflowY = 'auto';
          } else {
            top = undefined;
            bottom = viewportHeight - rect.top + scrollY + 8;
            menu.style.maxHeight = `${Math.max(100, spaceAbove - 16)}px`;
            menu.style.overflowY = 'auto';
          }
        }

        setMenuPosition({ top, left, right, bottom });
      });
    };

    // Initial position calculation
    updatePosition();

    // Update on scroll and resize
    const handleUpdate = () => updatePosition();
    window.addEventListener('resize', handleUpdate);
    window.addEventListener('scroll', handleUpdate, true);

    return () => {
      window.removeEventListener('resize', handleUpdate);
      window.removeEventListener('scroll', handleUpdate, true);
    };
  }, [open, align]);

  const itemNodes = useMemo(
    () =>
      items.map((item) => (
        <button
          key={item.key}
          type="button"
          className={`sr-dd__item${item.danger ? ' is-danger' : ''}`}
          onClick={() => {
            setOpen(false);
            item.onClick();
          }}
        >
          {item.iconClass ? <i className={item.iconClass} aria-hidden /> : null}
          <span>{item.label}</span>
        </button>
      )),
    [items]
  );

  const menuContent = open ? (
    <div
      ref={menuRef}
      className="sr-dd__menu sr-dd__menu--portal"
      style={{
        position: 'fixed',
        top: menuPosition?.top !== undefined ? `${menuPosition.top}px` : undefined,
        left: menuPosition?.left !== undefined ? `${menuPosition.left}px` : undefined,
        right: menuPosition?.right !== undefined ? `${menuPosition.right}px` : undefined,
        bottom: menuPosition?.bottom !== undefined ? `${menuPosition.bottom}px` : undefined,
      }}
    >
      {itemNodes}
    </div>
  ) : null;

  const portalRoot = typeof document !== 'undefined' ? (document.querySelector('[data-sr-theme-scope]') ?? document.body) : null;

  return (
    <div ref={rootRef} className="sr-dd">
      <button
        type="button"
        className="sr-dd__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {trigger}
      </button>
      {portalRoot && menuContent ? createPortal(menuContent, portalRoot) : null}
    </div>
  );
}
