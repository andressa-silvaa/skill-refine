import { useState } from 'react';

import './PreferencesCard.css';

export function PreferencesCard() {
  const [emailNotifications, setEmailNotifications] = useState(true);

  return (
    <section className="sr-profile__card" aria-label="Preferências">
      <header className="sr-profile__card-header">
        <div>
          <h2 className="sr-profile__card-title">Preferências</h2>
          <div className="sr-profile__muted">Ajustes rápidos de comunicação.</div>
        </div>
      </header>

      <div className="sr-pref__row" aria-label="Notificações por e-mail">
        <div className="sr-pref__left">
          <span className="sr-pref__icon" aria-hidden>
            <i className="fa-fw fa-regular fa-envelope" />
          </span>
          <div className="sr-pref__text">
            <div className="sr-pref__label">Notificações por e-mail</div>
            <div className="sr-pref__desc">Receba avisos importantes e lembretes.</div>
          </div>
        </div>
        <button
          type="button"
          className={`sr-pref__switch${emailNotifications ? ' is-on' : ''}`}
          role="switch"
          aria-checked={emailNotifications}
          onClick={() => setEmailNotifications((v) => !v)}
        >
          <span className="sr-pref__thumb" aria-hidden />
        </button>
      </div>
    </section>
  );
}


