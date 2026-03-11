import { apiRequest } from '@/shared/api/http';

export type NotificationItem = {
  id: string;
  type: string;
  titleKey: string;
  params: Record<string, string>;
  isRead: boolean;
  actionUrl: string;
  entityRef: Record<string, string>;
  createdAt: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  limit: number;
  offset: number;
  total: number;
  hasNext: boolean;
  nextOffset: number | null;
};

export type UnreadCountResponse = {
  count: number;
};

export const notificationsApi = {
  list(params?: { limit?: number; offset?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.limit != null) searchParams.set('limit', String(params.limit));
    if (params?.offset != null) searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    return apiRequest<NotificationListResponse>(
      `/notifications/${query ? `?${query}` : ''}`
    );
  },

  getUnreadCount() {
    return apiRequest<UnreadCountResponse>('/notifications/unread-count/');
  },

  markRead(notificationId: string) {
    return apiRequest<{ ok: boolean }>(
      `/notifications/${notificationId}/read/`,
      { method: 'POST' }
    );
  },

  markAllRead() {
    return apiRequest<{ ok: boolean }>('/notifications/read-all/', {
      method: 'POST',
    });
  },

  delete(notificationId: string) {
    return apiRequest<{ ok: boolean }>(`/notifications/${notificationId}/`, {
      method: 'DELETE',
    });
  },

  clearAll() {
    return apiRequest<{ ok: boolean; deleted: number }>('/notifications/clear-all/', {
      method: 'DELETE',
    });
  },
};
