/* ── TypeScript Types ─────────────────────────────────────────────────────── */

// ── Auth Types ──────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

// ── User Types ──────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  avatar_url?: string;
  roles: string[];
  department?: Department;
  department_id?: string;
  department_name?: string;
  parent_id?: string | null;
  city?: string;
  preferred_language: string;
  high_contrast_mode: boolean;
  reduced_motion: boolean;
  is_verified: boolean;
  email_verified?: boolean;
  mobile_verified?: boolean;
  identity_verified?: boolean;
  created_at: string;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description?: string;
  contact_email?: string;
  contact_phone?: string;
  head_name?: string;
  is_active: boolean;
}

// ── Complaint Types ─────────────────────────────────────────────────────────

export type ComplaintStatus =
  | 'submitted'
  | 'under_review'
  | 'verified'
  | 'rejected'
  | 'assigned'
  | 'in_progress'
  | 'resolved'
  | 'citizen_verification_pending'
  | 'reopened'
  | 'closed';

export type ComplaintPriority = 'low' | 'medium' | 'high' | 'critical';

export type MediaType = 'image' | 'video' | 'audio' | 'document';

export interface Complaint {
  id: string;
  public_id: string;
  title: string;
  description: string;
  category?: ComplaintCategory;
  category_name?: string;
  category_slug?: string;
  category_icon?: string;
  priority: ComplaintPriority;
  status: ComplaintStatus;
  latitude?: number;
  longitude?: number;
  address?: string;
  landmark?: string;
  state?: string;
  district?: string;
  city?: string;
  locality?: string;
  pincode?: string;
  original_language?: string;
  created_by?: string;
  creator?: UserSummary;
  creator_name?: string;
  assigned_department?: Department;
  assigned_department_id?: string;
  assigned_department_name?: string;
  assigned_staff?: UserSummary;
  assigned_staff_id?: string;
  assigned_staff_name?: string;
  ai_category?: string;
  ai_confidence?: number;
  ai_is_mock?: boolean;
  requires_human_review?: boolean;
  ai_outcome?: 'accepted' | 'human_review' | 'rejected' | string;
  ai_reason?: string;
  ai_model_version?: string;
  ai_verified_at?: string;
  ai_verification?: {
    outcome?: string;
    reason?: string;
    model_version?: string;
    category_match?: boolean;
    category_match_confidence?: number;
    severity?: string;
    confidence?: number;
    suspicious?: boolean;
    suspicious_reasons?: string[];
    limitations?: string[];
    duplicate_risk?: number;
    spam_check?: {
      is_spam?: boolean;
      spam_score?: number;
      reasons?: string[];
      is_mock?: boolean;
      check_unavailable?: boolean;
    };
    moderation?: {
      status?: string;
      action?: string;
      reason?: string;
      reviewed_by?: string;
      reviewed_at?: string;
    };
    evidence?: Array<{ media_type?: string; category?: string; confidence?: number; is_relevant?: boolean; suspicious?: boolean; requires_human_review?: boolean; message?: string; manipulation_indicators?: string[] }>;
  };
  media?: ComplaintMedia[];
  comments?: ComplaintComment[];
  status_history?: ComplaintStatusHistory[];
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  closed_at?: string;
  resolution_deadline?: string;
  resolution_submitted_at?: string;
  resolution_notes?: string;
  is_overdue?: boolean;
  escalation_level?: number;
}

export interface ComplaintCategory {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  color?: string;
  department?: Department;
  department_id?: string;
  department_name?: string;
  is_active: boolean;
}

export interface ComplaintMedia {
  id: string;
  media_type?: MediaType;
  media_url?: string;
  file_url?: string;
  file_name?: string;
  file_size?: number;
  mime_type?: string;
  is_resolution_proof?: boolean;
  is_resolution_evidence?: boolean;
  evidence_stage?: 'before' | 'after' | 'supporting' | string;
  caption?: string;
  created_at?: string;
}

export interface ComplaintFilters {
  status?: string;
  priority?: string;
  category_id?: string;
  department_id?: string;
  search?: string;
  page?: number;
  per_page?: number;
  start_date?: string;
  end_date?: string;
}

export interface ComplaintCreateRequest {
  title: string;
  description: string;
  category_id: string;
  priority: ComplaintPriority;
  latitude?: number;
  longitude?: number;
  address?: string;
  landmark?: string;
  state?: string;
  district?: string;
  city?: string;
  locality?: string;
  pincode?: string;
  language?: string;
}

