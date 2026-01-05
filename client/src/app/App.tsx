import { BrowserRouter } from 'react-router-dom';

import { AppRouter } from './router';

export function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <AppRouter />
      </div>
    </BrowserRouter>
  );
}


