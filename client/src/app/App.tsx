import { BrowserRouter } from 'react-router-dom';

import { SessionProvider } from '@/entities/session';

import { AppRouter } from './router';

export function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <div className="app-shell">
          <AppRouter />
        </div>
      </BrowserRouter>
    </SessionProvider>
  );
}


