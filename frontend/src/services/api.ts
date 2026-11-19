import axios from 'axios';
import { API_V1_URL } from '../config/api';

export const apiClient = axios.create({
  baseURL: API_V1_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

const refreshClient = axios.create({
  baseURL: API_V1_URL,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('civiclens_access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
          const res = await refreshClient.post('/auth/refresh', {});
          if (res.data?.data?.access_token) {
            localStorage.setItem('civiclens_access_token', res.data.data.access_token);
            originalRequest.headers.Authorization = `Bearer ${res.data.data.access_token}`;
            return apiClient(originalRequest);
          }
      } catch {
        localStorage.removeItem('civiclens_access_token');
        localStorage.removeItem('civiclens_refresh_token');
        localStorage.removeItem('civiclens_user');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
