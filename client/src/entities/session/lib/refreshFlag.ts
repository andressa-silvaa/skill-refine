const KEY = 'sr_has_refresh';

function safeGetStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function getHasRefreshCookieHint(): boolean {
  const storage = safeGetStorage();
  if (!storage) return false;
  return storage.getItem(KEY) === '1';
}

export function setHasRefreshCookieHint(): void {
  const storage = safeGetStorage();
  if (!storage) return;
  storage.setItem(KEY, '1');
}

export function clearHasRefreshCookieHint(): void {
  const storage = safeGetStorage();
  if (!storage) return;
  storage.removeItem(KEY);
}


