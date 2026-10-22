export type UserRole = "admin" | "manager" | "staff";

export interface AuthUser {
  permissions: string[];
  userId: string;
  username: string;
  email: string;
  role: UserRole;
}

export interface LoginResponse {
  permissions: string[];
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: UserRole;
}

export interface VerifyResponse {
  permissions: string[];
  user_id: string;
  username: string;
  email: string;
  role: UserRole;
  valid: boolean;
}

export interface DashboardMetrics {
  total_skus: number;
  active_cameras: number;
  total_cameras: number;
  low_stock_alerts: number;
  reconciliation_confidence: number;
}

export interface StoreInfo {
  name: string;
  location: string;
  floor: string;
}

export type ZoneHealth = "healthy" | "low" | "offline" | "pending";

export interface ZoneDto {
  id: string;
  name: string;
  description: string | null;
  camera_id: string;
  camera_name: string;
  health: ZoneHealth;
  skus: number;
  confidence: number;
  aisle: string;
  label: string;
}

export type InventoryStatus =
  "unknown" | "adequate" | "low_stock" | "out_of_stock" | "detection_uncertain" | "camera_offline";

export interface InventoryDto {
  id: string;
  zone_id: string;
  product_id: string;
  sku: string | null;
  name: string | null;
  current_quantity: number;
  threshold: number | null;
  status: InventoryStatus;
  verified: boolean;
  pending_quantity: number | null;
  confidence: number;
  last_observation_time: string | null;
  observations_count: number;
  created_at?: string;
  updated_at: string | null;
}

export interface EventDto {
  id: string;
  zone: string | null;
  product: string | null;
  from: number | null;
  to: number | null;
  confidence: number | null;
  minAgo: number;
}

export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  pages: number;
}

export interface Paginated<T> {
  data: T[];
  pagination: Pagination;
}

export type AlertStatus =
  "OPEN" | "ACKNOWLEDGED" | "IN_PROGRESS" | "RESOLVED" | "DISMISSED" | "ESCALATED" | "EXPIRED";

export type AlertSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface AlertDto {
  id: string;
  zone_id: string;
  product_id: string;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  current_quantity: number;
  threshold_value: number | null;
  threshold_type: string | null;
  description: string | null;
  recommendation: string | null;
  confidence: number;
  impact_score: number;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  snoozed_until?: string | null;
  acknowledged_by_user: string | null;
  resolved_by_user: string | null;
}

export interface AlertActionResponse {
  status: string;
  alert_id: string | null;
  affected: number;
  message: string;
}

export interface AlertStats {
  total_alerts: number;
  open_alerts: number;
  critical: number;
  high: number;
  by_type: Record<string, number>;
}

export interface CameraDto {
  id: string;
  name: string;
  location: string;
  source_url: string | null;
  fps: number;
  offline_timeout_seconds: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CameraInput {
  name: string;
  location: string;
  source_url?: string | null;
  fps?: number;
  offline_timeout_seconds?: number;
  is_active?: boolean;
}

export interface InventoryHistoryDto {
  id: string;
  zone_id: string;
  product_id: string;
  previous_quantity: number;
  new_quantity: number;
  quantity_delta: number;
  change_type: string;
  confidence: number;
  source_system: string;
  reason: string | null;
  created_at: string;
  processed_at: string;
  actor_user_id: string | null;
  actor_system: string | null;
}

export interface AgentRunDto {
  id: string;
  agent_type: string;
  status: string;
  trigger_event: string | null;
  output_action: string | null;
  confidence_score: number | null;
  execution_time_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface AgentStats {
  period_hours: number;
  total_runs: number;
  completed: number;
  failed: number;
  success_rate: number;
  by_agent_type: Record<string, number>;
  average_confidence: number;
}

export interface BasicHealth {
  status: "ok" | "degraded";
  database: "connected" | "disconnected";
  redis: "connected" | "disconnected";
}

export type VideoJobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";

export interface VideoJobDto {
  id: string;
  owner_user_id: string;
  camera_id: string | null;
  source_kind: "upload" | "camera";
  status: VideoJobStatus;
  original_filename: string | null;
  source_size_bytes: number | null;
  sample_interval_seconds: number;
  max_frames: number;
  max_duration_seconds: number | null;
  confidence_threshold: number;
  image_size: number;
  tracking_enabled: boolean;
  preview_only: boolean;
  cancel_requested: boolean;
  stage: string;
  frames_processed: number;
  total_frames: number | null;
  source_fps: number | null;
  source_duration_ms: number | null;
  detection_instances: number;
  frames_with_detections: number;
  unique_tracked_objects: number | null;
  summary: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VideoDetectionDto {
  id: string;
  class_id: number;
  class_name: string;
  confidence: number;
  track_id: number | null;
  product_id: string | null;
  identity_status: "identified" | "category_only" | "unknown" | "ambiguous";
  identity_confidence: number;
  category: string | null;
  brand: string | null;
  variant: string | null;
  package_size: string | null;
  barcode: string | null;
  identity_evidence: Record<string, unknown> | null;
  bbox: { x1: number; y1: number; x2: number; y2: number };
  normalized_bbox: { x1: number; y1: number; x2: number; y2: number };
}

export interface VideoFrameDto {
  id: string;
  sequence: number;
  source_frame_index: number;
  timestamp_ms: number;
  width: number;
  height: number;
  inference_ms: number;
  detection_count: number;
  annotated_image_url: string | null;
  detections: VideoDetectionDto[];
}

export interface VideoJobListDto {
  data: VideoJobDto[];
  total: number;
  limit: number;
  offset: number;
}

export interface VideoFrameListDto {
  data: VideoFrameDto[];
  total: number;
  limit: number;
  offset: number;
}

export interface DetectionReviewDto {
  id: string;
  job_id: string;
  frame_id: string;
  timestamp_ms: number;
  class_name: string;
  confidence: number;
  track_id: number | null;
  identity_status: "category_only" | "unknown" | "ambiguous";
  identity_confidence: number;
  category: string | null;
  product_id: string | null;
  annotated_image_url: string | null;
}

export interface DetectionReviewListDto {
  data: DetectionReviewDto[];
  total: number;
  limit: number;
  offset: number;
}

export interface DetectorHealthDto {
  detector: string;
  configured: boolean;
  loaded: boolean;
  model_path: string | null;
  manifest_path: string | null;
  manifest_verified: boolean;
  requested_device: string;
  actual_device: string;
  cuda_available: boolean;
  class_count: number;
  input_size: number;
  error: string | null;
  identity_evidence: Record<string, unknown>;
}
