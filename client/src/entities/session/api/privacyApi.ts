import { apiRequest } from '@/shared/api';

export type DataExportResponse = { status: 'requested' | string };

export const privacyApi = {
  requestDataExport() {
    return apiRequest<DataExportResponse>('/accounts/profile/privacy/export', { method: 'POST' });
  },

  deleteAccount() {
    return apiRequest<void>('/accounts/profile/privacy/delete', { method: 'POST' });
  },
};
