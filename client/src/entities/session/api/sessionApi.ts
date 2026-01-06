import { ApiError, apiRequest, clearAccessToken, setAccessToken } from '@/shared/api';

import type { SessionUser } from '../model/types';

type AuthResponse = { access_token: string; user: SessionUser };
type RefreshResponse = { access_token: string };
type MeResponse = { user: SessionUser };
type RegisterResponse = { user: SessionUser };

export const sessionApi = {
  async register(payload: { email: string; full_name: string; birth_date?: string | null; password: string }) {
    return apiRequest<RegisterResponse>('/accounts/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async login(payload: { email: string; password: string }) {
    const res = await apiRequest<AuthResponse>('/accounts/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setAccessToken(res.access_token);
    return res.user;
  },

  async loginGoogle(payload: { credential: string }) {
    const res = await apiRequest<AuthResponse>('/accounts/auth/google', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    setAccessToken(res.access_token);
    return res.user;
  },

  async refresh() {
    const res = await apiRequest<RefreshResponse>('/accounts/auth/refresh', { method: 'POST' });
    setAccessToken(res.access_token);
    return res.access_token;
  },

  async me() {
    try {
      const res = await apiRequest<MeResponse>('/accounts/auth/me', { method: 'GET' });
      return res.user;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        await sessionApi.refresh();
        const res = await apiRequest<MeResponse>('/accounts/auth/me', { method: 'GET' });
        return res.user;
      }
      throw e;
    }
  },

  async logout() {
    try {
      await apiRequest<void>('/accounts/auth/logout', { method: 'POST' });
    } finally {
      clearAccessToken();
    }
  },
};


