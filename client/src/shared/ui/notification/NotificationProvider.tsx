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
        pointerEvents: 'none',
      }}
      toastOptions={{
        duration: 3600,
        style: {
          background: '#ffffff',
          color: '#1e1a1d',
          border: '1px solid #f1c3ea',
          borderRadius: 14,
          padding: 12,
          boxShadow: '0 14px 32px rgba(0,0,0,0.14)',
          maxWidth: 420,
        },
        success: {
          iconTheme: { primary: '#c72cb8', secondary: '#ffffff' },
        },
        error: {
          iconTheme: { primary: '#9a1b1b', secondary: '#ffffff' },
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
                  border: '1px solid #f1c3ea',
                  background: '#ffffff',
                  color: '#775f73',
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


