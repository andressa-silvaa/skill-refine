import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import '@/app/styles';
import { App } from '@/app';
import { reportWebVitals } from '@/shared/lib/performance';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element #root not found');
}

const root = createRoot(rootElement);
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);

reportWebVitals();


