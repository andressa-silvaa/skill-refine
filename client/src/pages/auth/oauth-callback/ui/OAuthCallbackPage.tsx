import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useSession, useSessionActions } from '@/entities/session';
import { notify } from '@/shared/lib/notify';

function getErrorMessage(oauthError: string | null, googleError: string | null): string {
  if (oauthError) {
    switch (oauthError) {
      case 'invalid_state':
        return 'Sessão do Google expirada. Tente novamente.';
      case 'token_exchange_failed':
        return 'Falha ao concluir login com Google. Tente novamente.';
      case 'missing_id_token':
        return 'Falha ao concluir login com Google. Tente novamente.';
      case 'google_token_invalid':
        return 'Não foi possível validar sua conta do Google. Tente novamente.';
      default:
        return 'Ocorreu um erro inesperado ao tentar entrar com o Google. Tente novamente.';
    }
  }

  if (googleError) {
    switch (googleError) {
      case 'access_denied':
        return 'Login com Google foi cancelado.';
      case 'popup_closed_by_user':
        return 'Login com Google foi cancelado.';
      default:
        return 'Ocorreu um erro inesperado ao tentar entrar com o Google. Tente novamente.';
    }
  }

  return 'Ocorreu um erro inesperado ao tentar entrar com o Google. Tente novamente.';
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
  const bootstrapAttemptedRef = useRef(false);
  const errorHandledRef = useRef(false);
  const [isBootstraping, setIsBootstraping] = useState(false);

  // Tratamento de erro explícito da URL
  useEffect(() => {
    if (!oauthError && !googleError) return;
    if (errorHandledRef.current) return;

    errorHandledRef.current = true;

    const errorDetails = {
      oauth_error: oauthError,
      google_error: googleError,
      google_error_description: googleErrorDescription,
      status,
    };

    console.error('Erro no login com Google', errorDetails);

    const errorMessage = getErrorMessage(oauthError, googleError);
    notify.error(errorMessage);

    navigate('/login', { replace: true });
  }, [oauthError, googleError, googleErrorDescription, status, navigate]);

  useEffect(() => {
    if (oauthError || googleError) return;
    if (bootstrapAttemptedRef.current) return;
    if (isBootstraping) return;

    bootstrapAttemptedRef.current = true;
    setIsBootstraping(true);

    void (async () => {
      try {
        await new Promise((resolve) => setTimeout(resolve, 100));
        await bootstrap({ force: true });
      } catch (error) {
        console.error('Erro no login com Google ao fazer bootstrap', error);
      } finally {
        setIsBootstraping(false);
      }
    })();
  }, [bootstrap, oauthError, googleError, isBootstraping]);

  useEffect(() => {
    if (oauthError || googleError) return;
    if (errorHandledRef.current) return;
    if (isBootstraping) return;

    if (session.status === 'authenticated') {
      navigate('/protected', { replace: true });
      return;
    }

    if (session.status === 'anonymous' && bootstrapAttemptedRef.current) {
      errorHandledRef.current = true;

      console.error('Erro no login com Google: Login concluído no Google, mas a sessão não foi criada.', {
        oauthError,
        googleError,
        status,
        bootstrapAttempted: bootstrapAttemptedRef.current,
      });

      notify.error('Não foi possível criar a sessão após o login com Google. Verifique se os cookies estão habilitados e tente novamente.');
      navigate('/login', { replace: true });
    }
  }, [navigate, oauthError, googleError, session.status, status, isBootstraping]);

  return null;
}


