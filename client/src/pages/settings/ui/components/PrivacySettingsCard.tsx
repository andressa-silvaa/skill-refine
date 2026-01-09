import './PrivacySettingsCard.css';

export function PrivacySettingsCard() {
  return (
    <section className="sr-settings__card" aria-label="Privacidade">
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-lock" aria-hidden /> Privacidade
          </h2>
          <div className="sr-settings__muted">Controle simples sobre dados e conta.</div>
        </div>
      </header>

      <div className="sr-privacy__panel" aria-label="Seus dados estão protegidos">
        <div className="sr-privacy__panel-title">Seus dados estão protegidos</div>
        <p className="sr-privacy__panel-text">
          Seus currículos e informações pessoais são armazenados de forma segura e não são compartilhados com terceiros sem sua autorização.
        </p>
      </div>

      <div className="sr-privacy__actions" aria-label="Ações de dados">
        <div className="sr-privacy__actions-title">Ações de dados</div>
        <div className="sr-privacy__links">
          <button type="button" className="sr-privacy__link" onClick={() => void 0}>
            Exportar meus dados
          </button>
          <span className="sr-privacy__dot" aria-hidden>
            •
          </span>
          <button type="button" className="sr-privacy__link sr-privacy__link--danger" onClick={() => void 0}>
            Excluir minha conta
          </button>
        </div>
      </div>
    </section>
  );
}


