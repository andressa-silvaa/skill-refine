import { apiRequest, apiRequestBlob } from '@/shared/api';

export type DataExportResponse = { status: 'requested' | string };

export const privacyApi = {
  downloadDataExport() {
    return apiRequestBlob('/accounts/profile/privacy/export', { method: 'GET' });
  },

  requestDataExport() {
    return apiRequest<DataExportResponse>('/accounts/profile/privacy/export', { method: 'POST' });
  },

  deleteAccount() {
    return apiRequest<void>('/accounts/profile/privacy/delete', { method: 'POST' });
  },
};
