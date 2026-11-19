import { apiClient } from './api';
import { Department, ComplaintCategory } from '../types';

export const departmentService = {
  async getDepartments(): Promise<Department[]> {
    const res = await apiClient.get('/departments');
    return res.data.data;
  },

  async getCategories(): Promise<ComplaintCategory[]> {
    const res = await apiClient.get('/categories');
    return res.data.data;
  },

  async getStaff(departmentId?: string) {
    const res = await apiClient.get('/users/staff', {
      params: departmentId ? { department_id: departmentId } : {},
    });
    return res.data.data;
  },
};
