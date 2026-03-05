import { BrowserRouter } from 'react-router-dom';

import { SessionProvider } from '@/entities/session';
import { useBrowserBranding } from '@/shared/lib/browser';
import { NotificationProvider } from '@/shared/ui';

import { AppRouter } from './router';

function BrowserBrandingController() {
  useBrowserBranding();
  return null;
}

export function App() {
  return (
    <SessionProvider>
      <NotificationProvider />
      <BrowserRouter>
        <BrowserBrandingController />
        <div className="app-shell">
          <AppRouter />
        </div>
      </BrowserRouter>
    </SessionProvider>
  );
}


