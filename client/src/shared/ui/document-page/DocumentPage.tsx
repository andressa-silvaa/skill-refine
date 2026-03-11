import type { ReactNode } from 'react';

import { useTranslation } from 'react-i18next';

import './DocumentPage.css';

const LANG_OPTIONS = [
  { value: 'pt-BR', label: 'PT' },
  { value: 'en-US', label: 'EN' },
  { value: 'es-ES', label: 'ES' },
] as const;

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onBack?: () => void;
};

export function DocumentPage(props: Props) {
  const { title, subtitle, children, onBack } = props;
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language;

  return (
    <main className="document-page">
      <section className="document-card">
        <div className="document-header">
          {onBack && (
            <button type="button" className="document-back" onClick={onBack}>
              ‹ {t('legal.back')}
            </button>
          )}
          <div className="document-header-row">
            <div className="document-title-wrap">
              <h1 className="document-title">{title}</h1>
              {subtitle ? <p className="document-subtitle">{subtitle}</p> : null}
            </div>
            <div className="document-lang-switch" role="group" aria-label={t('legal.language')}>
              {LANG_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`document-lang-btn${currentLang === opt.value ? ' is-active' : ''}`}
                  onClick={() => void i18n.changeLanguage(opt.value)}
                  aria-pressed={currentLang === opt.value}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="document-body">{children}</div>
      </section>
    </main>
  );
}
