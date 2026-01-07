import { apiRequest } from '@/shared/api';

export const accountApi = {
  requestEmailConfirmation(payload: { email: string }) {
    return apiRequest<{ status: 'ok' }>('/accounts/auth/email-confirmation/request', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  confirmEmail(payload: { token: string }) {
    return apiRequest<{ status: 'ok' }>('/accounts/auth/email-confirmation/confirm', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};


