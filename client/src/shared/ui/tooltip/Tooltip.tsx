import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import './Tooltip.css';

type Props = {
  children: ReactNode;
  content: string;
  show?: boolean;
  align?: 'top' | 'bottom' | 'left' | 'right';
};

export function Tooltip(props: Props) {
  const { children, content, show = true, align = 'top' } = props;
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState<{ top?: number; left?: number; right?: number; bottom?: number } | null>(null);
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!visible || !triggerRef.current || !show) {
      setPosition(null);
      return;
    }

    const updatePosition = () => {
      const trigger = triggerRef.current;
      if (!trigger) return;

      const rect = trigger.getBoundingClientRect();
      const scrollY = window.scrollY;
      const scrollX = window.scrollX;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      // Set initial position immediately (rough estimate)
      let initialTop: number;
      let initialLeft: number;
      
      switch (align) {
        case 'top':
          initialTop = Math.max(scrollY + 8, rect.top + scrollY - 50);
          initialLeft = Math.max(scrollX + 8, rect.left + scrollX + rect.width / 2 - 100);
          break;
        case 'bottom':
          initialTop = rect.bottom + scrollY + 8;
          initialLeft = Math.max(scrollX + 8, rect.left + scrollX + rect.width / 2 - 100);
          break;
        case 'left':
          initialTop = Math.max(scrollY + 8, rect.top + scrollY + rect.height / 2 - 20);
          initialLeft = Math.max(scrollX + 8, rect.left + scrollX - 200);
          break;
        case 'right':
          initialTop = Math.max(scrollY + 8, rect.top + scrollY + rect.height / 2 - 20);
          initialLeft = Math.min(scrollX + viewportWidth - 220, rect.right + scrollX + 8);
          break;
        default:
          initialTop = Math.max(scrollY + 8, rect.top + scrollY - 50);
          initialLeft = Math.max(scrollX + 8, rect.left + scrollX + rect.width / 2 - 100);
      }
      
      // Ensure it's within viewport
      initialTop = Math.min(initialTop, scrollY + viewportHeight - 50);
      initialLeft = Math.min(initialLeft, scrollX + viewportWidth - 200);
      
      setPosition({ top: initialTop, left: initialLeft });

      requestAnimationFrame(() => {
        if (!tooltipRef.current) return;
        const tooltip = tooltipRef.current;
        const tooltipRect = tooltip.getBoundingClientRect();

        let top: number | undefined;
        let left: number | undefined;
        let right: number | undefined;
        let bottom: number | undefined;

        switch (align) {
          case 'top':
            top = rect.top + scrollY - tooltipRect.height - 8;
            left = rect.left + scrollX + rect.width / 2 - tooltipRect.width / 2;
            // Keep within viewport
            if (left < scrollX + 8) left = scrollX + 8;
            if (left + tooltipRect.width > scrollX + viewportWidth - 8) {
              left = scrollX + viewportWidth - tooltipRect.width - 8;
            }
            break;
          case 'bottom':
            top = rect.bottom + scrollY + 8;
            left = rect.left + scrollX + rect.width / 2 - tooltipRect.width / 2;
            // Keep within viewport
            if (left < scrollX + 8) left = scrollX + 8;
            if (left + tooltipRect.width > scrollX + viewportWidth - 8) {
              left = scrollX + viewportWidth - tooltipRect.width - 8;
            }
            break;
          case 'left':
            top = rect.top + scrollY + rect.height / 2 - tooltipRect.height / 2;
            left = rect.left + scrollX - tooltipRect.width - 8;
            // Keep within viewport
            if (top < scrollY + 8) top = scrollY + 8;
            if (top + tooltipRect.height > scrollY + viewportHeight - 8) {
              top = scrollY + viewportHeight - tooltipRect.height - 8;
            }
            break;
          case 'right':
            top = rect.top + scrollY + rect.height / 2 - tooltipRect.height / 2;
            left = rect.right + scrollX + 8;
            // Keep within viewport
            if (top < scrollY + 8) top = scrollY + 8;
            if (top + tooltipRect.height > scrollY + viewportHeight - 8) {
              top = scrollY + viewportHeight - tooltipRect.height - 8;
            }
            break;
        }

        setPosition({ top, left, right, bottom });
      });
    };

    updatePosition();

    const handleUpdate = () => updatePosition();
    window.addEventListener('resize', handleUpdate);
    window.addEventListener('scroll', handleUpdate, true);

    return () => {
      window.removeEventListener('resize', handleUpdate);
      window.removeEventListener('scroll', handleUpdate, true);
    };
  }, [visible, align, show]);

  if (!content) {
    return <>{children}</>;
  }

  const tooltipContent = visible && show ? (
    <div
      ref={tooltipRef}
      className={`sr-tooltip sr-tooltip--${align}`}
      style={{
        position: 'fixed',
        top: position?.top !== undefined ? `${position.top}px` : position === null ? '-9999px' : undefined,
        left: position?.left !== undefined ? `${position.left}px` : position === null ? '-9999px' : undefined,
        right: position?.right !== undefined ? `${position.right}px` : undefined,
        bottom: position?.bottom !== undefined ? `${position.bottom}px` : undefined,
        visibility: position ? 'visible' : 'hidden',
        opacity: position ? 1 : 0,
        pointerEvents: 'none',
      }}
    >
      {content}
    </div>
  ) : null;

  const portalRoot = typeof document !== 'undefined' ? (document.querySelector('[data-sr-theme-scope]') ?? document.body) : null;

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
      >
        {children}
      </div>
      {portalRoot && tooltipContent ? createPortal(tooltipContent, portalRoot) : null}
    </>
  );
}
