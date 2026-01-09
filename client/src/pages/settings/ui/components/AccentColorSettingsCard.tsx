import { useState } from 'react';

import './AccentColorSettingsCard.css';

type Accent = {
  key: string;
  label: string;
  color: string;
};

const accents: Accent[] = [
  { key: 'pink', label: 'Rosa', color: '#c72cb8' },
  { key: 'purple', label: 'Roxo', color: '#8b2e80' },
  { key: 'blue', label: 'Azul', color: '#2f6feb' },
  { key: 'green', label: 'Verde', color: '#2bbf5a' },
  { key: 'orange', label: 'Laranja', color: '#ff7a18' },
];

export function AccentColorSettingsCard() {
  const [selected, setSelected] = useState<string>('pink');

  return (
    <section className="sr-settings__card" aria-label="Cor de destaque">
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-regular fa-star" aria-hidden /> Cor de destaque
          </h2>
          <div className="sr-settings__muted">Apenas visual (não aplica tema real).</div>
        </div>
      </header>

      <div className="sr-accent" role="list" aria-label="Selecionar cor de destaque">
        {accents.map((a) => {
          const isActive = selected === a.key;
          return (
            <button
              key={a.key}
              type="button"
              className={`sr-accent__dot${isActive ? ' is-active' : ''}`}
              style={{ background: a.color }}
              aria-label={a.label}
              aria-pressed={isActive}
              onClick={() => setSelected(a.key)}
            >
              {isActive ? <i className="fa-solid fa-check" aria-hidden /> : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}


