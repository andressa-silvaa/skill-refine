import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { useTranslation } from 'react-i18next';

import './ScoreExplanationPopover.css';

type Props = {
  /** Texto do link que abre o popover (ex.: "Como calculamos?") */
  triggerLabel: string;
};

const FACTORS_KEYS = [
  'analysis.factorAts',
  'analysis.factorClarity',
  'analysis.factorStructure',
  'analysis.factorDensity',
  'analysis.factorKeywords',
] as const;

export function ScoreExplanationPopover(props: Props) {
  const { triggerLabel } = props;
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const factors = FACTORS_KEYS.map((key) => t(key));
  const title = t('analysis.howWeCalculate');

  const close = useCallback(() => setOpen(false), []);

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
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, close]);

  const triggerRect = triggerRef.current?.getBoundingClientRect();
  const portalRoot = typeof document !== 'undefined' ? (document.querySelector('[data-sr-theme-scope]') ?? document.body) : null;

  const panel = open && portalRoot ? (
    <div
      ref={panelRef}
      className="sr-score-explanation-popover"
      role="dialog"
      aria-label={triggerLabel}
      style={{
        position: 'fixed',
        top: triggerRect ? triggerRect.bottom + 8 : 0,
        left: triggerRect ? triggerRect.left : 0,
        zIndex: 1100,
      }}
    >
      <p className="sr-score-explanation-popover__title">{title}</p>
      <ul className="sr-score-explanation-popover__list">
        {factors.map((label, idx) => (
          <li key={idx}>{label}</li>
        ))}
      </ul>
    </div>
  ) : null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="sr-score-explanation-popover__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        {triggerLabel}
      </button>
      {panel && portalRoot ? createPortal(panel, portalRoot) : null}
    </>
  );
}
