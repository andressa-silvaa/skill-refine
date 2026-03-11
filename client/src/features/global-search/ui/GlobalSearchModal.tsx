import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { useModalEffects } from '@/shared/lib/hooks/useModalEffects';

import { useGlobalSearch } from '../model/useGlobalSearch';
import { SearchResultItem } from './SearchResultItem';

import './GlobalSearchModal.css';

type Props = {
  trigger: ReactNode;
};

export function GlobalSearchModal(props: Props) {
  const { trigger } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const { query, setQuery, items, loading, error } = useGlobalSearch();

  useModalEffects({ open, onClose: () => setOpen(false) });

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open, setQuery]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [items, query]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, items.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === 'Enter' && items[selectedIndex]) {
        e.preventDefault();
        const item = items[selectedIndex];
        setOpen(false);
        if (item?.url) navigate(item.url);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, items, selectedIndex, navigate]);

  const handleSelect = useCallback(
    (url: string) => {
      setOpen(false);
      if (url) navigate(url);
    },
    [navigate]
  );

  const portalRoot =
    typeof document !== 'undefined'
      ? document.querySelector('[data-sr-theme-scope]') ?? document.body
      : null;

  const modal = open && portalRoot ? (
    <div
      className="sr-global-search-modal"
      role="dialog"
      aria-modal="true"
      aria-label={t('nav.search')}
    >
      <button
        type="button"
        className="sr-global-search-modal__backdrop"
        aria-label={t('common.close')}
        onClick={() => setOpen(false)}
      />
      <div className="sr-global-search-modal__panel">
        <div className="sr-global-search-modal__input-wrap">
          <i className="fa-solid fa-magnifying-glass sr-global-search-modal__icon" aria-hidden />
          <input
            ref={inputRef}
            type="search"
            className="sr-global-search-modal__input"
            placeholder={t('search.placeholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            aria-label={t('search.placeholder')}
          />
        </div>
        <div ref={listRef} className="sr-global-search-modal__results">
          {loading && (
            <div className="sr-global-search-modal__state">{t('search.loading')}</div>
          )}
          {error && !loading && (
            <div className="sr-global-search-modal__state sr-global-search-modal__state--error">
              {t('search.error')}
            </div>
          )}
          {!loading && !error && query.trim() && items.length === 0 && (
            <div className="sr-global-search-modal__state">{t('search.empty')}</div>
          )}
          {!loading && !error && items.length > 0 && (
            <div className="sr-global-search-modal__list" role="listbox">
              {items.map((item, idx) => (
                <div key={`${item.type}-${item.id}`} role="option" aria-selected={idx === selectedIndex}>
                  <SearchResultItem
                    item={item}
                    isSelected={idx === selectedIndex}
                    onClick={() => handleSelect(item.url)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  ) : null;

  return (
    <>
      <div onClick={() => setOpen(true)} style={{ display: 'inline-flex' }}>
        {trigger}
      </div>
      {modal && portalRoot ? createPortal(modal, portalRoot) : null}
    </>
  );
}
