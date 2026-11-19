import { apiClient } from './api';
import { ImpactTracker, StateMetric } from '../types';

export interface OverviewStats {
  total_complaints: number;
  pending_complaints: number;
  in_progress_complaints: number;
  resolved_complaints: number;
  avg_resolution_time_hours: number;
  citizen_satisfaction_percentage: number;
  active_field_staff: number;
  duplicate_prevented_count: number;
  status_distribution: Array<{ status: string; count: number; percentage: number }>;
  category_distribution: Array<{
    category_id: string;
    category_name: string;
    count: number;
    resolved_count: number;
    sla_compliance_rate: number;
  }>;
  department_metrics: Array<{
    department_id: string;
    department_name: string;
    total_assigned: number;
    resolved: number;
    in_progress: number;
    avg_resolution_hours: number;
    satisfaction_rate: number;
  }>;
  trends_last_30_days: Array<{ date: string; reported: number; resolved: number }>;
}

export interface HeatmapPoint {
  latitude: number;
  longitude: number;
  intensity: number;
  category: string;
  title: string;
  status: string;
}

export const analyticsService = {
  async getOverview(): Promise<OverviewStats> {
    const res = await apiClient.get('/analytics/overview');
    return res.data.data;
  },

  async getHeatmap(): Promise<HeatmapPoint[]> {
    const res = await apiClient.get('/analytics/heatmap');
    return res.data.data;
  },
  async getImpact(params: Record<string, string | undefined> = {}): Promise<ImpactTracker> {
    const res = await apiClient.get('/analytics/impact', { params });
    return res.data.data;
  },
  async getIndia(state?: string): Promise<StateMetric[]> {
    const res = await apiClient.get('/analytics/india', { params: { state } });
    return res.data.data;
  },
  async getEscalations(status?: string) {
    const res = await apiClient.get('/analytics/escalations', { params: { status } });
    return res.data.data;
  },
};
