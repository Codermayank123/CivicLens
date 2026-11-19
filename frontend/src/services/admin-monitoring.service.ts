import { apiClient } from './api';

export interface RewardsAdminOverview {
  citizens_with_points: number;
  total_points_awarded: number;
  verified_contribution_count: number;
  transaction_count: number;
}

export interface DeliverySummary {
  total: number;
  by_channel: Record<string, number>;
  by_status: Record<string, number>;
  recent_failures: Array<{ notification_id?: string; channel?: string; error?: string }>;
}

export const adminMonitoringService = {
  async getRewards(): Promise<RewardsAdminOverview> {
    const response = await apiClient.get('/rewards/admin/overview');
    return response.data.data;
  },
  async getDeliverySummary(): Promise<DeliverySummary> {
    const response = await apiClient.get('/notifications/admin/delivery-summary');
    return response.data.data;
  },
};
