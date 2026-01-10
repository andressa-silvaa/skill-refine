import { useEffect, useId, useMemo, useRef, useState } from 'react';

import './GeneralSettingsCard.css';

type Option = { value: string; label: string };

export function GeneralSettingsCard() {
  const languageOptions = useMemo<Option[]>(
    () => [
      { value: 'pt-BR', label: 'Português (Brasil)' },
      { value: 'en-US', label: 'English (US)' },
      { value: 'es-ES', label: 'Español' },
    ],
    []
  );

  const [language, setLanguage] = useState('pt-BR');
  const [region, setRegion] = useState('BR');

  const languageId = useId();
  const langWrapRef = useRef<HTMLDivElement | null>(null);
  const [langOpen, setLangOpen] = useState(false);
  const [langActiveIndex, setLangActiveIndex] = useState(0);

  const languageLabel = useMemo(() => {
    return languageOptions.find((o) => o.value === language)?.label ?? 'Selecionar';
  }, [language, languageOptions]);

  useEffect(() => {
    if (!langOpen) return;
    const onDown = (e: MouseEvent) => {
      const el = langWrapRef.current;
      if (!el) return;
      if (e.target instanceof Node && el.contains(e.target)) return;
      setLangOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [langOpen]);

  useEffect(() => {
    if (!langOpen) return;
    const idx = Math.max(0, languageOptions.findIndex((o) => o.value === language));
    setLangActiveIndex(idx);
  }, [langOpen, language, languageOptions]);

  return (
    <section className="sr-settings__card" aria-label="Configurações gerais" data-lang-open={langOpen ? 'true' : undefined}>
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-gear" aria-hidden /> Geral
          </h2>
          <div className="sr-settings__muted">Preferências principais da sua conta.</div>
        </div>
      </header>

      <div className="sr-settings-general__grid">
        <label className="sr-field">
          <span className="sr-label">Idioma</span>
          <div ref={langWrapRef} className="sr-settings-general__select">
            <button
              type="button"
              className="sr-input sr-settings-general__select-trigger"
              aria-haspopup="listbox"
              aria-expanded={langOpen}
              aria-controls={languageId}
              onClick={() => setLangOpen((v) => !v)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setLangOpen(false);
                  return;
                }
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setLangOpen(true);
                  return;
                }
                if (e.key === 'ArrowDown') {
                  e.preventDefault();
                  setLangOpen(true);
                  setLangActiveIndex((i) => Math.min(languageOptions.length - 1, i + 1));
                  return;
                }
                if (e.key === 'ArrowUp') {
                  e.preventDefault();
                  setLangOpen(true);
                  setLangActiveIndex((i) => Math.max(0, i - 1));
                }
              }}
            >
              <span className="sr-settings-general__select-value">{languageLabel}</span>
              <span className="sr-settings-general__select-caret" aria-hidden />
            </button>

            {langOpen ? (
              <div className="sr-settings-general__select-menu" role="listbox" id={languageId} aria-label="Selecionar idioma">
                {languageOptions.map((opt, idx) => {
                  const selected = opt.value === language;
                  const active = idx === langActiveIndex;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      role="option"
                      aria-selected={selected}
                      className={`sr-settings-general__select-option${selected ? ' is-selected' : ''}${active ? ' is-active' : ''}`}
                      onMouseEnter={() => setLangActiveIndex(idx)}
                      onClick={() => {
                        setLanguage(opt.value);
                        setLangOpen(false);
                      }}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
          <span className="sr-settings-general__hint">Essa configuração afeta apenas a interface do sistema.</span>
        </label>

        <label className="sr-field">
          <span className="sr-label">Região (visual)</span>
          <select className="sr-input" value={region} onChange={(e) => setRegion(e.target.value)} disabled>
            <option value="BR">Brasil</option>
          </select>
          <span className="sr-settings-general__hint">Opção reservada para futuras integrações.</span>
        </label>
      </div>
    </section>
  );
}


