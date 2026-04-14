import { ApiError, clearAccessToken, setAccessToken } from '@/shared/api';

import { clearHasRefreshCookieHint, setHasRefreshCookieHint } from '../lib/refreshFlag';
import { authApi } from './authApi';

export const sessionApi = {
  async register(payload: { email: string; full_name: string; birth_date?: string | null; password: string }) {
    return authApi.register(payload);
  },

  async login(payload: { email: string; password: string }) {
    const res = await authApi.login(payload);
    setAccessToken(res.access_token);
    setHasRefreshCookieHint();
    return res.user;
  },

  async loginGoogle(payload: { credential: string }) {
    const res = await authApi.loginGoogle(payload);
    setAccessToken(res.access_token);
    setHasRefreshCookieHint();
    return res.user;
  },

  async refresh() {
    try {
      const res = await authApi.refresh();
      setAccessToken(res.access_token);
      setHasRefreshCookieHint();
      return res.access_token;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        clearAccessToken();
        clearHasRefreshCookieHint();
      }
      throw e;
    }
  },

  async me() {
    try {
      const res = await authApi.me();
      return res.user;
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        await sessionApi.refresh();
        const res = await authApi.me();
        return res.user;
      }
      throw e;
    }
  },

  async logout() {
    try {
      await authApi.logout();
    } finally {
      clearAccessToken();
      clearHasRefreshCookieHint();
    }
  },
};


