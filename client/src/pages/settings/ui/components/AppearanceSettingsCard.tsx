import { useState } from 'react';

import './AppearanceSettingsCard.css';

type Theme = 'light' | 'dark';

export function AppearanceSettingsCard() {
  const [theme, setTheme] = useState<Theme>('light');

  return (
    <section className="sr-settings__card" aria-label="Aparência">
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-palette" aria-hidden /> Aparência
          </h2>
          <div className="sr-settings__muted">Apenas visual (não aplica tema real).</div>
        </div>
      </header>

      <div className="sr-appearance">
        <div className="sr-appearance__label">Tema</div>
        <div className="sr-appearance__grid" role="group" aria-label="Selecionar tema">
          <button
            type="button"
            className={`sr-appearance__option${theme === 'light' ? ' is-active' : ''}`}
            onClick={() => setTheme('light')}
          >
            <i className="fa-regular fa-sun" aria-hidden />
            <span>Claro</span>
          </button>
          <button
            type="button"
            className={`sr-appearance__option${theme === 'dark' ? ' is-active' : ''}`}
            onClick={() => setTheme('dark')}
          >
            <i className="fa-regular fa-moon" aria-hidden />
            <span>Escuro</span>
          </button>
        </div>
      </div>
    </section>
  );
}


