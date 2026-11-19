import { apiClient } from './api';

export interface IdentityStatus {
  provider: string;
  citizen_registration_enabled: boolean;
  supports_verification_sessions: boolean;
  collects_otp_on_server: boolean;
  collects_aadhaar_on_server: boolean;
  is_sandbox: boolean;
  is_production_ready: boolean;
  consent_version: string;
}

export interface IdentitySession {
  session_id: string;
  status: string;
  message?: string;
  expires_at?: string;
  user_action?: Record<string, unknown>;
  official_endpoints?: Record<string, string>;
  verified?: boolean;
}

export const identityService = {
  async getStatus(): Promise<IdentityStatus> {
    const res = await apiClient.get('/identity/status');
    return res.data.data;
  },

  async startSession(consentVersion: string): Promise<IdentitySession> {
    const res = await apiClient.post('/identity/sessions', {
      consent_accepted: true,
      consent_version: consentVersion,
    });
    return res.data.data;
  },

  async completeOfflineEkyc(
    sessionId: string,
    encryptedXml: string,
    shareCode: string
  ): Promise<IdentitySession> {
    const res = await apiClient.post(`/identity/sessions/${sessionId}/complete`, {
      encrypted_xml: encryptedXml,
      share_code: shareCode,
    });
    return res.data.data;
  },
};
