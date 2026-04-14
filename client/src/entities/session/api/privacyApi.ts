import { apiRequest } from '@/shared/api';

export const privacyApi = {
  deleteAccount() {
    return apiRequest<void>('/accounts/profile/privacy/delete', { method: 'POST' });
  },
};
