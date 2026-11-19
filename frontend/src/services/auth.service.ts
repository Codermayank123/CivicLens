import { apiClient } from './api';
import { LoginRequest, RegisterRequest, AuthResponse, UserProfile } from '../types';

export const authService = {
  async requestRegistrationOtp(payload: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    verification_method: 'email' | 'sms';
  }): Promise<{ verification_session_id: string; verification_token: string; expires_in: number; resend_after: number; verification_method: 'email' | 'sms' }> {
    const res = await apiClient.post('/auth/register/request-otp', payload);
    return res.data.data;
  },

  async verifyRegistrationOtp(payload: { verification_session_id: string; verification_token: string; code: string }) {
    const res = await apiClient.post('/auth/register/verify-otp', payload);
    return res.data.data;
  },

  async completeRegistration(payload: { verification_session_id: string; verification_token: string }): Promise<AuthResponse> {
    const res = await apiClient.post('/auth/register', payload);
    const data = res.data.data;
    localStorage.setItem('civiclens_access_token', data.access_token);
    localStorage.removeItem('civiclens_refresh_token');
    localStorage.setItem('civiclens_user', JSON.stringify(data.user));
    return data;
  },

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const res = await apiClient.post('/auth/login', credentials);
    const data = res.data.data;
    localStorage.setItem('civiclens_access_token', data.access_token);
    localStorage.removeItem('civiclens_refresh_token');
    localStorage.setItem('civiclens_user', JSON.stringify(data.user));
    return data;
  },

  async register(payload: RegisterRequest): Promise<AuthResponse> {
    const res = await apiClient.post('/auth/register', payload);
    const data = res.data.data;
    localStorage.setItem('civiclens_access_token', data.access_token);
    localStorage.removeItem('civiclens_refresh_token');
    localStorage.setItem('civiclens_user', JSON.stringify(data.user));
    return data;
  },

  async getMe(): Promise<UserProfile> {
    const res = await apiClient.get('/auth/me');
    const user = res.data.data;
    localStorage.setItem('civiclens_user', JSON.stringify(user));
    return user;
  },

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post('/auth/verify-email', { token });
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('civiclens_access_token');
      localStorage.removeItem('civiclens_refresh_token');
      localStorage.removeItem('civiclens_user');
    }
  },

  getStoredUser(): UserProfile | null {
    const str = localStorage.getItem('civiclens_user');
    if (!str) return null;
    try {
      return JSON.parse(str);
    } catch {
      return null;
    }
  },
};
