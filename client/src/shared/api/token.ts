const STORAGE_KEY = 'sr_access_token';

function readStored(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

let accessToken: string | null = readStored();

export function setAccessToken(token: string) {
  accessToken = token;
  try {
    sessionStorage.setItem(STORAGE_KEY, token);
  } catch {
    /* private mode / quota */
  }
}

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = null;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
