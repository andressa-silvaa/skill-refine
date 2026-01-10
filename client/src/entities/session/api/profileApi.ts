import { apiRequest } from '@/shared/api';

import type { SessionUser } from '../model/types';

export type UploadAvatarResponse = {
  avatar_storage_key?: string;
  avatar_url?: string | null;
  avatarStorageKey?: string;
  avatarUrl?: string | null;
};

export type UpdateProfileResponse = { user: SessionUser };

export type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
  confirm_new_password: string;
};

export type PreferencesResponse = {
  email_notifications_enabled?: boolean;
  emailNotificationsEnabled?: boolean;
  language?: string;
  theme?: 'light' | 'dark' | string;
  accent_color?: string;
  accentColor?: string;
};

export const profileApi = {
  uploadAvatar(file: File) {
    const body = new FormData();
    body.append('avatar', file);
    return apiRequest<UploadAvatarResponse>('/accounts/profile/avatar', { method: 'POST', body });
  },

  updateProfile(payload: { full_name: string }) {
    return apiRequest<UpdateProfileResponse>('/accounts/profile', { method: 'PATCH', body: JSON.stringify(payload) });
  },

  changePassword(payload: ChangePasswordPayload) {
    return apiRequest<{ status: 'ok' }>('/accounts/auth/password/change', { method: 'POST', body: JSON.stringify(payload) });
  },

  getPreferences() {
    return apiRequest<PreferencesResponse>('/accounts/profile/preferences', { method: 'GET' });
  },

  updatePreferences(
    payload: Partial<{ email_notifications_enabled: boolean; language: string; theme: 'light' | 'dark'; accent_color: string }>
  ) {
    return apiRequest<PreferencesResponse>('/accounts/profile/preferences', { method: 'PATCH', body: JSON.stringify(payload) });
  },
};

