import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useSession, useSessionActions } from '@/entities/session';

function errorMessage(code: string) {
  switch (code) {
    case 'invalid_state':
      return 'Sessão do Google expirada. Tente novamente.';
    case 'token_exchange_failed':
      return 'Falha ao concluir login com Google. Tente novamente.';
    case 'missing_id_token':
      return 'Falha ao concluir login com Google. Tente novamente.';
    case 'google_token_invalid':
      return 'Não foi possível validar sua conta do Google.';
    default:
      return 'Não foi possível concluir o login com Google.';
  }
}

export function OAuthCallbackPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const oauthError = params.get('oauth_error');
  const googleError = params.get('google_error');
  const googleErrorDescription = params.get('google_error_description');
  const status = params.get('status');

  const session = useSession();
  const { bootstrap } = useSessionActions();

  const [localError, setLocalError] = useState<string | null>(null);

  const msg = useMemo(() => (oauthError ? errorMessage(oauthError) : null), [oauthError]);

  useEffect(() => {
    if (oauthError) return;
    void (async () => {
      try {
        await bootstrap({ force: true });
      } catch {
      }
    })();
  }, [bootstrap, oauthError]);

  useEffect(() => {
    if (oauthError) return;
    if (session.status === 'authenticated') navigate('/protected', { replace: true });
    if (session.status === 'anonymous') {
      setLocalError('Login concluído no Google, mas a sessão não foi criada. Verifique cookies e URL do backend.');
    }
  }, [navigate, oauthError, session.status]);

  return (
    <main style={{ padding: 24 }}>
      <h2>Concluindo login…</h2>
      {msg ? <p>{msg}</p> : null}
      {oauthError ? (
        <pre style={{ background: '#f6f6f6', padding: 12, borderRadius: 8 }}>
          {JSON.stringify(
            {
              oauth_error: oauthError,
              status,
              google_error: googleError,
              google_error_description: googleErrorDescription,
            },
            null,
            2
          )}
        </pre>
      ) : null}
      {localError ? <p>{localError}</p> : null}

      <button type="button" onClick={() => navigate('/login', { replace: true })}>
        Voltar para login
      </button>
    </main>
  );
}


