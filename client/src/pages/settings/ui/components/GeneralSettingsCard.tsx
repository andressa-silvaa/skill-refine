import { useState } from 'react';

import './GeneralSettingsCard.css';

export function GeneralSettingsCard() {
  const [language, setLanguage] = useState('pt-BR');
  const [region, setRegion] = useState('BR');

  return (
    <section className="sr-settings__card" aria-label="Configurações gerais">
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
          <select className="sr-input" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="pt-BR">Português (Brasil)</option>
            <option value="en-US">English (US)</option>
            <option value="es-ES">Español</option>
          </select>
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


