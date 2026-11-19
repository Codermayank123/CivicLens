import { apiClient } from './api';

export interface AddressDetails {
  formatted_address?: string;
  state?: string;
  district?: string;
  city?: string;
  locality?: string;
  pincode?: string;
}

export interface IndiaState { name: string; district_count: number; }
export interface IndiaDistrict { name: string; sub_district_count: number; }
export interface IndiaSubDistrict { name: string; }

export const locationService = {
  async reverseGeocode(latitude: number, longitude: number): Promise<AddressDetails> {
    const response = await apiClient.get('/locations/reverse-geocode', { params: { latitude, longitude } });
    return response.data.data;
  },
  async getStates(): Promise<IndiaState[]> {
    const response = await apiClient.get('/locations/india/states');
    return response.data.data;
  },
  async getDistricts(state: string): Promise<IndiaDistrict[]> {
    const response = await apiClient.get('/locations/india/districts', { params: { state } });
    return response.data.data;
  },
  async getSubDistricts(state: string, district: string): Promise<IndiaSubDistrict[]> {
    const response = await apiClient.get('/locations/india/sub-districts', { params: { state, district } });
    return response.data.data;
  },
};