export interface ComplaintStatusHistory {
  id: string;
  old_status?: string;
  new_status: string;
  from_status?: ComplaintStatus;
  to_status?: ComplaintStatus;
  changed_by?: any;
  changed_by_name?: string;
  notes?: string;
  reason?: string;
  created_at: string;
}

export interface ComplaintComment {
  id: string;
  user?: UserSummary;
  author_name?: string;
  author_role?: string;
  comment?: string;
  content?: string;
  is_internal?: boolean;
  created_at: string;
}

export interface ComplaintVerification {
  id: string;
  action: 'approved' | 'rejected';
  reason?: string;
  evidence_url?: string;
  user: UserSummary;
  created_at: string;
}

export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
  avatar_url?: string;
}

// ── Notification Types ──────────────────────────────────────────────────────

export type NotificationType =
  | 'complaint_submitted'
  | 'complaint_assigned'
  | 'status_changed'
  | 'complaint_resolved'
  | 'complaint_reopened'
  | 'verification_required'
  | 'complaint_rejected'
  | 'system';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  complaint_id?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

// ── Analytics Types ─────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_complaints: number;
  open_complaints: number;
  resolved_complaints: number;
  reopened_complaints: number;
  avg_resolution_hours: number;
  complaints_today: number;
  complaints_this_week: number;
  complaints_this_month: number;
}

export interface CategoryStat {
  category: string;
  slug: string;
  count: number;
  color: string;
}

export interface TrendData {
  date: string;
  submitted: number;
  resolved: number;
  reopened: number;
}

export interface DepartmentStat {
  department: string;
  code: string;
  total: number;
  resolved: number;
  avg_resolution_hours: number;
}

export interface StateMetric {
  state: string;
  total_complaints: number;
  resolved_complaints: number;
  pending_complaints: number;
  in_progress_complaints: number;
  overdue_complaints: number;
  resolution_percentage: number;
  districts: Array<Record<string, string | number>>;
}

export interface ImpactTracker {
  total_complaints: number;
  resolved_complaints: number;
  pending_complaints: number;
  in_progress_complaints: number;
  overdue_complaints: number;
  average_resolution_hours: number;
  resolution_percentage: number;
  on_time_resolution_percentage: number;
  citizen_satisfaction_percentage: number;
  pending_human_reviews: number;
  monthly_trends: Array<{ date: string; reported: number; resolved: number }>;
  department_metrics: Array<{ department_id: string; department_name: string; total_assigned: number; resolved: number; in_progress: number; avg_resolution_hours?: number; overdue: number; on_time_resolution_rate: number }>;
  state_metrics: StateMetric[];
}

// ── API Response Types ──────────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: PaginationMeta;
  request_id: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
  request_id: string;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

// ── Offline Sync Types ──────────────────────────────────────────────────────

export type SyncStatus = 'pending' | 'uploading' | 'synced' | 'failed' | 'requires_review';

export interface OfflineComplaint {
  client_id: string;
  data: ComplaintCreateRequest;
  images: File[];
  sync_status: SyncStatus;
  error_message?: string;
  attempts: number;
  created_at: string;
}

// ── Map Types ───────────────────────────────────────────────────────────────

export interface MapComplaint {
  id: string;
  public_id: string;
  title: string;
  category_slug: string;
  status: ComplaintStatus;
  priority: ComplaintPriority;
  latitude: number;
  longitude: number;
  color: string;
}

export interface HotspotData {
  latitude: number;
  longitude: number;
  intensity: number;
  complaint_count: number;
}

// ── AI Types ────────────────────────────────────────────────────────────────

export interface AIClassificationResult {
  category: string;
  confidence?: number | null;
  confidence_status?: 'available' | 'unavailable';
  is_mock: boolean;
  top_predictions: Array<{ category: string; confidence: number }>;
}

export interface AITextClassificationResult {
  category: string;
  confidence?: number | null;
  confidence_status?: 'available' | 'unavailable';
  keywords: string[];
  urgency: string;
  suggested_priority: string;
  is_mock: boolean;
}

export interface DuplicateCandidate {
  complaint_id: string;
  similarity_score: number;
  text_similarity: number;
  geo_distance_km: number;
  category_match: boolean;
}
