import { apiRequest } from '@/shared/api';

export type EmailConfirmationRequestResult = {
  status: 'ok';
  email_sent: boolean;
  already_verified: boolean;
};

export const accountApi = {
  requestEmailConfirmation(payload: { email: string }) {
    return apiRequest<EmailConfirmationRequestResult>('/accounts/auth/email-confirmation/request', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  confirmEmail(payload: { token: string }) {
    return apiRequest<{ status: 'ok'; already_confirmed?: boolean }>(
      '/accounts/auth/email-confirmation/confirm',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },
};


