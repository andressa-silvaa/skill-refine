type GoogleAccounts = {
  id: {
    initialize: (opts: {
      client_id: string;
      callback: (resp: { credential?: string }) => void;
    }) => void;
    prompt: (momentListener?: (notification: unknown) => void) => void;
  };
};

declare global {
  interface Window {
    google?: { accounts: GoogleAccounts };
  }
}

function loadScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-google-gsi]');
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => reject(new Error('Falha ao carregar Google SDK')));
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.dataset.googleGsi = '1';
    script.onload = () => {
      if (!window.google?.accounts?.id) {
        reject(new Error('Google SDK carregou, mas não inicializou'));
        return;
      }
      resolve();
    };
    script.onerror = () => reject(new Error('Falha ao carregar Google SDK'));
    document.head.appendChild(script);
  });
}

export async function googleOneTapGetCredential(clientId: string): Promise<string> {
  if (!clientId) throw new Error('Google Client ID não configurado');

  await loadScript();

  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => reject(new Error('Google login cancelado')), 60_000);

    window.google?.accounts?.id.initialize({
      client_id: clientId,
      callback: (resp) => {
        if (resp.credential) {
          window.clearTimeout(timeout);
          resolve(resp.credential);
          return;
        }
        window.clearTimeout(timeout);
        reject(new Error('Credencial do Google não recebida'));
      },
    });

    window.google?.accounts?.id.prompt();
  });
}


