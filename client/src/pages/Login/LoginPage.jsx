import './LoginPage.css';

function LoginPage() {
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="card-content container-fluid">
          <div className="row g-0">
            <div className="content-col col-12 col-lg-7 d-flex flex-column gap-2">
              <div className="welcome">
                <p className="welcome-back">Bem-vindo de volta!</p>
                <h1 className="login-title">Log In</h1>
              </div>

              <div className="content-body d-flex flex-column flex-grow-1 justify-content-center align-items-center gap-3">
                <form className="form d-flex flex-column gap-3 w-100">
                  <label className="field">
                    <span className="field-label">E-mail</span>
                    <input
                      className="field-input form-control"
                      type="email"
                      placeholder="Digite seu email"
                    />
                  </label>

                  <label className="field">
                    <div className="field-row">
                      <span className="field-label">Senha</span>
                      <a className="forgot-link" href="#">
                        Esqueceu a senha?
                      </a>
                    </div>
                    <input
                      className="field-input form-control"
                      type="password"
                      placeholder="*****************"
                    />
                  </label>

                  <button className="submit-btn align-self-center" type="button">
                    <span>ENTRAR</span>
                    <span className="arrow">→</span>
                  </button>
                </form>

                <div className="divider align-self-center">
                  Ou continue com o Google
                </div>

                <button className="google-btn align-self-center" type="button">
                  <img src="/google.svg" alt="Google" />
                </button>

                <div className="footer text-center">
                  <span>Ainda não tem uma conta?</span>
                  <a className="signup-link" href="#">
                    Cadastre-se aqui
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="brand-tag">
          <span className="brand-skill">Skill</span>
          <span className="brand-refine">Refine</span>
        </div>

        <img
          className="girl-img"
          src="/Character-working-laptop-sitting-chair.svg"
          alt="Person using laptop"
        />
        <img className="cactus-img" src="/cactus.svg" alt="Cactus" />
      </div>
    </div>
  );
}

export default LoginPage;
