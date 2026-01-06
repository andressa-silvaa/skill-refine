import { useNavigate } from 'react-router-dom';

import { useSession, useSessionActions } from '@/entities/session';

export function ProtectedPage() {
  const navigate = useNavigate();
  const session = useSession();
  const { logout } = useSessionActions();

  return (
    <main style={{ padding: 24 }}>
      <h2>Área protegida</h2>
      <p>Você está autenticado.</p>
      <pre style={{ background: '#f6f6f6', padding: 12, borderRadius: 8 }}>{JSON.stringify(session.user, null, 2)}</pre>

      <div style={{ display: 'flex', gap: 12 }}>
        <button
          type="button"
          onClick={async () => {
            await logout();
            navigate('/login');
          }}
        >
          Sair
        </button>
      </div>
    </main>
  );
}


