import { apiRequest } from '@/shared/api';

export const passwordRecoveryApi = {
  requestReset(payload: { email: string }) {
    return apiRequest<{ status: 'ok' }>('/accounts/auth/password-reset/request', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  verifyCode(payload: { email: string; code: string }) {
    return apiRequest<{ reset_token: string }>('/accounts/auth/password-reset/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  confirmNewPassword(payload: { email: string; reset_token: string; new_password: string }) {
    return apiRequest<{ status: 'ok' }>('/accounts/auth/password-reset/confirm', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};


