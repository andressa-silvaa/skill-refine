import { BrowserRouter } from 'react-router-dom';

import { SessionProvider } from '@/entities/session';
import { NotificationProvider } from '@/shared/ui';

import { AppRouter } from './router';

export function App() {
  return (
    <SessionProvider>
      <NotificationProvider />
      <BrowserRouter>
        <div className="app-shell">
          <AppRouter />
        </div>
      </BrowserRouter>
    </SessionProvider>
  );
}


