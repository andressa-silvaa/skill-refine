type ScreenKey = 'curriculos' | 'version-history' | 'dashboard' | 'ai-analysis' | 'other';

type ScreenMetrics = {
  total: number;
  byPath: Record<string, number>;
};

type MetricsStore = Record<ScreenKey, ScreenMetrics>;

declare global {
  interface Window {
    __srRequestMetrics?: MetricsStore;
    __srPrintRequestMetrics?: () => void;
    __srResetRequestMetrics?: () => void;
  }
}

function detectScreen(): ScreenKey {
  const pathname = (window.location.pathname || '').toLowerCase();
  if (pathname.includes('/protected/resumes')) return 'curriculos';
  if (pathname.includes('/protected/version-history')) return 'version-history';
  if (pathname.includes('/protected/dashboard')) return 'dashboard';
  if (pathname.includes('/protected/ai-analysis')) return 'ai-analysis';
  return 'other';
}

function ensureStore(): MetricsStore {
  if (!window.__srRequestMetrics) {
    window.__srRequestMetrics = {
      curriculos: { total: 0, byPath: {} },
      'version-history': { total: 0, byPath: {} },
      dashboard: { total: 0, byPath: {} },
      'ai-analysis': { total: 0, byPath: {} },
      other: { total: 0, byPath: {} },
    };
    window.__srPrintRequestMetrics = () => {
      const snapshot = window.__srRequestMetrics;
      if (!snapshot) return;
      console.table(
        Object.entries(snapshot).map(([screen, value]) => ({
          screen,
          total: value.total,
        }))
      );
    };
    window.__srResetRequestMetrics = () => {
      window.__srRequestMetrics = undefined;
      ensureStore();
    };
  }
  return window.__srRequestMetrics;
}

export function trackApiRequest(path: string): void {
  if (process.env.NODE_ENV !== 'development') return;
  const store = ensureStore();
  const screen = detectScreen();
  const bucket = store[screen];
  bucket.total += 1;
  bucket.byPath[path] = (bucket.byPath[path] || 0) + 1;
}

export function getRequestMetricsSnapshot(): MetricsStore | null {
  if (process.env.NODE_ENV !== 'development') return null;
  return window.__srRequestMetrics || null;
}
