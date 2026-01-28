import toast, { ToastBar, Toaster } from 'react-hot-toast';

export function NotificationProvider() {
  return (
    <Toaster
      position="top-right"
      gutter={10}
      containerStyle={{
        top: 16,
        right: 16,
        bottom: 16,
        left: 16,
        zIndex: 10001,
        pointerEvents: 'none',
      }}
      toastOptions={{
        duration: 3600,
        style: {
          background: 'var(--sr-surface)',
          color: 'var(--sr-ink)',
          border: '1px solid rgba(var(--sr-accent-rgb), 0.18)',
          borderRadius: 14,
          padding: 12,
          boxShadow: 'var(--sr-elev-1)',
          maxWidth: 420,
        },
        success: {
          iconTheme: { primary: 'var(--sr-accent)', secondary: '#ffffff' },
        },
        error: {
          iconTheme: { primary: 'var(--danger)', secondary: '#ffffff' },
        },
      }}
    >
      {(t) => (
        <ToastBar toast={t}>
          {({ icon, message }) => (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, pointerEvents: 'auto' }}>
              <div style={{ display: 'grid', placeItems: 'center' }}>{icon}</div>
              <div style={{ flex: 1, fontSize: 13, fontWeight: 600, lineHeight: '18px' }}>{message}</div>
              <button
                type="button"
                aria-label="Fechar notificação"
                onClick={() => toast.dismiss(t.id)}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 10,
                  border: '1px solid var(--sr-border)',
                  background: 'var(--sr-surface)',
                  color: 'var(--sr-ink-muted)',
                  cursor: 'pointer',
                  fontSize: 16,
                  lineHeight: '26px',
                  fontWeight: 800,
                }}
              >
                ×
              </button>
            </div>
          )}
        </ToastBar>
      )}
    </Toaster>
  );
}


