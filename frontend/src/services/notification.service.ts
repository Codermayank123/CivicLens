import { apiClient } from './api';
import { Notification } from '../types';

export const notificationService = {
  async getNotifications(limit = 50): Promise<{ notifications: Notification[]; unread_count: number }> {
    const res = await apiClient.get(`/notifications?limit=${limit}`);
    return res.data.data;
  },

  async markAsRead(notificationId?: string): Promise<boolean> {
    const res = await apiClient.post('/notifications/mark-read', null, {
      params: notificationId ? { notification_id: notificationId } : {},
    });
    return res.data.success;
  },
};
