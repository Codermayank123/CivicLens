import { apiClient } from './api';
import { Complaint, ComplaintFilters } from '../types';

export interface ComplaintCreateInput {
  title: string;
  description: string;
  category_id: string;
  priority?: string;
  latitude?: number;
  longitude?: number;
  address?: string;
  landmark?: string;
  media_urls?: string[];
  media_metadata?: { file_name: string; file_size: number; mime_type: string }[];
  voice_description_url?: string;
}

export interface UploadedMedia {
  url: string;
  file_name: string;
  file_size: number;
  mime_type: string;
}

export const complaintService = {
  async getComplaints(filters: ComplaintFilters = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.category_id) params.append('category_id', filters.category_id);
    if (filters.department_id) params.append('department_id', filters.department_id);
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', String(filters.page));
    if (filters.per_page) params.append('per_page', String(filters.per_page));
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);

    const res = await apiClient.get(`/complaints?${params.toString()}`);
    return {
      items: res.data.data as Complaint[],
      meta: res.data.meta,
    };
  },

  async getMyComplaints(page = 1, per_page = 20) {
    const res = await apiClient.get(`/complaints/my?page=${page}&per_page=${per_page}`);
    return {
      items: res.data.data as Complaint[],
      meta: res.data.meta,
    };
  },

  async getAssignedToMe(page = 1, per_page = 20) {
    const res = await apiClient.get(`/complaints/assigned-to-me?page=${page}&per_page=${per_page}`);
    return {
      items: res.data.data as Complaint[],
      meta: res.data.meta,
    };
  },

  async getNearby(latitude: number, longitude: number, radiusKm = 2) {
    const res = await apiClient.get('/complaints/nearby', { params: { latitude, longitude, radius_km: radiusKm } });
    return res.data.data as Complaint[];
  },

  async support(complaintId: string) {
    const res = await apiClient.post(`/complaints/${complaintId}/support`);
    return res.data.data;
  },

  async getById(idOrPublicId: string): Promise<Complaint> {
    const res = await apiClient.get(`/complaints/${idOrPublicId}`);
    return res.data.data;
  },

  async create(data: ComplaintCreateInput): Promise<Complaint> {
    const res = await apiClient.post('/complaints', data);
    return res.data.data;
  },

  async uploadMedia(file: File): Promise<UploadedMedia> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return {
      url: res.data.data.url,
      file_name: res.data.data.filename,
      file_size: res.data.data.file_size,
      mime_type: res.data.data.mime_type,
    };
  },

  async updateStatus(
    complaintId: string,
    status: string,
    notes?: string,
    resolutionMediaUrls: string[] = [],
    resolutionEvidence: Array<{ media_url: string; stage: 'before' | 'after'; caption?: string }> = []
  ): Promise<Complaint> {
    const res = await apiClient.patch(`/complaints/${complaintId}/status`, {
      status,
      notes,
      resolution_media_urls: resolutionMediaUrls,
      resolution_evidence: resolutionEvidence,
    });
    return res.data.data;
  },

  async assign(
    complaintId: string,
    departmentId?: string,
    staffId?: string,
    notes?: string
  ): Promise<Complaint> {
    const res = await apiClient.patch(`/complaints/${complaintId}/assign`, {
      department_id: departmentId,
      staff_id: staffId,
      notes,
    });
    return res.data.data;
  },

  async verifyResolution(
    complaintId: string,
    action: 'approved' | 'rejected',
    feedback?: string,
    rating?: number
  ): Promise<Complaint> {
    const res = await apiClient.post(`/complaints/${complaintId}/verify`, {
      action,
      feedback,
      rating,
    });
    return res.data.data;
  },

  async reviewAIModeration(
    complaintId: string,
    action: 'approve' | 'reject' | 'request_information' | 'confirmed_spam' | 'not_spam' | 'escalated',
    reason: string
  ): Promise<Complaint> {
    const res = await apiClient.post(`/complaints/${complaintId}/ai-moderation/review`, { action, reason });
    return res.data.data;
  },

  async addComment(complaintId: string, comment: string, isInternal = false) {
    const res = await apiClient.post(`/complaints/${complaintId}/comments`, {
      comment,
      is_internal: isInternal,
    });
    return res.data.data;
  },

  async checkDuplicates(
    title: string,
    description: string,
    categoryId: string,
    lat?: number,
    lng?: number
  ) {
    const res = await apiClient.post('/complaints/duplicates/check', null, {
      params: {
        title,
        description,
        category_id: categoryId,
        latitude: lat,
        longitude: lng,
      },
    });
    return res.data.data;
  },

  async suggestAI(text: string) {
    const res = await apiClient.post('/ai/suggest', { text });
    return res.data.data;
  },

  async getAIReviewQueue(page = 1, perPage = 50) {
    const res = await apiClient.get('/complaints/ai-review-queue', { params: { page, per_page: perPage } });
    return { items: res.data.data as Complaint[], meta: res.data.meta };
  },
};
