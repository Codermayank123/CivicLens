import { apiClient } from './api';

export interface RewardProfile { points: number; tier: string; next_tier?: string; points_to_next_tier: number; badges: string[]; transactions: Array<{ id: string; points: number; action_type: string; created_at: string }> }
export interface LeaderboardItem { rank: number; user_id: string; full_name: string; city?: string; points: number; tier: string; badges: string[] }
export interface ChallengeItem { id: string; title: string; description: string; challenge_type: string; city?: string; points: number; start_date: string; end_date: string; participant_count: number; joined: boolean }
export interface CertificateItem { id: string; title: string; issued_for: string; certificate_hash: string; issued_at: string }
export interface RewardAward { award: string; period: string; recipient?: LeaderboardItem }

export const rewardsService = {
  async getProfile(): Promise<RewardProfile> { const res = await apiClient.get('/rewards/me'); return res.data.data; },
  async getLeaderboard(scope: 'monthly' | 'city' | 'annual'): Promise<LeaderboardItem[]> { const res = await apiClient.get('/rewards/leaderboard', { params: { scope } }); return res.data.data; },
  async getChallenges(): Promise<ChallengeItem[]> { const res = await apiClient.get('/rewards/challenges'); return res.data.data; },
  async joinChallenge(id: string): Promise<ChallengeItem> { const res = await apiClient.post(`/rewards/challenges/${id}/join`); return res.data.data; },
  async getCertificates(): Promise<CertificateItem[]> { const res = await apiClient.get('/rewards/certificates'); return res.data.data; },
  async getAwards(): Promise<RewardAward[]> { const res = await apiClient.get('/rewards/awards'); return res.data.data; },
};
