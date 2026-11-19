import { apiClient } from './api';
import { ImpactTracker, StateMetric } from '../types';

export interface PublicPlatformSummary {
  total_complaints: number;
  resolved_complaints: number;
  active_departments: number;
  resolution_rate: number;
  recent_resolutions: Array<{ public_id: string; title: string; category_name: string; status: string; updated_at: string }>;
}

export interface PublicHeatmapPoint {
  latitude: number;
  longitude: number;
  intensity: number;
  category: string;
  title: string;
  status: string;
  complaint_count: number;
}

export interface AccountabilityMetric {
  department_id: string;
  department_name: string;
  code: string;
  total_complaints: number;
  resolved_complaints: number;
  pending_complaints: number;
  resolution_rate: number;
}

export const publicService = {
  async getPlatformSummary(): Promise<PublicPlatformSummary> {
    const response = await apiClient.get('/public/platform');
    return response.data.data;
  },
  async getHeatmap(): Promise<PublicHeatmapPoint[]> {
    const response = await apiClient.get('/public/heatmap');
    return response.data.data;
  },
  async getAccountability(): Promise<AccountabilityMetric[]> {
    const response = await apiClient.get('/public/accountability');
    return response.data.data;
  },
  async getImpact(): Promise<ImpactTracker> {
    const response = await apiClient.get('/public/impact');
    return response.data.data;
  },
  async getIndia(): Promise<StateMetric[]> {
    const response = await apiClient.get('/public/india');
    return response.data.data;
  },
};
