import { apiRequest } from '@/shared/api';

import type { SessionUser } from '../model/types';

type AuthResponse = { access_token: string; user: SessionUser };
type RefreshResponse = { access_token: string };
type MeResponse = { user: SessionUser };
type RegisterResponse = { user: SessionUser; email_confirmation_sent?: boolean };

export const authApi = {
  register(payload: { email: string; full_name: string; birth_date?: string | null; password: string }) {
    return apiRequest<RegisterResponse>('/accounts/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  login(payload: { email: string; password: string }) {
    return apiRequest<AuthResponse>('/accounts/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  loginGoogle(payload: { credential: string }) {
    return apiRequest<AuthResponse>('/accounts/auth/google', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  refresh() {
    return apiRequest<RefreshResponse>('/accounts/auth/refresh', { method: 'POST' });
  },

  me() {
    return apiRequest<MeResponse>('/accounts/auth/me', { method: 'GET' });
  },

  logout() {
    return apiRequest<void>('/accounts/auth/logout', { method: 'POST' });
  },
};


